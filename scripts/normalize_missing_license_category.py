"""
Normalize residual missing license-category metadata.

The final release audit found 18 instruction rows from one legacy gist family
whose release-governance fields already marked them as unresolved/no-license
and restricted/internal-only, but whose `metadata.license_category` field was
left null. This script makes that state explicit by setting
`license_category = no_license` for those rows.

The update does not alter public-release eligibility; it only removes the
ambiguous `<missing>` category from release-distribution summaries.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from project_paths import PROCESSED_DIR, format_display_path


OWNER_REPO = "IvanIsCoding/gist-988251a65389706b0e067a0a0c42a579"
REPO_OWNER = "IvanIsCoding"
REPO_NAME = "gist-988251a65389706b0e067a0a0c42a579"
NORMALIZATION_VERSION = "missing_license_category_normalization_2026_05_03_v1"

TARGET_FILES = {
    "train": PROCESSED_DIR / "train_clean.jsonl",
    "validation": PROCESSED_DIR / "validation_clean.jsonl",
    "test": PROCESSED_DIR / "test_clean.jsonl",
    "benchmark_master": PROCESSED_DIR / "pqid_2026_master_corpus.jsonl",
}

EVIDENCE_DIR = PROCESSED_DIR / "license_evidence"
EVIDENCE_FILE = EVIDENCE_DIR / "missing_license_category_normalization_2026-05-03.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Count affected rows and write nothing.")
    return parser.parse_args()


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl_row(handle, row: dict[str, Any]) -> None:
    handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def is_target_row(row: dict[str, Any]) -> bool:
    metadata = row.get("metadata") or {}
    owner = str(metadata.get("repo_owner") or "").strip()
    name = str(metadata.get("repo_name") or "").strip()
    if owner == REPO_OWNER and name == REPO_NAME:
        return True
    original_url = str(metadata.get("original_url") or "").strip()
    return OWNER_REPO in original_url


def needs_patch(row: dict[str, Any]) -> bool:
    metadata = row.get("metadata") or {}
    return is_target_row(row) and not str(metadata.get("license_category") or "").strip()


def patch_row(row: dict[str, Any]) -> dict[str, Any]:
    patched = dict(row)
    metadata = dict(patched.get("metadata") or {})
    previous = {
        "repo_license": metadata.get("repo_license"),
        "license_category": metadata.get("license_category"),
        "license_evidence_source": metadata.get("license_evidence_source"),
        "license_detection_method": metadata.get("license_detection_method"),
        "license_resolution_status": metadata.get("license_resolution_status"),
        "distribution_rights_status": metadata.get("distribution_rights_status"),
        "public_release_bucket": metadata.get("public_release_bucket"),
    }
    metadata.update(
        {
            "repo_license": metadata.get("repo_license"),
            "license_category": "no_license",
            "license_evidence_source": "missing",
            "license_detection_method": "legacy_gist_missing_license_metadata_normalization",
            "license_resolution_status": "unresolved_no_license",
            "distribution_rights_status": "unresolved_no_license",
            "public_release_bucket": "restricted_internal_only",
            "release_view_membership": "restricted_index",
            "manual_license_review_status": metadata.get("manual_license_review_status") or "not_started",
            "permission_response_status": metadata.get("permission_response_status") or "not_contacted",
            "license_category_normalization_version": NORMALIZATION_VERSION,
            "license_category_normalization_reason": (
                "Residual null license_category was normalized to no_license because "
                "the row already had unresolved_no_license governance status and "
                "belongs to a legacy gist family with no usable repository-license evidence."
            ),
            "license_category_previous_state": previous,
        }
    )
    patched["metadata"] = metadata
    return patched


def patch_file(path: Path, *, dry_run: bool) -> dict[str, Any]:
    tmp_path = Path(str(path) + f".{NORMALIZATION_VERSION}.tmp")
    input_rows = 0
    patched_rows = 0
    previous_categories: Counter[str] = Counter()
    previous_statuses: Counter[str] = Counter()

    out_handle = None
    try:
        if not dry_run:
            out_handle = tmp_path.open("w", encoding="utf-8")
        for row in iter_jsonl(path):
            input_rows += 1
            if needs_patch(row):
                metadata = row.get("metadata") or {}
                previous_categories[str(metadata.get("license_category") or "<missing>")] += 1
                previous_statuses[str(metadata.get("license_resolution_status") or "<missing>")] += 1
                row = patch_row(row)
                patched_rows += 1
            if out_handle is not None:
                write_jsonl_row(out_handle, row)
    finally:
        if out_handle is not None:
            out_handle.close()

    if not dry_run:
        tmp_path.replace(path)

    return {
        "input_rows": input_rows,
        "patched_rows": patched_rows,
        "previous_license_category_counts": dict(sorted(previous_categories.items())),
        "previous_license_resolution_status_counts": dict(sorted(previous_statuses.items())),
    }


def main() -> None:
    args = parse_args()
    file_summaries = {}
    for label, path in TARGET_FILES.items():
        file_summaries[label] = patch_file(path, dry_run=args.dry_run)

    total_patched = sum(summary["patched_rows"] for summary in file_summaries.values())
    evidence = {
        "evidence_version": NORMALIZATION_VERSION,
        "owner_repo": OWNER_REPO,
        "interpretation": (
            "Rows from this legacy gist family were already restricted/internal-only "
            "with unresolved_no_license status. The null license_category field was "
            "normalized to no_license so release summaries no longer expose a vague "
            "<missing> category."
        ),
        "public_release_effect": (
            "No rows are added to public release views; affected rows remain restricted/internal-only."
        ),
        "file_summaries": file_summaries,
        "total_patched_rows": total_patched,
    }
    if not args.dry_run:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        EVIDENCE_FILE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    print("missing license-category normalization")
    print("  dry run      :", args.dry_run)
    print("  owner/repo   :", OWNER_REPO)
    print("  total patched:", f"{total_patched:,}")
    for label, summary in file_summaries.items():
        print(f"  {label:<16}: {summary['patched_rows']:,} / {summary['input_rows']:,}")
    if not args.dry_run:
        print("  evidence     :", format_display_path(EVIDENCE_FILE))


if __name__ == "__main__":
    main()
