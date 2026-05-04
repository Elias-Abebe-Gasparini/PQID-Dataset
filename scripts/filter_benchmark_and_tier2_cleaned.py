from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from project_paths import PROCESSED_DIR
from project_paths import format_display_path

from filter_benchmark_and_tier2 import BENCHMARK_CHECK_DESCRIPTIONS
from filter_benchmark_and_tier2 import BENCHMARK_CHECK_DESCRIPTIONS_V2
from filter_benchmark_and_tier2 import BENCHMARK_CHECK_ORDER
from filter_benchmark_and_tier2 import BENCHMARK_CHECK_ORDER_V2
from filter_benchmark_and_tier2 import annotate_entry_with_benchmark_suitability
from filter_benchmark_and_tier2 import annotate_entry_with_benchmark_suitability_v2
from filter_benchmark_and_tier2 import core_rejection_reason
from filter_benchmark_and_tier2 import default_input_file
from filter_benchmark_and_tier2 import evaluate_benchmark_suitability
from filter_benchmark_and_tier2 import evaluate_benchmark_suitability_v2
from filter_benchmark_and_tier2 import load_jsonl
from filter_benchmark_and_tier2 import pct
from filter_benchmark_and_tier2 import write_jsonl

BASE = PROCESSED_DIR
MUTATION_PATH_MARKERS = (
    "/mutants/",
    "mutants_of_",
)


def default_core_output_file(input_path: Path, *, include_empirical_in_core: bool) -> Path:
    stem = input_path.stem
    if stem == "circuits_unified_plus_phase2_plus_phase3_enriched":
        if include_empirical_in_core:
            return BASE / "circuits_unified_plus_phase2_plus_phase3_core_extended_cleaned_enriched.jsonl"
        return BASE / "circuits_unified_plus_phase2_plus_phase3_core_cleaned_enriched.jsonl"

    base_stem = stem[:-len("_enriched")] if stem.endswith("_enriched") else stem
    suffix = "_core_extended_cleaned_enriched.jsonl" if include_empirical_in_core else "_core_cleaned_enriched.jsonl"
    return input_path.with_name(base_stem + suffix)


def default_tier2_output_file(input_path: Path, *, include_empirical_in_core: bool) -> Path:
    stem = input_path.stem
    if stem == "circuits_unified_plus_phase2_plus_phase3_enriched":
        if include_empirical_in_core:
            return BASE / "circuits_unified_plus_phase2_plus_phase3_tier2_extended_cleaned.jsonl"
        return BASE / "circuits_unified_plus_phase2_plus_phase3_tier2_cleaned_enriched.jsonl"

    base_stem = stem[:-len("_enriched")] if stem.endswith("_enriched") else stem
    suffix = "_tier2_extended_cleaned.jsonl" if include_empirical_in_core else "_tier2_cleaned_enriched.jsonl"
    return input_path.with_name(base_stem + suffix)


def default_report_file(input_path: Path, *, include_empirical_in_core: bool) -> Path:
    stem = input_path.stem
    if stem == "circuits_unified_plus_phase2_plus_phase3_enriched":
        if include_empirical_in_core:
            return BASE / "benchmark_tiering_report_phase3_extended_cleaned.md"
        return BASE / "benchmark_tiering_report_phase3_cleaned.md"

    base_stem = stem[:-len("_enriched")] if stem.endswith("_enriched") else stem
    suffix = "_benchmark_tiering_report_extended_cleaned.md" if include_empirical_in_core else "_benchmark_tiering_report_cleaned.md"
    return input_path.with_name(base_stem + suffix)


def parse_args() -> argparse.Namespace:
    default_input = default_input_file()
    parser = argparse.ArgumentParser(
        description="Split an enriched raw pool into cleaned strict core and Tier 2 files."
    )
    parser.add_argument("--input-file", default=str(default_input), help="Path to the enriched broad raw pool.")
    parser.add_argument("--core-output-file", default=None, help="Path to write the cleaned core benchmark file.")
    parser.add_argument("--tier2-output-file", default=None, help="Path to write the cleaned Tier 2 file.")
    parser.add_argument("--report-file", default=None, help="Path to write a cleaned markdown summary report.")
    parser.add_argument("--min-code-lines", type=int, default=5, help="Minimum code_lines required for the core set.")
    parser.add_argument("--min-gate-count", type=int, default=2, help="Minimum gate_count required for the core set.")
    parser.add_argument(
        "--include-empirical-in-core",
        action="store_true",
        help="Allow validated high-confidence empirical_promoted_repo entries into the core set before path cleaning.",
    )
    parser.add_argument(
        "--exclude-mutation-paths",
        action="store_true",
        default=True,
        help="Exclude mutation-suite file paths such as */Mutants/* from the cleaned core outputs.",
    )
    parser.add_argument(
        "--no-exclude-mutation-paths",
        dest="exclude_mutation_paths",
        action="store_false",
        help="Disable mutation-suite path cleaning.",
    )
    return parser.parse_args()


