"""
build_missing_seed_retry_manifest.py
------------------------------------
Build a retry manifest containing only the seed rows still missing from a
materialized PQID seed artifact.
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


DEFAULT_MANIFEST_FILE = PROCESSED_DIR / "seed_role_manifest_v1_source_code.jsonl"
DEFAULT_OUTPUT_FILE = PROCESSED_DIR / "seed_drafts_quality_aware_source_code_v1.jsonl"
DEFAULT_RETRY_MANIFEST_FILE = PROCESSED_DIR / "seed_role_manifest_v1_source_code_retry.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-file", default=str(DEFAULT_MANIFEST_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument("--retry-manifest-file", default=str(DEFAULT_RETRY_MANIFEST_FILE))
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def seed_key_from_manifest(row: dict) -> tuple[str, str]:
    return row["source_record"]["circuit_hash"], row["seed_role"]


def seed_key_from_output(row: dict) -> tuple[str | None, str | None]:
    meta = row.get("metadata", {})
    return meta.get("circuit_hash"), meta.get("seed_role")


def main() -> None:
    args = parse_args()
    manifest_file = Path(args.manifest_file)
    output_file = Path(args.output_file)
    retry_manifest_file = Path(args.retry_manifest_file)

    manifest_rows = load_jsonl(manifest_file)
    output_rows = load_jsonl(output_file) if output_file.exists() else []

    existing_keys = {seed_key_from_output(row) for row in output_rows}
    retry_rows = [row for row in manifest_rows if seed_key_from_manifest(row) not in existing_keys]

    retry_manifest_file.parent.mkdir(parents=True, exist_ok=True)
    with retry_manifest_file.open("w", encoding="utf-8") as handle:
        for row in retry_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    role_counts = Counter(row["seed_role"] for row in retry_rows)
    print("retry manifest:", format_display_path(retry_manifest_file))
    print("retry rows:", f"{len(retry_rows):,}")
    print("role distribution")
    for key, value in role_counts.most_common():
        print(f"  {key}: {value:,}")
    if retry_rows:
        sample = retry_rows[0]
        print("sample missing key:", seed_key_from_manifest(sample))


if __name__ == "__main__":
    main()
