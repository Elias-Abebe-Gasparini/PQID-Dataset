"""
apply_acceptance_disagreement_adjudication.py
---------------------------------------------
Apply the disagreement-adjudication defaults back onto the Stage K pilot review
sheet so the existing K7/K8 import path can be reused without extra notebook
editing.

Policy implemented here:
- rows marked `obvious_rewrite` in the disagreement adjudication sheet are
  converted to `rewrite`
- rows marked `manual_spot_check` retain the existing human review decision
- a snapshot of the pre-adjudication review sheet is written before overwrite
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import shutil
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path


DEFAULT_REVIEW_SHEET = PROCESSED_DIR / "instruction_acceptance_gate_pilot_review_sheet_v1.csv"
DEFAULT_ADJUDICATION_SHEET = (
    PROCESSED_DIR / "instruction_acceptance_gate_pilot_disagreement_adjudication_v1.csv"
)
DEFAULT_SNAPSHOT_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_pilot_review_sheet_v1_preadjudication_snapshot.csv"
)
DEFAULT_SUMMARY_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_pilot_review_sheet_v1_adjudication_summary.json"
)

ADJUDICATION_APPLY_VERSION = "instruction_acceptance_gate_pilot_review_bulk_adjudication_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-sheet", default=str(DEFAULT_REVIEW_SHEET))
    parser.add_argument("--adjudication-sheet", default=str(DEFAULT_ADJUDICATION_SHEET))
    parser.add_argument("--snapshot-file", default=str(DEFAULT_SNAPSHOT_FILE))
    parser.add_argument("--summary-file", default=str(DEFAULT_SUMMARY_FILE))
    return parser.parse_args()


def load_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


def write_csv_rows(rows: list[dict[str, str]], fieldnames: list[str], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize(value: str | None) -> str:
    return str(value or "").strip()


def build_adjudication_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for row in rows:
        key = normalize(row.get("instruction_key"))
        if key:
            mapping[key] = row
    return mapping


def main() -> None:
    args = parse_args()
    review_sheet = Path(args.review_sheet)
    adjudication_sheet = Path(args.adjudication_sheet)
    snapshot_file = Path(args.snapshot_file)
    summary_file = Path(args.summary_file)

    review_rows, fieldnames = load_csv_rows(review_sheet)
    adjudication_rows, _ = load_csv_rows(adjudication_sheet)
    adjudication_map = build_adjudication_map(adjudication_rows)

    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(review_sheet, snapshot_file)

    original_decision_counts = Counter(normalize(r.get("acceptance_decision")) or "<blank>" for r in review_rows)
    applied_bucket_counts = Counter()
    final_decision_counts = Counter()

    updated = 0
    retained = 0

    for row in review_rows:
        key = normalize(row.get("instruction_key"))
        adjudication = adjudication_map.get(key)
        if not adjudication:
            final_decision_counts[normalize(row.get("acceptance_decision")) or "<blank>"] += 1
            continue

        bucket = normalize(adjudication.get("adjudication_bucket"))
        applied_bucket_counts[bucket or "<missing>"] += 1

        if bucket == "obvious_rewrite":
            row["acceptance_review_status"] = "reviewed"
            row["acceptance_decision"] = "rewrite"
            row["acceptance_rewrite_required"] = "yes"
            row["role_fidelity"] = "major_issue"
            row["semantic_grounding"] = "major_issue"
            if normalize(row.get("source_branch")) == "source_code":
                row["teacher_text_answer_quality"] = "n_a"
            note = normalize(adjudication.get("adjudication_rationale"))
            model_note = normalize(adjudication.get("model_reviewer_notes"))
            guidance = normalize(adjudication.get("model_rewrite_guidance"))
            row["reviewer_notes"] = (
                "bulk_adjudicated_rewrite; "
                + note
                + (f"; model_note={model_note}" if model_note else "")
            ).strip()
            row["rewrite_guidance"] = guidance
            updated += 1
        else:
            retained += 1

        final_decision_counts[normalize(row.get("acceptance_decision")) or "<blank>"] += 1

    write_csv_rows(review_rows, fieldnames, review_sheet)

    summary = {
        "adjudication_apply_version": ADJUDICATION_APPLY_VERSION,
        "review_sheet": format_display_path(review_sheet),
        "preadjudication_snapshot": format_display_path(snapshot_file),
        "adjudication_sheet": format_display_path(adjudication_sheet),
        "rows_total": len(review_rows),
        "rows_bulk_rewritten": updated,
        "rows_retained_for_manual_or_existing_decision": retained,
        "original_decision_counts": dict(sorted(original_decision_counts.items())),
        "applied_bucket_counts": dict(sorted(applied_bucket_counts.items())),
        "final_decision_counts": dict(sorted(final_decision_counts.items())),
    }
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Acceptance-gate pilot bulk adjudication applied")
    print(f"  review sheet updated: {review_sheet}")
    print(f"  preadjudication snapshot: {snapshot_file}")
    print(f"  summary file: {summary_file}")
    print(f"  rows bulk rewritten: {updated:,}")
    print(f"  rows retained: {retained:,}")
    print("  final decision counts:")
    for key, value in sorted(final_decision_counts.items()):
        print(f"    {key}: {value:,}")


if __name__ == "__main__":
    main()