def normalized_file_path(entry: dict) -> str:
    meta = entry.get("metadata", {})
    raw_path = meta.get("file_path") or meta.get("original_url") or ""
    return raw_path.replace("\\", "/").lower()


def is_mutation_suite_entry(entry: dict) -> bool:
    path = normalized_file_path(entry)
    if not path:
        return False
    return any(marker in path for marker in MUTATION_PATH_MARKERS)


def repo_key(entry: dict) -> str:
    meta = entry.get("metadata", {})
    owner = meta.get("repo_owner") or "<missing-owner>"
    name = meta.get("repo_name") or "<missing-repo>"
    return f"{owner}/{name}"


def annotate_cleaning(entry: dict) -> dict:
    entry = dict(entry)
    meta = dict(entry.get("metadata", {}))
    mutation_suite_candidate = is_mutation_suite_entry(entry)
    flags = []
    if mutation_suite_candidate:
        flags.append("mutation_suite_path")
    meta["mutation_suite_candidate"] = mutation_suite_candidate
    meta["benchmark_cleaning_flags"] = flags
    entry["metadata"] = meta
    return entry


def build_report(
    *,
    total: int,
    entries: list[dict],
    core_entries: list[dict],
    tier2_entries: list[dict],
    rejection_reasons: Counter,
    core_strategy_counts: Counter,
    tier2_strategy_counts: Counter,
    suitability_tier_counts: Counter,
    score_counts: Counter,
    suitability_tier_counts_v2: Counter,
    score_counts_v2: Counter,
    include_empirical_in_core: bool,
    exclude_mutation_paths: bool,
    min_code_lines: int,
    min_gate_count: int,
    mutation_excluded_total: int,
    mutation_excluded_repos: Counter,
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
    lines.append("# Benchmark Tiering Report (Cleaned)")
    lines.append("")
    lines.append("This report documents the cleaned split from the enriched broad raw pool into:")
    lines.append("- a cleaned core benchmark candidate set")
    lines.append("- a cleaned Tier 2 repair / fixing set")
    lines.append("")
    lines.append("## Core Rule")
    lines.append("")
    lines.append("- `validation_status == \"validated\"`")
    lines.append("- `extraction_confidence == \"high\"`")
    lines.append("- `contains_demo_scaffolding == False`")
    lines.append("- `cleanup_candidate == False`")
    lines.append(f"- `code_lines >= {min_code_lines}`")
    lines.append(f"- `gate_count >= {min_gate_count}`")
    lines.append(f"- `retrieval_strategy != \"empirical_promoted_repo\"`: `{not include_empirical_in_core}`")
    lines.append(f"- `exclude mutation-suite paths`: `{exclude_mutation_paths}`")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Total enriched entries: `{total:,}`")
    lines.append(f"- `validated` entries: `{validated_total:,}` ({pct(validated_total, total)})")
    lines.append(f"- `materialized_circuit=True`: `{materialized_total:,}` ({pct(materialized_total, total)})")
    lines.append(f"- `validated` and `materialized_circuit=True`: `{validated_materialized:,}`")
    lines.append(f"- `validated` and `gate_count > 0`: `{validated_nonzero_gate:,}`")
    lines.append(f"- `validated` and `gate_count == 0`: `{validated_zero_gate:,}`")
    lines.append(f"- Cleaned core benchmark candidates: `{len(core_entries):,}` ({pct(len(core_entries), total)})")
    lines.append(f"- Cleaned Tier 2 entries: `{len(tier2_entries):,}` ({pct(len(tier2_entries), total)})")
    if exclude_mutation_paths:
        lines.append(f"- Tier 2 entries excluded by mutation-path cleaning: `{mutation_excluded_total:,}`")
    lines.append("")
    lines.append("## Benchmark Suitability Checks (`n/7`)")
    lines.append("")
    for check_id in BENCHMARK_CHECK_ORDER:
        desc = BENCHMARK_CHECK_DESCRIPTIONS[check_id]
        lines.append(f"- `{check_id}`: `{desc}`")
    lines.append("")
    lines.append("## Benchmark Suitability Tier Distribution (`n/7`)")
    lines.append("")
    for k, v in suitability_tier_counts.most_common():
        lines.append(f"- `{k}`: `{v:,}` ({pct(v, total)})")
    if not suitability_tier_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Benchmark Suitability Score Distribution (`n/7`)")
    lines.append("")
    for passed in sorted(score_counts):
        v = score_counts[passed]
        lines.append(f"- `{passed}/{len(BENCHMARK_CHECK_ORDER)}`: `{v:,}` ({pct(v, total)})")
    if not score_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Cleanliness-Aware Benchmark Checks (`n/8`)")
    lines.append("")
    for check_id in BENCHMARK_CHECK_ORDER_V2:
        desc = BENCHMARK_CHECK_DESCRIPTIONS_V2[check_id]
        lines.append(f"- `{check_id}`: `{desc}`")
    lines.append("")
    lines.append("## Cleanliness-Aware Tier Distribution (`n/8`)")
    lines.append("")
    for k, v in suitability_tier_counts_v2.most_common():
        lines.append(f"- `{k}`: `{v:,}` ({pct(v, total)})")
    if not suitability_tier_counts_v2:
        lines.append("- None")
    lines.append("")
    lines.append("## Cleanliness-Aware Score Distribution (`n/8`)")
    lines.append("")
    for passed in sorted(score_counts_v2):
        v = score_counts_v2[passed]
        lines.append(f"- `{passed}/{len(BENCHMARK_CHECK_ORDER_V2)}`: `{v:,}` ({pct(v, total)})")
    if not score_counts_v2:
        lines.append("- None")
    lines.append("")
    lines.append("## Cleaned Core Strategy Distribution")
    lines.append("")
    for k, v in core_strategy_counts.most_common():
        lines.append(f"- `{k}`: `{v:,}`")
    if not core_strategy_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Cleaned Tier 2 Strategy Distribution")
    lines.append("")
    for k, v in tier2_strategy_counts.most_common():
        lines.append(f"- `{k}`: `{v:,}`")
    if not tier2_strategy_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Top Cleaned Core Rejection Reasons")
    lines.append("")
    for k, v in rejection_reasons.most_common():
        lines.append(f"- `{k}`: `{v:,}`")
    if not rejection_reasons:
        lines.append("- None")
    lines.append("")
    if exclude_mutation_paths:
        lines.append("## Top Mutation-Path Exclusions")
        lines.append("")
        for k, v in mutation_excluded_repos.most_common():
            lines.append(f"- `{k}`: `{v:,}`")
        if not mutation_excluded_repos:
            lines.append("- None")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()

    input_path = Path(args.input_file)
    core_path = Path(args.core_output_file) if args.core_output_file else default_core_output_file(
        input_path,
        include_empirical_in_core=args.include_empirical_in_core,
    )
    tier2_path = Path(args.tier2_output_file) if args.tier2_output_file else default_tier2_output_file(
        input_path,
        include_empirical_in_core=args.include_empirical_in_core,
    )
    report_path = Path(args.report_file) if args.report_file else default_report_file(
        input_path,
        include_empirical_in_core=args.include_empirical_in_core,
    )

    if not input_path.exists():
        raise SystemExit(f"ERROR: input file not found: {format_display_path(input_path)}")

    entries = load_jsonl(input_path)
    core_entries = []
    tier2_entries = []
    rejection_reasons = Counter()
    core_strategy_counts = Counter()
    tier2_strategy_counts = Counter()
    suitability_tier_counts = Counter()
    score_counts = Counter()
    suitability_tier_counts_v2 = Counter()
    score_counts_v2 = Counter()
    mutation_excluded_total = 0
    mutation_excluded_repos = Counter()

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
        annotated_entry = annotate_cleaning(annotated_entry)
        evaluation_v2 = evaluate_benchmark_suitability_v2(
            annotated_entry,
            min_code_lines=args.min_code_lines,
            min_gate_count=args.min_gate_count,
        )
        annotated_entry = annotate_entry_with_benchmark_suitability_v2(
            annotated_entry,
            evaluation_v2,
            min_code_lines=args.min_code_lines,
            min_gate_count=args.min_gate_count,
        )

        if args.exclude_mutation_paths and is_mutation_suite_entry(entry):
            reason = "mutation_suite_excluded"
            mutation_excluded_total += 1
            mutation_excluded_repos[repo_key(entry)] += 1
        else:
            reason = core_rejection_reason(
                evaluation,
                include_empirical_in_core=args.include_empirical_in_core,
            )

        suitability_tier_counts[evaluation["suitability_tier"]] += 1
        score_counts[evaluation["checks_passed"]] += 1
        suitability_tier_counts_v2[evaluation_v2["suitability_tier"]] += 1
        score_counts_v2[evaluation_v2["checks_passed"]] += 1

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
        suitability_tier_counts_v2=suitability_tier_counts_v2,
        score_counts_v2=score_counts_v2,
        include_empirical_in_core=args.include_empirical_in_core,
        exclude_mutation_paths=args.exclude_mutation_paths,
        min_code_lines=args.min_code_lines,
        min_gate_count=args.min_gate_count,
        mutation_excluded_total=mutation_excluded_total,
        mutation_excluded_repos=mutation_excluded_repos,
    )
    report_path.write_text(report_text, encoding="utf-8")

    print(f"Input   : {format_display_path(input_path)}")
    print(f"Core    : {format_display_path(core_path)}")
    print(f"Tier 2  : {format_display_path(tier2_path)}")
    print(f"Report  : {format_display_path(report_path)}")
    print(f"Total   : {len(entries):,}")
    print(f"Core    : {len(core_entries):,}")
    print(f"Tier 2  : {len(tier2_entries):,}")
    if args.exclude_mutation_paths:
        print(f"Mutation-path exclusions: {mutation_excluded_total:,}")


if __name__ == "__main__":
    main()
