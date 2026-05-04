"""
build_seed_role_manifest.py
---------------------------
Create a role-conditioned manifest for the quality-aware seed-generation
pipeline. The manifest does not generate any prompts itself; it freezes the
mapping from upstream record metadata to seed-generation role, learning
objective, and expected response mode.

This file is intended to be the first executable stage of the new seed stack.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, format_display_path

from quality_aware_seed_common import (
    MANIFEST_VERSION,
    build_manifest_entry,
    role_stats_key,
)


DEFAULT_INPUT_FILE = PROCESSED_DIR / "pqid_2026_enriched_github_circuits.jsonl"
DEFAULT_MASTER_OVERLAY_FILE = PROCESSED_DIR / "pqid_2026_master_corpus.jsonl"
DEFAULT_OUTPUT_FILE = PROCESSED_DIR / "seed_role_manifest_v1.jsonl"
DEFAULT_REPORT_FILE = PROCESSED_DIR / "seed_role_manifest_v1_report.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-file",
        default=str(DEFAULT_INPUT_FILE),
        help="Source corpus used to derive the seed-role manifest.",
    )
    parser.add_argument(
        "--output-file",
        default=str(DEFAULT_OUTPUT_FILE),
        help="Manifest JSONL to write.",
    )
    parser.add_argument(
        "--master-overlay-file",
        default=str(DEFAULT_MASTER_OVERLAY_FILE),
        help=(
            "Optional master-corpus JSONL used to overlay benchmark-readiness "
            "and semantic metadata onto the full enriched corpus during routing."
        ),
    )
    parser.add_argument(
        "--report-file",
        default=str(DEFAULT_REPORT_FILE),
        help="Markdown summary report to write.",
    )
    parser.add_argument(
        "--source-artifact-name",
        default=DEFAULT_INPUT_FILE.name,
        help="Artifact label stored in manifest entries for reproducibility.",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def write_jsonl(entries: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def build_master_overlay_index(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}

    overlay: dict[str, dict] = {}
    for row in load_jsonl(path):
        meta = row.get("metadata", {})
        circuit_hash = meta.get("circuit_hash")
        if circuit_hash:
            overlay[circuit_hash] = meta
    return overlay


def apply_master_overlay(record: dict, overlay_index: dict[str, dict]) -> dict:
    merged = json.loads(json.dumps(record))
    meta = merged.setdefault("metadata", {})
    circuit_hash = meta.get("circuit_hash")
    if not circuit_hash:
        return merged

    overlay_meta = overlay_index.get(circuit_hash)
    if not overlay_meta:
        return merged

    overlay_keys = [
        "benchmark_checks_passed",
        "benchmark_checks_total",
        "benchmark_checks_ratio",
        "benchmark_suitability_tier",
        "benchmark_failed_checks",
        "benchmark_passed_checks",
        "benchmark_profile_version",
        "benchmark_checks_passed_v2",
        "benchmark_checks_total_v2",
        "benchmark_checks_ratio_v2",
        "benchmark_suitability_tier_v2",
        "benchmark_failed_checks_v2",
        "benchmark_passed_checks_v2",
        "benchmark_profile_version_v2",
        "mutation_suite_candidate",
        "benchmark_cleaning_flags",
        "circuit_family",
        "semantic_intent",
        "license_category",
        "repo_license",
        "repo_topics",
        "is_org_repo",
        "retrieval_strategy",
        "code_lines",
        "gate_count",
        "n_qubits",
        "depth",
    ]

    for key in overlay_keys:
        if overlay_meta.get(key) is not None:
            meta[key] = overlay_meta[key]
    return merged


def build_report(
    *,
    input_file: Path,
    output_file: Path,
    entries: list[dict],
) -> str:
    role_counts = Counter(entry["seed_role"] for entry in entries)
    response_mode_counts = Counter(entry["expected_response_mode"] for entry in entries)
    target_mode_counts = Counter(entry["target_supervision_mode"] for entry in entries)
    role_tier_counts = Counter(role_stats_key(entry) for entry in entries)

    lines: list[str] = []
    lines.append("# Seed Role Manifest Report")
    lines.append("")
    lines.append(f"- manifest version: `{MANIFEST_VERSION}`")
    lines.append(f"- source corpus: `{format_display_path(input_file)}`")
    lines.append(f"- output manifest: `{format_display_path(output_file)}`")
    lines.append(f"- total entries: `{len(entries):,}`")
    lines.append("")
    lines.append("## Seed Role Counts")
    lines.append("")
    for role, count in role_counts.most_common():
        lines.append(f"- `{role}`: `{count:,}`")
    lines.append("")
    lines.append("## Expected Response Modes")
    lines.append("")
    for mode, count in response_mode_counts.most_common():
        lines.append(f"- `{mode}`: `{count:,}`")
    lines.append("")
    lines.append("## Target Supervision Modes")
    lines.append("")
    for mode, count in target_mode_counts.most_common():
        lines.append(f"- `{mode}`: `{count:,}`")
    lines.append("")
    lines.append("## Role by n/8 Tier")
    lines.append("")
    for (role, tier), count in role_tier_counts.most_common():
        lines.append(f"- `{role}` / `{tier}`: `{count:,}`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    input_file = Path(args.input_file)
    master_overlay_file = Path(args.master_overlay_file)
    output_file = Path(args.output_file)
    report_file = Path(args.report_file)

    records = load_jsonl(input_file)
    overlay_index = build_master_overlay_index(master_overlay_file)
    routed_records = [apply_master_overlay(record, overlay_index) for record in records]
    entries = [build_manifest_entry(record, args.source_artifact_name) for record in routed_records]

    write_jsonl(entries, output_file)
    report_file.write_text(
        build_report(input_file=input_file, output_file=output_file, entries=entries),
        encoding="utf-8",
    )

    print("seed-role manifest written to:", format_display_path(output_file))
    print("seed-role report written to:", format_display_path(report_file))
    print("master overlay file:", format_display_path(master_overlay_file))
    print("master overlay records indexed:", len(overlay_index))
    print("total manifest entries:", len(entries))


if __name__ == "__main__":
    main()
