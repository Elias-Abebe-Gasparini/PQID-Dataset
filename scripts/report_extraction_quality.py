"""
report_extraction_quality.py
----------------------------
Audits the extraction-quality diagnostics added during pre-seed raw enrichment.
This script is intentionally read-only with respect to the dataset itself: it
summarizes the current enriched raw pool and writes a small sample file for
manual inspection before seed generation.

Default input:
    PQID/data/processed/circuits_unified_enriched.jsonl

Default outputs:
    PQID/data/processed/extraction_quality_report.md
    PQID/data/processed/extraction_quality_samples.jsonl

Examples:
    python report_extraction_quality.py
    python report_extraction_quality.py --input-file ...\\circuits_unified_plus_aggressive_enriched.jsonl
    python report_extraction_quality.py --sample-per-group 15 --snippet-chars 600
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from project_paths import PROCESSED_DIR
from project_paths import format_display_path


BASE = PROCESSED_DIR


def default_input_file() -> Path:
    candidates = [
        BASE / "circuits_unified_plus_phase2_plus_phase3_enriched.jsonl",
        BASE / "circuits_unified_plus_aggressive_broad_enriched.jsonl",
        BASE / "circuits_unified_plus_aggressive_enriched.jsonl",
        BASE / "circuits_unified_enriched.jsonl",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]


def report_basename_for_input(input_path: Path) -> str:
    stem = input_path.stem
    if stem == "circuits_unified_enriched":
        return "extraction_quality_report"
    if stem == "circuits_unified_plus_aggressive_broad_enriched":
        return "extraction_quality_report_broad"
    if stem == "circuits_unified_plus_phase2_plus_phase3_enriched":
        return "extraction_quality_report_phase3"
    return stem + "_report"


def default_report_file(input_path: Path) -> Path:
    return BASE / f"{report_basename_for_input(input_path)}.md"


def default_samples_file(input_path: Path) -> Path:
    stem = input_path.stem
    if stem == "circuits_unified_enriched":
        return BASE / "extraction_quality_samples.jsonl"
    if stem == "circuits_unified_plus_aggressive_broad_enriched":
        return BASE / "extraction_quality_samples_broad.jsonl"
    if stem == "circuits_unified_plus_phase2_plus_phase3_enriched":
        return BASE / "extraction_quality_samples_phase3.jsonl"
    return input_path.with_name(stem + "_samples.jsonl")


def parse_args():
    default_input = default_input_file()
    parser = argparse.ArgumentParser(
        description="Generate a reproducible extraction-quality audit report."
    )
    parser.add_argument(
        "--input-file",
        default=str(default_input),
        help="Path to an enriched raw circuit JSONL file.",
    )
    parser.add_argument(
        "--report-file",
        default=None,
        help="Optional markdown report output path.",
    )
    parser.add_argument(
        "--samples-file",
        default=None,
        help="Optional JSONL file containing deterministic review samples.",
    )
    parser.add_argument(
        "--sample-per-group",
        type=int,
        default=10,
        help="How many examples to keep per review group.",
    )
    parser.add_argument(
        "--snippet-chars",
        type=int,
        default=500,
        help="How many code characters to include in sample snippets.",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def pct(n: int, d: int) -> str:
    if d <= 0:
        return "0.0%"
    return f"{(100.0 * n / d):.1f}%"


def entry_sort_key(entry: dict) -> tuple:
    meta = entry.get("metadata", {})
    return (
        meta.get("repo_owner") or "",
        meta.get("repo_name") or "",
        meta.get("file_path") or "",
        meta.get("start_line") or -1,
        meta.get("end_line") or -1,
        meta.get("circuit_hash") or "",
    )


def compact_entry(entry: dict, group: str, snippet_chars: int) -> dict:
    meta = entry.get("metadata", {})
    code = (entry.get("output") or "").replace("\r", "")
    snippet = code[:snippet_chars]
    if len(code) > snippet_chars:
        snippet += "\n..."
    return {
        "sample_group": group,
        "circuit_hash": meta.get("circuit_hash"),
        "validation_status": meta.get("validation_status"),
        "materialized_circuit": meta.get("materialized_circuit"),
        "gate_count": meta.get("gate_count"),
        "extraction_confidence": meta.get("extraction_confidence"),
        "contains_demo_scaffolding": meta.get("contains_demo_scaffolding"),
        "cleanup_candidate": meta.get("cleanup_candidate"),
        "cleanup_rules_triggered": meta.get("cleanup_rules_triggered"),
        "repo_owner": meta.get("repo_owner"),
        "repo_name": meta.get("repo_name"),
        "file_path": meta.get("file_path"),
        "github_anchor": meta.get("github_anchor"),
        "snippet": snippet,
    }


def sample_entries(entries: list[dict], predicate, limit: int) -> list[dict]:
    matches = [entry for entry in entries if predicate(entry)]
    matches.sort(key=entry_sort_key)
    return matches[:limit]


def repo_counter(entries: list[dict], predicate) -> Counter:
    counts = Counter()
    for entry in entries:
        if not predicate(entry):
            continue
        meta = entry.get("metadata", {})
        owner = meta.get("repo_owner") or "<missing-owner>"
        repo = meta.get("repo_name") or "<missing-repo>"
        counts[f"{owner}/{repo}"] += 1
    return counts


def write_samples(path: Path, sample_groups: dict[str, list[dict]], snippet_chars: int):
    with open(path, "w", encoding="utf-8") as f:
        for group, entries in sample_groups.items():
            for entry in entries:
                rec = compact_entry(entry, group, snippet_chars)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def build_report(
    entries: list[dict],
    sample_groups: dict[str, list[dict]],
    sample_per_group: int,
    samples_path: Path,
) -> str:
    total = len(entries)
    confidence_counts = Counter()
    status_counts = Counter()
    rule_counts = Counter()
    demo_true = 0
    cleanup_true = 0
    cleanup_validated = 0
    low_validated = 0
    materialized_true = 0
    validated_materialized = 0
    validated_zero_gate = 0
    validated_zero_gate_materialized = 0

    for entry in entries:
        meta = entry.get("metadata", {})
        confidence_counts[meta.get("extraction_confidence", "<missing>")] += 1
        status = meta.get("validation_status", "<missing>")
        status_counts[status] += 1
        if meta.get("materialized_circuit") is True:
            materialized_true += 1
            if status == "validated":
                validated_materialized += 1
        if meta.get("contains_demo_scaffolding"):
            demo_true += 1
        if meta.get("cleanup_candidate"):
            cleanup_true += 1
            if status == "validated":
                cleanup_validated += 1
        if meta.get("extraction_confidence") == "low" and status == "validated":
            low_validated += 1
        if status == "validated" and (meta.get("gate_count") or 0) == 0:
            validated_zero_gate += 1
            if meta.get("materialized_circuit") is True:
                validated_zero_gate_materialized += 1
        for rule in meta.get("cleanup_rules_triggered") or []:
            rule_counts[rule] += 1

    low_repo_counts = repo_counter(
        entries,
        lambda entry: entry.get("metadata", {}).get("extraction_confidence") == "low",
    )
    cleanup_repo_counts = repo_counter(
        entries,
        lambda entry: entry.get("metadata", {}).get("cleanup_candidate") is True,
    )
    zero_gate_validated_repo_counts = repo_counter(
        entries,
        lambda entry: entry.get("metadata", {}).get("validation_status") == "validated"
        and (entry.get("metadata", {}).get("gate_count") or 0) == 0,
    )

    lines = []
    lines.append("# Extraction Quality Audit Report")
    lines.append("")
    lines.append("This report is generated from the enriched raw circuit pool.")
    lines.append(
        "It is an inspection layer only: it does not rewrite or filter the raw dataset."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total entries: `{total:,}`")
    lines.append(
        f"- `materialized_circuit=True`: `{materialized_true:,}` ({pct(materialized_true, total)})"
    )
    lines.append(
        f"- `validated` and `materialized_circuit=True`: `{validated_materialized:,}`"
    )
    lines.append(
        f"- `validated` and `gate_count == 0`: `{validated_zero_gate:,}`"
    )
    lines.append(
        f"- `validated` and `gate_count == 0` and `materialized_circuit=True`: `{validated_zero_gate_materialized:,}`"
    )
    lines.append(
        f"- `contains_demo_scaffolding=True`: `{demo_true:,}` ({pct(demo_true, total)})"
    )
    lines.append(
        f"- `cleanup_candidate=True`: `{cleanup_true:,}` ({pct(cleanup_true, total)})"
    )
    lines.append(
        f"- `cleanup_candidate=True` and `validated`: `{cleanup_validated:,}`"
    )
    lines.append(
        f"- `extraction_confidence='low'` and `validated`: `{low_validated:,}`"
    )
    lines.append("")
    lines.append("## Extraction Confidence")
    lines.append("")
    for key in ("high", "medium", "low", "<missing>"):
        value = confidence_counts.get(key, 0)
        if value:
            lines.append(f"- `{key}`: `{value:,}` ({pct(value, total)})")
    lines.append("")
    lines.append("## Validation Status")
    lines.append("")
    for status, value in status_counts.most_common():
        lines.append(f"- `{status}`: `{value:,}` ({pct(value, total)})")
    lines.append("")
    lines.append("## Top Cleanup Rules Triggered")
    lines.append("")
    if rule_counts:
        for rule, value in rule_counts.most_common(10):
            lines.append(f"- `{rule}`: `{value:,}`")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Top Repositories By Low-Confidence Entries")
    lines.append("")
    for repo, value in low_repo_counts.most_common(10):
        lines.append(f"- `{repo}`: `{value:,}`")
    if not low_repo_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Top Repositories By Cleanup Candidates")
    lines.append("")
    for repo, value in cleanup_repo_counts.most_common(10):
        lines.append(f"- `{repo}`: `{value:,}`")
    if not cleanup_repo_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Top Repositories By `validated` + `gate_count == 0`")
    lines.append("")
    for repo, value in zero_gate_validated_repo_counts.most_common(10):
        lines.append(f"- `{repo}`: `{value:,}`")
    if not zero_gate_validated_repo_counts:
        lines.append("- None")
    lines.append("")
    lines.append("## Deterministic Review Samples")
    lines.append("")
    lines.append(
        f"- Samples written to `{samples_path.name}` with `{sample_per_group}` entries per group."
    )
    for group, group_entries in sample_groups.items():
        lines.append(f"- `{group}`: `{len(group_entries)}` sampled entries")
    lines.append("")
    lines.append("Sample groups included:")
    lines.append("- `low_confidence`")
    lines.append("- `cleanup_candidates`")
    lines.append("- `cleanup_candidates_validated`")
    lines.append("- `validated_zero_gate`")
    lines.append("")

    return "\n".join(lines) + "\n"


def main():
    args = parse_args()

    input_path = Path(args.input_file)
    report_path = Path(args.report_file) if args.report_file else default_report_file(input_path)
    samples_path = Path(args.samples_file) if args.samples_file else default_samples_file(input_path)

    if not input_path.exists():
        raise SystemExit(
            f"ERROR: input file not found: {format_display_path(input_path)}"
        )

    entries = load_jsonl(input_path)
    sample_groups = {
        "low_confidence": sample_entries(
            entries,
            lambda entry: entry.get("metadata", {}).get("extraction_confidence") == "low",
            args.sample_per_group,
        ),
        "cleanup_candidates": sample_entries(
            entries,
            lambda entry: entry.get("metadata", {}).get("cleanup_candidate") is True,
            args.sample_per_group,
        ),
        "cleanup_candidates_validated": sample_entries(
            entries,
            lambda entry: entry.get("metadata", {}).get("cleanup_candidate") is True
            and entry.get("metadata", {}).get("validation_status") == "validated",
            args.sample_per_group,
        ),
        "validated_zero_gate": sample_entries(
            entries,
            lambda entry: entry.get("metadata", {}).get("validation_status") == "validated"
            and (entry.get("metadata", {}).get("gate_count") or 0) == 0,
            args.sample_per_group,
        ),
    }

    report_text = build_report(
        entries=entries,
        sample_groups=sample_groups,
        sample_per_group=args.sample_per_group,
        samples_path=samples_path,
    )

    report_path.write_text(report_text, encoding="utf-8")
    write_samples(samples_path, sample_groups, args.snippet_chars)

    print(f"Input   : {format_display_path(input_path)}")
    print(f"Report  : {format_display_path(report_path)}")
    print(f"Samples : {format_display_path(samples_path)}")
    print(f"Entries : {len(entries):,}")
    print(f"Groups  : {', '.join(sample_groups.keys())}")


if __name__ == "__main__":
    main()
