"""
split_validated.py
------------------
Partitions each *_clean.jsonl split into two tiers based on validation_status:

  Tier 1 — validated (validation_status == "validated")
    train_validated.jsonl
    validation_validated.jsonl
    test_validated.jsonl

  Tier 2 — unvalidated (all other statuses)
    community_unvalidated.jsonl  (all splits merged — target for annotation)

This is the final step of the PQID pipeline. Run it after enrich_metadata.py
and enrich_circuit_family.py have both completed.

Prints a full breakdown by validation_status and split.

Run:
    python split_validated.py
"""

import json
from collections import Counter
from pathlib import Path

from project_paths import PROCESSED_DIR

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = PROCESSED_DIR

SPLITS = {
    "train":      BASE / "train_clean.jsonl",
    "validation": BASE / "validation_clean.jsonl",
    "test":       BASE / "test_clean.jsonl",
}

TIER1_FILES = {
    "train":      BASE / "train_validated.jsonl",
    "validation": BASE / "validation_validated.jsonl",
    "test":       BASE / "test_validated.jsonl",
}

COMMUNITY_FILE = BASE / "community_unvalidated.jsonl"

VALIDATED_STATUS = "validated"


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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    all_status_counts: Counter = Counter()
    community: list = []

    for split_name, input_path in SPLITS.items():
        print(f"\nProcessing {split_name}...", flush=True)
        entries = load_jsonl(input_path)
        if not entries:
            print(f"  SKIP — file not found or empty: {input_path}", flush=True)
            continue

        tier1 = []
        tier2 = []
        status_counts: Counter = Counter()

        for entry in entries:
            status = entry.get("metadata", {}).get("validation_status", "unknown")
            status_counts[status] += 1
            all_status_counts[status] += 1
            if status == VALIDATED_STATUS:
                tier1.append(entry)
            else:
                tier2.append(entry)

        # Print per-split breakdown
        total = len(entries)
        print(f"  Total       : {total:,}", flush=True)
        for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
            print(f"    {status:<30} {count:>7,}  ({100*count/total:.1f}%)", flush=True)
        print(f"  Tier 1 (validated)   : {len(tier1):,}", flush=True)
        print(f"  Tier 2 (unvalidated) : {len(tier2):,}", flush=True)

        # Save Tier 1
        save_jsonl(tier1, TIER1_FILES[split_name])
        # Accumulate Tier 2 for community file
        community.extend(tier2)

    # Save community file (all Tier 2 entries across all splits)
    print(f"\nSaving community_unvalidated.jsonl ({len(community):,} entries)...", flush=True)
    save_jsonl(community, COMMUNITY_FILE)

    # Dataset-level summary
    print("\n" + "=" * 55)
    print("PQID — Tier Summary")
    print("=" * 55)

    tier1_total = sum(
        sum(1 for _ in open(p, encoding="utf-8"))
        for p in TIER1_FILES.values()
        if p.exists()
    )
    print(f"Tier 1 (validated) total   : {tier1_total:,}")
    print(f"Tier 2 (community) total   : {len(community):,}")
    grand_total = tier1_total + len(community)
    print(f"Grand total                : {grand_total:,}")
    if grand_total > 0:
        print(f"Tier 1 fraction            : {100*tier1_total/grand_total:.1f}%")

    print("\nAll validation status counts:")
    for status, count in sorted(all_status_counts.items(), key=lambda x: -x[1]):
        print(f"  {status:<30} {count:>8,}")

    print("\nOutput files:")
    for name, path in {**TIER1_FILES, "community": COMMUNITY_FILE}.items():
        if path.exists():
            n = sum(1 for _ in open(path, encoding="utf-8"))
            print(f"  {path.name:<40} {n:>8,}")


if __name__ == "__main__":
    main()
