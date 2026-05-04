"""
materialize_seed_drafts_quality_aware_batch.py
----------------------------------------------
Convert Batch API response output for quality-aware seed generation into the
standard PQID seed JSONL artifact and error log.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from generate_seed_drafts_quality_aware import (
    DEFAULT_LOG_FILE,
    DEFAULT_MANIFEST_FILE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_OUTPUT_FILE,
    DEFAULT_SOURCE_FILE,
    DEFAULT_TEMPERATURE,
    build_output_entry,
    extract_json_blob,
    load_completed_keys,
    load_jsonl,
)
from quality_aware_batch_common import (
    append_jsonl,
    extract_batch_output_text,
    iter_jsonl,
    make_seed_custom_id,
    summarize_batch_error,
)


DEFAULT_BATCH_OUTPUT_FILE = PROCESSED_DIR / "seed_drafts_quality_aware_batch_output_v1.jsonl"
DEFAULT_BATCH_ERROR_FILE = PROCESSED_DIR / "seed_drafts_quality_aware_batch_errors_v1.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-file", default=str(DEFAULT_MANIFEST_FILE))
    parser.add_argument("--source-file", default=str(DEFAULT_SOURCE_FILE))
    parser.add_argument("--batch-output-file", default=str(DEFAULT_BATCH_OUTPUT_FILE))
    parser.add_argument("--batch-error-file", default=str(DEFAULT_BATCH_ERROR_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    return parser.parse_args()


def load_logged_error_keys(path: Path) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    if not path.exists():
        return keys
    for row in load_jsonl(path):
        keys.add(
            (
                str(row.get("custom_id") or ""),
                str(row.get("error_type") or ""),
                str(row.get("error_message") or ""),
            )
        )
    return keys


def append_error_once(entry: dict, log_file: Path, logged_error_keys: set[tuple[str, str, str]]) -> bool:
    key = (
        str(entry.get("custom_id") or ""),
        str(entry.get("error_type") or ""),
        str(entry.get("error_message") or ""),
    )
    if key in logged_error_keys:
        return False
    append_jsonl(entry, log_file)
    logged_error_keys.add(key)
    return True


def log_materialization_error(
    *,
    log_file: Path,
    custom_id: str,
    seed_role: str,
    message: str,
    logged_error_keys: set[tuple[str, str, str]],
) -> None:
    append_error_once(
        {
            "error_type": "BatchMaterializationError",
            "error_message": message,
            "seed_role": seed_role,
            "custom_id": custom_id,
        },
        log_file,
        logged_error_keys,
    )


def summarize_materialized_seed_artifact(output_file: Path, log_file: Path) -> dict:
    role_counts = Counter()
    prompt_type_counts = Counter()
    supervision_mode_counts = Counter()
    rows = 0
    circuit_hashes: set[str] = set()

    for row in load_jsonl(output_file):
        meta = row.get("metadata", {})
        rows += 1
        role_counts[meta.get("seed_role", "<missing>")] += 1
        prompt_type_counts[meta.get("prompt_type", "<missing>")] += 1
        supervision_mode_counts[meta.get("seed_target_supervision_mode", "<missing>")] += 1
        circuit_hash = str(meta.get("circuit_hash", "")).strip()
        if circuit_hash:
            circuit_hashes.add(circuit_hash)

    error_rows = 0
    error_type_counts = Counter()
    for row in load_jsonl(log_file):
        error_rows += 1
        error_type_counts[row.get("error_type", "<missing>")] += 1

    return {
        "rows": rows,
        "unique_circuit_hashes": len(circuit_hashes),
        "role_counts": role_counts,
        "prompt_type_counts": prompt_type_counts,
        "supervision_mode_counts": supervision_mode_counts,
        "error_rows": error_rows,
        "error_type_counts": error_type_counts,
    }


def main() -> None:
    args = parse_args()
    manifest_file = Path(args.manifest_file)
    source_file = Path(args.source_file)
    batch_output_file = Path(args.batch_output_file)
    batch_error_file = Path(args.batch_error_file)
    output_file = Path(args.output_file)
    log_file = Path(args.log_file)

    manifest_rows = load_jsonl(manifest_file)
    source_rows = {
        row["metadata"]["circuit_hash"]: row
        for row in load_jsonl(source_file)
        if row.get("metadata", {}).get("circuit_hash")
    }
    manifest_map = {
        make_seed_custom_id(entry["source_record"]["circuit_hash"], entry["seed_role"]): entry
        for entry in manifest_rows
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    completed_keys = load_completed_keys(output_file)
    logged_error_keys = load_logged_error_keys(log_file)
    written = 0
    failed = 0
    skipped_existing = 0

    for batch_line in iter_jsonl(batch_output_file):
        custom_id = batch_line.get("custom_id", "")
        manifest_entry = manifest_map.get(custom_id)
        if not manifest_entry:
            failed += 1
            log_materialization_error(
                log_file=log_file,
                custom_id=custom_id,
                seed_role="<unknown>",
                message="custom_id not found in manifest map",
                logged_error_keys=logged_error_keys,
            )
            continue

        seed_role = manifest_entry["seed_role"]
        seed_key = (manifest_entry["source_record"]["circuit_hash"], seed_role)
        if seed_key in completed_keys:
            skipped_existing += 1
            continue
        response = batch_line.get("response") or {}
        status_code = response.get("status_code")
        if status_code != 200:
            failed += 1
            summary = summarize_batch_error(batch_line)
            summary["seed_role"] = seed_role
            append_error_once(summary, log_file, logged_error_keys)
            continue

        try:
            response_body = response.get("body") or {}
            if response_body.get("status") == "incomplete":
                failed += 1
                incomplete = response_body.get("incomplete_details") or {}
                reason = incomplete.get("reason") or "unknown"
                log_materialization_error(
                    log_file=log_file,
                    custom_id=custom_id,
                    seed_role=seed_role,
                    message=f"incomplete response: {reason}",
                    logged_error_keys=logged_error_keys,
                )
                continue
            content = extract_batch_output_text(batch_line)
            parsed = extract_json_blob(content)
            seed_input = str(parsed["seed_input"]).strip()
            seed_quality_note = str(parsed.get("seed_quality_note", "")).strip()
            teacher_output = str(parsed.get("teacher_output", "")).strip() or None
            source_record = source_rows[manifest_entry["source_record"]["circuit_hash"]]
            request_max_output_tokens = int(
                response_body.get("max_output_tokens") or DEFAULT_MAX_TOKENS
            )
            append_jsonl(
                build_output_entry(
                    manifest_entry=manifest_entry,
                    source_record=source_record,
                    seed_input=seed_input,
                    seed_quality_note=seed_quality_note,
                    model=args.model,
                    temperature=args.temperature,
                    max_output_tokens=request_max_output_tokens,
                    teacher_output=teacher_output,
                ),
                output_file,
            )
            written += 1
            completed_keys.add(seed_key)
        except Exception as exc:
            failed += 1
            log_materialization_error(
                log_file=log_file,
                custom_id=custom_id,
                seed_role=seed_role,
                message=str(exc),
                logged_error_keys=logged_error_keys,
            )

    if batch_error_file.exists():
        for batch_line in iter_jsonl(batch_error_file):
            summary = summarize_batch_error(batch_line)
            manifest_entry = manifest_map.get(summary["custom_id"] or "")
            summary["seed_role"] = manifest_entry["seed_role"] if manifest_entry else "<unknown>"
            append_error_once(summary, log_file, logged_error_keys)

    print("materialized output file:", format_display_path(output_file))
    print("materialized error log:", format_display_path(log_file))
    print("rows written:", f"{written:,}")
    print("rows failed/logged:", f"{failed:,}")
    print("rows skipped because already materialized:", f"{skipped_existing:,}")
    summary = summarize_materialized_seed_artifact(output_file, log_file)
    print("total rows in artifact:", f"{summary['rows']:,}")
    print("unique circuit_hash values:", f"{summary['unique_circuit_hashes']:,}")
    print("total logged errors:", f"{summary['error_rows']:,}")
    print("\nrole distribution")
    for key, value in summary["role_counts"].most_common():
        print(f"  {key}: {value:,}")
    print("\nprompt types")
    for key, value in summary["prompt_type_counts"].most_common():
        print(f"  {key}: {value:,}")
    print("\ntarget supervision modes")
    for key, value in summary["supervision_mode_counts"].most_common():
        print(f"  {key}: {value:,}")
    if summary["error_type_counts"]:
        print("\nlogged error types")
        for key, value in summary["error_type_counts"].most_common():
            print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()
