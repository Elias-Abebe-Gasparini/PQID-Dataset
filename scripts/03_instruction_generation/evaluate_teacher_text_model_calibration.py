"""
evaluate_teacher_text_model_calibration.py
------------------------------------------
Evaluate matched teacher-text model-comparison outputs using role-aware
automatic metrics and simple paired statistical tests.

This is intended for the Stage H-Cal notebook blocks, where the main question is
whether a cheaper teacher-text model remains acceptable for a specific
pedagogical role such as `validation_diagnosis` or `mutation_robustness`.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_FILE = ROOT / "data/processed/pqid_2026_enriched_github_circuits.jsonl"
DEFAULT_COMPARISON_DIR = ROOT / "data/processed/teacher_text_model_comparison"
DEFAULT_OUTPUT_FILE = DEFAULT_COMPARISON_DIR / "teacher_text_model_calibration_evaluation.json"

EPSILON = 1e-12
BOOTSTRAP_ROUNDS = 5000
BOOTSTRAP_SEED = 42

IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_+-]*")

VALIDATION_PROMPT_PATTERNS = [
    r"\bdiagnos(?:e|is)\b",
    r"\breview this\b",
    r"\bshould not be treated\b",
    r"\bnot be treated as\b",
    r"\bnot be trusted\b",
    r"\bincomplete\b",
]
VALIDATION_OUTPUT_PATTERNS = [
    r"\bmissing\b",
    r"\bincomplete\b",
    r"\bunsafe\b",
    r"\bnot\b.{0,24}\btrust",
    r"\bcontext\b",
    r"\bassum",
    r"\bverify\b|\bvalidate\b|\bcheck\b",
]
MUTATION_PROMPT_PATTERNS = [
    r"\bmutation\b",
    r"\brobust",
    r"\bbug\b",
    r"\bcompare\b",
    r"\bcanonical\b",
    r"\brestore\b",
]
MUTATION_OUTPUT_PATTERNS = [
    r"\bmutation\b",
    r"\bcanonical\b",
    r"\bsemantic\b",
    r"\bdiffer",
    r"\brestore\b|\brepair\b",
    r"\bbug\b|\bincorrect\b|\bdrift\b",
]
VALIDATION_CAUTION_PATTERNS = [
    r"\bshould not\b",
    r"\bnot\b.{0,24}\btrust",
    r"\bmissing\b",
    r"\bunclear\b",
    r"\bassum",
    r"\bdepends\b",
    r"\bverify\b|\bvalidate\b|\bcheck\b",
]
VALIDATION_ACTION_PATTERNS = [
    r"\brepair plan\b",
    r"\bverify\b",
    r"\bvalidate\b",
    r"\bcheck\b",
    r"\bconfirm\b",
    r"\btest\b",
    r"\badd\b",
    r"\bguard\b",
]
MUTATION_CAUTION_PATTERNS = [
    r"\bmutation\b",
    r"\bbug(?:-stress)?\b",
    r"\brisk\b",
    r"\bsemantic\b",
    r"\bdrift\b",
    r"\bperturb",
    r"\bdistort\b|\balter\b|\bchange\b",
    r"\binterference\b|\bdistribution\b|\bbehavior\b",
]
MUTATION_ACTION_PATTERNS = [
    r"\brepair\b|\brestore\b|\brevert\b",
    r"\bremove\b|\bundo\b|\bcorrect\b",
    r"\bcompare\b|\bvalidate\b|\bcheck\b|\btest\b",
    r"\bcanonical\b",
    r"\bunmutated\b|\boriginal\b",
    r"\bmeasure\b|\bbenchmark\b",
]
OVERCLAIM_PATTERNS = [
    r"\bfully trustworthy\b",
    r"\bsafe as is\b",
    r"\bcorrect as written\b",
    r"\bready to use\b",
    r"\bcomplete and reliable\b",
]

IDENTIFIER_STOPWORDS = {
    "self",
    "cls",
    "return",
    "true",
    "false",
    "none",
    "quantumcircuit",
    "quantumregister",
    "classicalregister",
    "qiskit",
    "circuit",
    "gate",
    "qubit",
    "qubits",
    "clbit",
    "clbits",
    "register",
    "registers",
    "param",
    "params",
    "data",
    "index",
    "value",
    "values",
    "result",
    "results",
    "input",
    "output",
    "method",
    "class",
    "definition",
    "build",
    "define",
    "label",
    "repeat",
    "inverse",
    "circuiterror",
    "qiskiterror",
    "append",
    "compose",
    "control",
    "target",
    "num",
    "int",
    "float",
    "bool",
    "list",
    "dict",
    "tuple",
    "range",
    "len",
    "for",
    "while",
    "and",
    "or",
    "not",
    "with",
    "from",
    "import",
    "main",
    "python",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", type=Path, default=DEFAULT_SOURCE_FILE)
    parser.add_argument("--comparison-dir", type=Path, default=DEFAULT_COMPARISON_DIR)
    parser.add_argument("--file-prefix", required=True)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--manifest-file", type=Path, default=None)
    parser.add_argument("--study-label", required=True)
    parser.add_argument("--role", default="")
    parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT_FILE)
    return parser.parse_args()


def safe_model_name(model_name: str) -> str:
    return model_name.replace(".", "p")


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def mean(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)


def exact_sign_test(wins: int, losses: int) -> float:
    non_ties = wins + losses
    if non_ties == 0:
        return 1.0
    lower_tail = 0.0
    for k in range(0, min(wins, losses) + 1):
        lower_tail += math.comb(non_ties, k)
    lower_tail /= 2**non_ties
    return min(1.0, 2.0 * lower_tail)


def bootstrap_mean_diff(values_a: list[float], values_b: list[float]) -> tuple[float | None, float | None]:
    if not values_a or len(values_a) != len(values_b):
        return None, None
    rng = random.Random(BOOTSTRAP_SEED)
    diffs = [a - b for a, b in zip(values_a, values_b)]
    samples = []
    n = len(diffs)
    for _ in range(BOOTSTRAP_ROUNDS):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        samples.append(sum(sample) / n)
    samples.sort()
    low_idx = int(0.025 * len(samples))
    high_idx = int(0.975 * len(samples)) - 1
    return samples[low_idx], samples[max(high_idx, 0)]


def match_any(text: str, patterns: list[str]) -> int:
    lowered = text.lower()
    return 1 if any(re.search(pattern, lowered) for pattern in patterns) else 0


def cue_ratio(text: str, patterns: list[str]) -> float:
    lowered = text.lower()
    if not patterns:
        return 0.0
    matches = sum(1 for pattern in patterns if re.search(pattern, lowered))
    return matches / len(patterns)


def extract_source_identifiers(source_row: dict) -> list[str]:
    meta = source_row.get("metadata", {})
    corpus = " ".join(
        [
            str(source_row.get("output", "") or ""),
            str(meta.get("file_path", "") or ""),
            str(meta.get("original_url", "") or ""),
        ]
    ).lower()
    counts = Counter()
    for token in IDENTIFIER_RE.findall(corpus):
        if len(token) < 3:
            continue
        if token in IDENTIFIER_STOPWORDS:
            continue
        if token.isdigit():
            continue
        counts[token] += 1
    salient = sorted(counts, key=lambda key: (-counts[key], -len(key), key))
    return salient[:12]


def source_specificity_score(prompt: str, answer: str, source_row: dict) -> float | None:
    salient = extract_source_identifiers(source_row)
    if not salient:
        return None
    combined_tokens = {token.lower() for token in WORD_RE.findall((prompt + " " + answer).lower())}
    matched = sum(1 for token in salient if token in combined_tokens)
    return matched / len(salient)


def evaluate_row(row: dict, source_row: dict) -> dict[str, Any]:
    meta = row.get("metadata", {})
    role = meta.get("seed_role", "")
    prompt = str(row.get("input", "")).strip()
    answer = str(row.get("output", "")).strip()

    if role == "mutation_robustness":
        prompt_patterns = MUTATION_PROMPT_PATTERNS
        output_patterns = MUTATION_OUTPUT_PATTERNS
        caution_patterns = MUTATION_CAUTION_PATTERNS
        action_patterns = MUTATION_ACTION_PATTERNS
    else:
        prompt_patterns = VALIDATION_PROMPT_PATTERNS
        output_patterns = VALIDATION_OUTPUT_PATTERNS
        caution_patterns = VALIDATION_CAUTION_PATTERNS
        action_patterns = VALIDATION_ACTION_PATTERNS

    prompt_role_fidelity = float(match_any(prompt, prompt_patterns))
    output_role_fidelity = float(match_any(answer, output_patterns))
    caution_score = cue_ratio(answer, caution_patterns)
    actionability_score = cue_ratio(answer, action_patterns)
    specificity_score = source_specificity_score(prompt, answer, source_row)
    overclaim_clean = 0.0 if match_any(answer, OVERCLAIM_PATTERNS) else 1.0

    component_values = [
        prompt_role_fidelity,
        output_role_fidelity,
        caution_score,
        actionability_score,
        overclaim_clean,
    ]
    if specificity_score is not None:
        component_values.append(specificity_score)

    overall_score = mean(component_values) or 0.0
    caution_threshold = 0.25
    actionability_threshold = 0.25
    strict_pass = float(
        prompt_role_fidelity == 1.0
        and output_role_fidelity == 1.0
        and caution_score >= caution_threshold
        and actionability_score >= actionability_threshold
        and overclaim_clean == 1.0
    )

    return {
        "circuit_hash": meta.get("circuit_hash"),
        "seed_role": role,
        "prompt_words": len(prompt.split()),
        "output_words": len(answer.split()),
        "prompt_role_fidelity": prompt_role_fidelity,
        "output_role_fidelity": output_role_fidelity,
        "caution_score": caution_score,
        "actionability_score": actionability_score,
        "source_specificity_score": specificity_score,
        "overclaim_clean": overclaim_clean,
        "overall_score": overall_score,
        "strict_pass": strict_pass,
    }


def summarize_model(rows: list[dict], source_map: dict[str, dict], expected_rows: int | None) -> dict[str, Any]:
    opener_counts = Counter()
    norm_counts = Counter()
    analyses = []
    role_counts = Counter()

    for row in rows:
        prompt = str(row.get("input", "")).strip()
        opener = " ".join(prompt.split()[:2]).lower() if prompt else "<empty>"
        opener_counts[opener] += 1
        norm_counts[normalize_text(prompt)] += 1
        role_counts[row.get("metadata", {}).get("seed_role", "<missing>")] += 1
        circuit_hash = row.get("metadata", {}).get("circuit_hash")
        source_row = source_map.get(str(circuit_hash))
        if source_row is None:
            continue
        analyses.append(evaluate_row(row, source_row))

    def metric_list(name: str) -> list[float]:
        return [float(item[name]) for item in analyses if item.get(name) is not None]

    repeated_openers = {key: value for key, value in opener_counts.items() if value > 1}
    exact_dupes = sum(1 for value in norm_counts.values() if value > 1)

    expected = expected_rows if expected_rows is not None else len(rows)
    completion_rate = (len(rows) / expected) if expected else None

    return {
        "rows": len(rows),
        "expected_rows": expected_rows,
        "completion_rate": completion_rate,
        "exact_normalized_duplicates": exact_dupes,
        "repeated_openers": repeated_openers,
        "role_distribution": dict(role_counts),
        "avg_input_words": mean(metric_list("prompt_words")),
        "avg_output_words": mean(metric_list("output_words")),
        "prompt_role_fidelity_mean": mean(metric_list("prompt_role_fidelity")),
        "output_role_fidelity_mean": mean(metric_list("output_role_fidelity")),
        "caution_score_mean": mean(metric_list("caution_score")),
        "actionability_score_mean": mean(metric_list("actionability_score")),
        "source_specificity_score_mean": mean(metric_list("source_specificity_score")),
        "overclaim_clean_rate": mean(metric_list("overclaim_clean")),
        "overall_score_mean": mean(metric_list("overall_score")),
        "strict_pass_rate": mean(metric_list("strict_pass")),
        "analyses": analyses,
    }


def pairwise_stats(model_a: str, model_b: str, indexed: dict[str, dict]) -> dict[str, Any]:
    keys = sorted(set(indexed[model_a]) & set(indexed[model_b]))
    metrics = [
        "overall_score",
        "strict_pass",
        "source_specificity_score",
        "caution_score",
        "actionability_score",
    ]
    metric_reports = {}
    for metric in metrics:
        wins = losses = ties = 0
        a_values: list[float] = []
        b_values: list[float] = []
        for key in keys:
            left = indexed[model_a][key].get(metric)
            right = indexed[model_b][key].get(metric)
            if left is None or right is None:
                continue
            left_f = float(left)
            right_f = float(right)
            a_values.append(left_f)
            b_values.append(right_f)
            diff = left_f - right_f
            if diff > EPSILON:
                wins += 1
            elif diff < -EPSILON:
                losses += 1
            else:
                ties += 1
        mean_diff = mean([a - b for a, b in zip(a_values, b_values)]) if a_values else None
        ci_low, ci_high = bootstrap_mean_diff(a_values, b_values)
        metric_reports[metric] = {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "mean_diff": mean_diff,
            "p_value_sign_test": exact_sign_test(wins, losses),
            "bootstrap_ci_low": ci_low,
            "bootstrap_ci_high": ci_high,
            "matched_rows": len(a_values),
        }
    return {"models": [model_a, model_b], "matched_keys": len(keys), "metrics": metric_reports}


def fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def main() -> None:
    args = parse_args()

    source_map = {
        str(row.get("metadata", {}).get("circuit_hash")): row
        for row in load_jsonl(args.source_file)
        if row.get("metadata", {}).get("circuit_hash")
    }

    expected_rows = None
    if args.manifest_file and args.manifest_file.exists():
        manifest_rows = load_jsonl(args.manifest_file)
        if args.role:
            manifest_rows = [row for row in manifest_rows if row.get("seed_role") == args.role]
        expected_rows = len(manifest_rows)

    rows_by_model: dict[str, list[dict]] = {}
    indexed: dict[str, dict[str, dict[str, Any]]] = {}
    summaries: dict[str, Any] = {}

    for model_name in args.models:
        output_file = args.comparison_dir / f"{args.file_prefix}_{safe_model_name(model_name)}.jsonl"
        if not output_file.exists():
            raise FileNotFoundError(f"missing comparison output: {output_file}")
        rows = load_jsonl(output_file)
        if args.role:
            rows = [row for row in rows if row.get("metadata", {}).get("seed_role") == args.role]
        rows_by_model[model_name] = rows
        summaries[model_name] = summarize_model(rows, source_map, expected_rows)
        indexed[model_name] = {
            f"{item['circuit_hash']}::{item['seed_role']}": item
            for item in summaries[model_name]["analyses"]
        }

    pairwise = []
    models = list(args.models)
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            pairwise.append(pairwise_stats(models[i], models[j], indexed))

    report = {
        "study_label": args.study_label,
        "role": args.role,
        "file_prefix": args.file_prefix,
        "models": models,
        "expected_rows": expected_rows,
        "summaries": summaries,
        "pairwise": pairwise,
    }

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("teacher-text model calibration report:", args.output_file)
    print("study label:", args.study_label)
    if args.role:
        print("role:", args.role)
    print()
    for model_name in models:
        summary = summaries[model_name]
        print(f"Model {model_name}")
        print(f"  rows: {summary['rows']}")
        if summary["expected_rows"] is not None:
            print(f"  completion_rate: {fmt(summary['completion_rate'])}")
        print(f"  avg_input_words: {fmt(summary['avg_input_words'])}")
        print(f"  avg_output_words: {fmt(summary['avg_output_words'])}")
        print(f"  source_specificity: {fmt(summary['source_specificity_score_mean'])}")
        print(f"  caution_score: {fmt(summary['caution_score_mean'])}")
        print(f"  actionability_score: {fmt(summary['actionability_score_mean'])}")
        print(f"  overclaim_clean_rate: {fmt(summary['overclaim_clean_rate'])}")
        print(f"  overall_score: {fmt(summary['overall_score_mean'])}")
        print(f"  strict_pass: {fmt(summary['strict_pass_rate'])}")
        print(f"  max_opener_share: {fmt(max(summary['repeated_openers'].values()) / summary['rows'] if summary['rows'] and summary['repeated_openers'] else (1.0 / summary['rows'] if summary['rows'] else None))}")
        print()

    for pair in pairwise:
        left, right = pair["models"]
        print(f"Pairwise matched comparison: {left} vs {right}")
        print("  matched_rows:", pair["matched_keys"])
        for metric, stats in pair["metrics"].items():
            print(
                "  "
                f"{metric}: wins={stats['wins']} losses={stats['losses']} ties={stats['ties']} "
                f"mean_diff={fmt(stats['mean_diff'])} "
                f"p={fmt(stats['p_value_sign_test'])} "
                f"ci=[{fmt(stats['bootstrap_ci_low'])}, {fmt(stats['bootstrap_ci_high'])}]"
            )
        print()


if __name__ == "__main__":
    main()
