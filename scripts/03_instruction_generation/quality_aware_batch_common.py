"""
quality_aware_batch_common.py
-----------------------------
Shared helpers for Batch API preparation and materialization of the
quality-aware seed and paraphrase stages.
"""

from __future__ import annotations

import json
from pathlib import Path


def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def append_jsonl(entry: dict, path: Path) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def make_seed_custom_id(circuit_hash: str, seed_role: str) -> str:
    return f"seed::{circuit_hash}::{seed_role}"


def make_paraphrase_custom_id(source_seed_id: str) -> str:
    return f"paraphrase::{source_seed_id}"


def extract_batch_output_text(batch_line: dict) -> str:
    response = batch_line.get("response") or {}
    body = response.get("body") or {}

    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    chunks: list[str] = []
    for item in body.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"}:
                text = (
                    content.get("text")
                    or content.get("output_text")
                    or content.get("value")
                    or ""
                )
                if text:
                    chunks.append(str(text))
    return "".join(chunks).strip()


def summarize_batch_error(batch_line: dict) -> dict:
    response = batch_line.get("response") or {}
    body = response.get("body") or {}
    error = batch_line.get("error") or body.get("error") or {}
    incomplete = body.get("incomplete_details") or {}
    status = body.get("status")
    incomplete_reason = incomplete.get("reason")
    message = error.get("message") or str(error) or "unknown batch failure"
    if status == "incomplete" and incomplete_reason:
        message = f"incomplete response: {incomplete_reason}"
    return {
        "custom_id": batch_line.get("custom_id"),
        "status_code": response.get("status_code"),
        "error_type": error.get("type") or batch_line.get("type") or "BatchRequestError",
        "error_message": message,
        "response_status": status,
        "incomplete_reason": incomplete_reason,
    }
