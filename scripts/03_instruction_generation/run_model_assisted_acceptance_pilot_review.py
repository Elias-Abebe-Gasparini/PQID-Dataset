"""
run_model_assisted_acceptance_pilot_review.py
--------------------------------------------
Run a resumable model-assisted review pass over the Stage K pilot review sheet.

This pass is intentionally supplementary:
- it does not overwrite the human review sheet
- it writes a separate cache and comparison sheet
- it is designed as a second-opinion layer, not a replacement for human judgment
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from openai import AsyncOpenAI, RateLimitError
except ImportError:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore[assignment]

    class RateLimitError(Exception):
        pass

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path, load_openai_api_key


DEFAULT_REVIEW_SHEET = PROCESSED_DIR / "instruction_acceptance_gate_pilot_review_sheet_v1.csv"
DEFAULT_CACHE_FILE = PROCESSED_DIR / "instruction_acceptance_gate_pilot_model_review_cache_v1.jsonl"
DEFAULT_SUGGESTION_SHEET = (
    PROCESSED_DIR / "instruction_acceptance_gate_pilot_model_review_sheet_v1.csv"
)
DEFAULT_SUMMARY_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_pilot_model_review_summary_v1.json"
)
DEFAULT_ERROR_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_pilot_model_review_errors_v1.jsonl"
)

DEFAULT_MODEL = "gpt-5.4"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_OUTPUT_TOKENS = 320
DEFAULT_CONCURRENCY = 8
MODEL_REVIEW_VERSION = "instruction_acceptance_gate_pilot_model_review_v1"

VALID_DECISIONS = {"accept", "rewrite", "reject", "defer"}
VALID_REWRITE_VALUES = {"yes", "no"}
VALID_RUBRIC_VALUES = {"pass", "minor_issue", "major_issue", "n_a"}
RUBRIC_FIELDS = [
    "role_fidelity",
    "semantic_grounding",
    "confidence_discipline",
    "hallucination_risk",
    "teacher_text_answer_quality",
]

SYSTEM_PROMPT = """You are assisting with the PQID acceptance-gate pilot review.

You are reviewing an instruction-output pair. Be conservative, structured, and concise.

Important policy:
- Multilingual traces in upstream source-code comments are not automatically a defect.
- For `source_code` rows, non-English comments inherited from original repositories may be acceptable.
- Only recommend `rewrite` when the instruction/output pair itself has a quality problem worth correcting.
- Use `teacher_text_answer_quality = n_a` for `source_code` rows unless there is a very specific reason otherwise.

Return valid JSON only with exactly these keys:
- "acceptance_decision"         -> one of: accept, rewrite, reject, defer
- "acceptance_rewrite_required" -> one of: yes, no
- "role_fidelity"               -> one of: pass, minor_issue, major_issue, n_a
- "semantic_grounding"          -> one of: pass, minor_issue, major_issue, n_a
- "confidence_discipline"       -> one of: pass, minor_issue, major_issue, n_a
- "hallucination_risk"          -> one of: pass, minor_issue, major_issue, n_a
- "teacher_text_answer_quality" -> one of: pass, minor_issue, major_issue, n_a
- "reviewer_notes"              -> short plain-text note
- "rewrite_guidance"            -> short plain-text guidance, empty string if not needed
- "language_scope_note"         -> short note about any relevant language/multilingual observation
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-sheet", default=str(DEFAULT_REVIEW_SHEET))
    parser.add_argument("--cache-file", default=str(DEFAULT_CACHE_FILE))
    parser.add_argument("--suggestion-sheet", default=str(DEFAULT_SUGGESTION_SHEET))
    parser.add_argument("--summary-file", default=str(DEFAULT_SUMMARY_FILE))
    parser.add_argument("--error-file", default=str(DEFAULT_ERROR_FILE))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--max-rows", type=int, default=None)
    return parser.parse_args()


