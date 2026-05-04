"""
prepare_paraphrases_quality_aware_batch.py
-----------------------------------------
Create a Batch API request file for quality-aware paraphrase generation.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from generate_paraphrases_quality_aware import (
    DEFAULT_PROMPT_MODE,
    DEFAULT_NUM_PARAPHRASES,
    DEFAULT_TEMPERATURE,
    MAX_TOKENS,
    SYSTEM_PROMPT,
    build_user_prompt,
    default_input_file,
    effective_paraphrases_needed,
    load_existing_paraphrases,
    load_jsonl,
    select_seed_rows,
    source_seed_id,
)
from quality_aware_batch_common import append_jsonl, make_paraphrase_custom_id


DEFAULT_REQUEST_FILE = PROCESSED_DIR / "seed_paraphrases_quality_aware_batch_requests_v1.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-file", default=str(default_input_file()))
    parser.add_argument("--request-file", default=str(DEFAULT_REQUEST_FILE))
    parser.add_argument("--existing-output-file", default="")
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--num-paraphrases", type=int, default=DEFAULT_NUM_PARAPHRASES)
    parser.add_argument("--max-output-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--max-paraphrases-per-request", type=int, default=None)
    parser.add_argument("--prompt-mode", default=DEFAULT_PROMPT_MODE)
    parser.add_argument("--max-seeds", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seed_file = Path(args.seed_file)
    request_file = Path(args.request_file)
    existing_output_file = Path(args.existing_output_file) if args.existing_output_file else None

    seed_rows = select_seed_rows(load_jsonl(seed_file), args.max_seeds)
    existing_rows = (
        load_existing_paraphrases(existing_output_file)
        if existing_output_file and existing_output_file.exists()
        else {}
    )

    request_file.parent.mkdir(parents=True, exist_ok=True)
    if request_file.exists():
        request_file.unlink()

    selected = 0
    skipped = 0
    role_counts = Counter()

    for seed_entry in seed_rows:
        key = source_seed_id(seed_entry)
        existing = existing_rows.get(key, [])
        existing_texts = [row.get("input", "") for row in existing]
        needed = effective_paraphrases_needed(
            seed_entry=seed_entry,
            total_missing=max(0, args.num_paraphrases - len(existing_texts)),
            max_paraphrases_per_request=args.max_paraphrases_per_request,
        )
        if needed == 0:
            skipped += 1
            continue

        custom_id = make_paraphrase_custom_id(key)
        request = {
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v1/responses",
            "body": {
                "model": args.model,
                "temperature": args.temperature,
                "max_output_tokens": args.max_output_tokens,
                "input": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_user_prompt(
                            seed_entry=seed_entry,
                            paraphrases_needed=needed,
                            existing_texts=existing_texts,
                            prompt_mode=args.prompt_mode,
                        ),
                    },
                ],
            },
        }
        append_jsonl(request, request_file)
        selected += 1
        role_counts[seed_entry.get("metadata", {}).get("seed_role", "<missing>")] += 1

    print("batch request file:", format_display_path(request_file))
    print("requests written:", f"{selected:,}")
    print("requests skipped from existing output:", f"{skipped:,}")
    print("model:", args.model)
    print("temperature:", args.temperature)
    print("paraphrases per seed:", args.num_paraphrases)
    print("prompt mode:", args.prompt_mode)
    if args.max_paraphrases_per_request is not None:
        print("max paraphrases per request:", args.max_paraphrases_per_request)
    print("max_output_tokens:", args.max_output_tokens)
    print("\nseed-role distribution")
    for key, value in role_counts.most_common():
        print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()
