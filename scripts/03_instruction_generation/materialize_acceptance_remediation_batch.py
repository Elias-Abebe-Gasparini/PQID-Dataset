"""
materialize_acceptance_remediation_batch.py
-------------------------------------------
Normalize Batch API outputs from the Stage K acceptance-gate remediation pass.

Input is the downloaded Batch API output JSONL corresponding to
``instruction_acceptance_gate_remediation_batch_requests_v1.jsonl``. The script
joins each response back to the remediation candidate sidecar and writes a
reviewable normalized result file.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from quality_aware_batch_common import extract_batch_output_text, summarize_batch_error


REMEDIATION_RESULT_VERSION = "instruction_acceptance_gate_remediation_result_v1"

DEFAULT_CANDIDATE_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_remediation_candidates_v1.jsonl"
)
DEFAULT_BATCH_OUTPUT_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_remediation_batch_outputs_v1.jsonl"
)
DEFAULT_RESULT_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_remediation_outputs_v1.jsonl"
)
DEFAULT_REVIEW_SHEET = (
    PROCESSED_DIR / "instruction_acceptance_gate_remediation_outputs_v1.csv"
)
DEFAULT_ERROR_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_remediation_errors_v1.jsonl"
)
DEFAULT_SUMMARY_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_remediation_outputs_v1_summary.json"
)

VALID_DECISIONS = {"rewrite", "keep_original", "needs_manual_review"}

CSV_FIELDS = [
    "instruction_key",
    "review_group_key",
    "remediation_candidate_type",
    "remediation_priority",
    "source_branch",
    "instruction_kind",
    "seed_role",
    "remediation_decision",
    "changes_summary",
    "residual_risk_note",
    "input",
    "original_output",
    "remediated_output",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-file", default=str(DEFAULT_CANDIDATE_FILE))
    parser.add_argument("--batch-output-file", default=str(DEFAULT_BATCH_OUTPUT_FILE))
    parser.add_argument("--result-file", default=str(DEFAULT_RESULT_FILE))
    parser.add_argument("--review-sheet", default=str(DEFAULT_REVIEW_SHEET))
    parser.add_argument("--error-file", default=str(DEFAULT_ERROR_FILE))
    parser.add_argument("--summary-file", default=str(DEFAULT_SUMMARY_FILE))
    return parser.parse_args()


def normalize(value: Any) -> str:
    return str(value or "").strip()


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def append_jsonl(entry: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def extract_json_blob(text: str) -> dict[str, Any]:
    text = normalize(text)
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("response did not contain a JSON object")
        return json.loads(match.group(0))


def normalize_decision(value: Any) -> str:
    decision = normalize(value).lower()
    if decision in VALID_DECISIONS:
        return decision
    return "needs_manual_review"


def candidate_custom_id(row: dict[str, Any]) -> str:
    return f"acceptance_remediation::{row['instruction_key']}"


def load_candidates(path: Path) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(path):
        key = normalize(row.get("instruction_key"))
        if key:
            candidates[candidate_custom_id(row)] = row
    return candidates


def build_result(candidate: dict[str, Any], parsed: dict[str, Any], raw_text: str) -> dict[str, Any]:
    decision = normalize_decision(parsed.get("remediation_decision"))
    remediated_input = normalize(parsed.get("remediated_input")) or normalize(candidate.get("input"))
    remediated_output = normalize(parsed.get("remediated_output"))
    if decision == "keep_original" and not remediated_output:
        remediated_output = normalize(candidate.get("output"))
    result = dict(candidate)
    result["remediation_result"] = {
        "remediation_result_version": REMEDIATION_RESULT_VERSION,
        "remediation_decision": decision,
        "remediated_input": remediated_input,
        "remediated_output": remediated_output,
        "changes_summary": normalize(parsed.get("changes_summary")),
        "residual_risk_note": normalize(parsed.get("residual_risk_note")),
        "raw_model_text": raw_text,
    }
    return result


def result_csv_row(row: dict[str, Any]) -> dict[str, str]:
    context = row.get("review_context") or {}
    remediation = row.get("remediation_context") or {}
    result = row.get("remediation_result") or {}
    return {
        "instruction_key": normalize(row.get("instruction_key")),
        "review_group_key": normalize(row.get("review_group_key")),
        "remediation_candidate_type": normalize(remediation.get("remediation_candidate_type")),
        "remediation_priority": normalize(remediation.get("remediation_priority")),
        "source_branch": normalize(row.get("source_branch")),
        "instruction_kind": normalize(row.get("instruction_kind")),
        "seed_role": normalize(context.get("seed_role")),
        "remediation_decision": normalize(result.get("remediation_decision")),
        "changes_summary": normalize(result.get("changes_summary")),
        "residual_risk_note": normalize(result.get("residual_risk_note")),
        "input": normalize(result.get("remediated_input") or row.get("input")),
        "original_output": normalize(row.get("output")),
        "remediated_output": normalize(result.get("remediated_output")),
    }


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(result_csv_row(row))


def main() -> None:
    args = parse_args()
    candidate_file = Path(args.candidate_file)
    batch_output_file = Path(args.batch_output_file)
    result_file = Path(args.result_file)
    review_sheet = Path(args.review_sheet)
    error_file = Path(args.error_file)
    summary_file = Path(args.summary_file)

    candidates = load_candidates(candidate_file)
    results: list[dict[str, Any]] = []
    decision_counts = Counter()
    candidate_type_counts = Counter()
    error_counts = Counter()

    if result_file.exists():
        result_file.unlink()
    if error_file.exists():
        error_file.unlink()

    for batch_line in iter_jsonl(batch_output_file):
        custom_id = normalize(batch_line.get("custom_id"))
        candidate = candidates.get(custom_id)
        if not candidate:
            error = summarize_batch_error(batch_line)
            error["error_message"] = "custom_id not found in candidate file"
            append_jsonl(error, error_file)
            error_counts["missing_candidate"] += 1
            continue
        try:
            output_text = extract_batch_output_text(batch_line)
            parsed = extract_json_blob(output_text)
            result = build_result(candidate, parsed, output_text)
        except Exception as exc:
            error = summarize_batch_error(batch_line)
            error["error_message"] = f"{error.get('error_message')}; parse_error={exc}"
            append_jsonl(error, error_file)
            error_counts["parse_error"] += 1
            continue

        append_jsonl(result, result_file)
        results.append(result)
        decision = result["remediation_result"]["remediation_decision"]
        decision_counts[decision] += 1
        candidate_type_counts[
            normalize((candidate.get("remediation_context") or {}).get("remediation_candidate_type"))
        ] += 1

    write_csv(results, review_sheet)

    missing_outputs = sorted(set(candidates) - {candidate_custom_id(r) for r in results})
    summary = {
        "remediation_result_version": REMEDIATION_RESULT_VERSION,
        "candidate_file": format_display_path(candidate_file),
        "batch_output_file": format_display_path(batch_output_file),
        "result_file": format_display_path(result_file),
        "review_sheet": format_display_path(review_sheet),
        "error_file": format_display_path(error_file),
        "summary_file": format_display_path(summary_file),
        "candidate_rows": len(candidates),
        "result_rows": len(results),
        "error_counts": dict(sorted(error_counts.items())),
        "decision_counts": dict(sorted(decision_counts.items())),
        "candidate_type_counts": dict(sorted(candidate_type_counts.items())),
        "missing_output_count": len(missing_outputs),
        "missing_output_custom_ids_sample": missing_outputs[:20],
    }
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Acceptance-gate remediation outputs materialized")
    print(f"  candidates: {len(candidates):,}")
    print(f"  results: {len(results):,}")
    print(f"  errors: {sum(error_counts.values()):,}")
    print(f"  result file: {format_display_path(result_file)}")
    print(f"  review sheet: {format_display_path(review_sheet)}")
    print(f"  summary file: {format_display_path(summary_file)}")


if __name__ == "__main__":
    main()