def append_jsonl(entry: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            key = str(row.get("instruction_key") or "").strip()
            if key:
                rows[key] = row
    return rows


def extract_json_blob(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("model response did not contain a JSON object")
        return json.loads(match.group(0))


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_decision(value: Any) -> str:
    decision = normalize_text(value).lower()
    if decision in VALID_DECISIONS:
        return decision
    return "defer"


def normalize_rewrite_required(value: Any, *, decision: str) -> str:
    rewrite = normalize_text(value).lower()
    if rewrite in VALID_REWRITE_VALUES:
        return rewrite
    if decision == "accept":
        return "no"
    if decision in {"rewrite", "defer"}:
        return "yes"
    return "no"


def normalize_rubric_value(value: Any, *, default: str = "n_a") -> str:
    rubric = normalize_text(value).lower()
    if rubric in VALID_RUBRIC_VALUES:
        return rubric
    return default


def build_user_prompt(row: dict[str, str]) -> str:
    payload = {
        "source_branch": normalize_text(row.get("source_branch")),
        "instruction_kind": normalize_text(row.get("instruction_kind")),
        "seed_role": normalize_text(row.get("seed_role")),
        "seed_target_supervision_mode": normalize_text(row.get("seed_target_supervision_mode")),
        "expected_response_mode": normalize_text(row.get("expected_response_mode")),
        "prompt_type": normalize_text(row.get("prompt_type")),
        "paraphrase_prompt_mode": normalize_text(row.get("paraphrase_prompt_mode")),
        "review_priority": normalize_text(row.get("review_priority")),
        "validation_status": normalize_text(row.get("validation_status")),
        "repo_owner": normalize_text(row.get("repo_owner")),
        "repo_name": normalize_text(row.get("repo_name")),
        "file_path": normalize_text(row.get("file_path")),
        "original_url": normalize_text(row.get("original_url")),
        "input": normalize_text(row.get("input")),
        "output": normalize_text(row.get("output")),
    }
    return (
        "Review this PQID pilot row and return a structured suggestion.\n\n"
        "Context:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Remember:\n"
        "- multilingual code comments inherited from upstream source repositories can be acceptable;\n"
        "- do not force English-only assumptions onto source_code outputs;\n"
        "- focus on whether this pair is suitable as-is for the dataset.\n"
    )


async def review_one(
    *,
    client: AsyncOpenAI,
    row: dict[str, str],
    model: str,
    temperature: float,
    max_output_tokens: int,
) -> dict[str, Any]:
    response = await client.responses.create(
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(row)},
        ],
    )
    content = getattr(response, "output_text", "") or ""
    parsed = extract_json_blob(content)
    decision = normalize_decision(parsed.get("acceptance_decision"))
    source_branch = normalize_text(row.get("source_branch"))
    teacher_default = "n_a" if source_branch == "source_code" else "pass"
    suggestion = {
        "acceptance_decision": decision,
        "acceptance_rewrite_required": normalize_rewrite_required(
            parsed.get("acceptance_rewrite_required"),
            decision=decision,
        ),
        "role_fidelity": normalize_rubric_value(parsed.get("role_fidelity"), default="pass"),
        "semantic_grounding": normalize_rubric_value(
            parsed.get("semantic_grounding"),
            default="pass",
        ),
        "confidence_discipline": normalize_rubric_value(
            parsed.get("confidence_discipline"),
            default="pass",
        ),
        "hallucination_risk": normalize_rubric_value(
            parsed.get("hallucination_risk"),
            default="pass",
        ),
        "teacher_text_answer_quality": normalize_rubric_value(
            parsed.get("teacher_text_answer_quality"),
            default=teacher_default,
        ),
        "reviewer_notes": normalize_text(parsed.get("reviewer_notes")),
        "rewrite_guidance": normalize_text(parsed.get("rewrite_guidance")),
        "language_scope_note": normalize_text(parsed.get("language_scope_note")),
    }
    return {
        "instruction_key": normalize_text(row.get("instruction_key")),
        "pilot_row_index": normalize_text(row.get("pilot_row_index")),
        "model_review_version": MODEL_REVIEW_VERSION,
        "model_review_model": model,
        "model_review_temperature": temperature,
        "model_review_status": "reviewed",
        "model_review_raw_text": content,
        "model_review_suggestion": suggestion,
    }


