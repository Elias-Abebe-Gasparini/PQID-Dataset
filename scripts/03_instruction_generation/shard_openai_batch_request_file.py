"""
shard_openai_batch_request_file.py
---------------------------------
Split an oversized OpenAI Batch request JSONL file into deterministic shards
small enough to satisfy the Batch API input-file size limit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import format_display_path


DEFAULT_MAX_BYTES = 190 * 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--request-prefix", required=True)
    parser.add_argument("--index-file", required=True)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Optional maximum number of request rows per shard. Use 0 to disable.",
    )
    return parser.parse_args()


def shard_paths(request_prefix: Path, part_idx: int) -> dict[str, Path]:
    part = f"part{part_idx:03d}"
    return {
        "request_file": request_prefix.with_name(f"{request_prefix.name}_{part}.jsonl"),
        "state_file": request_prefix.with_name(f"{request_prefix.name}_{part}_batch.json"),
        "output_file": request_prefix.with_name(f"{request_prefix.name}_{part}_batch_output.jsonl"),
        "error_file": request_prefix.with_name(f"{request_prefix.name}_{part}_batch_error.jsonl"),
    }


def main() -> None:
    args = parse_args()
    input_file = Path(args.input_file)
    request_prefix = Path(args.request_prefix)
    index_file = Path(args.index_file)

    if not input_file.exists():
        raise SystemExit(f"ERROR: input file not found: {format_display_path(input_file)}")

    request_prefix.parent.mkdir(parents=True, exist_ok=True)
    index_file.parent.mkdir(parents=True, exist_ok=True)

    existing = list(request_prefix.parent.glob(f"{request_prefix.name}_part*.jsonl"))
    for path in existing:
        path.unlink()
    for path in request_prefix.parent.glob(f"{request_prefix.name}_part*_batch.json"):
        path.unlink()
    for path in request_prefix.parent.glob(f"{request_prefix.name}_part*_batch_output.jsonl"):
        path.unlink()
    for path in request_prefix.parent.glob(f"{request_prefix.name}_part*_batch_error.jsonl"):
        path.unlink()

    part_idx = 1
    part_rows = 0
    part_bytes = 0
    total_rows = 0
    shards: list[dict] = []
    current = shard_paths(request_prefix, part_idx)

    def start_new_part() -> None:
        nonlocal part_idx, part_rows, part_bytes, current
        if part_rows == 0:
            return
        shards.append(
            {
                "part": part_idx,
                "rows": part_rows,
                "bytes": part_bytes,
                **{key: str(value) for key, value in current.items()},
            }
        )
        part_idx += 1
        part_rows = 0
        part_bytes = 0
        current = shard_paths(request_prefix, part_idx)

    with input_file.open(encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            encoded = raw_line.encode("utf-8")
            line_bytes = len(encoded)
            if line_bytes > args.max_bytes:
                raise SystemExit(
                    "ERROR: a single request line exceeds the shard max-bytes limit; "
                    f"line_bytes={line_bytes:,}, max_bytes={args.max_bytes:,}"
                )
            if part_rows > 0 and (
                part_bytes + line_bytes > args.max_bytes
                or (args.max_rows > 0 and part_rows >= args.max_rows)
            ):
                start_new_part()
            with current["request_file"].open("ab") as out:
                out.write(encoded)
            part_rows += 1
            part_bytes += line_bytes
            total_rows += 1

    start_new_part()

    payload = {
        "source_request_file": str(input_file),
        "request_prefix": str(request_prefix),
        "index_version": 1,
        "max_bytes": args.max_bytes,
        "max_rows": args.max_rows,
        "total_rows": total_rows,
        "shard_count": len(shards),
        "shards": shards,
    }
    index_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("source request file:", format_display_path(input_file))
    print("shard index file:", format_display_path(index_file))
    print("total rows:", f"{total_rows:,}")
    print("shard count:", len(shards))
    print("max bytes per shard:", f"{args.max_bytes:,}")
    if args.max_rows:
        print("max rows per shard:", f"{args.max_rows:,}")
    print("\nshards")
    for shard in shards:
        print(
            f"  part{shard['part']:03d}: rows={shard['rows']:,} bytes={shard['bytes']:,} "
            f"request={format_display_path(Path(shard['request_file']))}"
        )


if __name__ == "__main__":
    main()
