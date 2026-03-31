"""
enrich_repo_license.py
----------------------
Fetches the SPDX license identifier for every unique GitHub repository
referenced in the dataset and patches each entry's metadata with two new
fields:

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

After all repos are resolved the three *_clean.jsonl files are patched
in-place (atomic rename via tmp file).

Run:
    python enrich_repo_license.py
"""

import json
import os
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = Path(
    "c:/Users/Abebe/Downloads/CAREER/ACADEMIC CAREER/SCHOOLS/YONSEI/"
    "YONSEI 2023/Yonsei SS 2025/MS Thesis/MS_THESIS_DATASET/PQID/data/processed"
)

INPUT_FILES = [
    BASE / "train_clean.jsonl",
    BASE / "validation_clean.jsonl",
    BASE / "test_clean.jsonl",
]

CACHE_FILE   = BASE / "repo_license_cache.jsonl"
TOKEN_FILE   = r"C:\Users\Abebe\Downloads\IT\GITHUB\GITHUB_TOKEN_PQID_V1.txt"
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
    # Load token
    token = ""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            token = f.read().strip()
    if not token:
        token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("ERROR: GitHub token not found.")

    session = requests.Session()
    session.headers.update({
        "Authorization": f"token {token}",
        "Accept":        "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })

    # Collect all unique repos
    print("Scanning dataset for unique repositories...", flush=True)
    all_repos = collect_repos(INPUT_FILES)
    print(f"  Unique repos found: {len(all_repos):,}", flush=True)

    # Load cache
    cache_records = load_jsonl(CACHE_FILE)
    cache = {r["owner_repo"]: r for r in cache_records}
    print(f"  Already cached    : {len(cache):,}", flush=True)

    pending = [r for r in all_repos if r not in cache]
    print(f"  To fetch          : {len(pending):,}", flush=True)

    # Fetch missing
    t0 = time.time()
    for i, owner_repo in enumerate(pending, 1):
        rec = fetch_license(session, owner_repo)
        cache[owner_repo] = rec
        append_jsonl(rec, CACHE_FILE)
        if i % 100 == 0 or i == len(pending):
            elapsed = time.time() - t0
            print(
                f"  {i}/{len(pending)} ({100*i/len(pending):.1f}%)  "
                f"elapsed={elapsed:.0f}s",
                flush=True,
            )
        # Gentle rate-limiting: 5000 req/hr authenticated = ~1.4/s; stay safe
        time.sleep(0.25)

    # Patch files
    print("\nPatching JSONL files...", flush=True)
    total_patched = 0
    for path in INPUT_FILES:
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
        print(f"  {path.name}: patched {patched:,} / {len(entries):,}", flush=True)

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
