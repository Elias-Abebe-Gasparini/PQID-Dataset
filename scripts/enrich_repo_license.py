"""
enrich_repo_license.py
----------------------
Fetches the SPDX license identifier for every unique GitHub repository
referenced in one or more JSONL dataset files and patches each entry's
metadata with two new fields:

    repo_license      str | None   SPDX identifier, e.g. "MIT", "Apache-2.0",
                                   "GPL-3.0", or None if GitHub reports no license
    license_category  str          "permissive" | "copyleft" | "no_license" | "other"

Classification:
    permissive  — MIT, Apache-2.0, BSD-*, ISC, Unlicense, CC0-1.0, EUPL-1.x,
                  MPL-2.0, LGPL-2.1, LGPL-3.0, Artistic-2.0, Zlib, PSF-2.0
    copyleft    — GPL-2.0, GPL-3.0, AGPL-3.0, EUPL (strict), CC-BY-SA*
    no_license  — repo has no license file (NOASSERTION / null)
    other       — anything else (commercial, custom, unrecognised)

Resume-safe: results are cached in repo_license_cache.jsonl.
On re-run only repos not yet in the cache are queried.

Run:
    python enrich_repo_license.py
    python enrich_repo_license.py --input-files path1.jsonl path2.jsonl
"""

import argparse
import json
import os
import time
from pathlib import Path

import requests
from project_paths import PROCESSED_DIR, format_display_path, load_github_token

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = PROCESSED_DIR

CACHE_FILE   = BASE / "repo_license_cache.jsonl"
API_BASE     = "https://api.github.com"
RETRY_AFTER  = 60   # seconds to wait on rate limit

PERMISSIVE = {
    "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc",
    "unlicense", "cc0-1.0", "eupl-1.1", "eupl-1.2", "mpl-2.0",
    "lgpl-2.1", "lgpl-3.0", "artistic-2.0", "zlib", "psf-2.0",
    "0bsd", "wtfpl", "bsl-1.0",
}
COPYLEFT = {
    "gpl-2.0", "gpl-3.0", "agpl-3.0",
    "cc-by-sa-4.0", "cc-by-sa-3.0",
}


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
        description="Patch repo license metadata into one or more JSONL dataset files."
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
        help="Path to the resume-safe repository license cache JSONL.",
    )
    parser.add_argument(
        "--refresh-owner-repos",
        nargs="*",
        default=[],
        help=(
            "Optional owner/repo keys to force-refresh from GitHub even if they "
            "already exist in the local cache."
        ),
    )
    return parser.parse_args()


def classify_license(spdx: str | None) -> str:
    if not spdx or spdx.upper() in ("NOASSERTION", "OTHER"):
        return "no_license"
    key = spdx.lower()
    if key in PERMISSIVE:
        return "permissive"
    if key in COPYLEFT:
        return "copyleft"
    return "other"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def save_jsonl(entries: list, path: Path) -> None:
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    tmp.replace(path)


def append_jsonl(record: dict, path: Path) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Extract unique owner/repo pairs from original_url
# ---------------------------------------------------------------------------
def extract_owner_repo(url: str) -> str | None:
    """Return 'owner/repo' from a github.com URL, or None."""
    try:
        parts = url.replace("https://github.com/", "").split("/")
        if len(parts) >= 2 and parts[0] and parts[1]:
            return f"{parts[0]}/{parts[1]}"
    except Exception:
        pass
    return None


