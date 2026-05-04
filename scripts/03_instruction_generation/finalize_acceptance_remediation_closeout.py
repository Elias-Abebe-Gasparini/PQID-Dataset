"""
finalize_acceptance_remediation_closeout.py
-------------------------------------------
Apply the final human closeout overrides for the two non-rewrite rows left by
the Stage K-R acceptance-gate remediation materialization.

This script updates only the remediation sidecar outputs. It does not mutate the
canonical acceptance-gate manifest or the canonical instruction splits.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from materialize_acceptance_remediation_batch import write_csv


MANUAL_CLOSEOUT_VERSION = "instruction_acceptance_gate_remediation_manual_closeout_v1"

RESULT_FILE = PROCESSED_DIR / "instruction_acceptance_gate_remediation_outputs_v1.jsonl"
REVIEW_SHEET = PROCESSED_DIR / "instruction_acceptance_gate_remediation_outputs_v1.csv"
SUMMARY_FILE = PROCESSED_DIR / "instruction_acceptance_gate_remediation_outputs_v1_summary.json"
CLOSEOUT_FILE = PROCESSED_DIR / "instruction_acceptance_gate_remediation_manual_closeout_v1.json"

OVERRIDES: dict[str, dict[str, str]] = {
    "e5670c7ce95c8ebc48b7b8c31560e8acc9f6d112": {
        "remediation_decision": "rewrite",
        "remediated_output": """from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

theta = Parameter("theta")
phi = Parameter("phi")
lam = Parameter("lambda")

u3_to_u = QuantumCircuit(2, 2)
u3_to_u.u(theta, phi, lam, 0)
u3_to_u.cx(0, 1)
u3_to_u.rz(phi, 1)
u3_to_u.cx(0, 1)
u3_to_u.measure([0, 1], [0, 1])""",
        "changes_summary": (
            "Manual closeout rewrite. Replaced the undefined-symbol fragment "
            "with a complete two-qubit Qiskit circuit, explicit Parameter "
            "objects, additional operations, and measurements."
        ),
        "residual_risk_note": (
            "Closed by manual adjudication as a self-contained illustrative "
            "benchmark-readiness rewrite; no unresolved symbols remain."
        ),
    },
    "dd3eaeeaaec9a4cfeaa22e8698ad726718a2caa1": {
        "remediation_decision": "rewrite",
        "remediated_output": """from qiskit import QuantumCircuit

qc = QuantumCircuit(3, 3)
qc.h(0)
qc.cx(0, 1)
qc.cx(0, 2)
qc.measure([0, 1, 2], [0, 1, 2])""",
        "changes_summary": (
            "Manual closeout rewrite. Preserved the requested GHZ construction "
            "while adding the missing import and removing the dangling simulator "
            "comment from the original lineage-neighbor output."
        ),
        "residual_risk_note": (
            "Closed by manual adjudication; the snippet is now complete for the "
            "requested circuit-construction task."
        ),
    },
}


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    rows = list(iter_jsonl(RESULT_FILE))
    applied: list[dict[str, Any]] = []
    closeout_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for row in rows:
        instruction_key = str(row.get("instruction_key") or "")
        override = OVERRIDES.get(instruction_key)
        if not override:
            continue

        result = row.setdefault("remediation_result", {})
        result.update(
            {
                "remediation_decision": override["remediation_decision"],
                "remediated_input": result.get("remediated_input") or row.get("input"),
                "remediated_output": override["remediated_output"],
                "changes_summary": override["changes_summary"],
                "residual_risk_note": override["residual_risk_note"],
                "manual_closeout_version": MANUAL_CLOSEOUT_VERSION,
                "manual_closeout_applied_at": closeout_timestamp,
            }
        )
        applied.append(
            {
                "instruction_key": instruction_key,
                "review_group_key": row.get("review_group_key"),
                "remediation_candidate_type": (row.get("remediation_context") or {}).get(
                    "remediation_candidate_type"
                ),
                "remediation_decision": override["remediation_decision"],
                "changes_summary": override["changes_summary"],
                "residual_risk_note": override["residual_risk_note"],
            }
        )

    missing = sorted(set(OVERRIDES) - {entry["instruction_key"] for entry in applied})
    if missing:
        raise SystemExit(f"ERROR: override keys not found in result file: {missing}")

    write_jsonl(rows, RESULT_FILE)
    write_csv(rows, REVIEW_SHEET)

    decision_counts = Counter(
        (row.get("remediation_result") or {}).get("remediation_decision") or "<missing>"
        for row in rows
    )
    candidate_type_counts = Counter(
        (row.get("remediation_context") or {}).get("remediation_candidate_type") or "<missing>"
        for row in rows
    )

    summary = load_summary(SUMMARY_FILE)
    summary.update(
        {
            "result_file": format_display_path(RESULT_FILE),
            "review_sheet": format_display_path(REVIEW_SHEET),
            "summary_file": format_display_path(SUMMARY_FILE),
            "candidate_rows": summary.get("candidate_rows", len(rows)),
            "result_rows": len(rows),
            "decision_counts": dict(sorted(decision_counts.items())),
            "candidate_type_counts": dict(sorted(candidate_type_counts.items())),
            "missing_output_count": 0,
            "missing_output_custom_ids_sample": [],
            "manual_closeout_version": MANUAL_CLOSEOUT_VERSION,
            "manual_closeout_rows": len(applied),
            "manual_closeout_file": format_display_path(CLOSEOUT_FILE),
            "closeout_status": "complete",
        }
    )
    SUMMARY_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    closeout = {
        "manual_closeout_version": MANUAL_CLOSEOUT_VERSION,
        "manual_closeout_applied_at": closeout_timestamp,
        "result_file": format_display_path(RESULT_FILE),
        "review_sheet": format_display_path(REVIEW_SHEET),
        "summary_file": format_display_path(SUMMARY_FILE),
        "applied_overrides": applied,
        "final_decision_counts": dict(sorted(decision_counts.items())),
    }
    CLOSEOUT_FILE.write_text(json.dumps(closeout, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Acceptance-gate remediation manual closeout complete")
    print(f"  overrides applied: {len(applied):,}")
    print(f"  results: {len(rows):,}")
    print(f"  decision counts: {dict(sorted(decision_counts.items()))}")
    print(f"  summary file: {format_display_path(SUMMARY_FILE)}")
    print(f"  closeout file: {format_display_path(CLOSEOUT_FILE)}")


if __name__ == "__main__":
    main()
