"""
project_paths.py
----------------
Shared repo-relative path and secret-loading helpers for PQID scripts.

Goals:
- avoid machine-specific absolute paths in committed scripts
- make scripts runnable from any clone location
- support secrets via environment variables or local untracked files
"""

from __future__ import annotations

import os
from pathlib import Path


def find_pqid_root(current_file: str) -> Path:
    start = Path(current_file).resolve().parent
    for candidate in (start, *start.parents):
        if (candidate / "scripts").exists() and (candidate / "data").exists():
            return candidate
    raise RuntimeError(f"Could not locate PQID root from {current_file}")


def get_repo_root(current_file: str) -> Path:
    return find_pqid_root(current_file).parent


def get_processed_dir(current_file: str) -> Path:
    return find_pqid_root(current_file) / "data" / "processed"


def get_user_secret_dir() -> Path:
    """
    Return the preferred out-of-repo secret directory.

    Priority:
    1. ``PQID_SECRET_DIR`` environment variable, if set
    2. ``~/.pqid_secrets``
    """
    override = os.environ.get("PQID_SECRET_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".pqid_secrets"


def get_named_secret_search_roots() -> list[Path]:
    home = Path.home()
    return [
        get_user_secret_dir(),
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        home / "AppData" / "Roaming",
        home / "AppData" / "Local",
    ]


def find_named_secret_file(filename: str) -> Path | None:
    for root in get_named_secret_search_roots():
        if not root.exists():
            continue
        try:
            for candidate in root.rglob(filename):
                if candidate.is_file():
                    return candidate
        except (OSError, PermissionError):
            continue
    return None


def load_secret(
    *,
    env_name: str,
    file_env_name: str,
    file_candidates: list[Path],
    named_file_candidates: list[str] | None,
    label: str,
) -> str:
    value = os.environ.get(env_name, "").strip()
    if value:
        return value

    override_path = os.environ.get(file_env_name, "").strip()
    if override_path:
        candidate = Path(override_path).expanduser()
        if candidate.is_file():
            secret = candidate.read_text(encoding="utf-8").strip()
            if secret:
                return secret

    for candidate in file_candidates:
        if candidate.is_file():
            secret = candidate.read_text(encoding="utf-8").strip()
            if secret:
                return secret

    for filename in named_file_candidates or []:
        discovered = find_named_secret_file(filename)
        if discovered and discovered.is_file():
            secret = discovered.read_text(encoding="utf-8").strip()
            if secret:
                return secret

    searched = ", ".join(str(p) for p in file_candidates)
    raise SystemExit(
        f"ERROR: {label} not found. Set {env_name}, set {file_env_name}, create one of: {searched}, or place the named secret file in a standard user directory."
    )


PQID_ROOT = find_pqid_root(__file__)
REPO_ROOT = get_repo_root(__file__)
PROCESSED_DIR = get_processed_dir(__file__)


PUBLICATION_ARTIFACT_SOURCES = {
    "raw_github_corpus": "circuits_unified_plus_phase2_plus_phase3.jsonl",
    "enriched_github_corpus": "circuits_unified_plus_phase2_plus_phase3_enriched.jsonl",
    "master_corpus": "circuits_unified_plus_phase2_plus_phase3_master_processable_enriched.jsonl",
    "benchmark_strict": "circuits_unified_plus_phase2_plus_phase3_core_enriched.jsonl",
    "benchmark_extended": "circuits_unified_plus_phase2_plus_phase3_core_extended_enriched.jsonl",
    "benchmark_strict_clean": "circuits_unified_plus_phase2_plus_phase3_core_cleaned_enriched.jsonl",
    "benchmark_extended_clean": "circuits_unified_plus_phase2_plus_phase3_core_extended_cleaned_enriched.jsonl",
    "benchmark_extended_balanced_cap20": "circuits_unified_plus_phase2_plus_phase3_core_extended_balanced_cap20_enriched.jsonl",
    "benchmark_extended_balanced_cap25": "circuits_unified_plus_phase2_plus_phase3_core_extended_balanced_cap25_enriched.jsonl",
    "extraction_audit_report": "extraction_quality_report_phase3.md",
    "benchmark_report_strict": "benchmark_tiering_report_phase3.md",
    "benchmark_report_extended": "benchmark_tiering_report_phase3_extended.md",
    "benchmark_report_strict_clean": "benchmark_tiering_report_phase3_cleaned.md",
    "benchmark_report_extended_clean": "benchmark_tiering_report_phase3_extended_cleaned.md",
    "master_corpus_report": "master_processable_report_phase3.md",
}

PUBLICATION_ARTIFACT_NAMES = {
    "raw_github_corpus": "pqid_2026_raw_github_circuits.jsonl",
    "enriched_github_corpus": "pqid_2026_enriched_github_circuits.jsonl",
    "master_corpus": "pqid_2026_master_corpus.jsonl",
    "benchmark_strict": "pqid_2026_benchmark_strict.jsonl",
    "benchmark_extended": "pqid_2026_benchmark_extended.jsonl",
    "benchmark_strict_clean": "pqid_2026_benchmark_strict_clean.jsonl",
    "benchmark_extended_clean": "pqid_2026_benchmark_extended_clean.jsonl",
    "benchmark_extended_balanced_cap20": "pqid_2026_benchmark_extended_balanced_cap20.jsonl",
    "benchmark_extended_balanced_cap25": "pqid_2026_benchmark_extended_balanced_cap25.jsonl",
    "extraction_audit_report": "pqid_2026_extraction_audit.md",
    "benchmark_report_strict": "pqid_2026_benchmark_report_strict.md",
    "benchmark_report_extended": "pqid_2026_benchmark_report_extended.md",
    "benchmark_report_strict_clean": "pqid_2026_benchmark_report_strict_clean.md",
    "benchmark_report_extended_clean": "pqid_2026_benchmark_report_extended_clean.md",
    "master_corpus_report": "pqid_2026_master_corpus_report.md",
}


def get_publication_artifact_map() -> dict[str, dict[str, Path]]:
    mapping = {}
    for key, source_name in PUBLICATION_ARTIFACT_SOURCES.items():
        mapping[key] = {
            "source": PROCESSED_DIR / source_name,
            "public": PROCESSED_DIR / PUBLICATION_ARTIFACT_NAMES[key],
        }
    return mapping


def format_display_path(path: str | Path) -> str:
    """
    Return a stable, publication-safe display path.

    If *path* is inside the repo root, return it relative to the repo root
    (e.g. ``PQID/data/processed/file.jsonl``). Otherwise fall back to the
    original string form.
    """
    candidate = Path(path)
    try:
        rel = candidate.resolve().relative_to(REPO_ROOT)
        return rel.as_posix()
    except Exception:
        return str(candidate)


def load_openai_api_key(current_file: str) -> str:
    repo_root = get_repo_root(current_file)
    pqid_root = find_pqid_root(current_file)
    user_secret_dir = get_user_secret_dir()
    return load_secret(
        env_name="OPENAI_API_KEY",
        file_env_name="OPENAI_API_KEY_FILE",
        file_candidates=[
            repo_root / ".openai_api_key",
            pqid_root / ".openai_api_key",
            user_secret_dir / "openai_api_key.txt",
        ],
        named_file_candidates=[
            "OPENAI_KEY_PQID_GPT54_V2.txt",
            "OPENAI_API_KEY_PQID_GPT54_V2.txt",
            "OPENAI_API_KEY_PQID_GPT54_V1.txt",
            "OPENAI_API_KEY_PQID_V1.txt",
        ],
        label="OpenAI API key",
    )


def load_github_token(current_file: str) -> str:
    repo_root = get_repo_root(current_file)
    pqid_root = find_pqid_root(current_file)
    user_secret_dir = get_user_secret_dir()
    return load_secret(
        env_name="GITHUB_TOKEN",
        file_env_name="GITHUB_TOKEN_FILE",
        file_candidates=[
            repo_root / ".github_token",
            pqid_root / ".github_token",
            user_secret_dir / "github_token.txt",
        ],
        named_file_candidates=["GITHUB_TOKEN_PQID_V1.txt"],
        label="GitHub token",
    )
