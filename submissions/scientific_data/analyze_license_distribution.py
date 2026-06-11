"""Build license-distribution tables for the Scientific Data draft.

This script reads the canonical construction splits and release-view summaries
and writes compact JSON/CSV/Markdown artifacts for manuscript tables.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = ROOT / "PQID" / "data" / "processed"
RELEASE_DIR = PROCESSED_DIR / "release_views"
OUT_DIR = Path(__file__).resolve().parent

CANONICAL_SPLITS = {
    "train": PROCESSED_DIR / "train_clean.jsonl",
    "validation": PROCESSED_DIR / "validation_clean.jsonl",
    "test": PROCESSED_DIR / "test_clean.jsonl",
}

RELEASE_PROFILES = {
    "license_valid": "pqid_v1_license_valid",
    "public_open": "pqid_v1_public_open",
}


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def metadata(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("metadata") or {}


def repo_key(meta: dict[str, Any]) -> str:
    owner = (meta.get("repo_owner") or "").strip()
    name = (meta.get("repo_name") or "").strip()
    if owner and name:
        return f"{owner}/{name}"
    if name:
        return name
    original_url = (meta.get("original_url") or "").strip()
    if original_url:
        return original_url
    return "<missing_repo>"


def normalized_license(meta: dict[str, Any]) -> str:
    return (meta.get("repo_license") or "<missing>").strip() or "<missing>"


def normalized_category(meta: dict[str, Any]) -> str:
    return (meta.get("license_category") or "<missing>").strip() or "<missing>"


def normalized_bucket(meta: dict[str, Any]) -> str:
    return (meta.get("public_release_bucket") or "<missing>").strip() or "<missing>"


def collect_canonical() -> dict[str, Any]:
    rows_by_split: dict[str, int] = {}
    category_counts: Counter[str] = Counter()
    category_by_split: dict[str, Counter[str]] = defaultdict(Counter)
    license_counts: Counter[str] = Counter()
    license_category_counts: Counter[tuple[str, str]] = Counter()
    bucket_counts: Counter[str] = Counter()
    repo_counts_by_category: dict[str, Counter[str]] = defaultdict(Counter)
    repos_by_category: dict[str, set[str]] = defaultdict(set)
    repos_by_category_license: dict[tuple[str, str], set[str]] = defaultdict(set)
    source_hashes_by_category: dict[str, set[str]] = defaultdict(set)

    for split, path in CANONICAL_SPLITS.items():
        rows = 0
        for row in iter_jsonl(path):
            rows += 1
            meta = metadata(row)
            category = normalized_category(meta)
            license_id = normalized_license(meta)
            bucket = normalized_bucket(meta)
            repo = repo_key(meta)
            source_hash = (
                meta.get("lineage_parent_id")
                or meta.get("circuit_hash")
                or meta.get("content_hash")
                or row.get("instruction_key")
                or ""
            )

            category_counts[category] += 1
            category_by_split[split][category] += 1
            license_counts[license_id] += 1
            license_category_counts[(category, license_id)] += 1
            bucket_counts[bucket] += 1
            repo_counts_by_category[category][repo] += 1
            repos_by_category[category].add(repo)
            repos_by_category_license[(category, license_id)].add(repo)
            if source_hash:
                source_hashes_by_category[category].add(str(source_hash))
        rows_by_split[split] = rows

    total_rows = sum(rows_by_split.values())
    category_rows = [
        {
            "license_category": category,
            "rows": count,
            "row_percent": round(count / total_rows * 100, 4),
            "unique_repositories": len(repos_by_category[category]),
            "unique_source_keys": len(source_hashes_by_category[category]),
            "split_counts": dict(sorted(category_by_split_by_name(category_by_split, category).items())),
        }
        for category, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    license_rows = []
    for (category, license_id), count in sorted(
        license_category_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1])
    ):
        license_rows.append(
            {
                "license_category": category,
                "repo_license": license_id,
                "rows": count,
                "row_percent": round(count / total_rows * 100, 4),
                "unique_repositories": len(repos_by_category_license[(category, license_id)]),
            }
        )

    top_repos = {}
    for category, counter in repo_counts_by_category.items():
        top_repos[category] = [
            {"repository": repo, "rows": rows}
            for repo, rows in counter.most_common(15)
        ]

    return {
        "total_rows": total_rows,
        "rows_by_split": rows_by_split,
        "license_category_distribution": category_rows,
        "repo_license_distribution": license_rows,
        "public_release_bucket_counts": dict(sorted(bucket_counts.items())),
        "top_repositories_by_license_category": top_repos,
    }


def category_by_split_by_name(category_by_split: dict[str, Counter[str]], category: str) -> dict[str, int]:
    return {split: counter.get(category, 0) for split, counter in category_by_split.items()}


def load_release_summaries() -> dict[str, Any]:
    summaries = {}
    for profile, stem in RELEASE_PROFILES.items():
        path = RELEASE_DIR / f"{stem}_summary.json"
        summaries[profile] = json.loads(path.read_text(encoding="utf-8"))
    missing_path = RELEASE_DIR / "pqid_v1_missing_license_internal_only_summary.json"
    summaries["missing_license_internal_only"] = json.loads(missing_path.read_text(encoding="utf-8"))
    return summaries


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(summary: dict[str, Any]) -> str:
    canonical = summary["canonical_construction_splits"]
    release = summary["release_views"]
    lines = [
        "# PQID License Distribution Summary",
        "",
        f"- canonical construction rows: `{canonical['total_rows']:,}`",
        f"- license-valid rows: `{release['license_valid']['total_exported_rows']:,}`",
        f"- public-open permissive rows: `{release['public_open']['total_exported_rows']:,}`",
        f"- internal-only missing-license rows: `{release['missing_license_internal_only']['rows']:,}`",
        "",
        "## License Categories In Canonical Construction Splits",
        "",
        "| category | rows | percent | unique repositories | unique source keys |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in canonical["license_category_distribution"]:
        lines.append(
            "| {license_category} | {rows:,} | {row_percent:.4f}% | {unique_repositories:,} | {unique_source_keys:,} |".format(
                **item
            )
        )
    lines.extend(
        [
            "",
            "## Repository License Distribution",
            "",
            "| category | repo_license | rows | percent | unique repositories |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for item in canonical["repo_license_distribution"]:
        lines.append(
            "| {license_category} | `{repo_license}` | {rows:,} | {row_percent:.4f}% | {unique_repositories:,} |".format(
                **item
            )
        )
    lines.extend(
        [
            "",
            "## Release-View Exported Categories",
            "",
            "| release view | categories | excluded categories |",
            "| --- | --- | --- |",
        ]
    )
    for profile in ["license_valid", "public_open"]:
        profile_summary = release[profile]
        exported = ", ".join(
            f"{key}: {value:,}"
            for key, value in sorted(profile_summary["exported_license_category_counts"].items())
        )
        excluded = ", ".join(
            f"{key}: {value:,}"
            for key, value in sorted(profile_summary["excluded_license_category_counts"].items())
        )
        lines.append(f"| `{profile}` | {exported} | {excluded} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    summary = {
        "summary_version": "pqid_scientific_data_license_distribution_v1",
        "canonical_construction_splits": collect_canonical(),
        "release_views": load_release_summaries(),
    }

    summary_path = OUT_DIR / "LICENSE_DISTRIBUTION_SUMMARY.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    canonical = summary["canonical_construction_splits"]
    write_csv(OUT_DIR / "LICENSE_CATEGORY_DISTRIBUTION.csv", canonical["license_category_distribution"])
    write_csv(OUT_DIR / "REPO_LICENSE_DISTRIBUTION.csv", canonical["repo_license_distribution"])
    markdown_path = OUT_DIR / "LICENSE_DISTRIBUTION_SUMMARY.md"
    markdown_path.write_text(build_markdown(summary), encoding="utf-8")

    print("wrote", summary_path)
    print("wrote", markdown_path)
    print("canonical rows", canonical["total_rows"])


if __name__ == "__main__":
    main()
