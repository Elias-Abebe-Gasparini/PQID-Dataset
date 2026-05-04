from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from project_paths import PROCESSED_DIR, format_display_path

from filter_benchmark_and_tier2 import (
    BENCHMARK_CHECK_ORDER,
    BENCHMARK_CHECK_ORDER_V2,
    annotate_entry_with_benchmark_suitability,
    annotate_entry_with_benchmark_suitability_v2,
    default_input_file,
    evaluate_benchmark_suitability,
    evaluate_benchmark_suitability_v2,
    load_jsonl,
    pct,
    write_jsonl,
)
from filter_benchmark_and_tier2_cleaned import annotate_cleaning

BASE = PROCESSED_DIR
MASTER_METADATA_CARRY_FORWARD_FIELDS = [
    "repo_topics",
    "is_org_repo",
    "repo_license",
    "license_category",
    "circuit_family",
    "semantic_intent",
]


def default_output_file(input_path: Path) -> Path:
    stem = input_path.stem
    if stem == "circuits_unified_plus_phase2_plus_phase3_enriched":
        return BASE / "circuits_unified_plus_phase2_plus_phase3_master_processable_enriched.jsonl"
    base_stem = stem[:-len("_enriched")] if stem.endswith("_enriched") else stem
    return input_path.with_name(base_stem + "_master_processable_enriched.jsonl")


def default_report_file(input_path: Path) -> Path:
    stem = input_path.stem
    if stem == "circuits_unified_plus_phase2_plus_phase3_enriched":
        return BASE / "master_processable_report_phase3.md"
    base_stem = stem[:-len("_enriched")] if stem.endswith("_enriched") else stem
    return input_path.with_name(base_stem + "_master_processable_report.md")


def parse_args() -> argparse.Namespace:
    default_input = default_input_file()
    parser = argparse.ArgumentParser(
        description="Build a master processable corpus for downstream seed/paraphrase generation."
    )
    parser.add_argument("--input-file", default=str(default_input), help="Path to the enriched broad raw pool.")
    parser.add_argument("--output-file", default=None, help="Path to write the master processable corpus.")
    parser.add_argument("--report-file", default=None, help="Path to write a markdown summary report.")
    parser.add_argument("--min-code-lines", type=int, default=5, help="Benchmark annotation profile: minimum code_lines.")
    parser.add_argument("--min-gate-count", type=int, default=2, help="Benchmark annotation profile: minimum gate_count.")
    parser.add_argument(
        "--require-nonzero-gate-count",
        action="store_true",
        default=True,
        help="Keep only entries with gate_count > 0 in the master processable corpus.",
    )
    parser.add_argument(
        "--allow-zero-gate-count",
        dest="require_nonzero_gate_count",
        action="store_false",
        help="Allow validated materialized entries with gate_count == 0 into the master processable corpus.",
    )
    parser.add_argument(
        "--no-carry-forward-existing-metadata",
        dest="carry_forward_existing_metadata",
        action="store_false",
        help=(
            "Do not preserve pre-existing master-only metadata such as circuit_family "
            "and semantic_intent from an older master file when rebuilding."
        ),
    )
    parser.set_defaults(carry_forward_existing_metadata=True)
    return parser.parse_args()


def is_processable(entry: dict, *, require_nonzero_gate_count: bool) -> bool:
    meta = entry.get("metadata", {})
    if meta.get("validation_status") != "validated":
        return False
    if meta.get("materialized_circuit") is not True:
        return False
    if require_nonzero_gate_count and (meta.get("gate_count") or 0) <= 0:
        return False
    return True


