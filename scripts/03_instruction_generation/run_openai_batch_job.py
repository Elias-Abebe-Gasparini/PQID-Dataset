"""
run_openai_batch_job.py
-----------------------
Upload a Batch API request file, create or inspect a batch job, and optionally
download the output and error files.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from openai import OpenAI

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import format_display_path, load_openai_api_key


TERMINAL_STATUSES = {"completed", "failed", "cancelled", "expired"}
HARD_BATCH_LIMIT_BYTES = 200 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-file", default="")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--state-file", default="")
    parser.add_argument("--endpoint", default="/v1/responses")
    parser.add_argument("--completion-window", default="24h")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--poll-interval-seconds", type=int, default=60)
    parser.add_argument("--download-output-file", default="")
    parser.add_argument("--download-error-file", default="")
    return parser.parse_args()


def write_state(path: Path | None, payload: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def batch_state_dict(batch) -> dict:
    request_counts = getattr(batch, "request_counts", None)
    errors = getattr(batch, "errors", None)
    return {
        "batch_id": getattr(batch, "id", None),
        "status": getattr(batch, "status", None),
        "input_file_id": getattr(batch, "input_file_id", None),
        "output_file_id": getattr(batch, "output_file_id", None),
        "error_file_id": getattr(batch, "error_file_id", None),
        "endpoint": getattr(batch, "endpoint", None),
        "completion_window": getattr(batch, "completion_window", None),
        "created_at": getattr(batch, "created_at", None),
        "errors": (
            errors.to_dict()
            if hasattr(errors, "to_dict")
            else errors
        ),
        "request_counts": (
            {
                "total": getattr(request_counts, "total", None),
                "completed": getattr(request_counts, "completed", None),
                "failed": getattr(request_counts, "failed", None),
            }
            if request_counts is not None
            else None
        ),
    }


def maybe_download_file(client: OpenAI, *, file_id: str | None, target_path: Path | None) -> None:
    if not file_id or not target_path:
        return
    content = client.files.retrieve_content(file_id)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    print("downloaded:", format_display_path(target_path))


def main() -> None:
    args = parse_args()
    if not args.request_file and not args.batch_id:
        raise SystemExit("ERROR: provide either --request-file to create a batch or --batch-id to inspect one.")

    state_file = Path(args.state_file) if args.state_file else None
    download_output_file = Path(args.download_output_file) if args.download_output_file else None
    download_error_file = Path(args.download_error_file) if args.download_error_file else None

    api_key = load_openai_api_key(__file__)
    client = OpenAI(api_key=api_key)

    if args.request_file:
        request_file = Path(args.request_file)
        if not request_file.exists():
            raise SystemExit(f"ERROR: request file not found: {format_display_path(request_file)}")
        request_bytes = request_file.stat().st_size
        if request_bytes > HARD_BATCH_LIMIT_BYTES:
            raise SystemExit(
                "ERROR: request file exceeds the 200 MB Batch API input-file limit. "
                f"size={request_bytes:,} bytes ({request_bytes / 1024 / 1024:.2f} MB). "
                "Shard the request file before batch creation."
            )
        with request_file.open("rb") as handle:
            uploaded = client.files.create(file=handle, purpose="batch")
        batch = client.batches.create(
            input_file_id=uploaded.id,
            endpoint=args.endpoint,
            completion_window=args.completion_window,
        )
        print("uploaded request file:", format_display_path(request_file))
        print("input file id:", uploaded.id)
        print("batch id:", batch.id)
        write_state(
            state_file,
            {
                "request_file": str(request_file),
                "input_file_id": uploaded.id,
                **batch_state_dict(batch),
            },
        )
    else:
        batch = client.batches.retrieve(args.batch_id)
        print("batch id:", batch.id)

    if args.wait:
        while getattr(batch, "status", None) not in TERMINAL_STATUSES:
            time.sleep(max(5, args.poll_interval_seconds))
            batch = client.batches.retrieve(batch.id)
            print(
                "batch status:",
                getattr(batch, "status", None),
                getattr(getattr(batch, "request_counts", None), "completed", None),
                "/",
                getattr(getattr(batch, "request_counts", None), "total", None),
            )

    state = batch_state_dict(batch)
    write_state(state_file, state)
    print("final status:", state["status"])
    if state.get("request_counts"):
        print("request counts:", state["request_counts"])
    if state.get("output_file_id"):
        print("output file id:", state["output_file_id"])
    if state.get("error_file_id"):
        print("error file id:", state["error_file_id"])
    if state.get("errors"):
        print("batch errors:", json.dumps(state["errors"], ensure_ascii=False))

    maybe_download_file(client, file_id=state.get("output_file_id"), target_path=download_output_file)
    maybe_download_file(client, file_id=state.get("error_file_id"), target_path=download_error_file)


if __name__ == "__main__":
    main()
