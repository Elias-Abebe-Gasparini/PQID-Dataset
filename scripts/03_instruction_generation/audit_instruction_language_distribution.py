"""
audit_instruction_language_distribution.py
------------------------------------------
Build a sidecar language-audit layer for the unified instruction acceptance
manifest.

This pass is intentionally non-destructive:
- it does not rewrite the canonical seed/paraphrase artifacts
- it does not modify the acceptance-gate manifest in place
- it creates a joinable metadata sidecar keyed by `instruction_key`

The audit is heuristic and is meant for corpus transparency rather than for
strong legal or linguistic claims.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PARENT_SCRIPTS_DIR = SCRIPTS_DIR.parents[0]
if str(PARENT_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_SCRIPTS_DIR))

from instruction_language_audit_common import (
    LANGUAGE_AUDIT_VERSION,
    audit_input_output_languages,
)
from project_paths import PROCESSED_DIR, format_display_path


DEFAULT_MANIFEST_FILE = PROCESSED_DIR / "instruction_acceptance_gate_manifest_v1.jsonl"
DEFAULT_AUDIT_FILE = PROCESSED_DIR / "instruction_language_audit_v1.jsonl"
DEFAULT_SUMMARY_FILE = PROCESSED_DIR / "instruction_language_audit_v1_summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-file", default=str(DEFAULT_MANIFEST_FILE))
    parser.add_argument("--audit-file", default=str(DEFAULT_AUDIT_FILE))
    parser.add_argument("--summary-file", default=str(DEFAULT_SUMMARY_FILE))
    parser.add_argument("--max-rows", type=int, default=None)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    manifest_file = Path(args.manifest_file)
    audit_file = Path(args.audit_file)
    summary_file = Path(args.summary_file)

    manifest_rows = load_jsonl(manifest_file)
    if args.max_rows is not None:
        manifest_rows = manifest_rows[: args.max_rows]

    audit_rows: list[dict] = []
    branch_counts = Counter()
    kind_counts = Counter()
    input_lang_counts = Counter()
    input_lang_resolved_counts = Counter()
    input_script_bucket_counts = Counter()
    output_lang_counts = Counter()
    output_lang_resolved_counts = Counter()
    output_script_bucket_counts = Counter()
    output_scope_counts = Counter()
    branch_input_lang_counts: dict[str, Counter] = defaultdict(Counter)
    branch_input_lang_resolved_counts: dict[str, Counter] = defaultdict(Counter)
    branch_output_lang_counts: dict[str, Counter] = defaultdict(Counter)
    branch_output_lang_resolved_counts: dict[str, Counter] = defaultdict(Counter)
    branch_kind_counts: dict[str, Counter] = defaultdict(Counter)
    non_english_examples: list[dict[str, str]] = []

    for row in manifest_rows:
        branch = str(row.get("source_branch") or "<missing>")
        instruction_kind = str(row.get("instruction_kind") or "<missing>")
        language_fields = audit_input_output_languages(
            input_text=str(row.get("input") or ""),
            output_text=str(row.get("output") or ""),
            source_branch=branch,
        )
        audit_row = {
            "instruction_key": row.get("instruction_key"),
            "source_branch": branch,
            "instruction_kind": instruction_kind,
            "seed_role": ((row.get("review_context") or {}).get("seed_role")),
            **language_fields,
        }
        audit_rows.append(audit_row)

        branch_counts[branch] += 1
        kind_counts[instruction_kind] += 1
        input_lang = str(language_fields["input_human_language"])
        input_lang_resolved = str(language_fields["input_human_language_resolved"])
        input_script_bucket = str(language_fields["input_human_script_bucket"])
        output_lang = str(language_fields["output_human_language"])
        output_lang_resolved = str(language_fields["output_human_language_resolved"])
        output_script_bucket = str(language_fields["output_human_script_bucket"])
        output_scope = str(language_fields["output_human_language_scope"])
        input_lang_counts[input_lang] += 1
        input_lang_resolved_counts[input_lang_resolved] += 1
        input_script_bucket_counts[input_script_bucket] += 1
        output_lang_counts[output_lang] += 1
        output_lang_resolved_counts[output_lang_resolved] += 1
        output_script_bucket_counts[output_script_bucket] += 1
        output_scope_counts[output_scope] += 1
        branch_input_lang_counts[branch][input_lang] += 1
        branch_input_lang_resolved_counts[branch][input_lang_resolved] += 1
        branch_output_lang_counts[branch][output_lang] += 1
        branch_output_lang_resolved_counts[branch][output_lang_resolved] += 1
        branch_kind_counts[branch][instruction_kind] += 1

        if (
            len(non_english_examples) < 25
            and (
                input_lang_resolved not in {"en", "none"}
                or output_lang_resolved not in {"en", "none"}
            )
        ):
            non_english_examples.append(
                {
                    "instruction_key": str(row.get("instruction_key") or ""),
                    "source_branch": branch,
                    "instruction_kind": instruction_kind,
                    "input_human_language": input_lang,
                    "input_human_language_resolved": input_lang_resolved,
                    "input_human_script_bucket": input_script_bucket,
                    "output_human_language": output_lang,
                    "output_human_language_resolved": output_lang_resolved,
                    "output_human_script_bucket": output_script_bucket,
                    "output_human_language_scope": output_scope,
                    "input_preview": str(row.get("input") or "")[:180],
                    "output_preview": str(row.get("output") or "")[:180],
                }
            )

    audit_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(audit_rows, audit_file)

    summary = {
        "language_audit_version": LANGUAGE_AUDIT_VERSION,
        "manifest_file": format_display_path(manifest_file),
        "audit_file": format_display_path(audit_file),
        "rows": len(audit_rows),
        "branch_counts": dict(sorted(branch_counts.items())),
        "instruction_kind_counts": dict(sorted(kind_counts.items())),
        "input_human_language_counts": dict(sorted(input_lang_counts.items())),
        "input_human_language_resolved_counts": dict(sorted(input_lang_resolved_counts.items())),
        "input_human_script_bucket_counts": dict(sorted(input_script_bucket_counts.items())),
        "output_human_language_counts": dict(sorted(output_lang_counts.items())),
        "output_human_language_resolved_counts": dict(sorted(output_lang_resolved_counts.items())),
        "output_human_script_bucket_counts": dict(sorted(output_script_bucket_counts.items())),
        "output_human_language_scope_counts": dict(sorted(output_scope_counts.items())),
        "branch_input_human_language_counts": {
            key: dict(sorted(value.items()))
            for key, value in sorted(branch_input_lang_counts.items())
        },
        "branch_input_human_language_resolved_counts": {
            key: dict(sorted(value.items()))
            for key, value in sorted(branch_input_lang_resolved_counts.items())
        },
        "branch_output_human_language_counts": {
            key: dict(sorted(value.items()))
            for key, value in sorted(branch_output_lang_counts.items())
        },
        "branch_output_human_language_resolved_counts": {
            key: dict(sorted(value.items()))
            for key, value in sorted(branch_output_lang_resolved_counts.items())
        },
        "branch_instruction_kind_counts": {
            key: dict(sorted(value.items()))
            for key, value in sorted(branch_kind_counts.items())
        },
        "non_english_examples": non_english_examples,
        "audit_note": (
            "This is a heuristic language audit. It should be read as an "
            "English-dominant corpus analysis, not as a claim of perfect "
            "language identification."
        ),
    }
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Instruction language audit completed")
    print("  manifest file:", format_display_path(manifest_file))
    print("  audit file:", format_display_path(audit_file))
    print("  summary file:", format_display_path(summary_file))
    print("  rows:", f"{len(audit_rows):,}")
    print("  input human languages:")
    for key, value in sorted(input_lang_counts.items()):
        print(f"    {key}: {value:,}")
    print("  input human languages (resolved):")
    for key, value in sorted(input_lang_resolved_counts.items()):
        print(f"    {key}: {value:,}")
    print("  input human script buckets:")
    for key, value in sorted(input_script_bucket_counts.items()):
        print(f"    {key}: {value:,}")
    print("  output human languages:")
    for key, value in sorted(output_lang_counts.items()):
        print(f"    {key}: {value:,}")
    print("  output human languages (resolved):")
    for key, value in sorted(output_lang_resolved_counts.items()):
        print(f"    {key}: {value:,}")
    print("  output human script buckets:")
    for key, value in sorted(output_script_bucket_counts.items()):
        print(f"    {key}: {value:,}")
    print("  output human language scopes:")
    for key, value in sorted(output_scope_counts.items()):
        print(f"    {key}: {value:,}")
    print("  sampled non-English or mixed examples captured:", f"{len(non_english_examples):,}")


if __name__ == "__main__":
    main()