def merge_suggestions(
    *,
    review_rows: list[dict[str, str]],
    cache_rows: dict[str, dict[str, Any]],
    review_sheet: Path,
    suggestion_sheet: Path,
    summary_file: Path,
    model: str,
    temperature: float,
) -> None:
    fieldnames = [
        "pilot_row_index",
        "instruction_key",
        "source_branch",
        "instruction_kind",
        "seed_role",
        "paraphrase_prompt_mode",
        "review_priority",
        "input",
        "output",
        "acceptance_review_status",
        "acceptance_decision",
        "acceptance_rewrite_required",
        "role_fidelity",
        "semantic_grounding",
        "confidence_discipline",
        "hallucination_risk",
        "teacher_text_answer_quality",
        "reviewer_notes",
        "rewrite_guidance",
        "model_review_status",
        "model_review_model",
        "model_review_temperature",
        "model_acceptance_decision",
        "model_acceptance_rewrite_required",
        "model_role_fidelity",
        "model_semantic_grounding",
        "model_confidence_discipline",
        "model_hallucination_risk",
        "model_teacher_text_answer_quality",
        "model_reviewer_notes",
        "model_rewrite_guidance",
        "model_language_scope_note",
        "human_model_decision_agreement",
    ]

    merged_rows: list[dict[str, Any]] = []
    model_status_counts = Counter()
    model_decision_counts = Counter()
    agreement_counts = Counter()
    disagreement_examples: list[dict[str, str]] = []

    for row in review_rows:
        key = normalize_text(row.get("instruction_key"))
        cached = cache_rows.get(key)
        suggestion = (cached or {}).get("model_review_suggestion", {}) or {}

        human_decision = normalize_text(row.get("acceptance_decision")).lower()
        model_decision = normalize_text(suggestion.get("acceptance_decision")).lower()
        if human_decision and model_decision:
            agreement = "agree" if human_decision == model_decision else "disagree"
        else:
            agreement = "unscored"

        merged = {
            "pilot_row_index": row.get("pilot_row_index", ""),
            "instruction_key": key,
            "source_branch": row.get("source_branch", ""),
            "instruction_kind": row.get("instruction_kind", ""),
            "seed_role": row.get("seed_role", ""),
            "paraphrase_prompt_mode": row.get("paraphrase_prompt_mode", ""),
            "review_priority": row.get("review_priority", ""),
            "input": row.get("input", ""),
            "output": row.get("output", ""),
            "acceptance_review_status": row.get("acceptance_review_status", ""),
            "acceptance_decision": row.get("acceptance_decision", ""),
            "acceptance_rewrite_required": row.get("acceptance_rewrite_required", ""),
            "role_fidelity": row.get("role_fidelity", ""),
            "semantic_grounding": row.get("semantic_grounding", ""),
            "confidence_discipline": row.get("confidence_discipline", ""),
            "hallucination_risk": row.get("hallucination_risk", ""),
            "teacher_text_answer_quality": row.get("teacher_text_answer_quality", ""),
            "reviewer_notes": row.get("reviewer_notes", ""),
            "rewrite_guidance": row.get("rewrite_guidance", ""),
            "model_review_status": (cached or {}).get("model_review_status", "pending"),
            "model_review_model": (cached or {}).get("model_review_model", model),
            "model_review_temperature": (cached or {}).get("model_review_temperature", temperature),
            "model_acceptance_decision": suggestion.get("acceptance_decision", ""),
            "model_acceptance_rewrite_required": suggestion.get("acceptance_rewrite_required", ""),
            "model_role_fidelity": suggestion.get("role_fidelity", ""),
            "model_semantic_grounding": suggestion.get("semantic_grounding", ""),
            "model_confidence_discipline": suggestion.get("confidence_discipline", ""),
            "model_hallucination_risk": suggestion.get("hallucination_risk", ""),
            "model_teacher_text_answer_quality": suggestion.get("teacher_text_answer_quality", ""),
            "model_reviewer_notes": suggestion.get("reviewer_notes", ""),
            "model_rewrite_guidance": suggestion.get("rewrite_guidance", ""),
            "model_language_scope_note": suggestion.get("language_scope_note", ""),
            "human_model_decision_agreement": agreement,
        }
        merged_rows.append(merged)

        model_status_counts[merged["model_review_status"] or "<blank>"] += 1
        model_decision_counts[merged["model_acceptance_decision"] or "<blank>"] += 1
        agreement_counts[agreement] += 1
        if agreement == "disagree" and len(disagreement_examples) < 20:
            disagreement_examples.append(
                {
                    "pilot_row_index": str(merged["pilot_row_index"]),
                    "instruction_key": key,
                    "human_acceptance_decision": human_decision,
                    "model_acceptance_decision": model_decision,
                    "source_branch": str(merged["source_branch"]),
                    "instruction_kind": str(merged["instruction_kind"]),
                    "seed_role": str(merged["seed_role"]),
                }
            )

    suggestion_sheet.parent.mkdir(parents=True, exist_ok=True)
    with suggestion_sheet.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_rows)

    summary = {
        "model_review_version": MODEL_REVIEW_VERSION,
        "source_review_sheet": format_display_path(review_sheet),
        "suggestion_sheet": format_display_path(suggestion_sheet),
        "summary_file": format_display_path(summary_file),
        "rows": len(merged_rows),
        "model_review_model": model,
        "model_review_temperature": temperature,
        "model_review_status_counts": dict(sorted(model_status_counts.items())),
        "model_acceptance_decision_counts": dict(sorted(model_decision_counts.items())),
        "human_model_decision_agreement_counts": dict(sorted(agreement_counts.items())),
        "decision_disagreement_examples": disagreement_examples,
    }
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Model-assisted pilot review completed")
    print("  source review sheet:", format_display_path(DEFAULT_REVIEW_SHEET))
    print("  suggestion sheet:", format_display_path(suggestion_sheet))
    print("  summary file:", format_display_path(summary_file))
    print("  model review status counts:")
    for key, value in sorted(model_status_counts.items()):
        print(f"    {key}: {value:,}")
    print("  model acceptance decisions:")
    for key, value in sorted(model_decision_counts.items()):
        print(f"    {key}: {value:,}")
    print("  human/model decision agreement:")
    for key, value in sorted(agreement_counts.items()):
        print(f"    {key}: {value:,}")


