"""
evaluate_pqid_metadata_design_fields.py
--------------------------------------
Evaluate the additive metadata-design layer by reporting coverage, field
distributions, cross-tabs against existing corpus signals, and split-group
statistics.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from metadata_design_common import (
    DEFAULT_EVAL_JSON_FILE,
    DEFAULT_EVAL_MD_FILE,
    DEFAULT_MERGED_OUTPUT_FILE,
    DERIVED_FIELD_NAMES,
    jsonl_rows,
)


DEFAULT_INPUT_FILE = PROCESSED_DIR / DEFAULT_MERGED_OUTPUT_FILE
DEFAULT_REPORT_JSON_FILE = PROCESSED_DIR / DEFAULT_EVAL_JSON_FILE
DEFAULT_REPORT_MD_FILE = PROCESSED_DIR / DEFAULT_EVAL_MD_FILE
NON_DISTRIBUTION_FIELDS = {
    "split_group_id",
    "near_duplicate_group_id",
    "source_revision_id",
    "lineage_parent_id",
}
DISTRIBUTION_FIELD_NAMES = [field for field in DERIVED_FIELD_NAMES if field not in NON_DISTRIBUTION_FIELDS]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-file",
        default=str(DEFAULT_INPUT_FILE),
        help="Merged corpus view that already includes the metadata-design fields.",
    )
    parser.add_argument(
        "--report-json-file",
        default=str(DEFAULT_REPORT_JSON_FILE),
        help="JSON report to write.",
    )
    parser.add_argument(
        "--report-md-file",
        default=str(DEFAULT_REPORT_MD_FILE),
        help="Markdown report to write.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap for dry runs and smoke tests.",
    )
    return parser.parse_args()


def counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common()}


def nested_counter_dict(counter_map: dict[str, Counter[str]]) -> dict[str, dict[str, int]]:
    return {
        str(key): {str(inner_key): counter_dict(inner_counter) for inner_key, inner_counter in sorted(value.items())}
        for key, value in sorted(counter_map.items())
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    string_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in string_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def format_row(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(values)) + " |"

    divider = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([format_row(headers), divider, *(format_row(row) for row in string_rows)])


def print_counter_block(title: str, counter: Counter[str], limit: int = 12) -> None:
    print(title)
    for key, value in counter.most_common(limit):
        print(f"  {key}: {value:,}")


def extract_context(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata = row.get("metadata", {})
    derived = {field: metadata.get(field) for field in DERIVED_FIELD_NAMES}
    return metadata, derived


def update_crosstab(
    crosstabs: dict[str, dict[str, Counter[str]]],
    table_name: str,
    row_key: Any,
    column_key: Any,
) -> None:
    crosstabs[table_name][str(row_key)][str(column_key)] += 1


def build_markdown_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# PQID Metadata-Design Evaluation Report")
    lines.append("")
    lines.append(f"- input file: `{report['input_file']}`")
    lines.append(f"- rows: `{report['rows']:,}`")
    lines.append("")

    coverage_rows = []
    for field, missing in report["field_missing_counts"].items():
        coverage_rows.append([field, report["rows"] - missing, missing])
    lines.append("## Field Coverage")
    lines.append("")
    lines.append(markdown_table(["field", "present_rows", "missing_rows"], coverage_rows))
    lines.append("")

    lines.append("## Field Value Distributions")
    lines.append("")
    for field, distribution in report["field_value_counts"].items():
        lines.append(f"### `{field}`")
        lines.append("")
        rows = [[key, value] for key, value in distribution.items()]
        lines.append(markdown_table(["value", "count"], rows))
        lines.append("")

    lines.append("## Split Group Statistics")
    lines.append("")
    split_stats = report["split_group_stats"]
    split_rows = [
        ["unique_groups", split_stats["unique_groups"]],
        ["singleton_groups", split_stats["singleton_groups"]],
        ["non_singleton_groups", split_stats["non_singleton_groups"]],
        ["max_group_size", split_stats["max_group_size"]],
        ["avg_group_size", split_stats["avg_group_size"]],
        ["median_group_size", split_stats["median_group_size"]],
    ]
    lines.append(markdown_table(["metric", "value"], split_rows))
    lines.append("")
    lines.append("### `split_group_source`")
    lines.append("")
    source_rows = [[key, value] for key, value in split_stats["split_group_source_counts"].items()]
    lines.append(markdown_table(["value", "count"], source_rows))
    lines.append("")

    lines.append("## Near-Duplicate Group Statistics")
    lines.append("")
    near_dup_stats = report["near_duplicate_group_stats"]
    near_dup_rows = [
        ["unique_groups", near_dup_stats["unique_groups"]],
        ["singleton_groups", near_dup_stats["singleton_groups"]],
        ["non_singleton_groups", near_dup_stats["non_singleton_groups"]],
        ["max_group_size", near_dup_stats["max_group_size"]],
        ["avg_group_size", near_dup_stats["avg_group_size"]],
        ["median_group_size", near_dup_stats["median_group_size"]],
    ]
    lines.append(markdown_table(["metric", "value"], near_dup_rows))
    lines.append("")

    lines.append("## Cross-Tabs")
    lines.append("")
    for name, table in report["cross_tabs"].items():
        lines.append(f"### `{name}`")
        lines.append("")
        column_names = sorted({column for row in table.values() for column in row})
        headers = ["row_key", *column_names]
        rows = []
        for row_key, row_values in table.items():
            rows.append([row_key, *[row_values.get(column, 0) for column in column_names]])
        lines.append(markdown_table(headers, rows))
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    input_file = Path(args.input_file)
    report_json_file = Path(args.report_json_file)
    report_md_file = Path(args.report_md_file)

    field_missing_counts: Counter[str] = Counter()
    field_value_counts: dict[str, Counter[str]] = {field: Counter() for field in DISTRIBUTION_FIELD_NAMES}
    validation_status_counts: Counter[str] = Counter()
    benchmark_tier_counts: Counter[str] = Counter()
    hallucination_type_counts: Counter[str] = Counter()
    split_group_sizes: Counter[str] = Counter()
    near_duplicate_group_sizes: Counter[str] = Counter()
    crosstabs: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))

    rows = 0
    for index, row in enumerate(jsonl_rows(input_file), start=1):
        metadata, derived = extract_context(row)
        rows += 1

        validation_status = str(metadata.get("validation_status") or "<missing>")
        benchmark_tier = str(metadata.get("benchmark_suitability_tier_v2") or "<missing>")
        hallucination_type = str(metadata.get("hallucination_type") or "<missing>")

        validation_status_counts[validation_status] += 1
        benchmark_tier_counts[benchmark_tier] += 1
        hallucination_type_counts[hallucination_type] += 1

        for field in DERIVED_FIELD_NAMES:
            value = derived.get(field)
            if value in {None, ""}:
                field_missing_counts[field] += 1
                if field in field_value_counts:
                    field_value_counts[field]["<missing>"] += 1
            else:
                if field in field_value_counts:
                    field_value_counts[field][str(value)] += 1

        split_group_id = str(derived.get("split_group_id") or "")
        if split_group_id:
            split_group_sizes[split_group_id] += 1
        near_duplicate_group_id = str(derived.get("near_duplicate_group_id") or "")
        if near_duplicate_group_id:
            near_duplicate_group_sizes[near_duplicate_group_id] += 1

        update_crosstab(
            crosstabs,
            "expected_model_stance__by_validation_status",
            derived.get("expected_model_stance") or "<missing>",
            validation_status,
        )
        update_crosstab(
            crosstabs,
            "expected_model_stance__by_benchmark_suitability_tier_v2",
            derived.get("expected_model_stance") or "<missing>",
            benchmark_tier,
        )
        update_crosstab(
            crosstabs,
            "context_sufficiency_class__by_validation_status",
            derived.get("context_sufficiency_class") or "<missing>",
            validation_status,
        )
        update_crosstab(
            crosstabs,
            "repairability_band__by_expected_model_stance",
            derived.get("repairability_band") or "<missing>",
            derived.get("expected_model_stance") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "evidence_regime__by_expected_model_stance",
            derived.get("evidence_regime") or "<missing>",
            derived.get("expected_model_stance") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "context_sufficiency_class__by_evidence_regime",
            derived.get("context_sufficiency_class") or "<missing>",
            derived.get("evidence_regime") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "distribution_rights_status__by_license_category",
            derived.get("distribution_rights_status") or "<missing>",
            metadata.get("license_category") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "public_release_bucket__by_expected_model_stance",
            derived.get("public_release_bucket") or "<missing>",
            derived.get("expected_model_stance") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "license_audit_priority__by_expected_model_stance",
            derived.get("license_audit_priority") or "<missing>",
            derived.get("expected_model_stance") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "license_evidence_source__by_license_category",
            derived.get("license_evidence_source") or "<missing>",
            metadata.get("license_category") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "license_detection_method__by_license_category",
            derived.get("license_detection_method") or "<missing>",
            metadata.get("license_category") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "release_view_membership__by_distribution_rights_status",
            derived.get("release_view_membership") or "<missing>",
            derived.get("distribution_rights_status") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "benchmark_view_membership__by_expected_model_stance",
            derived.get("benchmark_view_membership") or "<missing>",
            derived.get("expected_model_stance") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "domain_slice__by_expected_model_stance",
            derived.get("domain_slice") or "<missing>",
            derived.get("expected_model_stance") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "shift_axis__by_expected_model_stance",
            derived.get("shift_axis") or "<missing>",
            derived.get("expected_model_stance") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "permission_response_status__by_distribution_rights_status",
            derived.get("permission_response_status") or "<missing>",
            derived.get("distribution_rights_status") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "manual_license_review_status__by_distribution_rights_status",
            derived.get("manual_license_review_status") or "<missing>",
            derived.get("distribution_rights_status") or "<missing>",
        )
        update_crosstab(
            crosstabs,
            "source_snapshot_granularity__by_license_evidence_source",
            derived.get("source_snapshot_granularity") or "<missing>",
            derived.get("license_evidence_source") or "<missing>",
        )

        if args.max_rows and index >= args.max_rows:
            break

    group_sizes = list(split_group_sizes.values())
    near_duplicate_group_size_values = list(near_duplicate_group_sizes.values())
    split_group_source_counts = field_value_counts["split_group_source"]
    split_group_stats = {
        "unique_groups": len(split_group_sizes),
        "singleton_groups": sum(1 for size in group_sizes if size == 1),
        "non_singleton_groups": sum(1 for size in group_sizes if size > 1),
        "max_group_size": max(group_sizes) if group_sizes else 0,
        "avg_group_size": round(sum(group_sizes) / len(group_sizes), 4) if group_sizes else 0.0,
        "median_group_size": statistics.median(group_sizes) if group_sizes else 0,
        "split_group_source_counts": counter_dict(split_group_source_counts),
    }
    near_duplicate_group_stats = {
        "unique_groups": len(near_duplicate_group_sizes),
        "singleton_groups": sum(1 for size in near_duplicate_group_size_values if size == 1),
        "non_singleton_groups": sum(1 for size in near_duplicate_group_size_values if size > 1),
        "max_group_size": max(near_duplicate_group_size_values) if near_duplicate_group_size_values else 0,
        "avg_group_size": (
            round(sum(near_duplicate_group_size_values) / len(near_duplicate_group_size_values), 4)
            if near_duplicate_group_size_values
            else 0.0
        ),
        "median_group_size": statistics.median(near_duplicate_group_size_values) if near_duplicate_group_size_values else 0,
    }

    report = {
        "input_file": format_display_path(input_file),
        "rows": rows,
        "field_missing_counts": {field: int(field_missing_counts.get(field, 0)) for field in DERIVED_FIELD_NAMES},
        "field_value_counts": {field: counter_dict(counter) for field, counter in field_value_counts.items()},
        "validation_status_counts": counter_dict(validation_status_counts),
        "benchmark_suitability_tier_v2_counts": counter_dict(benchmark_tier_counts),
        "hallucination_type_counts": counter_dict(hallucination_type_counts),
        "split_group_stats": split_group_stats,
        "near_duplicate_group_stats": near_duplicate_group_stats,
        "cross_tabs": nested_counter_dict(crosstabs),
    }

    report_json_file.parent.mkdir(parents=True, exist_ok=True)
    report_json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_file.write_text(build_markdown_report(report), encoding="utf-8")

    print("metadata-design evaluation completed")
    print("  input file       :", format_display_path(input_file))
    print("  report json      :", format_display_path(report_json_file))
    print("  report markdown  :", format_display_path(report_md_file))
    print("  rows             :", f"{rows:,}")
    print("")

    coverage_rows = []
    for field in DERIVED_FIELD_NAMES:
        missing = field_missing_counts.get(field, 0)
        coverage_rows.append([field, rows - missing, missing])
    print("field coverage")
    print(markdown_table(["field", "present_rows", "missing_rows"], coverage_rows))
    print("")

    for field in [
        "source_snapshot_timestamp",
        "source_snapshot_granularity",
        "license_evidence_source",
        "license_detection_method",
        "release_view_membership",
        "benchmark_view_membership",
        "expected_model_stance",
        "context_sufficiency_class",
        "repairability_band",
        "evidence_regime",
        "split_group_source",
        "domain_slice",
        "shift_axis",
        "distribution_rights_status",
        "license_resolution_status",
        "public_release_bucket",
        "license_audit_priority",
        "contact_outreach_status",
        "permission_response_status",
        "manual_license_review_status",
    ]:
        print_counter_block(field, field_value_counts[field])
        print("")

    print("split-group statistics")
    print(f"  unique_groups: {split_group_stats['unique_groups']:,}")
    print(f"  singleton_groups: {split_group_stats['singleton_groups']:,}")
    print(f"  non_singleton_groups: {split_group_stats['non_singleton_groups']:,}")
    print(f"  max_group_size: {split_group_stats['max_group_size']:,}")
    print(f"  avg_group_size: {split_group_stats['avg_group_size']}")
    print(f"  median_group_size: {split_group_stats['median_group_size']}")
    print("")

    print("near-duplicate-group statistics")
    print(f"  unique_groups: {near_duplicate_group_stats['unique_groups']:,}")
    print(f"  singleton_groups: {near_duplicate_group_stats['singleton_groups']:,}")
    print(f"  non_singleton_groups: {near_duplicate_group_stats['non_singleton_groups']:,}")
    print(f"  max_group_size: {near_duplicate_group_stats['max_group_size']:,}")
    print(f"  avg_group_size: {near_duplicate_group_stats['avg_group_size']}")
    print(f"  median_group_size: {near_duplicate_group_stats['median_group_size']}")
    print("")

    for table_name in [
        "expected_model_stance__by_validation_status",
        "expected_model_stance__by_benchmark_suitability_tier_v2",
        "repairability_band__by_expected_model_stance",
        "distribution_rights_status__by_license_category",
        "public_release_bucket__by_expected_model_stance",
        "license_audit_priority__by_expected_model_stance",
        "license_evidence_source__by_license_category",
        "license_detection_method__by_license_category",
        "release_view_membership__by_distribution_rights_status",
        "benchmark_view_membership__by_expected_model_stance",
        "domain_slice__by_expected_model_stance",
        "shift_axis__by_expected_model_stance",
        "permission_response_status__by_distribution_rights_status",
        "manual_license_review_status__by_distribution_rights_status",
        "source_snapshot_granularity__by_license_evidence_source",
    ]:
        table = report["cross_tabs"][table_name]
        column_names = sorted({column for row in table.values() for column in row})
        headers = ["row_key", *column_names]
        rows_out = []
        for row_key, row_values in table.items():
            rows_out.append([row_key, *[row_values.get(column, 0) for column in column_names]])
        print(table_name)
        print(markdown_table(headers, rows_out))
        print("")


if __name__ == "__main__":
    main()
