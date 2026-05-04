"""
generate_paraphrases_quality_aware.py
-------------------------------------
Generate paraphrase variants for quality-aware PQID seed instructions.

This stage belongs to the rebuilt 2026 instruction-generation path, not the
legacy thesis pipeline. It expects quality-aware seed JSONL entries and
preserves their role-conditioned lineage while adding paraphrase-specific
metadata.

Key properties:
- resume-safe at the source-seed level
- partial-run aware (can fill missing paraphrase slots)
- grounded in the original seed role plus source-code context
- uses the Responses API for current GPT-5.x models

The intended production order is:
1. generate or review quality-aware seeds
2. expand those seeds into paraphrases

For now, the notebook may still point this stage at audited draft seeds until a
separate critique/rewrite pass is implemented.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import datetime as dt
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from openai import AsyncOpenAI, RateLimitError

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from project_paths import (
    PROCESSED_DIR,
    format_display_path,
    load_openai_api_key,
)
from quality_aware_seed_common import (
    QUALITY_AWARE_PARAPHRASE_PROMPT_TYPE,
    DEFAULT_PARAPHRASE_MODEL,
    PARAPHRASE_TEMPLATE_VERSION,
    canonicalize_quality_aware_prompt_type,
)

try:
    import tiktoken

    _CL100K = tiktoken.get_encoding("cl100k_base")
except Exception:
    _CL100K = None


DEFAULT_INPUT_CANDIDATES = [
    PROCESSED_DIR / "seed_drafts_quality_aware_source_code_v1.jsonl",
    PROCESSED_DIR / "seed_drafts_quality_aware_v1.jsonl",
]
DEFAULT_OUTPUT_FILE = PROCESSED_DIR / "seed_paraphrases_quality_aware_source_code_v1.jsonl"
DEFAULT_LOG_FILE = PROCESSED_DIR / "seed_paraphrases_quality_aware_source_code_v1_errors.jsonl"

BATCH_SIZE = 12
DEFAULT_TEMPERATURE = 0.2
DEFAULT_NUM_PARAPHRASES = 5
MAX_TOKENS = 500
DEFAULT_PROMPT_MODE = "standard"


ANTI_TEMPLATE_STYLE_GUIDANCE = {
    "direct_question": (
        "Write the instruction as a direct question to the assistant. Do not use a"
        " generic review-style opener."
    ),
    "troubleshooting_request": (
        "Write it as a troubleshooting request from a user trying to debug the"
        " snippet or fragment."
    ),
    "code_review_request": (
        "Write it as a cautious code-review request that asks for trustworthiness,"
        " ambiguity, and missing-context analysis."
    ),
    "repair_plan_request": (
        "Write it as a request for a repair or completion plan, while still making"
        " clear that the snippet is incomplete or unreliable."
    ),
    "risk_assessment_request": (
        "Write it as a request to assess reliability, risks, and missing context"
        " before any repair or completion is attempted."
    ),
}


SYSTEM_PROMPT = """You are generating paraphrase variants for the PQID project.

Return valid JSON only with exactly this key:
- "paraphrases"