async def async_main(args: argparse.Namespace) -> None:
    if AsyncOpenAI is None:
        raise RuntimeError("openai package is required for model-assisted review")

    review_sheet = Path(args.review_sheet)
    cache_file = Path(args.cache_file)
    suggestion_sheet = Path(args.suggestion_sheet)
    summary_file = Path(args.summary_file)
    error_file = Path(args.error_file)

    with review_sheet.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        review_rows = list(reader)
    if args.max_rows is not None:
        review_rows = review_rows[: args.max_rows]

    cache_rows = load_cache(cache_file)
    pending_rows = [
        row for row in review_rows
        if normalize_text(row.get("instruction_key")) not in cache_rows
    ]

    api_key = load_openai_api_key(__file__)
    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(max(1, args.concurrency))
    completed_count = len(cache_rows)
    total = len(review_rows)

    async def worker(row: dict[str, str]) -> None:
        nonlocal completed_count
        instruction_key = normalize_text(row.get("instruction_key"))
        try:
            async with semaphore:
                suggestion = await review_one(
                    client=client,
                    row=row,
                    model=args.model,
                    temperature=args.temperature,
                    max_output_tokens=args.max_output_tokens,
                )
            append_jsonl(suggestion, cache_file)
            cache_rows[instruction_key] = suggestion
            completed_count += 1
            if completed_count == total or completed_count % 10 == 0:
                print(f"model-reviewed {completed_count:,} / {total:,}")
        except RateLimitError as exc:
            append_jsonl(
                {
                    "instruction_key": instruction_key,
                    "error_type": "RateLimitError",
                    "error_message": str(exc),
                },
                error_file,
            )
            raise
        except Exception as exc:
            append_jsonl(
                {
                    "instruction_key": instruction_key,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
                error_file,
            )
            completed_count += 1
            print(f"model-review error for {instruction_key}: {type(exc).__name__}: {exc}")

    if pending_rows:
        print("Running model-assisted pilot review")
        print("  review sheet:", format_display_path(review_sheet))
        print("  cache file:", format_display_path(cache_file))
        print("  model:", args.model)
        print("  temperature:", args.temperature)
        print("  max_output_tokens:", args.max_output_tokens)
        print("  concurrency:", args.concurrency)
        print("  pending rows:", f"{len(pending_rows):,}")
        await asyncio.gather(*(worker(row) for row in pending_rows))
    else:
        print("Model-assisted pilot review cache already complete; rebuilding merged outputs only.")

    merge_suggestions(
        review_rows=review_rows,
        cache_rows=cache_rows,
        review_sheet=review_sheet,
        suggestion_sheet=suggestion_sheet,
        summary_file=summary_file,
        model=args.model,
        temperature=args.temperature,
    )


def main() -> None:
    args = parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
