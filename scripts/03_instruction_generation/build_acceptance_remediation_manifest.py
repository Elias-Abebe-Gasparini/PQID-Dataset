"""
build_acceptance_remediation_manifest.py
----------------------------------------
Build a bounded Stage K remediation set from the adjudicated acceptance-gate
pilot rewrite tail plus nearest lineage neighbors.

This script does not mutate the canonical acceptance-gate manifest. It writes a
sidecar remediation candidate set that can be reviewed or sent through a later
rewrite/materialization pass.

Remediation v1 neighbor policy:
- core rows are the final human-adjudicated pilot rows with
  ``acceptance_decision == "rewrite"``
- nearest risk-neighbors are all full-manifest rows sharing one of those core
  rows' ``review_group_key`` values
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path


REMEDIATION_VERSION = "instruction_acceptance_gate_remediation_v1"

DEFAULT_MANIFEST_FILE = PROCESSED_DIR / "instruction_acceptance_gate_manifest_v1.jsonl"
DEFAULT_REVIEWED_FILE = PROCESSED_DIR / "instruction_acceptance_gate_pilot_reviewed_v1.jsonl"
DEFAULT_ADJUDICATION_SHEET = (
    PROCESSED_DIR / "instruction_acceptance_gate_pilot_disagreement_adjudication_v1.csv"
)
DEFAULT_CANDIDATE_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_remediation_candidates_v1.jsonl"
)
DEFAULT_REVIEW_SHEET = (
    PROCESSED_DIR / "instruction_acceptance_gate_remediation_review_sheet_v1.csv"
)
DEFAULT_SUMMARY_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_remediation_candidates_v1_summary.json"
)
DEFAULT_BATCH_REQUEST_FILE = (
    PROCESSED_DIR / "instruction_acceptance_gate_remediation_batch_requests_v1.jsonl"
)

DEFAULT_MODEL = "gpt-5.4"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_OUTPUT_TOKENS = 900

REMEDIATION_SYSTEM_PROMPT = """You are remediating PQID acceptance-gate rows.

Goal:
- Preserve the intended dataset role and source grounding.
- Fix only concrete role-fidelity or semantic-grounding problems.
- Do not invent unsupported APIs, missing evidence, or unrelated commentary.
- For source_code rows that ask for code, return runnable Qiskit code only unless the instruction explicitly asks for explanation.
- For repair_or_explanation rows, either provide a real minimal repair or clearly explain why the original row is not benchmark-ready.
- For lineage neighbors, inspect whether the same failure is present; if not, keep the original output.

