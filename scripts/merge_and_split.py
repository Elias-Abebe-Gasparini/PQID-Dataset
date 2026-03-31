"""
merge_and_split.py
------------------
Merges seeds.jsonl + paraphrases.jsonl into the three canonical splits:

    train_clean.jsonl       80 %
    validation_clean.jsonl  10 %
    test_clean.jsonl        10 %

The split is circuit-aware: all instructions for a given circuit (its seed +
all paraphrases) land in the same split, preventing instruction-level leakage.
Split assignment is deterministic (seeded by circuit_hash mod 10).

Content-level deduplication: entries with identical content_hash are dropped.

Run:
    python merge_and_split.py
"""

import json
import random
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = Path(
    "c:/Users/Abebe/Downloads/CAREER/ACADEMIC CAREER/SCHOOLS/YONSEI/"
    "YONSEI 2023/Yonsei SS 2025/MS Thesis/MS_THESIS_DATASET/PQID/data/processed"
)

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
    """Deterministic split based on last hex character of circuit_hash."""
    last = circuit_hash[-1].lower() if circuit_hash else "0"
    if last in TRAIN_DIGITS:
        return "train"
    elif last in VAL_DIGITS:
        return "validation"
    else:
        return "test"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Loading seeds...", flush=True)
    seeds = load_jsonl(SEEDS_FILE)
    print(f"  Seeds: {len(seeds):,}", flush=True)

    print("Loading paraphrases...", flush=True)
    paraphrases = load_jsonl(PARAPHRASES_FILE)
    print(f"  Paraphrases: {len(paraphrases):,}", flush=True)

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
    save_jsonl(train, TRAIN_FILE)
    save_jsonl(val,   VAL_FILE)
    save_jsonl(test,  TEST_FILE)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
