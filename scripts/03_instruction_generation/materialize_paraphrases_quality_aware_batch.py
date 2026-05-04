"""
materialize_paraphrases_quality_aware_batch.py
----------------------------------------------
Convert Batch API response output for quality-aware paraphrase generation into
the standard PQID paraphrase JSONL artifact and error log.
"""

from __future__ import annotations

import argparse
from collections import Counter
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from generate_paraphrases_quality_aware import (
    DEFAULT_PROMPT_MODE,
    DEFAULT_LOG_FILE,
    DEFAULT_NUM_PARAPHRASES,
    DEFAULT_OUTPUT_FILE,
    DEFAULT_TEMPERATURE,
    MAX_TOKENS,
    build_output_entry,
    effective_paraphrases_needed,
    extract_json_blob,
    load_existing_paraphrases,
    load_jsonl,
    sanitize_paraphrases,
    select_seed_rows,
    source_seed_id,
    retry_prompt_mode,
)
from quality_aware_batch_common import (
    append_jsonl,
    extract_batch_output_text,
    iter_jsonl,
    make_paraphrase_custom_id,
    summarize_batch_error,
)


DEFAULT_BATCH_OUTPUT_FILE = PROCESSED_DIR / "seed_paraphrases_quality_aware_batch_output_v1.jsonl"
DEFAULT_BATCH_ERROR_FILE = PROCESSED_DIR / "seed_paraphrases_quality_aware_batch_errors_v1.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-file", required=True)
    parser.add_argument("--batch-output-file", default=str(DEFAULT_BATCH_OUTPUT_FILE))
    parser.add_argument("--batch-error-file", default=str(DEFAULT_BATCH_ERROR_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--num-paraphrases", type=int, default=DEFAULT_NUM_PARAPHRASES)
    parser.add_argument("--max-output-tokens", type=int, default=MAX_TOKENS)
    return parser.parse_args()


def log_materialization_error(*, log_file: Path, custom_id: str, seed_role: str, message: str) -> None:
    append_jsonl(
        {
            "error_type": "BatchMaterializationError",
            "error_message": message,
            "seed_role": seed_role,
            "custom_id": custom_id,
        },
        log_file,
    )


def summarize_materialized_paraphrase_artifact(output_file: Path, log_file: Path) -> dict:
    role_counts = Counter()
    prompt_type_counts = Counter()
    source_prompt_type_counts = Counter()
    rows = 0
    source_seed_ids: set[str] = set()

    for row in load_jsonl(output_file):
        meta = row.get("metadata", {})
        rows += 1
        role_counts[meta.get("seed_role", "<missing>")] += 1
        prompt_type_counts[meta.get("prompt_type", "<missing>")] += 1
        source_prompt_type_counts[meta.get("paraphrase_source_prompt_type", "<missing>")] += 1
        source_seed_id = str(
            meta.get("paraphrase_source_content_hash")
            or meta.get("paraphrase_source")
            or ""
        ).strip()
        if source_seed_id:
            source_seed_ids.add(source_seed_id)

    error_rows = 0
    error_type_counts = Counter()
    for row in load_jsonl(log_file):
        error_rows += 1
        error_type_counts[row.get("error_type", "<missing>")] += 1

    return {
        "rows": rows,
        "unique_source_seed_ids": len(source_seed_ids),
        "role_counts": role_counts,
        "prompt_type_counts": prompt_type_counts,
        "source_prompt_type_counts": source_prompt_type_counts,
        "error_rows": error_rows,
        "error_type_counts": error_type_counts,
    }


def main() -> None:
    args = parse_args()
    seed_file = Path(args.seed_file)
    batch_output_file = Path(args.batch_output_file)
    batch_error_file = Path(args.batch_error_file)
    output_file = Path(args.output_file)
    log_file = Path(args.log_file)

    seed_rows = select_seed_rows(load_jsonl(seed_file), None)
    seed_map = {make_paraphrase_custom_id(source_seed_id(row)): row for row in seed_rows}
    existing_rows = load_existing_paraphrases(output_file) if output_file.exists() else {}

    output_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    failed = 0

    for batch_line in iter_jsonl(batch_output_file):
        custom_id = batch_line.get("custom_id", "")
        seed_entry = seed_map.get(custom_id)
        if not seed_entry:
            failed += 1
            log_materialization_error(
                log_file=log_file,
                custom_id=custom_id,
                seed_role="<unknown>",
                message="custom_id not found in seed map",
            )
            continue

        seed_role = seed_entry.get("metadata", {}).get("seed_role", "<missing>")
        response = batch_line.get("response") or {}
        status_code = response.get("status_code")
        if status_code != 200:
            failed += 1
            summary = summarize_batch_error(batch_line)
            summary["seed_role"] = seed_role
            append_jsonl(summary, log_file)
            continue

        try:
            key = source_seed_id(seed_entry)
            existing = existing_rows.get(key, [])
            existing_texts = [row.get("input", "") for row in existing]
            needed = effective_paraphrases_needed(
                seed_entry=seed_entry,
                total_missing=max(0, args.num_paraphrases - len(existing_texts)),
            )
            if needed == 0:
                continue

            content = extract_batch_output_text(batch_line)
            parsed = extract_json_blob(content)
            raw_paraphrases = parsed.get("paraphrases", [])
            if not isinstance(raw_paraphrases, list):
                raise ValueError("model response did not contain a paraphrases list")

            paraphrases = sanitize_paraphrases(
                [str(item) for item in raw_paraphrases],
                original_prompt=seed_entry.get("input", ""),
                existing_texts=existing_texts,
                limit=needed,
            )
            if len(paraphrases) < needed:
                raise ValueError(f"expected {needed} clean paraphrases, got {len(paraphrases)}")

            next_index = len(existing_texts) + 1
            for offset, text in enumerate(paraphrases):
                append_jsonl(
                    build_output_entry(
                        seed_entry=seed_entry,
                        paraphrase_text=text,
                        model=args.model,
                        temperature=args.temperature,
                        max_output_tokens=args.max_output_tokens,
                        variant_index=next_index + offset,
                        prompt_mode=retry_prompt_mode(seed_entry) or DEFAULT_PROMPT_MODE,
                    ),
                    output_file,
                )
                written += 1
        except Exception as exc:
            failed += 1
            log_materialization_error(
                log_file=log_file,
                custom_id=custom_id,
                seed_role=seed_role,
                message=str(exc),
            )

    if batch_error_file.exists():
        for batch_line in iter_jsonl(batch_error_file):
            summary = summarize_batch_error(batch_line)
            seed_entry = seed_map.get(summary["custom_id"] or "")
            summary["seed_role"] = (
                seed_entry.get("metadata", {}).get("seed_role", "<unknown>")
                if seed_entry
                else "<unknown>"
            )
            append_jsonl(summary, log_file)

    print("materialized output file:", format_display_path(output_file))
    print("materialized error log:", format_display_path(log_file))
    print("rows written:", f"{written:,}")
    print("rows failed/logged:", f"{failed:,}")
    summary = summarize_materialized_paraphrase_artifact(output_file, log_file)
    print("total rows in artifact:", f"{summary['rows']:,}")
    print("unique source seeds represented:", f"{summary['unique_source_seed_ids']:,}")
    print("total logged errors:", f"{summary['error_rows']:,}")
    print("\nrole distribution")
    for key, value in summary["role_counts"].most_common():
        print(f"  {key}: {value:,}")
    print("\nprompt types")
    for key, value in summary["prompt_type_counts"].most_common():
        print(f"  {key}: {value:,}")
    print("\nparaphrase source prompt types")
    for key, value in summary["source_prompt_type_counts"].most_common():
        print(f"  {key}: {value:,}")
    if summary["error_type_counts"]:
        print("\nlogged error types")
        for key, value in summary["error_type_counts"].most_common():
            print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()
