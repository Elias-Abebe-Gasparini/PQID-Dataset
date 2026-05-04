"""
export_license_valid_release_views.py
-------------------------------------
Export publication-facing PQID instruction splits that exclude unresolved or
review-required license buckets.

The canonical instruction splits intentionally remain construction artifacts.
This script writes separate release views so public packaging can include only
license-resolved rows while preserving the original split labels and metadata.

Profiles:
- public_open: permissive-license rows only
- license_valid: permissive + copyleft rows, with copyleft rows retained in a
  separate `public_open_with_obligations` bucket, plus manually reviewed
  `other` license rows when the detected license is in the approved override
  list below.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import sys
from pathlib import Path
from typing import Any

from project_paths import PROCESSED_DIR, format_display_path


EXPORT_VERSION = "pqid_license_valid_release_v1"
MANUAL_LICENSE_REVIEW_VERSION = "pqid_manual_license_review_2026_04_26_v1"
MISSING_LICENSE_INTERNAL_VERSION = "pqid_missing_license_internal_only_v1"

MANUALLY_REVIEWED_OTHER_LICENSES = {
    "BSD-3-Clause-Clear",
    "CC-BY-4.0",
    "EPL-2.0",
    "MulanPSL-2.0",
}

SPLIT_FILES = {
    "train": "train_clean.jsonl",
    "validation": "validation_clean.jsonl",
    "test": "test_clean.jsonl",
}

PROFILE_CONFIG = {
    "public_open": {
        "license_categories": {"permissive"},
        "output_stem": "pqid_v1_public_open",
        "description": "Permissive-license rows only.",
    },
    "license_valid": {
        "license_categories": {"permissive", "copyleft"},
        "include_reviewed_other": True,
        "output_stem": "pqid_v1_license_valid",
        "description": (
            "License-resolved rows: permissive, copyleft, and manually reviewed other-license rows "
            "with obligations preserved."
        ),
    },
}

GOVERNANCE_BY_LICENSE_CATEGORY = {
    "permissive": {
        "distribution_rights_status": "redistributable_permissive",
        "license_resolution_status": "resolved",
        "public_release_bucket": "public_open",
        "release_view_membership": "public_open",
    },
    "copyleft": {
        "distribution_rights_status": "redistributable_copyleft",
        "license_resolution_status": "resolved",
        "public_release_bucket": "public_open_with_obligations",
        "release_view_membership": "public_obligations",
    },
    "other": {
        "distribution_rights_status": "reviewed_other_license",
        "license_resolution_status": "resolved_after_manual_review",
        "public_release_bucket": "public_open_with_obligations",
        "release_view_membership": "public_obligations",
        "manual_license_review_status": "reviewed_release_approved",
        "permission_response_status": "not_applicable_after_manual_review",
        "release_manual_review_version": MANUAL_LICENSE_REVIEW_VERSION,
        "release_obligation_note": (
            "License category was manually reviewed for public release eligibility; "
            "preserve attribution and license-specific obligations."
        ),
    },
    "<missing>": {
        "distribution_rights_status": "unresolved_no_license",
        "license_resolution_status": "unresolved_no_license",
        "public_release_bucket": "restricted_internal_only",
        "release_view_membership": "restricted_index",
        "manual_license_review_status": "not_started",
        "permission_response_status": "not_contacted",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_CONFIG),
        default="license_valid",
        help="Release profile to export.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROCESSED_DIR / "release_views"),
        help="Directory where release-view files should be written.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing output files.",
    )
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl_row(handle, row: dict[str, Any]) -> None:
    handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalized_license_category(row: dict[str, Any]) -> str:
    metadata = row.get("metadata") or {}
    return str(metadata.get("license_category") or "<missing>").strip() or "<missing>"


def normalized_repo_license(row: dict[str, Any]) -> str:
    metadata = row.get("metadata") or {}
    return str(metadata.get("repo_license") or "<missing>").strip() or "<missing>"


def include_row(row: dict[str, Any], *, profile: str) -> bool:
    config = PROFILE_CONFIG[profile]
    category = normalized_license_category(row)
    if category in config["license_categories"]:
        return True
    if category == "other" and config.get("include_reviewed_other", False):
        return normalized_repo_license(row) in MANUALLY_REVIEWED_OTHER_LICENSES
    return False


def apply_release_metadata(row: dict[str, Any], *, split: str, profile: str) -> dict[str, Any]:
    exported = dict(row)
    metadata = dict(exported.get("metadata") or {})
    category = normalized_license_category(row)
    governance = GOVERNANCE_BY_LICENSE_CATEGORY.get(category, {})
    metadata.update(governance)
    metadata["release_export_version"] = EXPORT_VERSION
    metadata["release_export_profile"] = profile
    metadata["release_split"] = split
    metadata["release_filter_basis"] = "license_category"
    exported["metadata"] = metadata
    return exported


def apply_missing_license_internal_metadata(row: dict[str, Any], *, split: str) -> dict[str, Any]:
    exported = dict(row)
    metadata = dict(exported.get("metadata") or {})
    metadata.update(GOVERNANCE_BY_LICENSE_CATEGORY["<missing>"])
    metadata["release_export_version"] = MISSING_LICENSE_INTERNAL_VERSION
    metadata["release_export_profile"] = "missing_license_internal_only"
    metadata["release_split"] = split
    metadata["release_filter_basis"] = "missing_license_category"
    exported["metadata"] = metadata
    return exported


def repo_key(metadata: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(metadata.get("repo_owner") or "<missing>").strip(),
        str(metadata.get("repo_name") or "<missing>").strip(),
        str(metadata.get("repo_license") or "<missing>").strip(),
        str(metadata.get("license_category") or "<missing>").strip(),
    )


def add_attribution(attribution: dict[tuple[str, str, str, str], dict[str, Any]], row: dict[str, Any]) -> None:
    metadata = row.get("metadata") or {}
    key = repo_key(metadata)
    entry = attribution.setdefault(
        key,
        {
            "repo_owner": key[0],
            "repo_name": key[1],
            "repo_license": key[2],
            "license_category": key[3],
            "rows": 0,
            "source_urls": set(),
        },
    )
    entry["rows"] += 1
    original_url = str(metadata.get("original_url") or "").strip()
    if original_url:
        entry["source_urls"].add(original_url)


def write_attribution_csv(attribution: dict[tuple[str, str, str, str], dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "repo_owner",
        "repo_name",
        "repo_license",
        "license_category",
        "rows",
        "source_url_count",
        "sample_source_url",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for entry in sorted(attribution.values(), key=lambda item: (-item["rows"], item["repo_owner"], item["repo_name"])):
            urls = sorted(entry["source_urls"])
            writer.writerow(
                {
                    "repo_owner": entry["repo_owner"],
                    "repo_name": entry["repo_name"],
                    "repo_license": entry["repo_license"],
                    "license_category": entry["license_category"],
                    "rows": entry["rows"],
                    "source_url_count": len(urls),
                    "sample_source_url": urls[0] if urls else "",
                }
            )


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    text_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in text_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def fmt(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(values)) + " |"

    return "\n".join(
        [
            fmt(headers),
            "| " + " | ".join("-" * width for width in widths) + " |",
            *(fmt(row) for row in text_rows),
        ]
    )


def build_markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# PQID License-Valid Release View",
        "",
        f"- export version: `{summary['export_version']}`",
        f"- profile: `{summary['profile']}`",
        f"- description: {summary['profile_description']}",
        f"- included license categories: `{', '.join(summary['included_license_categories'])}`",
        f"- manually reviewed other licenses: `{', '.join(summary['manually_reviewed_other_licenses']) or 'none'}`",
        f"- total input rows: `{summary['total_input_rows']:,}`",
        f"- total exported rows: `{summary['total_exported_rows']:,}`",
        f"- total excluded rows: `{summary['total_excluded_rows']:,}`",
        "",
        "## Split Counts",
        "",
    ]
    split_rows = []
    for split, stats in summary["splits"].items():
        split_rows.append([split, stats["input_rows"], stats["exported_rows"], stats["excluded_rows"]])
    lines.append(markdown_table(["split", "input_rows", "exported_rows", "excluded_rows"], split_rows))
    lines.extend(["", "## Exported License Categories", ""])
    lines.append(
        markdown_table(
            ["license_category", "rows"],
            [[key, value] for key, value in summary["exported_license_category_counts"].items()],
        )
    )
    lines.extend(["", "## Excluded License Categories", ""])
    lines.append(
        markdown_table(
            ["license_category", "rows"],
            [[key, value] for key, value in summary["excluded_license_category_counts"].items()],
        )
    )
    lines.extend(
        [
            "",
            "## Release Rule",
            "",
            "Rows with `license_category` outside the selected profile are excluded from this release view.",
            "`no_license` rows are not exported. Residual missing license-category rows, if present, are treated as restricted governance-metadata gaps.",
            "`other` rows are exported only when their detected license appears in the manual review override list.",
            "Copyleft rows, when included by profile, remain marked as `public_open_with_obligations` and should not be presented as obligation-free.",
            "",
        ]
    )
    return "\n".join(lines)


def ensure_can_write(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise SystemExit(
            f"ERROR: output exists: {format_display_path(path)}. Re-run with --overwrite to replace it."
        )


def main() -> None:
    args = parse_args()
    profile = args.profile
    config = PROFILE_CONFIG[profile]
    included_categories = set(config["license_categories"])
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_stem = config["output_stem"]

    split_output_paths = {
        split: output_dir / f"{output_stem}_{split}.jsonl"
        for split in SPLIT_FILES
    }
    summary_json_path = output_dir / f"{output_stem}_summary.json"
    summary_md_path = output_dir / f"{output_stem}_summary.md"
    attribution_csv_path = output_dir / f"{output_stem}_attribution_manifest.csv"
    missing_license_internal_path = output_dir / "pqid_v1_missing_license_internal_only.jsonl"
    missing_license_internal_summary_path = output_dir / "pqid_v1_missing_license_internal_only_summary.json"

    for path in [
        *split_output_paths.values(),
        summary_json_path,
        summary_md_path,
        attribution_csv_path,
        missing_license_internal_path,
        missing_license_internal_summary_path,
    ]:
        ensure_can_write(path, args.overwrite)

    total_input_rows = 0
    total_exported_rows = 0
    total_excluded_rows = 0
    exported_category_counts: Counter[str] = Counter()
    excluded_category_counts: Counter[str] = Counter()
    included_other_license_counts: Counter[str] = Counter()
    missing_license_split_counts: Counter[str] = Counter()
    split_summaries: dict[str, dict[str, Any]] = {}
    attribution: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    excluded_repositories: dict[str, Counter[str]] = defaultdict(Counter)

    with missing_license_internal_path.open("w", encoding="utf-8") as missing_handle:
        for split, filename in SPLIT_FILES.items():
            input_path = PROCESSED_DIR / filename
            output_path = split_output_paths[split]
            input_rows = 0
            exported_rows = 0
            excluded_rows = 0
            split_exported_counts: Counter[str] = Counter()
            split_excluded_counts: Counter[str] = Counter()

            with output_path.open("w", encoding="utf-8") as out_handle:
                for row in iter_jsonl(input_path):
                    input_rows += 1
                    category = normalized_license_category(row)
                    repo_license = normalized_repo_license(row)
                    if include_row(row, profile=profile):
                        exported = apply_release_metadata(row, split=split, profile=profile)
                        write_jsonl_row(out_handle, exported)
                        add_attribution(attribution, exported)
                        exported_rows += 1
                        split_exported_counts[category] += 1
                        exported_category_counts[category] += 1
                        if category == "other":
                            included_other_license_counts[repo_license] += 1
                    else:
                        excluded_rows += 1
                        split_excluded_counts[category] += 1
                        excluded_category_counts[category] += 1
                        metadata = row.get("metadata") or {}
                        excluded_repositories[
                            f"{metadata.get('repo_owner') or '<missing>'}/{metadata.get('repo_name') or '<missing>'}"
                        ][category] += 1
                        if category == "<missing>":
                            internal_row = apply_missing_license_internal_metadata(row, split=split)
                            write_jsonl_row(missing_handle, internal_row)
                            missing_license_split_counts[split] += 1

            total_input_rows += input_rows
            total_exported_rows += exported_rows
            total_excluded_rows += excluded_rows
            split_summaries[split] = {
                "input_file": format_display_path(input_path),
                "output_file": format_display_path(output_path),
                "input_rows": input_rows,
                "exported_rows": exported_rows,
                "excluded_rows": excluded_rows,
                "exported_license_category_counts": dict(sorted(split_exported_counts.items())),
                "excluded_license_category_counts": dict(sorted(split_excluded_counts.items())),
            }

    write_attribution_csv(attribution, attribution_csv_path)

    top_excluded_repositories = []
    for repo, counter in excluded_repositories.items():
        total = sum(counter.values())
        top_excluded_repositories.append(
            {
                "repo": repo,
                "excluded_rows": total,
                "excluded_license_category_counts": dict(sorted(counter.items())),
            }
        )
    top_excluded_repositories.sort(key=lambda item: item["excluded_rows"], reverse=True)

    summary = {
        "export_version": EXPORT_VERSION,
        "profile": profile,
        "profile_description": config["description"],
        "included_license_categories": sorted(exported_category_counts),
        "include_reviewed_other": bool(config.get("include_reviewed_other", False)),
        "manually_reviewed_other_licenses": sorted(MANUALLY_REVIEWED_OTHER_LICENSES)
        if config.get("include_reviewed_other", False)
        else [],
        "output_dir": format_display_path(output_dir),
        "splits": split_summaries,
        "summary_json_file": format_display_path(summary_json_path),
        "summary_markdown_file": format_display_path(summary_md_path),
        "attribution_manifest_file": format_display_path(attribution_csv_path),
        "total_input_rows": total_input_rows,
        "total_exported_rows": total_exported_rows,
        "total_excluded_rows": total_excluded_rows,
        "exported_license_category_counts": dict(sorted(exported_category_counts.items())),
        "excluded_license_category_counts": dict(sorted(excluded_category_counts.items())),
        "included_other_license_counts": dict(sorted(included_other_license_counts.items())),
        "missing_license_internal_file": format_display_path(missing_license_internal_path),
        "missing_license_internal_summary_file": format_display_path(missing_license_internal_summary_path),
        "missing_license_internal_rows": sum(missing_license_split_counts.values()),
        "missing_license_internal_split_counts": dict(sorted(missing_license_split_counts.items())),
        "top_excluded_repositories": top_excluded_repositories[:50],
        "release_rule": (
            "Export rows whose metadata.license_category is in the selected profile. "
            + (
                "Export `other` rows only when their detected license appears in the "
                "manual review override list. "
                if config.get("include_reviewed_other", False)
                else "Exclude `other` rows. "
            )
            + "Always exclude no_license rows; residual missing license-category rows, if present, are restricted governance-metadata gaps."
        ),
    }
    summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_markdown_summary(summary), encoding="utf-8")
    missing_summary = {
        "export_version": MISSING_LICENSE_INTERNAL_VERSION,
        "output_file": format_display_path(missing_license_internal_path),
        "rows": sum(missing_license_split_counts.values()),
        "split_counts": dict(sorted(missing_license_split_counts.items())),
        "release_status": "restricted_internal_only",
        "reason": "missing license metadata",
    }
    missing_license_internal_summary_path.write_text(
        json.dumps(missing_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("license-valid release view exported")
    print("  profile       :", profile)
    print("  output dir    :", format_display_path(output_dir))
    print("  input rows    :", f"{total_input_rows:,}")
    print("  exported rows :", f"{total_exported_rows:,}")
    print("  excluded rows :", f"{total_excluded_rows:,}")
    print("  summary       :", format_display_path(summary_json_path))
    print("  attribution   :", format_display_path(attribution_csv_path))


if __name__ == "__main__":
    main()
