import argparse
import json
import math
import re
from collections import Counter
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPARISON_DIR = ROOT / "data/processed/seed_temperature_comparison"
DEFAULT_OUTPUT_FILE = DEFAULT_COMPARISON_DIR / "seed_temperature_empirical_evaluation_v1.json"

EPSILON = 1e-12

GENERATION_ROLES = {"gold_generation", "broad_generation"}
REPAIR_ROLES = {"repair_or_explanation"}

REPAIR_CUE_RE = re.compile(r"\b(repair|complete|fix|finish|correct)\b")
INCOMPLETE_CUE_RE = re.compile(
    r"\b(missing|incomplete|unfinished|too minimal|not ready|skeletal|bare|too bare|minimal|absent|not benchmark-ready|not benchmark ready)\b"
)
MEASUREMENT_RE = re.compile(r"\b(measure|measurement|measurements|classical bit|classical bits|counts|readout)\b")
PARAM_TOKEN_RE = re.compile(r"\b(theta|phi|lambda|lam|alpha|beta|gamma)\b")
QUBIT_COUNT_RE = re.compile(r"\b(\d+)\s*-\s*qubit\b|\b(\d+)\s+qubit\b")
OPENQASM_RE = re.compile(r"\bopenqasm(?:\s*3)?\b")

TARGET_TAG_PATTERNS = {
    "bell": [r"\bbell\b", r"bell pair", r"bell-state"],
    "ghz": [r"\bghz\b"],
    "rxx": [r"\brxx\b", r"xx interaction", r"xx-style"],
    "ryy": [r"\bryy\b", r"yy interaction", r"yy-style"],
    "rzz": [r"\brzz\b", r"zz interaction", r"zz-style"],
    "rzx": [r"\brzx\b", r"zx interaction", r"zx-style"],
    "qft": [r"\bqft\b", r"quantum fourier"],
    "grover": [r"\bgrover\b"],
    "oracle": [r"\boracle\b"],
}

