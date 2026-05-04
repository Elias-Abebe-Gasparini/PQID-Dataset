"""
build_acceptance_disagreement_adjudication_sheet.py
---------------------------------------------------
Build a disagreement-only adjudication sheet for the Stage K pilot review.

This helper is intentionally local and non-destructive:
- it reads the model-assisted comparison sheet from K9/K10
- it selects only human/model decision disagreements
- it prelabels obvious rewrite cases using conservative heuristics
- it leaves ambiguous leftovers for spot-check rather than forcing a verdict
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path


DEFAULT_MODEL_REVIEW_SHEET = (
    PROCESSED_DIR / "instruction_acceptance_gate_pilot_model_review_sheet_v1.csv"
)
DEFAULT_ADJUDICATION_SHEET = (
    PROCESSED_DIR / "instruction_acceptance_gate_pilot_disagreement_adjudication_v1.csv"
)
DEFAULT_SUMMARY_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_pilot_disagreement_adjudication_v1_summary.json"
)

ADJUDICATION_VERSION = "instruction_acceptance_gate_pilot_disagreement_adjudication_v1"

STRONG_REWRITE_PATTERNS = [
    (
        "undefined_or_missing_symbol",
        re.compile(
            r"\bundefined\b|"
            r"\bleaves? .* undefined\b|"
            r"\bfails? to define\b|"
            r"\bmissing\b|"
            r"\bnot runnable\b|"
            r"\bself-contained\b",
            re.IGNORECASE,
        ),
    ),
    (
        "repair_not_done",
        re.compile(
            r"\bdoes not satisfy the repair\b|"
            r"\bdoes not satisfy the repair/explanation request\b|"
            r"\bdoes not perform the requested repair\b|"
            r"\bdoes not perform the repair\b|"
            r"\bdoes not repair\b|"
            r"\bfails to .*repair\b|"
            r"\bonly repeats\b|"
            r"\bmerely repeats\b|"
            r"\bonly restates\b|"
            r"\bincomplete code fragment\b|"
            r"\bincomplete fragment\b|"
            r"\bdoes not make the example runnable\b",
            re.IGNORECASE,
        ),
    ),
    (
        "wrong_shape_or_target",
        re.compile(
            r"\bwrong\b.*\b(qubit|register|target|size|semantics)\b|"
            r"\bapplies .* instead of\b|"
            r"\ball qubits instead of\b|"
            r"\bmismatch\b|"
            r"\bwrong classical register\b|"
            r"\bwrong target\b|"
            r"\bwrong .* qubit\b|"
            r"\bwrong .* register\b",
            re.IGNORECASE,
        ),
    ),
    (
        "extra_content_violates_prompt",
        re.compile(
            r"\btwo circuits\b|"
            r"\balternative circuit\b|"
            r"\bextra .*commentary\b|"
            r"\bwarning/commentary\b|"
            r"\bintroduces evaluative commentary\b",
            re.IGNORECASE,
        ),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-review-sheet", default=str(DEFAULT_MODEL_REVIEW_SHEET))
    parser.add_argument("--adjudication-sheet", default=str(DEFAULT_ADJUDICATION_SHEET))
    parser.add_argument("--summary-file", default=str(DEFAULT_SUMMARY_FILE))
    return parser.parse_args()


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(rows: list[dict[str, str]], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def model_note_blob(row: dict[str, str]) -> str:
    return " ".join(
        [
            normalize_text(row.get("model_reviewer_notes")),
            normalize_text(row.get("model_rewrite_guidance")),
        ]
    ).strip()


def classify_row(row: dict[str, str]) -> tuple[str, str, str]:
    source_branch = normalize_text(row.get("source_branch"))
    model_decision = normalize_text(row.get("model_acceptance_decision")).lower()
    notes = model_note_blob(row)

    if model_decision != "rewrite":
        return ("manual_spot_check", "", "model did not recommend rewrite")

    if source_branch != "source_code":
        return (
            "manual_spot_check",
            "",
            "teacher_text disagreements are kept for human spot-check",
        )

    for bucket, pattern in STRONG_REWRITE_PATTERNS:
        if pattern.search(notes):
            return (
                "obvious_rewrite",
                bucket,
                f"model notes indicate {bucket.replace('_', ' ')}",
            )

    return (
        "manual_spot_check",
        "",
        "model suggested rewrite but no strong automatic rule matched",
    )


def build_output_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict]:
    disagreements = [
        row
        for row in rows
        if normalize_text(row.get("human_model_decision_agreement")).lower() == "disagree"
    ]

    output_rows: list[dict[str, str]] = []
    branch_counts = Counter()
    role_counts = Counter()
    kind_counts = Counter()
    bucket_counts = Counter()
    proposed_counts = Counter()
    reason_counts = Counter()

    for row in disagreements:
        bucket, reason_bucket, rationale = classify_row(row)
        proposed_final_decision = "rewrite" if bucket == "obvious_rewrite" else ""
        proposed_rewrite_required = "yes" if bucket == "obvious_rewrite" else ""
        human_spot_check_required = "no" if bucket == "obvious_rewrite" else "yes"

        out_row = {
            "pilot_row_index": normalize_text(row.get("pilot_row_index")),
            "instruction_key": normalize_text(row.get("instruction_key")),
            "source_branch": normalize_text(row.get("source_branch")),
            "instruction_kind": normalize_text(row.get("instruction_kind")),
            "seed_role": normalize_text(row.get("seed_role")),
            "review_priority": normalize_text(row.get("review_priority")),
            "input": normalize_text(row.get("input")),
            "output": normalize_text(row.get("output")),
            "human_acceptance_decision": normalize_text(row.get("acceptance_decision")),
            "model_acceptance_decision": normalize_text(row.get("model_acceptance_decision")),
            "model_reviewer_notes": normalize_text(row.get("model_reviewer_notes")),
            "model_rewrite_guidance": normalize_text(row.get("model_rewrite_guidance")),
            "adjudication_bucket": bucket,
            "adjudication_reason_bucket": reason_bucket,
            "adjudication_rationale": rationale,
            "proposed_final_decision": proposed_final_decision,
            "proposed_final_rewrite_required": proposed_rewrite_required,
            "human_spot_check_required": human_spot_check_required,
            "final_human_decision": "",
            "final_human_rewrite_required": "",
            "final_human_notes": "",
        }
        output_rows.append(out_row)

        branch_counts[out_row["source_branch"] or "<missing>"] += 1
        kind_counts[out_row["instruction_kind"] or "<missing>"] += 1
        role_counts[out_row["seed_role"] or "<missing>"] += 1
        bucket_counts[bucket] += 1
        proposed_counts[proposed_final_decision or "<blank>"] += 1
        reason_counts[reason_bucket or "<none>"] += 1

    summary = {
        "adjudication_version": ADJUDICATION_VERSION,
        "source_model_review_sheet": format_display_path(
            Path(args.model_review_sheet)  # type: ignore[name-defined]
        ),
        "adjudication_sheet": format_display_path(
            Path(args.adjudication_sheet)  # type: ignore[name-defined]
        ),
        "rows_scanned": len(rows),
        "disagreement_rows": len(disagreements),
        "branch_counts": dict(sorted(branch_counts.items())),
        "instruction_kind_counts": dict(sorted(kind_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "adjudication_bucket_counts": dict(sorted(bucket_counts.items())),
        "proposed_final_decision_counts": dict(sorted(proposed_counts.items())),
        "adjudication_reason_bucket_counts": dict(sorted(reason_counts.items())),
    }
    return output_rows, summary


def main() -> None:
    global args
    args = parse_args()
    model_review_sheet = Path(args.model_review_sheet)
    adjudication_sheet = Path(args.adjudication_sheet)
    summary_file = Path(args.summary_file)

    rows = load_csv_rows(model_review_sheet)
    output_rows, summary = build_output_rows(rows)

    adjudication_sheet.parent.mkdir(parents=True, exist_ok=True)
    summary_file.parent.mkdir(parents=True, exist_ok=True)

    write_csv_rows(output_rows, adjudication_sheet)
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Acceptance-gate disagreement adjudication sheet built")
    print(f"  source rows scanned: {summary['rows_scanned']:,}")
    print(f"  disagreement rows: {summary['disagreement_rows']:,}")
    print(f"  adjudication sheet: {adjudication_sheet}")
    print(f"  summary file: {summary_file}")
    print("  adjudication buckets:")
    for key, value in summary["adjudication_bucket_counts"].items():
        print(f"    {key}: {value:,}")
    print("  proposed final decisions:")
    for key, value in summary["proposed_final_decision_counts"].items():
        print(f"    {key}: {value:,}")


if __name__ == "__main__":
    main()
