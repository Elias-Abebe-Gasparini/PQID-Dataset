"""
preflight_teacher_text_production.py
------------------------------------
Additive integrity gate for the Stage H teacher-text production branch.

This script does not modify the dataset. It verifies that the role-specific
teacher-text production manifests are internally consistent with:

- the parent teacher-text manifest
- the enriched source corpus
- the calibrated Stage H production policy

It is intended to reduce spending risk before the large teacher-text batch run.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = ROOT / "PQID/data/processed"
DEFAULT_PARENT_MANIFEST = PROCESSED_DIR / "seed_role_manifest_v1_teacher_text.jsonl"
DEFAULT_VALIDATION_MANIFEST = PROCESSED_DIR / "seed_role_manifest_v1_teacher_text_validation_diagnosis.jsonl"
DEFAULT_MUTATION_MANIFEST = PROCESSED_DIR / "seed_role_manifest_v1_teacher_text_mutation_robustness.jsonl"
DEFAULT_SOURCE_FILE = PROCESSED_DIR / "pqid_2026_enriched_github_circuits.jsonl"
DEFAULT_VALIDATION_REPORT = PROCESSED_DIR / "teacher_text_model_comparison/teacher_text_model_calibration_validation_eval.json"
DEFAULT_MUTATION_REPORT = PROCESSED_DIR / "teacher_text_model_comparison/teacher_text_model_calibration_mutation_eval.json"
DEFAULT_OUTPUT_REPORT = PROCESSED_DIR / "teacher_text_production_preflight_report.json"
DEFAULT_EXISTING_OUTPUT = PROCESSED_DIR / "seed_drafts_quality_aware_teacher_text_v1.jsonl"

FROZEN_POLICY = {
    "validation_diagnosis": {"model": "gpt-5.4", "temperature": 0.1},
    "mutation_robustness": {"model": "gpt-5.4-mini", "temperature": 0.1},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-manifest", default=str(DEFAULT_PARENT_MANIFEST))
    parser.add_argument("--validation-manifest", default=str(DEFAULT_VALIDATION_MANIFEST))
    parser.add_argument("--mutation-manifest", default=str(DEFAULT_MUTATION_MANIFEST))
    parser.add_argument("--source-file", default=str(DEFAULT_SOURCE_FILE))
    parser.add_argument("--validation-report", default=str(DEFAULT_VALIDATION_REPORT))
    parser.add_argument("--mutation-report", default=str(DEFAULT_MUTATION_REPORT))
    parser.add_argument("--existing-output-file", default=str(DEFAULT_EXISTING_OUTPUT))
    parser.add_argument("--output-report", default=str(DEFAULT_OUTPUT_REPORT))
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_manifest(rows: list[dict[str, Any]], expected_role: str, source_hashes: set[str]) -> dict[str, Any]:
    role_counts = Counter()
    target_mode_counts = Counter()
    teacher_model_defaults = Counter()
    circuit_hash_counts = Counter()
    missing_source_hashes: list[str] = []

    for row in rows:
        role = row.get("seed_role", "<missing>")
        role_counts[role] += 1
        target_mode_counts[row.get("target_supervision_mode", "<missing>")] += 1
        teacher_model_defaults[row.get("generation_defaults", {}).get("teacher_model", "<missing>")] += 1
        circuit_hash = row.get("source_record", {}).get("circuit_hash")
        if circuit_hash:
            circuit_hash_counts[circuit_hash] += 1
            if circuit_hash not in source_hashes:
                missing_source_hashes.append(circuit_hash)

    duplicate_hashes = [h for h, c in circuit_hash_counts.items() if c > 1]
    role_impure = any(role != expected_role for role in role_counts)
    target_mode_impure = any(mode != "teacher_text" for mode in target_mode_counts)

    return {
        "rows": len(rows),
        "expected_role": expected_role,
        "role_counts": dict(role_counts),
        "target_mode_counts": dict(target_mode_counts),
        "teacher_model_defaults": dict(teacher_model_defaults),
        "unique_circuit_hashes": len(circuit_hash_counts),
        "duplicate_circuit_hash_count": len(duplicate_hashes),
        "duplicate_circuit_hash_examples": duplicate_hashes[:10],
        "missing_source_count": len(missing_source_hashes),
        "missing_source_examples": missing_source_hashes[:10],
        "role_impure": role_impure,
        "target_mode_impure": target_mode_impure,
        "circuit_hash_set": set(circuit_hash_counts.keys()),
    }


def analyze_existing_output(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "rows": 0, "role_counts": {}, "model_role_counts": {}}
    role_counts = Counter()
    model_role_counts = Counter()
    rows = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            meta = row.get("metadata", {})
            role = meta.get("seed_role", "<missing>")
            model = meta.get("generation_model", "<missing>")
            rows += 1
            role_counts[role] += 1
            model_role_counts[f"{role} | {model}"] += 1
    return {
        "exists": True,
        "rows": rows,
        "role_counts": dict(role_counts),
        "model_role_counts": dict(model_role_counts),
    }


def extract_calibration_decision(report: dict[str, Any], chosen_model: str) -> dict[str, Any]:
    summaries = report.get("summaries", {})
    if not summaries:
        return {
            "chosen_model": chosen_model,
            "report_present": False,
            "overall_winner": None,
            "strict_winner": None,
            "chosen_matches_overall_winner": None,
            "chosen_matches_strict_winner": None,
        }

    overall_winner = max(
        summaries.items(),
        key=lambda kv: kv[1].get("overall_score_mean", float("-inf")),
    )[0]
    strict_winner = max(
        summaries.items(),
        key=lambda kv: kv[1].get("strict_pass_rate", float("-inf")),
    )[0]

    return {
        "chosen_model": chosen_model,
        "report_present": True,
        "overall_winner": overall_winner,
        "strict_winner": strict_winner,
        "chosen_matches_overall_winner": chosen_model == overall_winner,
        "chosen_matches_strict_winner": chosen_model == strict_winner,
        "chosen_summary": summaries.get(chosen_model, {}),
    }


def main() -> None:
    args = parse_args()
    parent_manifest = Path(args.parent_manifest)
    validation_manifest = Path(args.validation_manifest)
    mutation_manifest = Path(args.mutation_manifest)
    source_file = Path(args.source_file)
    validation_report_file = Path(args.validation_report)
    mutation_report_file = Path(args.mutation_report)
    existing_output_file = Path(args.existing_output_file)
    output_report = Path(args.output_report)

    parent_rows = load_jsonl(parent_manifest)
    validation_rows = load_jsonl(validation_manifest)
    mutation_rows = load_jsonl(mutation_manifest)
    source_rows = load_jsonl(source_file)
    validation_report = load_json(validation_report_file)
    mutation_report = load_json(mutation_report_file)
    existing_output = analyze_existing_output(existing_output_file)

    source_hashes = {
        row.get("metadata", {}).get("circuit_hash")
        for row in source_rows
        if row.get("metadata", {}).get("circuit_hash")
    }

    parent_hashes = {
        row.get("source_record", {}).get("circuit_hash")
        for row in parent_rows
        if row.get("source_record", {}).get("circuit_hash")
    }

    validation_analysis = analyze_manifest(validation_rows, "validation_diagnosis", source_hashes)
    mutation_analysis = analyze_manifest(mutation_rows, "mutation_robustness", source_hashes)

    validation_hashes = validation_analysis.pop("circuit_hash_set")
    mutation_hashes = mutation_analysis.pop("circuit_hash_set")
    overlap_hashes = sorted(validation_hashes & mutation_hashes)
    combined_hashes = validation_hashes | mutation_hashes

    validation_decision = extract_calibration_decision(
        validation_report, FROZEN_POLICY["validation_diagnosis"]["model"]
    )
    mutation_decision = extract_calibration_decision(
        mutation_report, FROZEN_POLICY["mutation_robustness"]["model"]
    )

    blocking_issues: list[str] = []
    warnings: list[str] = []

    if len(validation_rows) + len(mutation_rows) != len(parent_rows):
        blocking_issues.append("split manifest row counts do not sum to parent teacher-text manifest rows")
    if combined_hashes != parent_hashes:
        blocking_issues.append("split manifest circuit_hash coverage does not exactly match the parent teacher-text manifest")
    if overlap_hashes:
        blocking_issues.append("validation and mutation manifests overlap on circuit_hash values")
    if validation_analysis["duplicate_circuit_hash_count"] > 0:
        blocking_issues.append("validation_diagnosis manifest contains duplicate circuit_hash values")
    if mutation_analysis["duplicate_circuit_hash_count"] > 0:
        blocking_issues.append("mutation_robustness manifest contains duplicate circuit_hash values")
    if validation_analysis["missing_source_count"] > 0 or mutation_analysis["missing_source_count"] > 0:
        blocking_issues.append("one or more teacher-text manifest rows are missing from the enriched source corpus")
    if validation_analysis["role_impure"] or mutation_analysis["role_impure"]:
        blocking_issues.append("one or more role-specific manifests contain rows from the wrong seed_role")
    if validation_analysis["target_mode_impure"] or mutation_analysis["target_mode_impure"]:
        blocking_issues.append("one or more role-specific manifests contain non-teacher_text supervision rows")

    if not validation_decision["chosen_matches_overall_winner"]:
        warnings.append("validation_diagnosis frozen policy does not match the calibration overall-score winner")
    if not mutation_decision["chosen_matches_overall_winner"]:
        warnings.append("mutation_robustness frozen policy does not match the calibration overall-score winner")

    validation_default_models = set(validation_analysis["teacher_model_defaults"])
    mutation_default_models = set(mutation_analysis["teacher_model_defaults"])
    if validation_default_models != {FROZEN_POLICY["validation_diagnosis"]["model"]}:
        warnings.append(
            "validation_diagnosis manifest generation_defaults.teacher_model does not match the frozen Stage H policy"
        )
    if mutation_default_models != {FROZEN_POLICY["mutation_robustness"]["model"]}:
        warnings.append(
            "mutation_robustness manifest generation_defaults.teacher_model does not match the frozen Stage H policy"
        )

    report = {
        "frozen_policy": FROZEN_POLICY,
        "parent_manifest_rows": len(parent_rows),
        "source_rows": len(source_rows),
        "validation_manifest": validation_analysis,
        "mutation_manifest": mutation_analysis,
        "split_checks": {
            "validation_rows_plus_mutation_rows": len(validation_rows) + len(mutation_rows),
            "parent_rows": len(parent_rows),
            "overlap_count": len(overlap_hashes),
            "overlap_examples": overlap_hashes[:10],
            "combined_hash_count": len(combined_hashes),
            "parent_hash_count": len(parent_hashes),
            "exact_hash_coverage_match": combined_hashes == parent_hashes,
        },
        "calibration_policy_checks": {
            "validation_diagnosis": validation_decision,
            "mutation_robustness": mutation_decision,
        },
        "existing_teacher_text_output": existing_output,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "recommended_to_proceed": len(blocking_issues) == 0,
    }

    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("teacher-text production preflight report:", output_report)
    print("\nfrozen Stage H policy")
    for role, cfg in FROZEN_POLICY.items():
        print(f"  {role}: model={cfg['model']} temperature={cfg['temperature']}")

    print("\nmanifest integrity summary")
    print(
        "  parent teacher-text rows:",
        f"{len(parent_rows):,}",
    )
    print(
        "  split teacher-text rows:",
        f"{(len(validation_rows) + len(mutation_rows)):,}",
    )
    print("  validation_diagnosis rows:", f"{len(validation_rows):,}")
    print("  mutation_robustness rows:", f"{len(mutation_rows):,}")
    print("  split overlap count:", f"{len(overlap_hashes):,}")
    print("  exact split/hash coverage match:", combined_hashes == parent_hashes)

    print("\nrole-manifest checks")
    print(
        "  validation_diagnosis:",
        f"duplicates={validation_analysis['duplicate_circuit_hash_count']:,}",
        f"missing_source={validation_analysis['missing_source_count']:,}",
        f"role_impure={validation_analysis['role_impure']}",
        f"target_mode_impure={validation_analysis['target_mode_impure']}",
    )
    print(
        "  mutation_robustness:",
        f"duplicates={mutation_analysis['duplicate_circuit_hash_count']:,}",
        f"missing_source={mutation_analysis['missing_source_count']:,}",
        f"role_impure={mutation_analysis['role_impure']}",
        f"target_mode_impure={mutation_analysis['target_mode_impure']}",
    )

    print("\ncalibration-policy alignment")
    for role, payload in report["calibration_policy_checks"].items():
        print(
            f"  {role}:",
            f"chosen={payload['chosen_model']}",
            f"overall_winner={payload['overall_winner']}",
            f"strict_winner={payload['strict_winner']}",
        )

    print("\nexisting teacher-text output")
    print("  exists:", existing_output["exists"])
    print("  rows:", f"{existing_output['rows']:,}")
    if existing_output["model_role_counts"]:
        print("  model/role counts:")
        for key, value in sorted(existing_output["model_role_counts"].items()):
            print(f"    {key}: {value:,}")

    if blocking_issues:
        print("\nblocking issues")
        for issue in blocking_issues:
            print("  -", issue)
    else:
        print("\nblocking issues")
        print("  none")

    if warnings:
        print("\nnon-blocking warnings")
        for warning in warnings:
            print("  -", warning)
    else:
        print("\nnon-blocking warnings")
        print("  none")

    print("\nrecommended to proceed:", report["recommended_to_proceed"])


if __name__ == "__main__":
    main()
