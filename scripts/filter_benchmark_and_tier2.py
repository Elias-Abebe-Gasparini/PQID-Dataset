"""
filter_benchmark_and_tier2.py
-----------------------------
Splits an enriched raw pool into:
1. a strict core benchmark candidate set
2. a broad Tier 2 set for repair / fixing challenges

The split is intentionally conservative by default:
- only validated, high-confidence, non-demo entries enter the core set
- `empirical_promoted_repo` entries are excluded from the core set unless
  `--include-empirical-in-core` is explicitly passed

Examples:
    python filter_benchmark_and_tier2.py
    python filter_benchmark_and_tier2.py --input-file ...\\circuits_unified_plus_aggressive_broad_enriched.jsonl
    python filter_benchmark_and_tier2.py --include-empirical-in-core
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from project_paths import PROCESSED_DIR
from project_paths import format_display_path

BASE = PROCESSED_DIR

BENCHMARK_CHECK_ORDER = [
    "validated_execution",
    "high_extraction_confidence",
    "no_demo_scaffolding",
    "no_cleanup_candidate",
    "minimum_code_lines",
    "minimum_gate_count",
    "trusted_retrieval_strategy",
]

BENCHMARK_CHECK_DESCRIPTIONS = {
    "validated_execution": 'validation_status == "validated"',
    "high_extraction_confidence": 'extraction_confidence == "high"',
    "no_demo_scaffolding": "contains_demo_scaffolding != True",
    "no_cleanup_candidate": "cleanup_candidate != True",
    "minimum_code_lines": "code_lines >= min_code_lines",
    "minimum_gate_count": "gate_count >= min_gate_count",
    "trusted_retrieval_strategy": 'retrieval_strategy != "empirical_promoted_repo"',
}

BENCHMARK_CHECK_ORDER_V2 = BENCHMARK_CHECK_ORDER + [
    "non_mutation_suite_path",
]

BENCHMARK_CHECK_DESCRIPTIONS_V2 = {
    **BENCHMARK_CHECK_DESCRIPTIONS,
    "non_mutation_suite_path": "mutation_suite_candidate != True",
}

CHECK_TO_REJECTION_REASON = {
    "validated_execution": "not_validated",
    "high_extraction_confidence": "not_high_confidence",
    "no_demo_scaffolding": "demo_scaffolding",
    "no_cleanup_candidate": "cleanup_candidate",
    "minimum_code_lines": "too_few_code_lines",
    "minimum_gate_count": "too_few_gates",
    "trusted_retrieval_strategy": "empirical_strategy_excluded",
}


def default_input_file() -> Path:
    candidates = [
        BASE / "circuits_unified_plus_phase2_plus_phase3_enriched.jsonl",
        BASE / "circuits_unified_plus_aggressive_broad_enriched.jsonl",
        BASE / "circuits_unified_plus_aggressive_enriched.jsonl",
        BASE / "circuits_unified_enriched.jsonl",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]


def default_core_output_file(
    input_path: Path,
    *,
    include_empirical_in_core: bool,
) -> Path:
    stem = input_path.stem
    if stem == "circuits_unified_plus_aggressive_broad_enriched":
        if include_empirical_in_core:
            return BASE / "circuits_unified_plus_aggressive_core_extended_enriched.jsonl"
        return BASE / "circuits_unified_plus_aggressive_core_enriched.jsonl"
    if stem == "circuits_unified_plus_phase2_plus_phase3_enriched":
        if include_empirical_in_core:
            return BASE / "circuits_unified_plus_phase2_plus_phase3_core_extended_enriched.jsonl"
        return BASE / "circuits_unified_plus_phase2_plus_phase3_core_enriched.jsonl"

    base_stem = stem[:-len("_enriched")] if stem.endswith("_enriched") else stem
    if include_empirical_in_core:
        return input_path.with_name(base_stem + "_core_extended_enriched.jsonl")
    return input_path.with_name(base_stem + "_core_enriched.jsonl")


def default_tier2_output_file(
    input_path: Path,
    *,
    include_empirical_in_core: bool,
) -> Path:
    stem = input_path.stem
    if stem == "circuits_unified_plus_aggressive_broad_enriched":
        if include_empirical_in_core:
            return BASE / "circuits_unified_plus_aggressive_tier2_extended.jsonl"
        return BASE / "circuits_unified_plus_aggressive_tier2_enriched.jsonl"
    if stem == "circuits_unified_plus_phase2_plus_phase3_enriched":
        if include_empirical_in_core:
            return BASE / "circuits_unified_plus_phase2_plus_phase3_tier2_extended.jsonl"
        return BASE / "circuits_unified_plus_phase2_plus_phase3_tier2_enriched.jsonl"

    base_stem = stem[:-len("_enriched")] if stem.endswith("_enriched") else stem
    if include_empirical_in_core:
        return input_path.with_name(base_stem + "_tier2_extended.jsonl")
    return input_path.with_name(base_stem + "_tier2_enriched.jsonl")


def default_report_file(
    input_path: Path,
    *,
    include_empirical_in_core: bool,
) -> Path:
    stem = input_path.stem
    if stem == "circuits_unified_plus_aggressive_broad_enriched":
        if include_empirical_in_core:
            return BASE / "benchmark_tiering_report_extended.md"
        return BASE / "benchmark_tiering_report.md"
    if stem == "circuits_unified_plus_phase2_plus_phase3_enriched":
        if include_empirical_in_core:
            return BASE / "benchmark_tiering_report_phase3_extended.md"
        return BASE / "benchmark_tiering_report_phase3.md"

    base_stem = stem[:-len("_enriched")] if stem.endswith("_enriched") else stem
    suffix = "_extended" if include_empirical_in_core else ""
    return input_path.with_name(base_stem + f"_benchmark_tiering_report{suffix}.md")


def parse_args():
    default_input = default_input_file()
    parser = argparse.ArgumentParser(
        description="Split an enriched raw pool into strict core and Tier 2 files."
    )
    parser.add_argument(
        "--input-file",
        default=str(default_input),
        help="Path to the enriched broad raw pool.",
    )
    parser.add_argument(
        "--core-output-file",
        default=None,
        help="Path to write the strict core benchmark candidate file.",
    )
    parser.add_argument(
        "--tier2-output-file",
        default=None,
        help="Path to write the broad Tier 2 file.",
    )
    parser.add_argument(
        "--report-file",
        default=None,
        help="Path to write a markdown summary report.",
    )
    parser.add_argument(
        "--min-code-lines",
        type=int,
        default=5,
        help="Minimum code_lines required for the strict core set.",
    )
    parser.add_argument(
        "--min-gate-count",
        type=int,
        default=2,
        help="Minimum gate_count required for the strict core set.",
    )
    parser.add_argument(
        "--include-empirical-in-core",
        action="store_true",
        help="Allow validated high-confidence empirical_promoted_repo entries into the core set.",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, entries: list[dict]) -> None:
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def pct(n: int, d: int) -> str:
    if d <= 0:
        return "0.0%"
    return f"{(100.0 * n / d):.1f}%"


def benchmark_profile_version(
    *, min_code_lines: int, min_gate_count: int
) -> str:
    return f"benchmark_suitability_v1_code{min_code_lines}_gate{min_gate_count}"


def benchmark_profile_version_v2(
    *, min_code_lines: int, min_gate_count: int
) -> str:
    return f"benchmark_suitability_v2_code{min_code_lines}_gate{min_gate_count}"


def evaluate_benchmark_suitability(
    entry: dict,
    *,
    min_code_lines: int,
    min_gate_count: int,
) -> dict:
    meta = entry.get("metadata", {})
    checks = {
        "validated_execution": meta.get("validation_status") == "validated",
        "high_extraction_confidence": meta.get("extraction_confidence") == "high",
        "no_demo_scaffolding": meta.get("contains_demo_scaffolding") is not True,
        "no_cleanup_candidate": meta.get("cleanup_candidate") is not True,
        "minimum_code_lines": (meta.get("code_lines") or 0) >= min_code_lines,
        "minimum_gate_count": (meta.get("gate_count") or 0) >= min_gate_count,
        "trusted_retrieval_strategy": (
            meta.get("retrieval_strategy") != "empirical_promoted_repo"
        ),
    }

    passed_checks = [cid for cid in BENCHMARK_CHECK_ORDER if checks[cid]]
    failed_checks = [cid for cid in BENCHMARK_CHECK_ORDER if not checks[cid]]
    total = len(BENCHMARK_CHECK_ORDER)
    passed = len(passed_checks)

    if not checks["validated_execution"]:
        tier = "tier2_unvalidated"
    elif failed_checks == ["trusted_retrieval_strategy"]:
        tier = "extended_core_candidate"
    elif not failed_checks:
        tier = "strict_core_candidate"
    else:
        tier = "validated_broad_candidate"

    return {
        "checks": checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "checks_total": total,
        "checks_passed": passed,
        "checks_ratio": (passed / total) if total else 0.0,
        "suitability_tier": tier,
    }


def evaluate_benchmark_suitability_v2(
    entry: dict,
    *,
    min_code_lines: int,
    min_gate_count: int,
) -> dict:
    meta = entry.get("metadata", {})
    checks = {
        "validated_execution": meta.get("validation_status") == "validated",
        "high_extraction_confidence": meta.get("extraction_confidence") == "high",
        "no_demo_scaffolding": meta.get("contains_demo_scaffolding") is not True,
        "no_cleanup_candidate": meta.get("cleanup_candidate") is not True,
        "minimum_code_lines": (meta.get("code_lines") or 0) >= min_code_lines,
        "minimum_gate_count": (meta.get("gate_count") or 0) >= min_gate_count,
        "trusted_retrieval_strategy": (
            meta.get("retrieval_strategy") != "empirical_promoted_repo"
        ),
        "non_mutation_suite_path": meta.get("mutation_suite_candidate") is not True,
    }

    passed_checks = [cid for cid in BENCHMARK_CHECK_ORDER_V2 if checks[cid]]
    failed_checks = [cid for cid in BENCHMARK_CHECK_ORDER_V2 if not checks[cid]]
    total = len(BENCHMARK_CHECK_ORDER_V2)
    passed = len(passed_checks)

    substantive_ready = all(
        checks[cid]
        for cid in [
            "validated_execution",
            "high_extraction_confidence",
            "no_demo_scaffolding",
            "no_cleanup_candidate",
            "minimum_code_lines",
            "minimum_gate_count",
        ]
    )

    if not checks["validated_execution"]:
        tier = "tier2_unvalidated"
    elif not substantive_ready:
        tier = "validated_broad_candidate"
    elif not checks["non_mutation_suite_path"]:
        tier = "mutation_stress_candidate"
    elif not checks["trusted_retrieval_strategy"]:
        tier = "extended_core_candidate"
    else:
        tier = "strict_core_candidate"

    return {
        "checks": checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "checks_total": total,
        "checks_passed": passed,
        "checks_ratio": (passed / total) if total else 0.0,
        "suitability_tier": tier,
    }


def annotate_entry_with_benchmark_suitability(
    entry: dict,
    evaluation: dict,
    *,
    min_code_lines: int,
    min_gate_count: int,
) -> dict:
    entry = dict(entry)
    meta = dict(entry.get("metadata", {}))
    meta.update({
        "benchmark_profile_version": benchmark_profile_version(
            min_code_lines=min_code_lines,
            min_gate_count=min_gate_count,
        ),
        "benchmark_checks_total": evaluation["checks_total"],
        "benchmark_checks_passed": evaluation["checks_passed"],
        "benchmark_checks_ratio": round(evaluation["checks_ratio"], 4),
        "benchmark_passed_checks": evaluation["passed_checks"],
        "benchmark_failed_checks": evaluation["failed_checks"],
        "benchmark_suitability_tier": evaluation["suitability_tier"],
    })
    entry["metadata"] = meta
    return entry


def annotate_entry_with_benchmark_suitability_v2(
    entry: dict,
    evaluation: dict,
    *,
    min_code_lines: int,
    min_gate_count: int,
) -> dict:
    entry = dict(entry)
    meta = dict(entry.get("metadata", {}))
    meta.update({
        "benchmark_profile_version_v2": benchmark_profile_version_v2(
            min_code_lines=min_code_lines,
            min_gate_count=min_gate_count,
        ),
        "benchmark_checks_total_v2": evaluation["checks_total"],
        "benchmark_checks_passed_v2": evaluation["checks_passed"],
        "benchmark_checks_ratio_v2": round(evaluation["checks_ratio"], 4),
        "benchmark_passed_checks_v2": evaluation["passed_checks"],
        "benchmark_failed_checks_v2": evaluation["failed_checks"],
        "benchmark_suitability_tier_v2": evaluation["suitability_tier"],
    })
    entry["metadata"] = meta
    return entry


def core_rejection_reason(
    evaluation: dict,
    *,
    include_empirical_in_core: bool,
) -> str | None:
    required_checks = [
        "validated_execution",
        "high_extraction_confidence",
        "no_demo_scaffolding",
        "no_cleanup_candidate",
        "minimum_code_lines",
        "minimum_gate_count",
    ]
    if not include_empirical_in_core:
        required_checks.append("trusted_retrieval_strategy")

    failed = set(evaluation["failed_checks"])
    for check_id in required_checks:
        if check_id in failed:
            return CHECK_TO_REJECTION_REASON[check_id]
    return None


def build_report(
    total: int,
    entries: list[dict],
    core_entries: list[dict],
    tier2_entries: list[dict],
    rejection_reasons: Counter,
    core_strategy_counts: Counter,
    tier2_strategy_counts: Counter,
    suitability_tier_counts: Counter,
    score_counts: Counter,
    include_empirical_in_core: bool,
    min_code_lines: int,
    min_gate_count: int,
) -> str:
    validated_total = 0
    materialized_total = 0
    validated_materialized = 0
    validated_zero_gate = 0
    validated_nonzero_gate = 0

    for entry in entries:
        meta = entry.get("metadata", {})
        status = meta.get("validation_status")
        materialized = meta.get("materialized_circuit") is True
        gate_count = meta.get("gate_count") or 0
        if materialized:
            materialized_total += 1
        if status == "validated":
            validated_total += 1
            if materialized:
                validated_materialized += 1
            if gate_count == 0:
                validated_zero_gate += 1
            else:
                validated_nonzero_gate += 1

    lines = []
    lines.append("# Benchmark Tiering Report")
    lines.append("")
    lines.append("This report documents the split from the enriched broad raw pool into:")
    lines.append("- a strict core benchmark candidate set")
    lines.append("- a broad Tier 2 repair / fixing set")
    lines.append("")
    lines.append("## Core Rule")
    lines.append("")
    lines.append("- `validation_status == \"validated\"`")
    lines.append("- `extraction_confidence == \"high\"`")
    lines.append("- `contains_demo_scaffolding == False`")
    lines.append("- `cleanup_candidate == False`")
    lines.append(f"- `code_lines >= {min_code_lines}`")
    lines.append(f"- `gate_count >= {min_gate_count}`")
    lines.append(
        f"- `retrieval_strategy != \"empirical_promoted_repo\"`: `{not include_empirical_in_core}`"
    )
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Total enriched entries: `{total:,}`")
    lines.append(
        f"- `validated` entries: `{validated_total:,}` ({pct(validated_total, total)})"
    )
    lines.append(
        f"- `materialized_circuit=True`: `{materialized_total:,}` ({pct(materialized_total, total)})"
    )
    lines.append(
        f"- `validated` and `materialized_circuit=True`: `{validated_materialized:,}`"
    )
    lines.append(
        f"- `validated` and `gate_count > 0`: `{validated_nonzero_gate:,}`"
    )
    lines.append(
        f"- `validated` and `gate_count == 0`: `{validated_zero_gate:,}`"
    )
    lines.append(
        f"- Core benchmark candidates: `{len(core_entries):,}` ({pct(len(core_entries), total)})"
    )
    lines.append(
        f"- Tier 2 entries: `{len(tier2_entries):,}` ({pct(len(tier2_entries), total)})"
    )
    lines.append("")
    lines.append("## Benchmark Suitability Checks")
    lines.append("")
    for check_id in BENCHMARK_CHECK_ORDER:
        desc = BENCHMARK_CHECK_DESCRIPTIONS[check_id]
        lines.append(f"- `{check_id}`: `{desc}`")
    lines.append("")
    lines.append("## Benchmark Suitability Tier Distribution")
    lines.append("")
    for k, v in suitability_tier_counts.most_common():
        lines.append(f"- `{k}`: `{v:,}` ({pct(v, total)})")
    if not suitability_tier_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Benchmark Suitability Score Distribution")
    lines.append("")
    for passed in sorted(score_counts):
        v = score_counts[passed]
        lines.append(
            f"- `{passed}/{len(BENCHMARK_CHECK_ORDER)}`: `{v:,}` ({pct(v, total)})"
        )
    if not score_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Core Strategy Distribution")
    lines.append("")
    for k, v in core_strategy_counts.most_common():
        lines.append(f"- `{k}`: `{v:,}`")
    if not core_strategy_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Tier 2 Strategy Distribution")
    lines.append("")
    for k, v in tier2_strategy_counts.most_common():
        lines.append(f"- `{k}`: `{v:,}`")
    if not tier2_strategy_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Top Core Rejection Reasons")
    lines.append("")
    for k, v in rejection_reasons.most_common():
        lines.append(f"- `{k}`: `{v:,}`")
    if not rejection_reasons:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()

    input_path = Path(args.input_file)
    core_path = (
        Path(args.core_output_file)
        if args.core_output_file
        else default_core_output_file(
            input_path,
            include_empirical_in_core=args.include_empirical_in_core,
        )
    )
    tier2_path = (
        Path(args.tier2_output_file)
        if args.tier2_output_file
        else default_tier2_output_file(
            input_path,
            include_empirical_in_core=args.include_empirical_in_core,
        )
    )
    report_path = (
        Path(args.report_file)
        if args.report_file
        else default_report_file(
            input_path,
            include_empirical_in_core=args.include_empirical_in_core,
        )
    )

    if not input_path.exists():
        raise SystemExit(
            f"ERROR: input file not found: {format_display_path(input_path)}"
        )

    entries = load_jsonl(input_path)
    core_entries = []
    tier2_entries = []
    rejection_reasons = Counter()
    core_strategy_counts = Counter()
    tier2_strategy_counts = Counter()
    suitability_tier_counts = Counter()
    score_counts = Counter()

    for entry in entries:
        meta = entry.get("metadata", {})
        strategy = meta.get("retrieval_strategy") or meta.get("source") or "<missing>"
        evaluation = evaluate_benchmark_suitability(
            entry,
            min_code_lines=args.min_code_lines,
            min_gate_count=args.min_gate_count,
        )
        annotated_entry = annotate_entry_with_benchmark_suitability(
            entry,
            evaluation,
            min_code_lines=args.min_code_lines,
            min_gate_count=args.min_gate_count,
        )
        reason = core_rejection_reason(
            evaluation,
            include_empirical_in_core=args.include_empirical_in_core,
        )
        suitability_tier_counts[evaluation["suitability_tier"]] += 1
        score_counts[evaluation["checks_passed"]] += 1

        if reason is None:
            core_entries.append(annotated_entry)
            core_strategy_counts[strategy] += 1
        else:
            tier2_entries.append(annotated_entry)
            tier2_strategy_counts[strategy] += 1
            rejection_reasons[reason] += 1

    write_jsonl(core_path, core_entries)
    write_jsonl(tier2_path, tier2_entries)

    report_text = build_report(
        total=len(entries),
        entries=entries,
        core_entries=core_entries,
        tier2_entries=tier2_entries,
        rejection_reasons=rejection_reasons,
        core_strategy_counts=core_strategy_counts,
        tier2_strategy_counts=tier2_strategy_counts,
        suitability_tier_counts=suitability_tier_counts,
        score_counts=score_counts,
        include_empirical_in_core=args.include_empirical_in_core,
        min_code_lines=args.min_code_lines,
        min_gate_count=args.min_gate_count,
    )
    report_path.write_text(report_text, encoding="utf-8")

    print(f"Input   : {format_display_path(input_path)}")
    print(f"Core    : {format_display_path(core_path)}")
    print(f"Tier 2  : {format_display_path(tier2_path)}")
    print(f"Report  : {format_display_path(report_path)}")
    print(f"Total   : {len(entries):,}")
    print(f"Core    : {len(core_entries):,}")
    print(f"Tier 2  : {len(tier2_entries):,}")


if __name__ == "__main__":
    main()
