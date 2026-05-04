"""
prepare_seed_drafts_quality_aware_batch.py
------------------------------------------
Create a Batch API request file for quality-aware seed draft generation.

This preserves the same prompt-building logic as the synchronous generator,
but writes `/v1/responses` batch requests to JSONL for asynchronous execution.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from generate_seed_drafts_quality_aware import (
    DEFAULT_MANIFEST_FILE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SOURCE_FILE,
    DEFAULT_TEMPERATURE,
    SYSTEM_PROMPT,
    build_user_prompt,
    load_completed_keys,
    load_jsonl,
    resolve_request_max_output_tokens,
)
from quality_aware_batch_common import append_jsonl, make_seed_custom_id


DEFAULT_REQUEST_FILE = PROCESSED_DIR / "seed_drafts_quality_aware_batch_requests_v1.jsonl"
SOFT_BATCH_WARNING_BYTES = 190 * 1024 * 1024
HARD_BATCH_LIMIT_BYTES = 200 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-file", default=str(DEFAULT_MANIFEST_FILE))
    parser.add_argument("--source-file", default=str(DEFAULT_SOURCE_FILE))
    parser.add_argument("--request-file", default=str(DEFAULT_REQUEST_FILE))
    parser.add_argument("--existing-output-file", default="")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--max-records", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_file = Path(args.manifest_file)
    source_file = Path(args.source_file)
    request_file = Path(args.request_file)
    existing_output_file = Path(args.existing_output_file) if args.existing_output_file else None

    manifest_rows = load_jsonl(manifest_file)
    if args.max_records is not None:
        manifest_rows = manifest_rows[: args.max_records]

    source_rows = {
        row["metadata"]["circuit_hash"]: row
        for row in load_jsonl(source_file)
        if row.get("metadata", {}).get("circuit_hash")
    }
    completed = load_completed_keys(existing_output_file) if existing_output_file and existing_output_file.exists() else set()

    request_file.parent.mkdir(parents=True, exist_ok=True)
    if request_file.exists():
        request_file.unlink()

    role_counts = Counter()
    mode_counts = Counter()
    selected = 0
    skipped = 0

    for entry in manifest_rows:
        source = entry["source_record"]
        key = (source["circuit_hash"], entry["seed_role"])
        if key in completed:
            skipped += 1
            continue

        source_record = source_rows[source["circuit_hash"]]
        request_max_output_tokens = resolve_request_max_output_tokens(
            entry,
            source_record,
            args.max_output_tokens,
        )
        custom_id = make_seed_custom_id(source["circuit_hash"], entry["seed_role"])
        request = {
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v1/responses",
            "body": {
                "model": args.model,
                "temperature": args.temperature,
                "max_output_tokens": request_max_output_tokens,
                "input": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_user_prompt(entry, source_record),
                    },
                ],
            },
        }
        append_jsonl(request, request_file)
        selected += 1
        role_counts[entry["seed_role"]] += 1
        mode_counts[entry.get("target_supervision_mode", "<missing>")] += 1

    print("batch request file:", format_display_path(request_file))
    print("requests written:", f"{selected:,}")
    print("requests skipped from existing output:", f"{skipped:,}")
    print("model:", args.model)
    print("temperature:", args.temperature)
    print("max_output_tokens:", args.max_output_tokens)
    request_bytes = request_file.stat().st_size if request_file.exists() else 0
    print("request file size bytes:", f"{request_bytes:,}")
    print("request file size MB:", f"{request_bytes / 1024 / 1024:.2f}")
    if request_bytes > HARD_BATCH_LIMIT_BYTES:
        print(
            "WARNING: request file exceeds the likely Batch API limit of 200 MB; "
            "shard this file before batch creation."
        )
    elif request_bytes > SOFT_BATCH_WARNING_BYTES:
        print(
            "WARNING: request file is close to the Batch API size limit; "
            "consider sharding if batch creation fails validation."
        )
    print("\nrole distribution")
    for key, value in role_counts.most_common():
        print(f"  {key}: {value:,}")
    print("\ntarget supervision modes")
    for key, value in mode_counts.most_common():
        print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()
