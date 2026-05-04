"""
normalize_quality_aware_prompt_types.py
---------------------------------------
Normalize legacy quality-aware prompt-type labels in an existing PQID artifact.

This is a release-cleanup utility for artifacts that were written across the
schema rename from `human_seed_quality_aware` to `base_seed_quality_aware`.

It updates:
- metadata.prompt_type
- metadata.paraphrase_source_prompt_type

The script is safe to run multiple times. Once an artifact is already using the
canonical labels, rerunning the script is a no-op.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path
from quality_aware_seed_common import canonicalize_quality_aware_prompt_type


DEFAULT_INPUT_FILE = PROCESSED_DIR / "seed_drafts_quality_aware_source_code_v1.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", default=str(DEFAULT_INPUT_FILE))
    parser.add_argument("--backup-file", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_file = Path(args.input_file)
    backup_file = Path(args.backup_file) if args.backup_file else None
    temp_file = input_file.with_suffix(input_file.suffix + ".tmp")

    if not input_file.exists():
        raise FileNotFoundError(f"input file not found: {input_file}")

    before_prompt_types = Counter()
    after_prompt_types = Counter()
    rows = 0
    row_updates = 0
    prompt_type_updates = 0
    source_prompt_type_updates = 0

    with input_file.open(encoding="utf-8") as src, temp_file.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            row = json.loads(line)
            meta = row.setdefault("metadata", {})

            before_prompt = str(meta.get("prompt_type", "")).strip()
            before_source_prompt = str(meta.get("paraphrase_source_prompt_type", "")).strip()
            before_prompt_types[before_prompt or "<missing>"] += 1

            after_prompt = canonicalize_quality_aware_prompt_type(before_prompt)
            after_source_prompt = canonicalize_quality_aware_prompt_type(before_source_prompt)

            updated = False
            if after_prompt != before_prompt:
                meta["prompt_type"] = after_prompt
                prompt_type_updates += 1
                updated = True
            if after_source_prompt != before_source_prompt:
                meta["paraphrase_source_prompt_type"] = after_source_prompt
                source_prompt_type_updates += 1
                updated = True

            if updated:
                row_updates += 1

            after_prompt_types[str(meta.get("prompt_type", "")).strip() or "<missing>"] += 1
            dst.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows += 1

    if backup_file:
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_file, backup_file)

    temp_file.replace(input_file)

    print("normalized file:", format_display_path(input_file))
    if backup_file:
        print("backup file:", format_display_path(backup_file))
    print("rows processed:", f"{rows:,}")
    print("rows updated:", f"{row_updates:,}")
    print("prompt_type updates:", f"{prompt_type_updates:,}")
    print("paraphrase_source_prompt_type updates:", f"{source_prompt_type_updates:,}")
    print("\nprompt types before")
    for key, value in before_prompt_types.most_common():
        print(f"  {key}: {value:,}")
    print("\nprompt types after")
    for key, value in after_prompt_types.most_common():
        print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()
