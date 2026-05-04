"""
enrich_repo_topics.py
---------------------
Fetches GitHub repository topics and the owner account type for every unique
repository referenced in one or more JSONL dataset files and patches each
entry's metadata with:

    repo_topics  list[str] | None
    is_org_repo  bool | None

Resume-safe: results are cached in repo_topics_cache.jsonl.
On re-run only repositories not yet in the cache are queried.

Run:
    python enrich_repo_topics.py
    python enrich_repo_topics.py --input-files path1.jsonl path2.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import requests

from project_paths import PROCESSED_DIR, format_display_path, load_github_token

BASE = PROCESSED_DIR
CACHE_FILE = BASE / "repo_topics_cache.jsonl"
API_BASE = "https://api.github.com"
RETRY_AFTER = 60


def default_input_files() -> list[Path]:
    candidates = [
        BASE / "circuits_unified_plus_phase2_plus_phase3_core_extended_enriched.jsonl",
        BASE / "circuits_unified_plus_phase2_plus_phase3_core_enriched.jsonl",
        BASE / "circuits_unified_plus_phase2_plus_phase3_enriched.jsonl",
        BASE / "circuits_unified_plus_aggressive_core_enriched.jsonl",
        BASE / "train_clean.jsonl",
        BASE / "validation_clean.jsonl",
        BASE / "test_clean.jsonl",
    ]
    existing = []
    seen = set()
    for path in candidates:
        if path.exists() and path not in seen:
            existing.append(path)
            seen.add(path)
    return existing or [candidates[0]]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Patch GitHub repo topics and org/user ownership into one or more JSONL files."
    )
    parser.add_argument(
        "--input-files",
        nargs="+",
        default=[str(p) for p in default_input_files()],
        help="One or more JSONL files to patch in place.",
    )
    parser.add_argument(
        "--cache-file",
        default=str(CACHE_FILE),
        help="Path to the resume-safe repo topics cache JSONL.",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_jsonl(entries: list[dict], path: Path) -> None:
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def append_jsonl(record: dict, path: Path) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def extract_owner_repo(url: str) -> str | None:
    try:
        parts = url.replace("https://github.com/", "").split("/")
        if len(parts) >= 2 and parts[0] and parts[1]:
            return f"{parts[0]}/{parts[1]}"
    except Exception:
        pass
    return None


def collect_repos(files: list[Path]) -> dict[str, int]:
    repos: dict[str, int] = {}
    for path in files:
        for entry in load_jsonl(path):
            url = entry.get("metadata", {}).get("original_url", "")
            key = extract_owner_repo(url)
            if key:
                repos[key] = repos.get(key, 0) + 1
    return repos


def fetch_repo_topics(session: requests.Session, owner_repo: str) -> dict:
    url = f"{API_BASE}/repos/{owner_repo}"
    for attempt in range(5):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                topics = data.get("topics") or []
                owner = data.get("owner") or {}
                owner_type = (owner.get("type") or "").lower()
                return {
                    "owner_repo": owner_repo,
                    "repo_topics": topics,
                    "is_org_repo": owner_type == "organization",
                }
            if resp.status_code == 404:
                return {
                    "owner_repo": owner_repo,
                    "repo_topics": [],
                    "is_org_repo": None,
                }
            if resp.status_code in (403, 429):
                remaining = int(resp.headers.get("X-RateLimit-Remaining", 0))
                reset_ts = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait = max(reset_ts - int(time.time()), RETRY_AFTER)
                print(f"  Rate limited (remaining={remaining}) — waiting {wait}s", flush=True)
                time.sleep(wait)
            else:
                print(f"  HTTP {resp.status_code} for {owner_repo}", flush=True)
                time.sleep(2 ** attempt)
        except Exception as exc:
            print(f"  Error for {owner_repo}: {exc}", flush=True)
            time.sleep(2 ** attempt)

    return {
        "owner_repo": owner_repo,
        "repo_topics": [],
        "is_org_repo": None,
    }


def main():
    args = parse_args()
    input_files = [Path(p) for p in args.input_files]
    cache_file = Path(args.cache_file)

    token = load_github_token(__file__)

    session = requests.Session()
    session.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })

    print("Scanning dataset for unique repositories...", flush=True)
    for path in input_files:
        print(f"  - {format_display_path(path)}", flush=True)
    all_repos = collect_repos(input_files)
    print(f"  Unique repos found: {len(all_repos):,}", flush=True)

    cache_records = load_jsonl(cache_file)
    cache = {rec["owner_repo"]: rec for rec in cache_records}
    print(f"  Already cached    : {len(cache):,}", flush=True)

    pending = [repo for repo in all_repos if repo not in cache]
    print(f"  To fetch          : {len(pending):,}", flush=True)

    t0 = time.time()
    for i, owner_repo in enumerate(pending, 1):
        rec = fetch_repo_topics(session, owner_repo)
        cache[owner_repo] = rec
        append_jsonl(rec, cache_file)
        if i % 100 == 0 or i == len(pending):
            elapsed = time.time() - t0
            print(
                f"  {i}/{len(pending)} ({100*i/len(pending):.1f}%)  elapsed={elapsed:.0f}s",
                flush=True,
            )
        time.sleep(0.25)

    print("\nPatching JSONL files...", flush=True)
    total_patched = 0
    for path in input_files:
        entries = load_jsonl(path)
        if not entries:
            continue
        patched = 0
        for entry in entries:
            url = entry.get("metadata", {}).get("original_url", "")
            owner_repo = extract_owner_repo(url)
            if owner_repo and owner_repo in cache:
                rec = cache[owner_repo]
                entry["metadata"]["repo_topics"] = rec["repo_topics"]
                entry["metadata"]["is_org_repo"] = rec["is_org_repo"]
                patched += 1
        save_jsonl(entries, path)
        total_patched += patched
        print(
            f"  {format_display_path(path)}: patched {patched:,} / {len(entries):,}",
            flush=True,
        )

    topic_hist = {}
    org_count = 0
    for rec in cache.values():
        if rec.get("is_org_repo") is True:
            org_count += 1
        for topic in rec.get("repo_topics") or []:
            topic_hist[topic] = topic_hist.get(topic, 0) + 1

    print("\n=== REPO CONTEXT SUMMARY (by unique repo) ===")
    print(f"  org-owned repos : {org_count:,}")
    print(f"  user-owned repos: {len(cache) - org_count:,}")
    print("  top topics:")
    for topic, count in sorted(topic_hist.items(), key=lambda kv: (-kv[1], kv[0]))[:20]:
        print(f"    {topic:<30} {count:>6,}")
    print(f"\nTotal entries patched: {total_patched:,}", flush=True)


if __name__ == "__main__":
    main()