Return valid JSON only with exactly these keys:
- "remediation_decision": one of "rewrite", "keep_original", "needs_manual_review"
- "remediated_input": the final input text, usually identical to the original input
- "remediated_output": the final output text
- "changes_summary": short explanation of what changed, or why no change was needed
- "residual_risk_note": short note, empty string if no known residual risk
"""


CSV_FIELDS = [
    "remediation_candidate_type",
    "remediation_priority",
    "remediation_reason_buckets",
    "source_core_instruction_keys",
    "instruction_key",
    "review_group_key",
    "source_branch",
    "instruction_kind",
    "seed_role",
    "expected_response_mode",
    "prompt_type",
    "paraphrase_variant_index",
    "paraphrase_prompt_mode",
    "repo_owner",
    "repo_name",
    "file_path",
    "validation_status",
    "original_acceptance_decision",
    "original_rewrite_required",
    "reviewer_notes",
    "rewrite_guidance",
    "input",
    "output",
    "remediation_decision",
    "remediated_input",
    "remediated_output",
    "remediator_notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-file", default=str(DEFAULT_MANIFEST_FILE))
    parser.add_argument("--reviewed-file", default=str(DEFAULT_REVIEWED_FILE))
    parser.add_argument("--adjudication-sheet", default=str(DEFAULT_ADJUDICATION_SHEET))
    parser.add_argument("--candidate-file", default=str(DEFAULT_CANDIDATE_FILE))
    parser.add_argument("--review-sheet", default=str(DEFAULT_REVIEW_SHEET))
    parser.add_argument("--summary-file", default=str(DEFAULT_SUMMARY_FILE))
    parser.add_argument("--batch-request-file", default=str(DEFAULT_BATCH_REQUEST_FILE))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument(
        "--skip-batch-requests",
        action="store_true",
        help="Do not write a local Batch API request file for the remediation candidates.",
    )
    return parser.parse_args()


def normalize(value: Any) -> str:
    return str(value or "").strip()


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_csv_by_key(path: Path, key_field: str) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            normalize(row.get(key_field)): row
            for row in reader
            if normalize(row.get(key_field))
        }


def load_reviewed_rows(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_key: dict[str, dict[str, Any]] = {}
    core_by_key: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(path):
        key = normalize(row.get("instruction_key"))
        if not key:
            continue
        by_key[key] = row
        if normalize(row.get("acceptance_decision")) == "rewrite":
            core_by_key[key] = row
    return by_key, core_by_key


def row_context(row: dict[str, Any]) -> dict[str, Any]:
    context = row.get("review_context") or {}
    if not isinstance(context, dict):
        return {}
    return context


def context_value(row: dict[str, Any], key: str) -> Any:
    value = row.get(key)
    if value not in (None, ""):
        return value
    return row_context(row).get(key)


def build_core_group_maps(
    core_by_key: dict[str, dict[str, Any]],
    adjudication_by_key: dict[str, dict[str, str]],
) -> tuple[dict[str, list[str]], dict[str, Counter]]:
    group_to_core_keys: dict[str, list[str]] = defaultdict(list)
    group_to_reasons: dict[str, Counter] = defaultdict(Counter)
    for key, row in core_by_key.items():
        group = normalize(row.get("review_group_key"))
        if not group:
            continue
        group_to_core_keys[group].append(key)
        adjudication = adjudication_by_key.get(key, {})
        reason = normalize(adjudication.get("adjudication_reason_bucket")) or "manual_rewrite"
        group_to_reasons[group][reason] += 1
    return group_to_core_keys, group_to_reasons


def candidate_priority(row: dict[str, Any], candidate_type: str) -> str:
    if candidate_type == "core_rewrite":
        return "p0_rewrite_required"
    if normalize(context_value(row, "source_branch")) == "source_code" and normalize(
        context_value(row, "seed_role")
    ) == "repair_or_explanation":
        return "p1_repair_lineage_neighbor"
    return "p2_lineage_neighbor"


def build_remediation_context(
    *,
    row: dict[str, Any],
    candidate_type: str,
    group_to_core_keys: dict[str, list[str]],
    group_to_reasons: dict[str, Counter],
    reviewed_by_key: dict[str, dict[str, Any]],
    adjudication_by_key: dict[str, dict[str, str]],
) -> dict[str, Any]:
    key = normalize(row.get("instruction_key"))
    group = normalize(row.get("review_group_key"))
    reviewed = reviewed_by_key.get(key, {})
    adjudication = adjudication_by_key.get(key, {})
    reasons = group_to_reasons.get(group, Counter())
    inherited_reason_buckets = sorted(reasons.elements())
    review_notes = normalize(reviewed.get("acceptance_reviewer_notes"))
    rewrite_guidance = normalize(reviewed.get("acceptance_rewrite_guidance"))
    if not review_notes:
        review_notes = normalize(row.get("acceptance_reviewer_notes"))
    if not rewrite_guidance:
        rewrite_guidance = normalize(row.get("acceptance_rewrite_guidance"))

    if candidate_type != "core_rewrite" and not rewrite_guidance:
        rewrite_guidance = (
            "Inspect this sibling of a rewrite-required row. Rewrite only if it shares "
            "the same role-fidelity or semantic-grounding failure; otherwise keep the original."
        )

    return {
        "remediation_version": REMEDIATION_VERSION,
        "remediation_status": "candidate",
        "remediation_candidate_type": candidate_type,
        "remediation_priority": candidate_priority(row, candidate_type),
        "remediation_neighbor_policy": "same_review_group_key_lineage_siblings",
        "source_core_instruction_keys": group_to_core_keys.get(group, []),
        "source_core_reason_buckets": inherited_reason_buckets,
        "original_acceptance_review_status": normalize(reviewed.get("acceptance_review_status")),
        "original_acceptance_decision": normalize(reviewed.get("acceptance_decision")),
        "original_acceptance_rewrite_required": normalize(
            reviewed.get("acceptance_rewrite_required")
        ),
        "adjudication_bucket": normalize(adjudication.get("adjudication_bucket")),
        "adjudication_reason_bucket": normalize(adjudication.get("adjudication_reason_bucket")),
        "reviewer_notes": review_notes,
        "rewrite_guidance": rewrite_guidance,
    }


def compact_csv_row(row: dict[str, Any]) -> dict[str, str]:
    remediation = row.get("remediation_context") or {}
    context = row_context(row)
    return {
        "remediation_candidate_type": normalize(remediation.get("remediation_candidate_type")),
        "remediation_priority": normalize(remediation.get("remediation_priority")),
        "remediation_reason_buckets": ";".join(remediation.get("source_core_reason_buckets") or []),
        "source_core_instruction_keys": ";".join(
            remediation.get("source_core_instruction_keys") or []
        ),
        "instruction_key": normalize(row.get("instruction_key")),
        "review_group_key": normalize(row.get("review_group_key")),
        "source_branch": normalize(row.get("source_branch") or context.get("source_branch")),
        "instruction_kind": normalize(row.get("instruction_kind")),
        "seed_role": normalize(context.get("seed_role")),
        "expected_response_mode": normalize(context.get("expected_response_mode")),
        "prompt_type": normalize(context.get("prompt_type")),
        "paraphrase_variant_index": normalize(context.get("paraphrase_variant_index")),
        "paraphrase_prompt_mode": normalize(context.get("paraphrase_generation_prompt_mode")),
        "repo_owner": normalize(context.get("repo_owner")),
        "repo_name": normalize(context.get("repo_name")),
        "file_path": normalize(context.get("file_path")),
        "validation_status": normalize(context.get("validation_status")),
        "original_acceptance_decision": normalize(
            remediation.get("original_acceptance_decision")
        ),
        "original_rewrite_required": normalize(
            remediation.get("original_acceptance_rewrite_required")
        ),
        "reviewer_notes": normalize(remediation.get("reviewer_notes")),
        "rewrite_guidance": normalize(remediation.get("rewrite_guidance")),
        "input": normalize(row.get("input")),
        "output": normalize(row.get("output")),
        "remediation_decision": "",
        "remediated_input": "",
        "remediated_output": "",
        "remediator_notes": "",
    }


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(compact_csv_row(row))


def build_batch_user_prompt(row: dict[str, Any]) -> str:
    remediation = row.get("remediation_context") or {}
    context = row_context(row)
    payload = {
        "remediation_candidate_type": remediation.get("remediation_candidate_type"),
        "remediation_priority": remediation.get("remediation_priority"),
        "source_core_reason_buckets": remediation.get("source_core_reason_buckets"),
        "reviewer_notes": remediation.get("reviewer_notes"),
        "rewrite_guidance": remediation.get("rewrite_guidance"),
        "source_branch": row.get("source_branch"),
        "instruction_kind": row.get("instruction_kind"),
        "seed_role": context.get("seed_role"),
        "expected_response_mode": context.get("expected_response_mode"),
        "prompt_type": context.get("prompt_type"),
        "validation_status": context.get("validation_status"),
        "repo_owner": context.get("repo_owner"),
        "repo_name": context.get("repo_name"),
        "file_path": context.get("file_path"),
        "input": row.get("input"),
        "output": row.get("output"),
    }
    return (
        "Remediate this PQID acceptance-gate candidate.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "For core_rewrite rows, produce a corrected output unless the row needs manual review.\n"
        "For lineage_neighbor rows, keep the original if it does not share the inherited failure.\n"
    )


def write_batch_requests(
    *,
    rows: list[dict[str, Any]],
    path: Path,
    model: str,
    temperature: float,
    max_output_tokens: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            request = {
                "custom_id": f"acceptance_remediation::{row['instruction_key']}",
                "method": "POST",
                "url": "/v1/responses",
                "body": {
                    "model": model,
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                    "input": [
                        {"role": "system", "content": REMEDIATION_SYSTEM_PROMPT},
                        {"role": "user", "content": build_batch_user_prompt(row)},
                    ],
                },
            }
            handle.write(json.dumps(request, ensure_ascii=False) + "\n")


def summarize(rows: list[dict[str, Any]], core_group_count: int) -> dict[str, Any]:
    candidate_type_counts = Counter()
    priority_counts = Counter()
    branch_counts = Counter()
    kind_counts = Counter()
    role_counts = Counter()
    reason_counts = Counter()
    group_sizes = Counter()
    repo_counts = Counter()
    for row in rows:
        remediation = row.get("remediation_context") or {}
        context = row_context(row)
        candidate_type_counts[normalize(remediation.get("remediation_candidate_type"))] += 1
        priority_counts[normalize(remediation.get("remediation_priority"))] += 1
        branch_counts[normalize(row.get("source_branch"))] += 1
        kind_counts[normalize(row.get("instruction_kind"))] += 1
        role_counts[normalize(context.get("seed_role"))] += 1
        repo = "/".join(
            part
            for part in [normalize(context.get("repo_owner")), normalize(context.get("repo_name"))]
            if part
        )
        repo_counts[repo or "<missing>"] += 1
        for reason in remediation.get("source_core_reason_buckets") or ["<none>"]:
            reason_counts[reason] += 1
        group_sizes[normalize(row.get("review_group_key"))] += 1

    sizes = list(group_sizes.values())
    return {
        "remediation_version": REMEDIATION_VERSION,
        "neighbor_policy": "same_review_group_key_lineage_siblings",
        "rows": len(rows),
        "core_rewrite_groups": core_group_count,
        "unique_review_group_keys": len(group_sizes),
        "candidate_type_counts": dict(sorted(candidate_type_counts.items())),
        "priority_counts": dict(sorted(priority_counts.items())),
        "branch_counts": dict(sorted(branch_counts.items())),
        "instruction_kind_counts": dict(sorted(kind_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "inherited_reason_bucket_counts": dict(sorted(reason_counts.items())),
        "group_size_min": min(sizes) if sizes else 0,
        "group_size_max": max(sizes) if sizes else 0,
        "group_size_mean": round(sum(sizes) / len(sizes), 4) if sizes else 0,
        "top_repo_counts": dict(repo_counts.most_common(20)),
    }


def main() -> None:
    args = parse_args()
    manifest_file = Path(args.manifest_file)
    reviewed_file = Path(args.reviewed_file)
    adjudication_sheet = Path(args.adjudication_sheet)
    candidate_file = Path(args.candidate_file)
    review_sheet = Path(args.review_sheet)
    summary_file = Path(args.summary_file)
    batch_request_file = Path(args.batch_request_file)

    reviewed_by_key, core_by_key = load_reviewed_rows(reviewed_file)
    adjudication_by_key = load_csv_by_key(adjudication_sheet, "instruction_key")
    group_to_core_keys, group_to_reasons = build_core_group_maps(core_by_key, adjudication_by_key)
    target_groups = set(group_to_core_keys)

    rows: list[dict[str, Any]] = []
    found_keys: set[str] = set()
    for row in iter_jsonl(manifest_file):
        group = normalize(row.get("review_group_key"))
        if group not in target_groups:
            continue
        key = normalize(row.get("instruction_key"))
        candidate_type = "core_rewrite" if key in core_by_key else "lineage_neighbor"
        row["remediation_context"] = build_remediation_context(
            row=row,
            candidate_type=candidate_type,
            group_to_core_keys=group_to_core_keys,
            group_to_reasons=group_to_reasons,
            reviewed_by_key=reviewed_by_key,
            adjudication_by_key=adjudication_by_key,
        )
        rows.append(row)
        found_keys.add(key)

    missing_core_keys = sorted(set(core_by_key) - found_keys)
    for key in missing_core_keys:
        row = dict(core_by_key[key])
        row["remediation_context"] = build_remediation_context(
            row=row,
            candidate_type="core_rewrite",
            group_to_core_keys=group_to_core_keys,
            group_to_reasons=group_to_reasons,
            reviewed_by_key=reviewed_by_key,
            adjudication_by_key=adjudication_by_key,
        )
        rows.append(row)

    rows.sort(
        key=lambda r: (
            normalize(r.get("review_group_key")),
            0
            if normalize((r.get("remediation_context") or {}).get("remediation_candidate_type"))
            == "core_rewrite"
            else 1,
            normalize(r.get("instruction_kind")),
            normalize(r.get("instruction_key")),
        )
    )

    write_jsonl(rows, candidate_file)
    write_csv(rows, review_sheet)

    summary = summarize(rows, core_group_count=len(target_groups))
    summary.update(
        {
            "source_manifest_file": format_display_path(manifest_file),
            "source_reviewed_file": format_display_path(reviewed_file),
            "source_adjudication_sheet": format_display_path(adjudication_sheet),
            "candidate_file": format_display_path(candidate_file),
            "review_sheet": format_display_path(review_sheet),
            "summary_file": format_display_path(summary_file),
            "missing_core_keys_recovered_from_reviewed_file": missing_core_keys,
        }
    )

    if not args.skip_batch_requests:
        write_batch_requests(
            rows=rows,
            path=batch_request_file,
            model=args.model,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
        )
        summary.update(
            {
                "batch_request_file": format_display_path(batch_request_file),
                "batch_request_model": args.model,
                "batch_request_temperature": args.temperature,
                "batch_request_max_output_tokens": args.max_output_tokens,
            }
        )

    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Acceptance-gate remediation candidates built")
    print(f"  candidates: {len(rows):,}")
    print(f"  core rewrite rows: {summary['candidate_type_counts'].get('core_rewrite', 0):,}")
    print(f"  lineage neighbors: {summary['candidate_type_counts'].get('lineage_neighbor', 0):,}")
    print(f"  review groups: {len(target_groups):,}")
    print(f"  candidate file: {format_display_path(candidate_file)}")
    print(f"  review sheet: {format_display_path(review_sheet)}")
    print(f"  summary file: {format_display_path(summary_file)}")
    if not args.skip_batch_requests:
        print(f"  batch request file: {format_display_path(batch_request_file)}")


if __name__ == "__main__":
    main()