def build_existing_master_index(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    index: dict[str, dict] = {}
    for entry in load_jsonl(path):
        meta = entry.get("metadata", {})
        circuit_hash = meta.get("circuit_hash")
        if circuit_hash:
            index[circuit_hash] = meta
    return index


def carry_forward_existing_master_metadata(entry: dict, existing_index: dict[str, dict]) -> dict:
    meta = entry.get("metadata", {})
    circuit_hash = meta.get("circuit_hash")
    if not circuit_hash:
        return entry

    previous_meta = existing_index.get(circuit_hash)
    if not previous_meta:
        return entry

    for field in MASTER_METADATA_CARRY_FORWARD_FIELDS:
        current_value = meta.get(field)
        if current_value in (None, "", []):
            previous_value = previous_meta.get(field)
            if previous_value not in (None, "", []):
                meta[field] = previous_value
    return entry


def build_report(*, total: int, kept_entries: list[dict], rejected_counts: Counter, require_nonzero_gate_count: bool) -> str:
    tier_counts = Counter()
    tier_counts_v2 = Counter()
    score_counts = Counter()
    score_counts_v2 = Counter()
    license_counts = Counter()
    mutation_counts = Counter()

    for entry in kept_entries:
        meta = entry.get("metadata", {})
        tier_counts[meta.get("benchmark_suitability_tier", "<missing>")] += 1
        tier_counts_v2[meta.get("benchmark_suitability_tier_v2", "<missing>")] += 1
        score_counts[meta.get("benchmark_checks_passed")] += 1
        score_counts_v2[meta.get("benchmark_checks_passed_v2")] += 1
        license_counts[meta.get("license_category") or "<missing>"] += 1
        mutation_counts[meta.get("mutation_suite_candidate")] += 1

    lines = []
    lines.append("# Master Processable Corpus Report")
    lines.append("")
    lines.append("This report documents the corpus that proceeds to seed generation, paraphrasing, and later semantic analyses before any final public-release filtering is applied.")
    lines.append("")
    lines.append("## Processability Rule")
    lines.append("")
    lines.append("- `validation_status == \"validated\"`")
    lines.append("- `materialized_circuit == True`")
    lines.append(f"- `gate_count > 0`: `{require_nonzero_gate_count}`")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Total enriched entries examined: `{total:,}`")
    lines.append(f"- Master processable entries kept: `{len(kept_entries):,}` ({pct(len(kept_entries), total)})")
    for key, value in rejected_counts.most_common():
        lines.append(f"- Rejected `{key}`: `{value:,}`")
    lines.append("")
    lines.append("## Benchmark Suitability Tier Distribution Within Master Corpus (`n/7`)")
    lines.append("")
    for key, value in tier_counts.most_common():
        lines.append(f"- `{key}`: `{value:,}`")
    lines.append("")
    lines.append("## Benchmark Suitability Score Distribution Within Master Corpus (`n/7`)")
    lines.append("")
    for passed in sorted(k for k in score_counts if k is not None):
        lines.append(f"- `{passed}/{len(BENCHMARK_CHECK_ORDER)}`: `{score_counts[passed]:,}`")
    lines.append("")
    lines.append("## Cleanliness-Aware Benchmark Tier Distribution Within Master Corpus (`n/8`)")
    lines.append("")
    for key, value in tier_counts_v2.most_common():
        lines.append(f"- `{key}`: `{value:,}`")
    lines.append("")
    lines.append("## Cleanliness-Aware Benchmark Score Distribution Within Master Corpus (`n/8`)")
    lines.append("")
    for passed in sorted(k for k in score_counts_v2 if k is not None):
        lines.append(f"- `{passed}/{len(BENCHMARK_CHECK_ORDER_V2)}`: `{score_counts_v2[passed]:,}`")
    lines.append("")
    lines.append("## License Distribution Within Master Corpus")
    lines.append("")
    for key, value in license_counts.most_common():
        lines.append(f"- `{key}`: `{value:,}`")
    lines.append("")
    lines.append("## Mutation-Suite Flag Distribution Within Master Corpus")
    lines.append("")
    for key, value in mutation_counts.most_common():
        lines.append(f"- `{key}`: `{value:,}`")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_file)
    output_path = Path(args.output_file) if args.output_file else default_output_file(input_path)
    report_path = Path(args.report_file) if args.report_file else default_report_file(input_path)

    if not input_path.exists():
        raise SystemExit(f"ERROR: input file not found: {format_display_path(input_path)}")

    entries = load_jsonl(input_path)
    existing_master_index = (
        build_existing_master_index(output_path)
        if args.carry_forward_existing_metadata
        else {}
    )
    kept_entries = []
    rejected_counts = Counter()

    for entry in entries:
        evaluation = evaluate_benchmark_suitability(
            entry,
            min_code_lines=args.min_code_lines,
            min_gate_count=args.min_gate_count,
        )
        annotated = annotate_entry_with_benchmark_suitability(
            entry,
            evaluation,
            min_code_lines=args.min_code_lines,
            min_gate_count=args.min_gate_count,
        )
        annotated = annotate_cleaning(annotated)
        evaluation_v2 = evaluate_benchmark_suitability_v2(
            annotated,
            min_code_lines=args.min_code_lines,
            min_gate_count=args.min_gate_count,
        )
        annotated = annotate_entry_with_benchmark_suitability_v2(
            annotated,
            evaluation_v2,
            min_code_lines=args.min_code_lines,
            min_gate_count=args.min_gate_count,
        )
        annotated = carry_forward_existing_master_metadata(annotated, existing_master_index)

        if is_processable(annotated, require_nonzero_gate_count=args.require_nonzero_gate_count):
            kept_entries.append(annotated)
            continue

        meta = annotated.get("metadata", {})
        if meta.get("validation_status") != "validated":
            rejected_counts["not_validated"] += 1
        elif meta.get("materialized_circuit") is not True:
            rejected_counts["not_materialized"] += 1
        elif args.require_nonzero_gate_count and (meta.get("gate_count") or 0) <= 0:
            rejected_counts["zero_gate_count"] += 1
        else:
            rejected_counts["other"] += 1

    write_jsonl(output_path, kept_entries)
    report_path.write_text(
        build_report(
            total=len(entries),
            kept_entries=kept_entries,
            rejected_counts=rejected_counts,
            require_nonzero_gate_count=args.require_nonzero_gate_count,
        ),
        encoding="utf-8",
    )

    print(f"Input   : {format_display_path(input_path)}")
    print(f"Output  : {format_display_path(output_path)}")
    print(f"Report  : {format_display_path(report_path)}")
    print(f"Total   : {len(entries):,}")
    print(f"Kept    : {len(kept_entries):,}")
    print(f"Rejected: {sum(rejected_counts.values()):,}")
    for key, value in rejected_counts.most_common():
        print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()
