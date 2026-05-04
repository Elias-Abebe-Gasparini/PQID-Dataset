"""
merge_and_split.py
------------------
Merges instruction artifacts into the three canonical splits:

    train_clean.jsonl       80 %
    validation_clean.jsonl  10 %
    test_clean.jsonl        10 %

The split is circuit-aware: all instructions for a given circuit (its seed +
all paraphrases) land in the same split, preventing instruction-level leakage.
Split assignment is deterministic (seeded by circuit_hash mod 10).

Content-level deduplication: entries with identical content_hash are dropped.

The script supports both the legacy two-file layout:

    seeds.jsonl
    paraphrases.jsonl

and the newer quality-aware multi-branch layout where separate source-code and
teacher-text seed/paraphrase artifacts are merged into the canonical split
layer.

Run:
    python merge_and_split.py
or:
    python merge_and_split.py --seed-file ... --seed-file ... \
        --paraphrase-file ... --paraphrase-file ...
"""

import argparse
import json
import random
from pathlib import Path

from project_paths import PROCESSED_DIR

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = PROCESSED_DIR

SEEDS_FILE       = BASE / "seeds.jsonl"
PARAPHRASES_FILE = BASE / "paraphrases.jsonl"

TRAIN_FILE = BASE / "train_clean.jsonl"
VAL_FILE   = BASE / "validation_clean.jsonl"
TEST_FILE  = BASE / "test_clean.jsonl"

# Deterministic split: use last hex digit of circuit_hash to assign bucket
# 0-7 → train (80%), 8 → val (10%), 9 → test (10%)
TRAIN_DIGITS = set("01234567")
VAL_DIGITS   = {"8"}
TEST_DIGITS  = {"9"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-file",
        action="append",
        default=None,
        help="Seed artifact to merge. May be provided multiple times.",
    )
    parser.add_argument(
        "--paraphrase-file",
        action="append",
        default=None,
        help="Paraphrase artifact to merge. May be provided multiple times.",
    )
    parser.add_argument("--train-file", default=str(TRAIN_FILE))
    parser.add_argument("--validation-file", default=str(VAL_FILE))
    parser.add_argument("--test-file", default=str(TEST_FILE))
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def save_jsonl(entries: list, path: Path) -> None:
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    tmp.replace(path)


def assign_split(circuit_hash: str) -> str:
    """Deterministic split based on circuit_hash modulo 10."""
    if not circuit_hash:
        bucket = 0
    else:
        try:
            bucket = int(circuit_hash, 16) % 10
        except ValueError:
            # Fallback for any unexpected non-hex hash representation.
            bucket = sum(ord(ch) for ch in circuit_hash) % 10

    bucket_digit = str(bucket)
    if bucket_digit in TRAIN_DIGITS:
        return "train"
    elif bucket_digit in VAL_DIGITS:
        return "validation"
    else:
        return "test"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    args = parse_args()

    seed_files = [Path(p) for p in (args.seed_file or [str(SEEDS_FILE)])]
    paraphrase_files = [Path(p) for p in (args.paraphrase_file or [str(PARAPHRASES_FILE)])]
    train_file = Path(args.train_file)
    val_file = Path(args.validation_file)
    test_file = Path(args.test_file)

    seeds = []
    print("Loading seeds...", flush=True)
    for path in seed_files:
        part = load_jsonl(path)
        seeds.extend(part)
        print(f"  {path.name}: {len(part):,}", flush=True)
    print(f"  Seeds total: {len(seeds):,}", flush=True)

    paraphrases = []
    print("Loading paraphrases...", flush=True)
    for path in paraphrase_files:
        part = load_jsonl(path)
        paraphrases.extend(part)
        print(f"  {path.name}: {len(part):,}", flush=True)
    print(f"  Paraphrases total: {len(paraphrases):,}", flush=True)

    all_entries = seeds + paraphrases
    print(f"  Total before dedup: {len(all_entries):,}", flush=True)

    # Content-level dedup
    seen_content_hashes: set = set()
    deduped = []
    for e in all_entries:
        ch = e.get("metadata", {}).get("content_hash", "")
        if ch and ch in seen_content_hashes:
            continue
        if ch:
            seen_content_hashes.add(ch)
        deduped.append(e)
    print(f"  After content dedup: {len(deduped):,}", flush=True)

    # Assign splits
    train, val, test = [], [], []
    for e in deduped:
        circuit_hash = e.get("metadata", {}).get("circuit_hash", "")
        split = assign_split(circuit_hash)
        if split == "train":
            train.append(e)
        elif split == "validation":
            val.append(e)
        else:
            test.append(e)

    # Shuffle within each split (deterministic seed)
    rng = random.Random(42)
    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)

    print(f"\nSplit sizes:", flush=True)
    total = len(train) + len(val) + len(test)
    print(f"  train      : {len(train):,}  ({100*len(train)/total:.1f}%)", flush=True)
    print(f"  validation : {len(val):,}  ({100*len(val)/total:.1f}%)", flush=True)
    print(f"  test       : {len(test):,}  ({100*len(test)/total:.1f}%)", flush=True)
    print(f"  TOTAL      : {total:,}", flush=True)

    print("\nSaving splits...", flush=True)
    save_jsonl(train, train_file)
    save_jsonl(val,   val_file)
    save_jsonl(test,  test_file)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