PROMPT_GATE_PATTERNS = {
    "h": [r"\bhadamard\b", r"(?<![a-z0-9_])h(?![a-z0-9_])"],
    "cx": [r"\bcnot\b", r"\bcx\b", r"controlled-not", r"controlled not"],
    "cz": [r"\bcz\b", r"controlled-z", r"controlled z"],
    "cp": [r"\bcp\b", r"controlled-phase", r"controlled phase", r"cphase"],
    "rx": [r"\brx\b", r"rotation around x"],
    "ry": [r"\bry\b", r"rotation around y"],
    "rz": [r"\brz\b", r"rotation around z"],
    "crx": [r"\bcrx\b", r"controlled-rx", r"controlled rx"],
    "cry": [r"\bcry\b", r"controlled-ry", r"controlled ry"],
    "crz": [r"\bcrz\b", r"controlled-rz", r"controlled rz"],
    "rxx": [r"\brxx\b", r"xx interaction", r"xx-style"],
    "ryy": [r"\bryy\b", r"yy interaction", r"yy-style"],
    "rzz": [r"\brzz\b", r"zz interaction", r"zz-style"],
    "rzx": [r"\brzx\b", r"zx interaction", r"zx-style"],
    "s": [r"\bapply s\b", r"\bapplies s\b", r"\bs to both\b", r"\bs on qubit\b"],
    "sdg": [r"\bsdg\b", r"s-dagger", r"s†"],
    "t": [r"\bt gate\b", r"\bapply t\b", r"\bapplies t\b", r"\bh-t-h\b"],
    "swap": [r"\bswap\b"],
    "x": [r"\bapply x\b", r"\bapplies x\b", r"\bx on qubit\b", r"pauli-x", r"\bx followed by h\b"],
    "z": [r"\bapply z\b", r"\bapplies z\b", r"\bz on qubit\b", r"pauli-z"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate temperature-calibration prompt batches empirically.")
    parser.add_argument(
        "--comparison-dir",
        type=Path,
        default=DEFAULT_COMPARISON_DIR,
        help="Directory containing temperature-comparison JSONL outputs.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help="Where to write the structured evaluation report JSON.",
    )
    parser.add_argument(
        "--study",
        action="append",
        default=[],
        help="Optional study spec in the form 'label|name|0.1,0.2,0.3'. If omitted, the built-in Stage C/Stage D studies are used.",
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def temp_suffix(temp: float) -> str:
    return f"{temp:.1f}".replace(".", "p")


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def detect_patterns(text: str, pattern_map: dict[str, list[str]]) -> set[str]:
    lowered = text.lower()
    found = set()
    for key, patterns in pattern_map.items():
        for pattern in patterns:
            if re.search(pattern, lowered):
                found.add(key)
                break
    return found


def canonical_source_gates(meta: dict) -> set[str]:
    gate_types = meta.get("gate_types") or {}
    if isinstance(gate_types, dict):
        raw = {str(key).lower() for key in gate_types}
    elif isinstance(gate_types, list):
        raw = {str(key).lower() for key in gate_types}
    else:
        raw = set()
    return {gate for gate in raw if gate in PROMPT_GATE_PATTERNS}


def extract_parameter_tokens(source_code: str, meta: dict) -> set[str]:
    tokens = set(PARAM_TOKEN_RE.findall(source_code.lower()))
    if meta.get("is_parameterized") or (meta.get("num_parameters") or 0) > 0:
        if not tokens:
            tokens.add("<generic>")
    return tokens


def extract_qubit_mentions(text: str) -> set[int]:
    mentions = set()
    for match in QUBIT_COUNT_RE.finditer(text.lower()):
        value = match.group(1) or match.group(2)
        if value is not None:
            mentions.add(int(value))
    return mentions


def exact_sign_test(wins: int, losses: int) -> float:
    non_ties = wins + losses
    if non_ties == 0:
        return 1.0
    lower_tail = 0.0
    for k in range(0, min(wins, losses) + 1):
        lower_tail += math.comb(non_ties, k)
    lower_tail /= 2**non_ties
    return min(1.0, 2.0 * lower_tail)


def mean(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)


def format_float(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def parse_study_spec(spec: str) -> tuple[str, str, list[float]]:
    parts = spec.split("|")
    if len(parts) != 3:
        raise ValueError(
            f"Invalid --study specification '{spec}'. Expected format: label|name|0.1,0.2,0.3"
        )
    label, name, temp_block = parts
    temps = [float(item.strip()) for item in temp_block.split(",") if item.strip()]
    if not temps:
        raise ValueError(f"Invalid --study specification '{spec}': no temperatures found.")
    return label.strip(), name.strip(), temps


def opener_stats(rows: list[dict]) -> dict:
    opener_counts = Counter()
    normalized_counts = Counter()
    prompt_lengths = []
    for row in rows:
        text = row.get("input", "").strip()
        opener = " ".join(text.split()[:2]).lower() if text else "<empty>"
        opener_counts[opener] += 1
        normalized_counts[normalize_text(text)] += 1
        prompt_lengths.append(len(text.split()))
    repeated_openers = {key: value for key, value in opener_counts.items() if value > 1}
    duplicate_count = sum(1 for value in normalized_counts.values() if value > 1)
    max_share = 0.0
    if rows and opener_counts:
        max_share = max(opener_counts.values()) / len(rows)
    return {
        "exact_normalized_duplicates": duplicate_count,
        "repeated_openers": repeated_openers,
        "unique_openers": len(opener_counts),
        "max_opener_share": max_share,
        "avg_prompt_tokens": mean(prompt_lengths),
    }


def analyze_row(row: dict) -> dict:
    meta = row.get("metadata", {})
    prompt = row.get("input", "")
    prompt_lower = prompt.lower()
    source_code = row.get("output", "")
    source_lower = source_code.lower()
    role = meta.get("seed_role")
    num_qubits = meta.get("num_qubits")
    measured_qubit_count = meta.get("measured_qubit_count")

    prompt_gates = detect_patterns(prompt, PROMPT_GATE_PATTERNS)
    source_gates = canonical_source_gates(meta)
    prompt_tags = detect_patterns(prompt, TARGET_TAG_PATTERNS)
    source_tags = detect_patterns(source_code, TARGET_TAG_PATTERNS)

    qubit_alignment = None
    qubit_options = set()
    if isinstance(num_qubits, int) and num_qubits > 0:
        qubit_options.add(num_qubits)
    if isinstance(measured_qubit_count, int) and measured_qubit_count > 0:
        qubit_options.add(measured_qubit_count)
    if qubit_options:
        qubit_alignment = 1.0 if (extract_qubit_mentions(prompt) & qubit_options) else 0.0

    source_has_measurement = bool(meta.get("has_measurement")) or (meta.get("measurement_count") or 0) > 0
    measurement_alignment = None
    if source_has_measurement:
        measurement_alignment = 1.0 if MEASUREMENT_RE.search(prompt_lower) else 0.0

    parameter_tokens = extract_parameter_tokens(source_code, meta)
    parameter_alignment = None
    if parameter_tokens:
        prompt_parameter_tokens = set(PARAM_TOKEN_RE.findall(prompt_lower))
        prompt_has_generic_parameter = bool(
            prompt_parameter_tokens
            or re.search(r"\b(parameter|parameterized|symbolic angle)\b", prompt_lower)
        )
        if "<generic>" in parameter_tokens:
            parameter_alignment = 1.0 if prompt_has_generic_parameter else 0.0
        else:
            parameter_alignment = 1.0 if (parameter_tokens & prompt_parameter_tokens or prompt_has_generic_parameter) else 0.0

    source_has_global_phase = "global_phase" in source_lower or "global phase" in source_lower
    global_phase_alignment = None
    if source_has_global_phase:
        global_phase_alignment = 1.0 if "global phase" in prompt_lower else 0.0

    original_prompt = str(meta.get("original_prompt") or "")
    openqasm_alignment = None
    if OPENQASM_RE.search(original_prompt.lower()):
        openqasm_alignment = 1.0 if OPENQASM_RE.search(prompt_lower) else 0.0

    role_fidelity = 1.0
    repair_cue = 1.0 if REPAIR_CUE_RE.search(prompt_lower) else 0.0
    incomplete_cue_flag = 1.0 if INCOMPLETE_CUE_RE.search(prompt_lower) else 0.0
    incomplete_cue = incomplete_cue_flag if role in REPAIR_ROLES else None
    if role in GENERATION_ROLES:
        role_fidelity = 0.0 if (repair_cue or incomplete_cue_flag) else 1.0
    elif role in REPAIR_ROLES:
        role_fidelity = 1.0 if repair_cue else 0.0

    gate_coverage = None
    target_alignment = None
    unsupported_additions = []
    if role in GENERATION_ROLES:
        if source_tags:
            target_alignment = 1.0 if (source_tags & prompt_tags) else 0.0
        if source_gates:
            gate_coverage = len(source_gates & prompt_gates) / len(source_gates)
            unsupported_additions = sorted(prompt_gates - source_gates)
        else:
            gate_coverage = 1.0
    else:
        if source_tags:
            unsupported_additions = sorted(prompt_tags - source_tags)
            target_alignment = 1.0 if (source_tags & prompt_tags) else 0.0
        else:
            unsupported_additions = []
            target_alignment = 1.0

    effective_gate_coverage = gate_coverage
    if role in GENERATION_ROLES and gate_coverage is not None and target_alignment == 1.0:
        effective_gate_coverage = 1.0

    missing_components = []
    component_values = []

    def add_component(name: str, value: float | None) -> None:
        if value is None:
            return
        component_values.append(value)
        if value < 1.0 - EPSILON:
            missing_components.append(name)

    add_component("role_fidelity", role_fidelity)
    add_component("qubit_alignment", qubit_alignment)
    if role in GENERATION_ROLES:
        add_component("measurement_alignment", measurement_alignment)
        add_component("parameter_alignment", parameter_alignment)
        add_component("global_phase_alignment", global_phase_alignment)
        add_component("openqasm_alignment", openqasm_alignment)
        add_component("target_alignment", target_alignment)
        add_component("gate_coverage", effective_gate_coverage)
        add_component("unsupported_clean", 1.0 if not unsupported_additions else 0.0)
    else:
        add_component("incompleteness_cue", incomplete_cue)
        add_component("target_alignment", target_alignment)
        add_component("unsupported_clean", 1.0 if not unsupported_additions else 0.0)

    overall_score = mean(component_values) or 0.0
    strict_pass = 1.0 if not missing_components else 0.0

    return {
        "circuit_hash": meta.get("circuit_hash"),
        "seed_role": role,
        "prompt": prompt,
        "prompt_gates": sorted(prompt_gates),
        "source_gates": sorted(source_gates),
        "prompt_tags": sorted(prompt_tags),
        "source_tags": sorted(source_tags),
        "role_fidelity": role_fidelity,
        "qubit_alignment": qubit_alignment,
        "measurement_alignment": measurement_alignment,
        "parameter_alignment": parameter_alignment,
        "global_phase_alignment": global_phase_alignment,
        "openqasm_alignment": openqasm_alignment,
        "gate_coverage": effective_gate_coverage,
        "target_alignment": target_alignment,
        "incompleteness_cue": incomplete_cue,
        "unsupported_additions": unsupported_additions,
        "unsupported_addition_count": len(unsupported_additions),
        "overall_score": overall_score,
        "strict_pass": strict_pass,
        "missing_components": missing_components,
    }


def summarize_temperature(rows: list[dict]) -> tuple[dict, dict]:
    analyses = [analyze_row(row) for row in rows]
    lexical = opener_stats(rows)
    summary = {
        "rows": len(rows),
        "overall_score_mean": mean([item["overall_score"] for item in analyses]),
        "strict_pass_rate": mean([item["strict_pass"] for item in analyses]),
        "role_fidelity_rate": mean([item["role_fidelity"] for item in analyses]),
        "qubit_alignment_rate": mean([item["qubit_alignment"] for item in analyses if item["qubit_alignment"] is not None]),
        "measurement_alignment_rate": mean(
            [item["measurement_alignment"] for item in analyses if item["measurement_alignment"] is not None]
        ),
        "parameter_alignment_rate": mean(
            [item["parameter_alignment"] for item in analyses if item["parameter_alignment"] is not None]
        ),
        "global_phase_alignment_rate": mean(
            [item["global_phase_alignment"] for item in analyses if item["global_phase_alignment"] is not None]
        ),
        "openqasm_alignment_rate": mean(
            [item["openqasm_alignment"] for item in analyses if item["openqasm_alignment"] is not None]
        ),
        "gate_coverage_mean": mean([item["gate_coverage"] for item in analyses if item["gate_coverage"] is not None]),
        "target_alignment_rate": mean([item["target_alignment"] for item in analyses if item["target_alignment"] is not None]),
        "incompleteness_cue_rate": mean(
            [item["incompleteness_cue"] for item in analyses if item["incompleteness_cue"] is not None]
        ),
        "unsupported_addition_mean": mean([item["unsupported_addition_count"] for item in analyses]),
        "drift_flag_rate": mean([1.0 if item["unsupported_addition_count"] > 0 else 0.0 for item in analyses]),
        **lexical,
    }
    flagged = []
    for item in analyses:
        if item["unsupported_addition_count"] > 0 or item["strict_pass"] < 1.0:
            flagged.append(
                {
                    "circuit_hash": item["circuit_hash"],
                    "seed_role": item["seed_role"],
                    "unsupported_additions": item["unsupported_additions"],
                    "missing_components": item["missing_components"],
                    "prompt": item["prompt"],
                }
            )
    return summary, {"analyses": analyses, "flagged": flagged}


def pairwise_sign_tests(indexed_analyses: dict[float, dict[tuple[str, str], dict]]) -> list[dict]:
    results = []
    temps = sorted(indexed_analyses)
    common_keys = sorted(set.intersection(*(set(mapping.keys()) for mapping in indexed_analyses.values())))
    for left_temp, right_temp in combinations(temps, 2):
        left = indexed_analyses[left_temp]
        right = indexed_analyses[right_temp]
        for metric, higher_is_better in [
            ("overall_score", True),
            ("strict_pass", True),
            ("unsupported_addition_count", False),
        ]:
            wins = losses = ties = 0
            diffs = []
            for key in common_keys:
                left_value = left[key][metric]
                right_value = right[key][metric]
                if left_value is None or right_value is None:
                    continue
                diff = (right_value - left_value) if higher_is_better else (left_value - right_value)
                diffs.append(diff)
                if diff > EPSILON:
                    wins += 1
                elif diff < -EPSILON:
                    losses += 1
                else:
                    ties += 1
            results.append(
                {
                    "comparison": f"{right_temp} vs {left_temp}",
                    "metric": metric,
                    "wins_for_right": wins,
                    "losses_for_right": losses,
                    "ties": ties,
                    "mean_signed_difference": mean(diffs),
                    "exact_sign_pvalue": exact_sign_test(wins, losses),
                }
            )
    return results


def evaluate_study(name: str, label: str, temps: list[float], comparison_dir: Path) -> dict:
    rows_by_temp = {}
    missing_files = []
    for temp in temps:
        output_file = comparison_dir / f"seed_drafts_quality_aware_{label}_temp_{temp_suffix(temp)}.jsonl"
        if not output_file.exists():
            missing_files.append(str(output_file))
            continue
        rows_by_temp[temp] = load_rows(output_file)

    if not rows_by_temp:
        return {"name": name, "label": label, "temps": temps, "missing_files": missing_files, "available": False}

    summaries = {}
    details = {}
    indexed_analyses = {}
    for temp, rows in rows_by_temp.items():
        summary, detail = summarize_temperature(rows)
        summaries[str(temp)] = summary
        details[str(temp)] = detail
        indexed_analyses[temp] = {}
        for analysis in detail["analyses"]:
            indexed_analyses[temp][(analysis["circuit_hash"], analysis["seed_role"])] = analysis

    common_keys = sorted(set.intersection(*(set(mapping.keys()) for mapping in indexed_analyses.values())))
    pairwise = pairwise_sign_tests(indexed_analyses)
    return {
        "name": name,
        "label": label,
        "temps": temps,
        "missing_files": missing_files,
        "available": True,
        "matched_rows": len(common_keys),
        "temperature_summaries": summaries,
        "pairwise_sign_tests": pairwise,
        "flagged_examples": {temp: details[temp]["flagged"][:3] for temp in details},
    }


def print_study_report(study: dict) -> None:
    print(f"\n{study['name']}")
    print("=" * len(study["name"]))
    if not study.get("available"):
        print("No comparison outputs available.")
        for path in study.get("missing_files", []):
            print("  missing:", path)
        return

    print("matched rows:", study["matched_rows"])
    print("\nPer-temperature summary")
    for temp in study["temps"]:
        temp_key = str(temp)
        summary = study["temperature_summaries"].get(temp_key)
        if summary is None:
            continue
        print(f"\nTemperature {temp}")
        print(f"  rows                    : {summary['rows']}")
        print(f"  overall_score_mean      : {format_float(summary['overall_score_mean'])}")
        print(f"  strict_pass_rate        : {format_float(summary['strict_pass_rate'])}")
        print(f"  role_fidelity_rate      : {format_float(summary['role_fidelity_rate'])}")
        print(f"  qubit_alignment_rate    : {format_float(summary['qubit_alignment_rate'])}")
        print(f"  measurement_alignment   : {format_float(summary['measurement_alignment_rate'])}")
        print(f"  parameter_alignment     : {format_float(summary['parameter_alignment_rate'])}")
        print(f"  global_phase_alignment  : {format_float(summary['global_phase_alignment_rate'])}")
        print(f"  openqasm_alignment      : {format_float(summary['openqasm_alignment_rate'])}")
        print(f"  gate_coverage_mean      : {format_float(summary['gate_coverage_mean'])}")
        print(f"  target_alignment_rate   : {format_float(summary['target_alignment_rate'])}")
        print(f"  incompleteness_cue_rate : {format_float(summary['incompleteness_cue_rate'])}")
        print(f"  unsupported_add_mean    : {format_float(summary['unsupported_addition_mean'])}")
        print(f"  drift_flag_rate         : {format_float(summary['drift_flag_rate'])}")
        print(f"  exact duplicates        : {summary['exact_normalized_duplicates']}")
        print(f"  unique_openers          : {summary['unique_openers']}")
        print(f"  max_opener_share        : {format_float(summary['max_opener_share'])}")
        print(f"  avg_prompt_tokens       : {format_float(summary['avg_prompt_tokens'])}")
        repeated_openers = summary["repeated_openers"]
        if repeated_openers:
            print("  repeated_openers        :", repeated_openers)

    print("\nPairwise exact sign tests")
    for result in study["pairwise_sign_tests"]:
        print(
            "  "
            f"{result['comparison']} | {result['metric']} | "
            f"wins={result['wins_for_right']} losses={result['losses_for_right']} ties={result['ties']} | "
            f"mean_diff={format_float(result['mean_signed_difference'])} | "
            f"p={format_float(result['exact_sign_pvalue'])}"
        )

    print("\nFlagged examples (up to 3 per temperature)")
    for temp in study["temps"]:
        temp_key = str(temp)
        examples = study["flagged_examples"].get(temp_key, [])
        print(f"  temperature {temp}: {len(examples)} shown")
        for example in examples:
            print(
                "   - "
                f"{example['seed_role']} | {example['circuit_hash']} | "
                f"missing={example['missing_components']} | unsupported={example['unsupported_additions']}"
            )


def main() -> None:
    args = parse_args()
    args.output_file.parent.mkdir(parents=True, exist_ok=True)

    if args.study:
        study_specs = [parse_study_spec(spec) for spec in args.study]
    else:
        study_specs = [
            ("tempstudy_v2", "Stage C — Broad Temperature Screen", [0.1, 0.3, 0.5]),
            ("tempstudy_v3", "Stage D — Low-Temperature Refinement", [0.1, 0.2, 0.3]),
        ]

    report = {
        "report_version": "seed_temperature_empirical_evaluation_v1",
        "comparison_dir": str(args.comparison_dir),
        "studies": [
            evaluate_study(name, label, temps, args.comparison_dir)
            for label, name, temps in study_specs
        ],
    }

    with args.output_file.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("empirical temperature evaluation written:", args.output_file)
    for study in report["studies"]:
        print_study_report(study)


if __name__ == "__main__":
    main()
