"""
merge_openai_batch_shard_outputs.py
----------------------------------
Merge sharded OpenAI Batch output/error JSONL files back into canonical files.
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-file", required=True)
    parser.add_argument("--merged-output-file", required=True)
    parser.add_argument("--merged-error-file", required=True)
    return parser.parse_args()


def append_if_exists(source: Path, target: Path) -> int:
    if not source.exists():
        return 0
    written = 0
    with source.open(encoding="utf-8") as src, target.open("a", encoding="utf-8") as dst:
        for line in src:
            if line.strip():
                dst.write(line if line.endswith("\n") else line + "\n")
                written += 1
    return written


def main() -> None:
    args = parse_args()
    index_file = Path(args.index_file)
    merged_output_file = Path(args.merged_output_file)
    merged_error_file = Path(args.merged_error_file)

    if not index_file.exists():
        raise SystemExit(f"ERROR: index file not found: {format_display_path(index_file)}")

    payload = json.loads(index_file.read_text(encoding="utf-8"))
    shards = payload.get("shards", [])

    merged_output_file.parent.mkdir(parents=True, exist_ok=True)
    merged_error_file.parent.mkdir(parents=True, exist_ok=True)
    if merged_output_file.exists():
        merged_output_file.unlink()
    if merged_error_file.exists():
        merged_error_file.unlink()

    output_rows = 0
    error_rows = 0
    for shard in shards:
        output_rows += append_if_exists(Path(shard["output_file"]), merged_output_file)
        error_rows += append_if_exists(Path(shard["error_file"]), merged_error_file)

    print("shard index file:", format_display_path(index_file))
    print("merged output file:", format_display_path(merged_output_file))
    print("merged error file:", format_display_path(merged_error_file))
    print("output rows merged:", f"{output_rows:,}")
    print("error rows merged:", f"{error_rows:,}")


if __name__ == "__main__":
    main()
