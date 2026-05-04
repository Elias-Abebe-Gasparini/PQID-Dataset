"""
derive_pqid_metadata_design_fields.py
------------------------------------
Build an additive metadata-design overlay for the full PQID enriched corpus and
materialize a merged corpus view that preserves the original records while
adding conservative behavior-oriented metadata.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from metadata_design_common import (
    DEFAULT_BASE_INPUT_FILE,
    DEFAULT_MASTER_OVERLAY_FILE,
    DEFAULT_MERGED_OUTPUT_FILE,
    DEFAULT_OVERLAY_OUTPUT_FILE,
    DERIVED_FIELD_NAMES,
    METADATA_DESIGN_VERSION,
    derive_metadata_design_fields,
    jsonl_rows,
    load_master_overlay_index,
    merge_master_overlay,
    write_jsonl_row,
)


DEFAULT_INPUT_FILE = PROCESSED_DIR / DEFAULT_BASE_INPUT_FILE
DEFAULT_MASTER_FILE = PROCESSED_DIR / DEFAULT_MASTER_OVERLAY_FILE
DEFAULT_OVERLAY_FILE = PROCESSED_DIR / DEFAULT_OVERLAY_OUTPUT_FILE
DEFAULT_MERGED_FILE = PROCESSED_DIR / DEFAULT_MERGED_OUTPUT_FILE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-file",
        default=str(DEFAULT_INPUT_FILE),
        help="Base enriched PQID corpus.",
    )
    parser.add_argument(
        "--master-overlay-file",
        default=str(DEFAULT_MASTER_FILE),
        help="Master corpus used to overlay benchmark and semantic metadata.",
    )
    parser.add_argument(
        "--overlay-output-file",
        default=str(DEFAULT_OVERLAY_FILE),
        help="JSONL sidecar with only the new metadata-design fields.",
    )
    parser.add_argument(
        "--merged-output-file",
        default=str(DEFAULT_MERGED_FILE),
        help="Merged corpus JSONL with additive metadata-design fields written into metadata.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap for dry runs and smoke tests.",
    )
    return parser.parse_args()


def build_overlay_row(record: dict, merged_meta: dict, derived_fields: dict) -> dict:
    return {
        "circuit_hash": merged_meta.get("circuit_hash"),
        "content_hash": merged_meta.get("content_hash"),
        "metadata_design_version": METADATA_DESIGN_VERSION,
        "source_record": {
            "repo_owner": merged_meta.get("repo_owner"),
            "repo_name": merged_meta.get("repo_name"),
            "file_path": merged_meta.get("file_path"),
            "original_url": merged_meta.get("original_url"),
        },
        "metadata_design_fields": derived_fields,
    }


def build_merged_row(record: dict, merged_meta: dict, derived_fields: dict) -> dict:
    merged_row = json.loads(json.dumps(record))
    merged_row["metadata"] = dict(merged_meta)
    for key, value in derived_fields.items():
        merged_row["metadata"][key] = value
    return merged_row


def main() -> None:
    args = parse_args()
    input_file = Path(args.input_file)
    master_overlay_file = Path(args.master_overlay_file)
    overlay_output_file = Path(args.overlay_output_file)
    merged_output_file = Path(args.merged_output_file)

    overlay_index = load_master_overlay_index(master_overlay_file)

    stance_counts: Counter[str] = Counter()
    snapshot_counts: Counter[str] = Counter()
    snapshot_granularity_counts: Counter[str] = Counter()
    license_evidence_source_counts: Counter[str] = Counter()
    license_detection_method_counts: Counter[str] = Counter()
    release_view_membership_counts: Counter[str] = Counter()
    benchmark_view_membership_counts: Counter[str] = Counter()
    context_counts: Counter[str] = Counter()
    repairability_counts: Counter[str] = Counter()
    evidence_regime_counts: Counter[str] = Counter()
    split_group_source_counts: Counter[str] = Counter()
    domain_slice_counts: Counter[str] = Counter()
    shift_axis_counts: Counter[str] = Counter()
    distribution_rights_counts: Counter[str] = Counter()
    public_release_bucket_counts: Counter[str] = Counter()
    license_audit_priority_counts: Counter[str] = Counter()
    permission_response_status_counts: Counter[str] = Counter()
    manual_license_review_status_counts: Counter[str] = Counter()
    lineage_parent_ids: set[str] = set()

    rows_written = 0
    overlaid_rows = 0

    overlay_output_file.parent.mkdir(parents=True, exist_ok=True)
    merged_output_file.parent.mkdir(parents=True, exist_ok=True)

    with (
        overlay_output_file.open("w", encoding="utf-8") as overlay_handle,
        merged_output_file.open("w", encoding="utf-8") as merged_handle,
    ):
        for index, record in enumerate(jsonl_rows(input_file), start=1):
            base_meta = record.get("metadata", {})
            circuit_hash = str(base_meta.get("circuit_hash") or "")
            merged_meta = merge_master_overlay(base_meta, overlay_index.get(circuit_hash))
            if circuit_hash and circuit_hash in overlay_index:
                overlaid_rows += 1

            derived_fields = derive_metadata_design_fields(record, merged_meta)

            write_jsonl_row(
                overlay_handle,
                build_overlay_row(record, merged_meta, derived_fields),
            )
            write_jsonl_row(
                merged_handle,
                build_merged_row(record, merged_meta, derived_fields),
            )

            rows_written += 1
            stance_counts[derived_fields["expected_model_stance"]] += 1
            snapshot_counts[derived_fields["source_snapshot_timestamp"] or "<missing>"] += 1
            snapshot_granularity_counts[derived_fields["source_snapshot_granularity"]] += 1
            license_evidence_source_counts[derived_fields["license_evidence_source"]] += 1
            license_detection_method_counts[derived_fields["license_detection_method"]] += 1
            release_view_membership_counts[derived_fields["release_view_membership"]] += 1
            benchmark_view_membership_counts[derived_fields["benchmark_view_membership"]] += 1
            context_counts[derived_fields["context_sufficiency_class"]] += 1
            repairability_counts[derived_fields["repairability_band"]] += 1
            evidence_regime_counts[derived_fields["evidence_regime"]] += 1
            split_group_source_counts[derived_fields["split_group_source"]] += 1
            domain_slice_counts[derived_fields["domain_slice"]] += 1
            shift_axis_counts[derived_fields["shift_axis"]] += 1
            distribution_rights_counts[derived_fields["distribution_rights_status"]] += 1
            public_release_bucket_counts[derived_fields["public_release_bucket"]] += 1
            license_audit_priority_counts[derived_fields["license_audit_priority"]] += 1
            permission_response_status_counts[derived_fields["permission_response_status"]] += 1
            manual_license_review_status_counts[derived_fields["manual_license_review_status"]] += 1
            if derived_fields["lineage_parent_id"]:
                lineage_parent_ids.add(derived_fields["lineage_parent_id"])

            if args.max_rows and index >= args.max_rows:
                break

    print("metadata-design derivation completed")
    print("  input corpus      :", format_display_path(input_file))
    print("  master overlay    :", format_display_path(master_overlay_file))
    print("  overlay output    :", format_display_path(overlay_output_file))
    print("  merged output     :", format_display_path(merged_output_file))
    print("  metadata version  :", METADATA_DESIGN_VERSION)
    print("  derived fields    :", ", ".join(DERIVED_FIELD_NAMES))
    print("  rows written      :", f"{rows_written:,}")
    print("  overlay matches   :", f"{overlaid_rows:,}")

    print("\nsource_snapshot_timestamp")
    for key, value in snapshot_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nsource_snapshot_granularity")
    for key, value in snapshot_granularity_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nlicense_evidence_source")
    for key, value in license_evidence_source_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nlicense_detection_method")
    for key, value in license_detection_method_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nrelease_view_membership")
    for key, value in release_view_membership_counts.most_common():
        print(f"  {key}: {value:,}")

    print(f"\nlineage_parent_id\n  unique ids: {len(lineage_parent_ids):,}")

    print("\nbenchmark_view_membership")
    for key, value in benchmark_view_membership_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nexpected_model_stance")
    for key, value in stance_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\ncontext_sufficiency_class")
    for key, value in context_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nrepairability_band")
    for key, value in repairability_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nevidence_regime")
    for key, value in evidence_regime_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nsplit_group_source")
    for key, value in split_group_source_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\ndomain_slice")
    for key, value in domain_slice_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nshift_axis")
    for key, value in shift_axis_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\ndistribution_rights_status")
    for key, value in distribution_rights_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\npublic_release_bucket")
    for key, value in public_release_bucket_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nlicense_audit_priority")
    for key, value in license_audit_priority_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\npermission_response_status")
    for key, value in permission_response_status_counts.most_common():
        print(f"  {key}: {value:,}")

    print("\nmanual_license_review_status")
    for key, value in manual_license_review_status_counts.most_common():
        print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()