def collect_repos(files: list) -> dict:
    """Return {owner_repo: [entry_count]} across all files."""
    repos: dict = {}
    for path in files:
        for entry in load_jsonl(path):
            url = entry.get("metadata", {}).get("original_url", "")
            key = extract_owner_repo(url)
            if key:
                repos[key] = repos.get(key, 0) + 1
    return repos


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------
def fetch_license(session: requests.Session, owner_repo: str) -> dict:
    """
    Query GET /repos/{owner}/{repo} and return a cache record.
    Handles rate limiting with exponential back-off.
    """
    url = f"{API_BASE}/repos/{owner_repo}"
    for attempt in range(5):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                lic  = data.get("license") or {}
                spdx = lic.get("spdx_id") or None
                # GitHub returns "NOASSERTION" when it can't identify the license
                if spdx == "NOASSERTION":
                    spdx = None
                return {
                    "owner_repo":       owner_repo,
                    "repo_license":     spdx,
                    "license_category": classify_license(spdx),
                }
            elif resp.status_code == 404:
                # Repo deleted or private
                return {
                    "owner_repo":       owner_repo,
                    "repo_license":     None,
                    "license_category": "no_license",
                }
            elif resp.status_code in (403, 429):
                remaining = int(resp.headers.get("X-RateLimit-Remaining", 0))
                reset_ts  = int(resp.headers.get("X-RateLimit-Reset", 0))
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
        "owner_repo":       owner_repo,
        "repo_license":     None,
        "license_category": "other",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    args = parse_args()
    input_files = [Path(p) for p in args.input_files]
    cache_file = Path(args.cache_file)
    refresh_owner_repos = [item.strip() for item in args.refresh_owner_repos if item.strip()]

    # Load token
    token = load_github_token(__file__)

    session = requests.Session()
    session.headers.update({
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })

    # Collect all unique repos
    print("Scanning dataset for unique repositories...", flush=True)
    for path in input_files:
        print(f"  - {format_display_path(path)}", flush=True)
    all_repos = collect_repos(input_files)
    print(f"  Unique repos found: {len(all_repos):,}", flush=True)

    # Load cache
    cache_records = load_jsonl(cache_file)
    cache = {r["owner_repo"]: r for r in cache_records}
    if refresh_owner_repos:
        for owner_repo in refresh_owner_repos:
            cache.pop(owner_repo, None)
    print(f"  Already cached    : {len(cache):,}", flush=True)
    if refresh_owner_repos:
        print(f"  Forced refresh    : {len(refresh_owner_repos):,}", flush=True)

    pending = list(dict.fromkeys([*refresh_owner_repos, *[r for r in all_repos if r not in cache]]))
    print(f"  To fetch          : {len(pending):,}", flush=True)

    # Fetch missing
    t0 = time.time()
    for i, owner_repo in enumerate(pending, 1):
        rec = fetch_license(session, owner_repo)
        cache[owner_repo] = rec
        append_jsonl(rec, cache_file)
        if i % 100 == 0 or i == len(pending):
            elapsed = time.time() - t0
            print(
                f"  {i}/{len(pending)} ({100*i/len(pending):.1f}%)  "
                f"elapsed={elapsed:.0f}s",
                flush=True,
            )
        # Gentle rate-limiting: 5000 req/hr authenticated = ~1.4/s; stay safe
        time.sleep(0.25)

    if pending or refresh_owner_repos:
        save_jsonl(list(cache.values()), cache_file)

    # Patch files
    print("\nPatching JSONL files...", flush=True)
    total_patched = 0
    for path in input_files:
        entries = load_jsonl(path)
        if not entries:
            continue
        patched = 0
        for entry in entries:
            url = entry.get("metadata", {}).get("original_url", "")
            key = extract_owner_repo(url)
            if key and key in cache:
                rec = cache[key]
                entry["metadata"]["repo_license"]     = rec["repo_license"]
                entry["metadata"]["license_category"] = rec["license_category"]
                patched += 1
        save_jsonl(entries, path)
        total_patched += patched
        print(
            f"  {format_display_path(path)}: patched {patched:,} / {len(entries):,}",
            flush=True,
        )

    # Summary
    cats: dict = {}
    for rec in cache.values():
        c = rec.get("license_category", "other")
        cats[c] = cats.get(c, 0) + 1

    print("\n=== LICENSE DISTRIBUTION (by unique repo) ===")
    for cat in ["permissive", "copyleft", "no_license", "other"]:
        print(f"  {cat:<15} {cats.get(cat, 0):>6,}")
    print(f"  {'TOTAL':<15} {sum(cats.values()):>6,}")
    print(f"\nTotal entries patched: {total_patched:,}", flush=True)


if __name__ == "__main__":
    main()
