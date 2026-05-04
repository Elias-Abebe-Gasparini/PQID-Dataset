"""
audit_pqid_license_governance.py
--------------------------------
Build a governance-oriented audit over the metadata-enriched PQID corpus with a
focus on release constraints caused by missing or unresolved repository
licenses.

This script does not relabel the dataset. It summarizes:
- release buckets and distribution-rights states across rows
- concentration of unresolved no-license rows by repository
- which unresolved repositories matter most for validated / generation-facing
  subsets
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from metadata_design_common import DEFAULT_MERGED_OUTPUT_FILE, jsonl_rows


DEFAULT_INPUT_FILE = PROCESSED_DIR / DEFAULT_MERGED_OUTPUT_FILE
DEFAULT_REPORT_JSON_FILE = PROCESSED_DIR / "pqid_license_governance_report_v3.json"
DEFAULT_REPORT_MD_FILE = PROCESSED_DIR / "pqid_license_governance_report_v3.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-file",
        default=str(DEFAULT_INPUT_FILE),
        help="Merged corpus view that already includes the metadata-design and license-governance fields.",
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
    parser.add_argument(
        "--top-k",
        type=int,
        default=25,
        help="Number of top unresolved repositories to retain in the report.",
    )
    return parser.parse_args()


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


def counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common()}


def repo_key(metadata: dict[str, Any]) -> str:
    owner = str(metadata.get("repo_owner") or "<missing>").strip()
    name = str(metadata.get("repo_name") or "<missing>").strip()
    return f"{owner}/{name}"


def compute_priority_score(stats: dict[str, Any]) -> int:
    return (
        stats["rows"]
        + 4 * stats["validated_rows"]
        + 2 * stats["non_diagnose_rows"]
        + 2 * stats["generate_rows"]
        + 1 * stats["repair_rows"]
        + 1 * stats["robustness_compare_rows"]
    )


def build_markdown_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# PQID License Governance Report")
    lines.append("")
    lines.append(f"- input file: `{report['input_file']}`")
    lines.append(f"- rows: `{report['rows']:,}`")
    lines.append("")

    lines.append("## Release State Overview")
    lines.append("")
    overview_rows = []
    for section_name in [
        "license_category_counts",
        "distribution_rights_status_counts",
        "public_release_bucket_counts",
        "license_audit_priority_counts",
        "permission_response_status_counts",
        "manual_license_review_status_counts",
    ]:
        for key, value in report[section_name].items():
            overview_rows.append([section_name, key, value])
    lines.append(markdown_table(["section", "value", "count"], overview_rows))
    lines.append("")

    lines.append("## Unresolved No-License Breakdown")
    lines.append("")
    for section_name in [
        "unresolved_no_license_by_validation_status",
        "unresolved_no_license_by_expected_model_stance",
        "unresolved_no_license_by_retrieval_strategy",
        "unresolved_no_license_by_source",
    ]:
        lines.append(f"### `{section_name}`")
        rows = [[key, value] for key, value in report[section_name].items()]
        lines.append("")
        lines.append(markdown_table(["value", "count"], rows))
        lines.append("")

    lines.append("## Top Unresolved Repositories")
    lines.append("")
    top_repo_rows = []
    for repo in report["top_unresolved_repositories"]:
        top_repo_rows.append(
            [
                repo["repo"],
                repo["rows"],
                repo["validated_rows"],
                repo["generate_rows"],
                repo["repair_rows"],
                repo["robustness_compare_rows"],
                repo["priority_score"],
            ]
        )
    lines.append(
        markdown_table(
            [
                "repo",
                "rows",
                "validated_rows",
                "generate_rows",
                "repair_rows",
                "robustness_compare_rows",
                "priority_score",
            ],
            top_repo_rows,
        )
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    input_file = Path(args.input_file)
    report_json_file = Path(args.report_json_file)
    report_md_file = Path(args.report_md_file)

    license_category_counts: Counter[str] = Counter()
    distribution_rights_status_counts: Counter[str] = Counter()
    public_release_bucket_counts: Counter[str] = Counter()
    license_audit_priority_counts: Counter[str] = Counter()
    permission_response_status_counts: Counter[str] = Counter()
    manual_license_review_status_counts: Counter[str] = Counter()

    unresolved_no_license_by_validation_status: Counter[str] = Counter()
    unresolved_no_license_by_expected_model_stance: Counter[str] = Counter()
    unresolved_no_license_by_retrieval_strategy: Counter[str] = Counter()
    unresolved_no_license_by_source: Counter[str] = Counter()

    unresolved_repo_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "rows": 0,
            "validated_rows": 0,
            "non_diagnose_rows": 0,
            "generate_rows": 0,
            "repair_rows": 0,
            "robustness_compare_rows": 0,
            "retrieval_strategies": Counter(),
            "sources": Counter(),
        }
    )

    rows = 0
    for index, row in enumerate(jsonl_rows(input_file), start=1):
        metadata = row.get("metadata", {})
        rows += 1

        license_category = str(metadata.get("license_category") or "<missing>")
        distribution_rights_status = str(metadata.get("distribution_rights_status") or "<missing>")
        public_release_bucket = str(metadata.get("public_release_bucket") or "<missing>")
        license_audit_priority = str(metadata.get("license_audit_priority") or "<missing>")
        permission_response_status = str(metadata.get("permission_response_status") or "<missing>")
        manual_license_review_status = str(metadata.get("manual_license_review_status") or "<missing>")

        license_category_counts[license_category] += 1
        distribution_rights_status_counts[distribution_rights_status] += 1
        public_release_bucket_counts[public_release_bucket] += 1
        license_audit_priority_counts[license_audit_priority] += 1
        permission_response_status_counts[permission_response_status] += 1
        manual_license_review_status_counts[manual_license_review_status] += 1

        if distribution_rights_status == "unresolved_no_license":
            validation_status = str(metadata.get("validation_status") or "<missing>")
            expected_model_stance = str(metadata.get("expected_model_stance") or "<missing>")
            retrieval_strategy = str(metadata.get("retrieval_strategy") or "<missing>")
            source = str(metadata.get("source") or "<missing>")
            repo = repo_key(metadata)

            unresolved_no_license_by_validation_status[validation_status] += 1
            unresolved_no_license_by_expected_model_stance[expected_model_stance] += 1
            unresolved_no_license_by_retrieval_strategy[retrieval_strategy] += 1
            unresolved_no_license_by_source[source] += 1

            stats = unresolved_repo_stats[repo]
            stats["rows"] += 1
            if validation_status == "validated":
                stats["validated_rows"] += 1
            if expected_model_stance != "diagnose":
                stats["non_diagnose_rows"] += 1
            if expected_model_stance == "generate":
                stats["generate_rows"] += 1
            elif expected_model_stance == "repair":
                stats["repair_rows"] += 1
            elif expected_model_stance == "robustness_compare":
                stats["robustness_compare_rows"] += 1
            stats["retrieval_strategies"][retrieval_strategy] += 1
            stats["sources"][source] += 1

        if args.max_rows and index >= args.max_rows:
            break

    top_unresolved_repositories = []
    for repo, stats in unresolved_repo_stats.items():
        top_unresolved_repositories.append(
            {
                "repo": repo,
                "rows": stats["rows"],
                "validated_rows": stats["validated_rows"],
                "non_diagnose_rows": stats["non_diagnose_rows"],
                "generate_rows": stats["generate_rows"],
                "repair_rows": stats["repair_rows"],
                "robustness_compare_rows": stats["robustness_compare_rows"],
                "priority_score": compute_priority_score(stats),
                "top_retrieval_strategy": stats["retrieval_strategies"].most_common(1)[0][0]
                if stats["retrieval_strategies"]
                else "<missing>",
                "top_source": stats["sources"].most_common(1)[0][0] if stats["sources"] else "<missing>",
            }
        )

    top_unresolved_repositories.sort(
        key=lambda item: (
            item["priority_score"],
            item["rows"],
            item["validated_rows"],
        ),
        reverse=True,
    )

    report = {
        "input_file": format_display_path(input_file),
        "rows": rows,
        "license_category_counts": counter_dict(license_category_counts),
        "distribution_rights_status_counts": counter_dict(distribution_rights_status_counts),
        "public_release_bucket_counts": counter_dict(public_release_bucket_counts),
        "license_audit_priority_counts": counter_dict(license_audit_priority_counts),
        "permission_response_status_counts": counter_dict(permission_response_status_counts),
        "manual_license_review_status_counts": counter_dict(manual_license_review_status_counts),
        "unresolved_no_license_by_validation_status": counter_dict(unresolved_no_license_by_validation_status),
        "unresolved_no_license_by_expected_model_stance": counter_dict(
            unresolved_no_license_by_expected_model_stance
        ),
        "unresolved_no_license_by_retrieval_strategy": counter_dict(unresolved_no_license_by_retrieval_strategy),
        "unresolved_no_license_by_source": counter_dict(unresolved_no_license_by_source),
        "top_unresolved_repositories": top_unresolved_repositories[: args.top_k],
    }

    report_json_file.parent.mkdir(parents=True, exist_ok=True)
    report_json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_file.write_text(build_markdown_report(report), encoding="utf-8")

    print("license-governance audit completed")
    print("  input file      :", format_display_path(input_file))
    print("  report json     :", format_display_path(report_json_file))
    print("  report markdown :", format_display_path(report_md_file))
    print("  rows            :", f"{rows:,}")
    print("")

    for title, counter in [
        ("license_category", license_category_counts),
        ("distribution_rights_status", distribution_rights_status_counts),
        ("public_release_bucket", public_release_bucket_counts),
        ("license_audit_priority", license_audit_priority_counts),
        ("permission_response_status", permission_response_status_counts),
        ("manual_license_review_status", manual_license_review_status_counts),
    ]:
        print(title)
        for key, value in counter.most_common():
            print(f"  {key}: {value:,}")
        print("")

    print("top unresolved repositories")
    for item in top_unresolved_repositories[: min(args.top_k, 15)]:
        print(
            f"  {item['repo']}: rows={item['rows']:,} | validated={item['validated_rows']:,} | "
            f"generate={item['generate_rows']:,} | repair={item['repair_rows']:,} | "
            f"robustness_compare={item['robustness_compare_rows']:,} | priority={item['priority_score']:,}"
        )


if __name__ == "__main__":
    main()
