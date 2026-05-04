"""
enrich_raw_circuits.py
----------------------
Backfills circuit-level metadata on raw scraped circuit pools before seed
generation. This is the pre-seed enrichment step used when you want structural
metadata to act as anchors for seed prompt generation.

Default input:
    PQID/data/processed/circuits_unified.jsonl

Default output:
    PQID/data/processed/circuits_unified_enriched.jsonl

Resume-safe:
    Uses a dedicated cache keyed by circuit_hash. Cache records are reused only
    when they contain the full current enrichment field set, so adding new
    metrics does not require manually deleting the cache.

Examples:
    python enrich_raw_circuits.py
    python enrich_raw_circuits.py --input-file ...\\circuits_unified_plus_aggressive.jsonl
    python enrich_raw_circuits.py --input-file in.jsonl --output-file out.jsonl --cache-file cache.jsonl
"""

import argparse
import os
import time
from collections import Counter
from pathlib import Path

from project_paths import PROCESSED_DIR
from project_paths import format_display_path
from enrich_metadata import (
    append_to_cache,
    apply_cache_record,
    cache_record_is_complete,
    enrich_entry,
    load_cache,
    load_jsonl,
    write_jsonl,
)


BASE = PROCESSED_DIR


def default_input_file() -> Path:
    candidates = [
        BASE / "circuits_unified_plus_phase2_plus_phase3.jsonl",
        BASE / "circuits_unified_plus_aggressive_broad.jsonl",
        BASE / "circuits_unified_plus_aggressive.jsonl",
        BASE / "circuits_unified.jsonl",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]


def default_output_file(input_path: Path) -> Path:
    stem = input_path.stem
    if stem.endswith("_enriched"):
        stem = stem[: -len("_enriched")]
    return input_path.with_name(stem + "_enriched.jsonl")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Backfill metadata on raw scraped circuit JSONL files."
    )
    parser.add_argument(
        "--input-file",
        default=str(default_input_file()),
        help="Path to the raw circuit JSONL file to enrich.",
    )
    parser.add_argument(
        "--output-file",
        default=None,
        help="Optional output path. Defaults to <input> with _enriched.jsonl suffix.",
    )
    parser.add_argument(
        "--cache-file",
        default=None,
        help="Optional override for the resume cache path.",
    )
    return parser.parse_args()


def process_entries(entries: list, cache: dict, cache_path: str) -> tuple:
    enriched_entries = []
    n_from_cache = 0
    status_counts = Counter()
    t0 = time.time()

    for idx, entry in enumerate(entries, 1):
        ch = entry.get("metadata", {}).get("circuit_hash", "")
        if ch and ch in cache and cache_record_is_complete(cache[ch]):
            enriched = apply_cache_record(entry, cache[ch])
            n_from_cache += 1
        else:
            enriched = enrich_entry(entry)
            append_to_cache(enriched, cache_path)

        enriched_entries.append(enriched)
        status = enriched.get("metadata", {}).get("validation_status", "<missing>")
        status_counts[status] += 1

        if idx % 500 == 0:
            elapsed = time.time() - t0
            print(
                f"  {idx:,}/{len(entries):,} processed | "
                f"cached={n_from_cache:,} | elapsed={elapsed:.0f}s",
                flush=True,
            )

    return enriched_entries, n_from_cache, status_counts


def main():
    args = parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file) if args.output_file else default_output_file(input_path)
    cache_path = Path(args.cache_file) if args.cache_file else output_path.with_name(
        output_path.stem + "_cache.jsonl"
    )

    if not input_path.exists():
        raise SystemExit(
            f"ERROR: input file not found: {format_display_path(input_path)}"
        )

    print(f"Input  : {format_display_path(input_path)}", flush=True)
    print(f"Output : {format_display_path(output_path)}", flush=True)
    print(f"Cache  : {format_display_path(cache_path)}", flush=True)

    entries = load_jsonl(str(input_path))
    print(f"Entries loaded : {len(entries):,}", flush=True)

    cache = load_cache(str(cache_path))
    print(f"Cache records  : {len(cache):,}", flush=True)

    overall_t0 = time.time()
    enriched_entries, n_from_cache, status_counts = process_entries(
        entries, cache, str(cache_path)
    )

    tmp_path = Path(str(output_path) + ".tmp")
    write_jsonl(enriched_entries, str(tmp_path))
    os.replace(tmp_path, output_path)

    elapsed = time.time() - overall_t0
    print("\n" + "=" * 55, flush=True)
    print("RAW ENRICHMENT COMPLETE", flush=True)
    print("=" * 55, flush=True)
    print(f"Total entries : {len(enriched_entries):,}", flush=True)
    print(f"From cache    : {n_from_cache:,}", flush=True)
    print(f"Elapsed       : {elapsed:.1f}s", flush=True)
    print("\nValidation status counts:", flush=True)
    for status, count in status_counts.most_common():
        print(f"  {status}: {count:,}", flush=True)
    print(
        f"\nWrote enriched raw pool to: {format_display_path(output_path)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
