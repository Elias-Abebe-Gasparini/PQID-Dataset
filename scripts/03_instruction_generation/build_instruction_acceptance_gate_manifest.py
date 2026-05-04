"""
build_instruction_acceptance_gate_manifest.py
---------------------------------------------
Build a unified post-Stage-J instruction manifest for the critique / rewrite
and acceptance-gate stage.

The manifest is intentionally local and non-destructive:
- it reads the canonical seed and paraphrase artifacts
- it does not call the API
- it does not modify the Stage J artifacts
- it prepares a review-ready corpus with compact provenance for the later gate
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from quality_aware_seed_common import (
    QUALITY_AWARE_PARAPHRASE_PROMPT_TYPE,
    canonicalize_quality_aware_prompt_type,
)


MANIFEST_VERSION = "instruction_acceptance_gate_manifest_v1"
ACCEPTANCE_GATE_VERSION = "instruction_acceptance_gate_v1"
ACCEPTANCE_REVIEW_AXES = [
    "role_fidelity",
    "semantic_grounding",
    "confidence_discipline",
    "hallucination_risk",
    "teacher_text_answer_quality",
]

DEFAULT_SOURCE_CODE_SEED_FILE = PROCESSED_DIR / "seed_drafts_quality_aware_source_code_v1.jsonl"
DEFAULT_SOURCE_CODE_PARAPHRASE_FILE = (
    PROCESSED_DIR / "seed_paraphrases_quality_aware_source_code_v1.jsonl"
)
DEFAULT_TEACHER_TEXT_SEED_FILE = PROCESSED_DIR / "seed_drafts_quality_aware_teacher_text_v1.jsonl"
DEFAULT_TEACHER_TEXT_PARAPHRASE_FILE = (
    PROCESSED_DIR / "seed_paraphrases_quality_aware_teacher_text_v1.jsonl"
)
DEFAULT_MANIFEST_FILE = PROCESSED_DIR / "instruction_acceptance_gate_manifest_v1.jsonl"
DEFAULT_SUMMARY_FILE = PROCESSED_DIR / "instruction_acceptance_gate_manifest_v1_summary.json"


BRANCH_SPECS = [
    {
        "label": "source_code",
        "seed_file_arg": "source_code_seed_file",
        "paraphrase_file_arg": "source_code_paraphrase_file",
    },
    {
        "label": "teacher_text",
        "seed_file_arg": "teacher_text_seed_file",
        "paraphrase_file_arg": "teacher_text_paraphrase_file",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-code-seed-file", default=str(DEFAULT_SOURCE_CODE_SEED_FILE))
    parser.add_argument(
        "--source-code-paraphrase-file",
        default=str(DEFAULT_SOURCE_CODE_PARAPHRASE_FILE),
    )
    parser.add_argument("--teacher-text-seed-file", default=str(DEFAULT_TEACHER_TEXT_SEED_FILE))
    parser.add_argument(
        "--teacher-text-paraphrase-file",
        default=str(DEFAULT_TEACHER_TEXT_PARAPHRASE_FILE),
    )
    parser.add_argument("--manifest-file", default=str(DEFAULT_MANIFEST_FILE))
    parser.add_argument("--summary-file", default=str(DEFAULT_SUMMARY_FILE))
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def determine_instruction_kind(row: dict) -> str:
    meta = row.get("metadata", {})
    prompt_type = canonicalize_quality_aware_prompt_type(meta.get("prompt_type"))
    if prompt_type == QUALITY_AWARE_PARAPHRASE_PROMPT_TYPE:
        return "paraphrase"
    if meta.get("paraphrase_source_content_hash") or meta.get("paraphrase_variant_index") is not None:
        return "paraphrase"
    return "seed"


def compact_review_context(meta: dict[str, Any], *, source_artifact: str) -> dict[str, Any]:
    return {
        "source_artifact": source_artifact,
        "circuit_hash": meta.get("circuit_hash"),
        "content_hash": meta.get("content_hash"),
        "repo_owner": meta.get("repo_owner"),
        "repo_name": meta.get("repo_name"),
        "original_url": meta.get("original_url"),
        "file_path": meta.get("file_path"),
        "validation_status": meta.get("validation_status"),
        "circuit_family": meta.get("circuit_family"),
        "semantic_intent": meta.get("semantic_intent"),
        "mutation_suite_candidate": meta.get("mutation_suite_candidate"),
        "benchmark_suitability_tier": meta.get("benchmark_suitability_tier"),
        "benchmark_suitability_tier_v2": meta.get("benchmark_suitability_tier_v2"),
        "seed_role": meta.get("seed_role"),
        "seed_target_supervision_mode": meta.get("seed_target_supervision_mode"),
        "seed_learning_objective": meta.get("seed_learning_objective"),
        "expected_response_mode": meta.get("seed_expected_response_mode"),
        "prompt_type": canonicalize_quality_aware_prompt_type(meta.get("prompt_type")),
        "seed_template_version": meta.get("seed_template_version"),
        "seed_critique_template_version": meta.get("seed_critique_template_version"),
        "seed_generation_model": meta.get("seed_generation_model"),
        "seed_generation_temperature": meta.get("seed_generation_temperature"),
        "seed_rewrite_pass_applied": meta.get("seed_rewrite_pass_applied"),
        "paraphrase_source": meta.get("paraphrase_source"),
        "paraphrase_source_content_hash": meta.get("paraphrase_source_content_hash"),
        "paraphrase_source_prompt_type": meta.get("paraphrase_source_prompt_type"),
        "paraphrase_template_version": meta.get("paraphrase_template_version"),
        "paraphrase_variant_index": meta.get("paraphrase_variant_index"),
        "paraphrase_generation_model": meta.get("paraphrase_generation_model"),
        "paraphrase_generation_temperature": meta.get("paraphrase_generation_temperature"),
        "paraphrase_generation_max_output_tokens": meta.get(
            "paraphrase_generation_max_output_tokens"
        ),
        "paraphrase_generation_prompt_mode": meta.get("paraphrase_generation_prompt_mode"),
    }


def build_instruction_key(
    *,
    branch: str,
    instruction_kind: str,
    row: dict,
) -> str:
    meta = row.get("metadata", {})
    basis = {
        "branch": branch,
        "instruction_kind": instruction_kind,
        "circuit_hash": meta.get("circuit_hash"),
        "content_hash": meta.get("content_hash"),
        "paraphrase_source_content_hash": meta.get("paraphrase_source_content_hash"),
        "paraphrase_variant_index": meta.get("paraphrase_variant_index"),
        "input": row.get("input", ""),
        "output": row.get("output", ""),
    }
    encoded = json.dumps(basis, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()


def build_review_group_key(branch: str, row: dict) -> str:
    meta = row.get("metadata", {})
    source_content_hash = (
        meta.get("paraphrase_source_content_hash")
        or meta.get("content_hash")
        or meta.get("circuit_hash")
        or ""
    )
    return f"{branch}:{source_content_hash}"


def build_manifest_entry(*, branch: str, row: dict, source_artifact: str) -> dict:
    instruction_kind = determine_instruction_kind(row)
    meta = row.get("metadata", {})
    return {
        "manifest_version": MANIFEST_VERSION,
        "acceptance_gate_version": ACCEPTANCE_GATE_VERSION,
        "acceptance_review_status": "pending",
        "acceptance_review_stage": "post_stage_j_canonical",
        "review_axes": ACCEPTANCE_REVIEW_AXES,
        "source_branch": branch,
        "instruction_kind": instruction_kind,
        "instruction_key": build_instruction_key(
            branch=branch,
            instruction_kind=instruction_kind,
            row=row,
        ),
        "review_group_key": build_review_group_key(branch, row),
        "input": row.get("input", ""),
        "output": row.get("output", ""),
        "review_context": compact_review_context(meta, source_artifact=source_artifact),
    }


def nested_counter_to_dict(counter_map: dict[str, Counter]) -> dict[str, dict[str, int]]:
    return {
        outer_key: dict(sorted(inner_counter.items()))
        for outer_key, inner_counter in sorted(counter_map.items())
    }


def main() -> None:
    args = parse_args()
    manifest_file = Path(args.manifest_file)
    summary_file = Path(args.summary_file)

    branch_inputs = {
        "source_code": {
            "seed_file": Path(args.source_code_seed_file),
            "paraphrase_file": Path(args.source_code_paraphrase_file),
        },
        "teacher_text": {
            "seed_file": Path(args.teacher_text_seed_file),
            "paraphrase_file": Path(args.teacher_text_paraphrase_file),
        },
    }

    manifest_rows: list[dict] = []
    branch_counts = Counter()
    instruction_kind_counts = Counter()
    role_counts = Counter()
    supervision_mode_counts = Counter()
    prompt_type_counts = Counter()
    prompt_mode_counts = Counter()
    branch_kind_counts: dict[str, Counter] = defaultdict(Counter)

    for branch_spec in BRANCH_SPECS:
        branch = branch_spec["label"]
        input_files = branch_inputs[branch]
        for instruction_kind, file_key in (("seed", "seed_file"), ("paraphrase", "paraphrase_file")):
            path = input_files[file_key]
            rows = load_jsonl(path)
            source_artifact = format_display_path(path)
            for row in rows:
                entry = build_manifest_entry(
                    branch=branch,
                    row=row,
                    source_artifact=source_artifact,
                )
                manifest_rows.append(entry)

                meta = entry["review_context"]
                branch_counts[branch] += 1
                instruction_kind_counts[instruction_kind] += 1
                branch_kind_counts[branch][instruction_kind] += 1
                role_counts[meta.get("seed_role") or "<missing>"] += 1
                supervision_mode_counts[meta.get("seed_target_supervision_mode") or "<missing>"] += 1
                prompt_type_counts[meta.get("prompt_type") or "<missing>"] += 1
                prompt_mode_counts[meta.get("paraphrase_generation_prompt_mode") or "<none>"] += 1

    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(manifest_rows, manifest_file)

    summary = {
        "manifest_version": MANIFEST_VERSION,
        "acceptance_gate_version": ACCEPTANCE_GATE_VERSION,
        "manifest_file": format_display_path(manifest_file),
        "total_rows": len(manifest_rows),
        "branch_counts": dict(sorted(branch_counts.items())),
        "instruction_kind_counts": dict(sorted(instruction_kind_counts.items())),
        "branch_instruction_kind_counts": nested_counter_to_dict(branch_kind_counts),
        "role_counts": dict(sorted(role_counts.items())),
        "supervision_mode_counts": dict(sorted(supervision_mode_counts.items())),
        "prompt_type_counts": dict(sorted(prompt_type_counts.items())),
        "prompt_mode_counts": dict(sorted(prompt_mode_counts.items())),
    }
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("acceptance-gate manifest:", format_display_path(manifest_file))
    print("summary file:", format_display_path(summary_file))
    print("total rows:", f"{len(manifest_rows):,}")

    print("branch counts")
    for key, value in branch_counts.most_common():
        print(f"  {key}: {value:,}")

    print("instruction kinds")
    for key, value in instruction_kind_counts.most_common():
        print(f"  {key}: {value:,}")

    print("role distribution")
    for key, value in role_counts.most_common():
        print(f"  {key}: {value:,}")

    print("supervision modes")
    for key, value in supervision_mode_counts.most_common():
        print(f"  {key}: {value:,}")

    print("prompt types")
    for key, value in prompt_type_counts.most_common():
        print(f"  {key}: {value:,}")

    print("paraphrase prompt modes")
    for key, value in prompt_mode_counts.most_common():
        print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()