Requirements:
- "paraphrases" must be a JSON array of strings.
- Each paraphrase must stay in English and remain a single natural-language instruction.
- Preserve task type, role framing, qubit counts, measurements, parameter names, gate families, and any explicit deliverables such as OpenQASM or explanation requirements.
- Do not change a generation task into a repair task or a repair task into a generation task.
- Do not introduce unsupported operations, extra requirements, or benchmark claims.
- Vary wording, sentence structure, and openers across the paraphrases.
- Do not number the paraphrases.
- Do not include commentary outside the JSON object.
"""


def default_input_file() -> Path:
    for candidate in DEFAULT_INPUT_CANDIDATES:
        if candidate.exists():
            return candidate
    return DEFAULT_INPUT_CANDIDATES[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-file", default=str(default_input_file()))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
    parser.add_argument("--model", default=DEFAULT_PARAPHRASE_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--num-paraphrases", type=int, default=DEFAULT_NUM_PARAPHRASES)
    parser.add_argument("--max-output-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--max-paraphrases-per-request", type=int, default=None)
    parser.add_argument("--prompt-mode", default=DEFAULT_PROMPT_MODE)
    parser.add_argument("--max-seeds", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(entry: dict, path: Path) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def token_count_cl100k(text: str) -> int | None:
    if _CL100K is None or not text or not text.strip():
        return None
    try:
        return len(_CL100K.encode(text))
    except Exception:
        return None


def content_hash(input_text: str, output_text: str) -> str:
    combined = (input_text + output_text).strip()
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


def source_seed_id(entry: dict) -> str:
    meta = entry.get("metadata", {})
    return str(meta.get("content_hash") or meta.get("circuit_hash") or "").strip()


def retry_requested_count(entry: dict) -> int | None:
    meta = entry.get("metadata", {})
    value = meta.get("paraphrase_retry_requested_count")
    if value in {None, ""}:
        return None
    try:
        count = int(value)
    except Exception:
        return None
    return count if count > 0 else None


def retry_missing_count(entry: dict) -> int | None:
    meta = entry.get("metadata", {})
    value = meta.get("paraphrase_retry_missing_count")
    if value in {None, ""}:
        return None
    try:
        count = int(value)
    except Exception:
        return None
    return count if count > 0 else None


def retry_prompt_mode(entry: dict) -> str:
    meta = entry.get("metadata", {})
    value = str(meta.get("paraphrase_retry_prompt_mode") or "").strip().lower()
    return value or DEFAULT_PROMPT_MODE


def retry_surface_form(entry: dict) -> str:
    meta = entry.get("metadata", {})
    return str(meta.get("paraphrase_retry_surface_form") or "").strip().lower()


def effective_paraphrases_needed(
    *,
    seed_entry: dict,
    total_missing: int,
    max_paraphrases_per_request: int | None = None,
) -> int:
    target = total_missing
    explicit_missing = retry_missing_count(seed_entry)
    if explicit_missing is not None:
        target = explicit_missing
    requested = retry_requested_count(seed_entry)
    if requested is not None:
        target = min(target, requested)
    if max_paraphrases_per_request is not None and max_paraphrases_per_request > 0:
        target = min(target, max_paraphrases_per_request)
    return max(0, target)


def extract_json_blob(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("model response did not contain a JSON object")
        return json.loads(match.group(0))


def load_existing_paraphrases(path: Path) -> dict[str, list[dict]]:
    rows_by_source: dict[str, list[dict]] = defaultdict(list)
    for row in load_jsonl(path):
        meta = row.get("metadata", {})
        key = str(
            meta.get("paraphrase_source_content_hash")
            or meta.get("paraphrase_source")
            or meta.get("circuit_hash")
            or ""
        ).strip()
        if key:
            rows_by_source[key].append(row)
    return rows_by_source


def summarize_paraphrase_artifacts(output_file: Path, log_file: Path) -> dict:
    role_counts = Counter()
    prompt_type_counts = Counter()
    source_prompt_type_counts = Counter()
    source_seed_ids: set[str] = set()
    rows = 0

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


def sanitize_paraphrases(
    paraphrases: list[str],
    *,
    original_prompt: str,
    existing_texts: list[str],
    limit: int,
) -> list[str]:
    existing_norm = {normalize_text(text) for text in existing_texts if text.strip()}
    original_norm = normalize_text(original_prompt)
    cleaned: list[str] = []
    seen_norm = set(existing_norm)

    for raw in paraphrases:
        text = str(raw).strip()
        if not text:
            continue
        norm = normalize_text(text)
        if not norm or norm == original_norm or norm in seen_norm:
            continue
        if len(text.split()) < 4:
            continue
        cleaned.append(text)
        seen_norm.add(norm)
        if len(cleaned) >= limit:
            break

    return cleaned


def opener_stems(texts: list[str], max_items: int = 8) -> list[str]:
    stems: list[str] = []
    seen: set[str] = set()
    for text in texts:
        words = str(text).strip().lower().split()
        if not words:
            continue
        stem = " ".join(words[: min(4, len(words))])
        if stem and stem not in seen:
            stems.append(stem)
            seen.add(stem)
        if len(stems) >= max_items:
            break
    return stems


def build_user_prompt(
    *,
    seed_entry: dict,
    paraphrases_needed: int,
    existing_texts: list[str],
    prompt_mode: str = DEFAULT_PROMPT_MODE,
) -> str:
    meta = seed_entry.get("metadata", {})
    resolved_prompt_mode = str(prompt_mode or retry_prompt_mode(seed_entry) or DEFAULT_PROMPT_MODE).strip().lower()
    resolved_surface_form = retry_surface_form(seed_entry)
    opener_blocklist = opener_stems([seed_entry.get("input", "")] + list(existing_texts))
    context = {
        "original_seed_instruction": seed_entry.get("input", ""),
        "seed_role": meta.get("seed_role"),
        "seed_learning_objective": meta.get("seed_learning_objective"),
        "seed_expected_response_mode": meta.get("seed_expected_response_mode"),
        "seed_quality_note": meta.get("seed_quality_note", ""),
        "source_prompt_type": canonicalize_quality_aware_prompt_type(meta.get("prompt_type")),
        "circuit_family": meta.get("circuit_family"),
        "semantic_intent": meta.get("semantic_intent"),
        "n_qubits": meta.get("n_qubits"),
        "output_code": seed_entry.get("output", ""),
        "openqasm3_code": seed_entry.get("openqasm3_code"),
        "paraphrases_needed": paraphrases_needed,
        "existing_paraphrases_to_avoid_repeating": existing_texts,
        "prompt_mode": resolved_prompt_mode,
    }
    prompt_parts = [
        "Generate paraphrases for the following quality-aware PQID seed.\n\n",
        "Keep the task semantics fixed while changing the surface form.\n",
        "Do not collapse role framing, technical constraints, or requested deliverables.\n",
    ]
    if resolved_prompt_mode == "anti_template":
        style_guidance = ANTI_TEMPLATE_STYLE_GUIDANCE.get(
            resolved_surface_form,
            (
                "Write a meaning-preserving but structurally distinct reframe. Avoid"
                " generic review-template openings."
            ),
        )
        prompt_parts.extend(
            [
                "This is an anti-template recovery request for a residual paraphrase slot.\n",
                "The current paraphrase pool has become template-heavy, so lexical and rhetorical diversity matter.\n",
                f"{style_guidance}\n",
                "Avoid generic opener families such as 'review this', 'assess this', 'explain why', 'diagnose', or near-equivalent boilerplate.\n",
            ]
        )
        if opener_blocklist:
            prompt_parts.append(
                "Avoid starting with any of these existing opener stems when possible:\n"
                f"{json.dumps(opener_blocklist, ensure_ascii=False)}\n"
            )
        if resolved_surface_form:
            context["anti_template_surface_form"] = resolved_surface_form
    prompt_parts.extend(
        [
            "\n",
            f"{json.dumps(context, ensure_ascii=False, indent=2)}\n\n",
            "Return valid JSON only.",
        ]
    )
    return "".join(prompt_parts)


async def paraphrase_one(
    *,
    client: AsyncOpenAI,
    model: str,
    temperature: float,
    max_output_tokens: int,
    seed_entry: dict,
    paraphrases_needed: int,
    existing_texts: list[str],
    prompt_mode: str,
) -> list[str]:
    response = await client.responses.create(
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(
                    seed_entry=seed_entry,
                    paraphrases_needed=paraphrases_needed,
                    existing_texts=existing_texts,
                    prompt_mode=prompt_mode,
                ),
            },
        ],
    )
    content = getattr(response, "output_text", "") or ""
    parsed = extract_json_blob(content)
    raw_paraphrases = parsed.get("paraphrases", [])
    if not isinstance(raw_paraphrases, list):
        raise ValueError("model response did not contain a paraphrases list")
    paraphrases = sanitize_paraphrases(
        [str(item) for item in raw_paraphrases],
        original_prompt=seed_entry.get("input", ""),
        existing_texts=existing_texts,
        limit=paraphrases_needed,
    )
    if len(paraphrases) < paraphrases_needed:
        raise ValueError(
            f"expected {paraphrases_needed} clean paraphrases, got {len(paraphrases)}"
        )
    return paraphrases


def build_output_entry(
    *,
    seed_entry: dict,
    paraphrase_text: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    variant_index: int,
    prompt_mode: str,
) -> dict:
    seed_meta = dict(seed_entry.get("metadata", {}))
    seed_prompt = str(seed_entry.get("input", "")).strip()
    seed_circuit_hash = str(seed_meta.get("circuit_hash", "")).strip()
    seed_content = str(seed_meta.get("content_hash", "")).strip()

    metadata = dict(seed_meta)
    metadata.update(
        {
            "prompt_type": QUALITY_AWARE_PARAPHRASE_PROMPT_TYPE,
            "generation_model": model,
            "generation_date": str(dt.date.today()),
            "paraphrase_source": seed_circuit_hash,
            "paraphrase_source_content_hash": seed_content,
            "paraphrase_source_prompt_type": canonicalize_quality_aware_prompt_type(
                seed_meta.get("prompt_type", "")
            ),
            "paraphrase_source_generation_model": seed_meta.get("generation_model", ""),
            "paraphrase_source_generation_date": seed_meta.get("generation_date", ""),
            "original_prompt": seed_prompt,
            "paraphrase_template_version": PARAPHRASE_TEMPLATE_VERSION,
            "paraphrase_generation_temperature": temperature,
            "paraphrase_generation_max_output_tokens": max_output_tokens,
            "paraphrase_generation_prompt_mode": prompt_mode,
            "paraphrase_variant_index": variant_index,
            "content_hash": content_hash(paraphrase_text, seed_entry.get("output", "")),
            "prompt_word_count": len(paraphrase_text.split()),
            "prompt_length_chars": len(paraphrase_text),
            "prompt_token_count_cl100k": token_count_cl100k(paraphrase_text),
        }
    )
    return {
        "input": paraphrase_text,
        "output": seed_entry.get("output", ""),
        "openqasm3_code": seed_entry.get("openqasm3_code"),
        "metadata": metadata,
    }


async def run_generation(
    *,
    seed_rows: list[dict],
    output_file: Path,
    log_file: Path,
    model: str,
    temperature: float,
    max_output_tokens: int,
    num_paraphrases: int,
    max_paraphrases_per_request: int | None,
    prompt_mode: str,
) -> None:
    api_key = load_openai_api_key(__file__)
    client = AsyncOpenAI(api_key=api_key)
    existing_rows = load_existing_paraphrases(output_file)
    sem = asyncio.Semaphore(BATCH_SIZE)

    async def worker(seed_entry: dict) -> None:
        key = source_seed_id(seed_entry)
        existing = existing_rows.get(key, [])
        existing_texts = [row.get("input", "") for row in existing]
        existing_count = len(existing_texts)
        total_missing = max(0, num_paraphrases - existing_count)
        if total_missing == 0:
            return
        paraphrases_needed = effective_paraphrases_needed(
            seed_entry=seed_entry,
            total_missing=total_missing,
            max_paraphrases_per_request=max_paraphrases_per_request,
        )
        if paraphrases_needed == 0:
            return

        try:
            async with sem:
                paraphrases = await paraphrase_one(
                    client=client,
                    model=model,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    seed_entry=seed_entry,
                    paraphrases_needed=paraphrases_needed,
                    existing_texts=existing_texts,
                    prompt_mode=prompt_mode,
                )
            next_index = existing_count + 1
            for offset, text in enumerate(paraphrases):
                append_jsonl(
                    build_output_entry(
                        seed_entry=seed_entry,
                        paraphrase_text=text,
                        model=model,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        variant_index=next_index + offset,
                        prompt_mode=prompt_mode,
                    ),
                    output_file,
                )
        except RateLimitError as exc:
            append_jsonl(
                {
                    "error_type": "RateLimitError",
                    "error_message": str(exc),
                    "seed_role": seed_entry.get("metadata", {}).get("seed_role"),
                    "source_seed_id": key,
                    "source_record": {
                        "circuit_hash": seed_entry.get("metadata", {}).get("circuit_hash"),
                        "content_hash": seed_entry.get("metadata", {}).get("content_hash"),
                    },
                },
                log_file,
            )
        except Exception as exc:
            append_jsonl(
                {
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "seed_role": seed_entry.get("metadata", {}).get("seed_role"),
                    "source_seed_id": key,
                    "source_record": {
                        "circuit_hash": seed_entry.get("metadata", {}).get("circuit_hash"),
                        "content_hash": seed_entry.get("metadata", {}).get("content_hash"),
                    },
                },
                log_file,
            )

    await asyncio.gather(*(worker(row) for row in seed_rows))


def select_seed_rows(seed_rows: list[dict], max_seeds: int | None) -> list[dict]:
    rows = [row for row in seed_rows if source_seed_id(row)]
    if max_seeds is not None:
        return rows[:max_seeds]
    return rows


def main() -> None:
    args = parse_args()
    seed_file = Path(args.seed_file)
    output_file = Path(args.output_file)
    log_file = Path(args.log_file)

    if not seed_file.exists():
        raise SystemExit(f"ERROR: seed file not found: {format_display_path(seed_file)}")

    seed_rows = select_seed_rows(load_jsonl(seed_file), args.max_seeds)
    print("seed file:", format_display_path(seed_file))
    print("loaded quality-aware seeds:", f"{len(seed_rows):,}")
    print("output file:", format_display_path(output_file))
    print("log file:", format_display_path(log_file))
    print("model:", args.model)
    print("temperature:", args.temperature)
    print("num paraphrases per seed:", args.num_paraphrases)
    print("max output tokens:", args.max_output_tokens)
    print("prompt mode:", args.prompt_mode)
    if args.max_paraphrases_per_request is not None:
        print("max paraphrases per request:", args.max_paraphrases_per_request)

    if not seed_rows:
        print("Nothing to do.")
        return

    if args.dry_run:
        preview_rows = seed_rows[: min(2, len(seed_rows))]
        for index, seed_entry in enumerate(preview_rows, start=1):
            existing_rows = load_existing_paraphrases(output_file).get(source_seed_id(seed_entry), [])
            existing_texts = [row.get("input", "") for row in existing_rows]
            needed = effective_paraphrases_needed(
                seed_entry=seed_entry,
                total_missing=max(0, args.num_paraphrases - len(existing_texts)),
                max_paraphrases_per_request=args.max_paraphrases_per_request,
            )
            print(f"\n=== Dry-run paraphrase prompt preview {index} ===\n")
            print(
                build_user_prompt(
                    seed_entry=seed_entry,
                    paraphrases_needed=needed,
                    existing_texts=existing_texts,
                    prompt_mode=args.prompt_mode,
                )
            )
        return

    asyncio.run(
        run_generation(
            seed_rows=seed_rows,
            output_file=output_file,
            log_file=log_file,
            model=args.model,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
            num_paraphrases=args.num_paraphrases,
            max_paraphrases_per_request=args.max_paraphrases_per_request,
            prompt_mode=args.prompt_mode,
        )
    )
    print("\nquality-aware paraphrase generation completed")
    print("output file:", format_display_path(output_file))
    print("log file:", format_display_path(log_file))
    summary = summarize_paraphrase_artifacts(output_file, log_file)
    print("rows materialized:", f"{summary['rows']:,}")
    print("unique source seeds represented:", f"{summary['unique_source_seed_ids']:,}")
    print("error rows logged:", f"{summary['error_rows']:,}")
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
        print("\nerror types")
        for key, value in summary["error_type_counts"].most_common():
            print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()
