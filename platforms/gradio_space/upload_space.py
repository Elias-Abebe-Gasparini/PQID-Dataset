from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from huggingface_hub import HfApi


SPACE_DIR = Path(__file__).resolve().parent
RUNTIME_FILES = ["app.py", "README.md", "requirements.txt"]
RUNTIME_UPLOAD_PATTERNS = [*RUNTIME_FILES, "assets/figures/*.png"]


def get_token() -> str | None:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print("No HF_TOKEN environment variable found; using cached Hugging Face login.")
        return None
    return token


def verify_runtime_files() -> None:
    missing = [name for name in RUNTIME_FILES if not (SPACE_DIR / name).exists()]
    if missing:
        raise SystemExit(f"Missing required runtime files: {', '.join(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or update the PQID Gradio Space on Hugging Face."
    )
    parser.add_argument(
        "--repo-id",
        required=True,
        help="Space repo id, e.g. Elias-Abebe-Gasparini/PQID-Dataset-Gateway",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create the Space as private. Default is public.",
    )
    parser.add_argument(
        "--include-audit-files",
        action="store_true",
        help="Also upload local audit helpers. Default uploads only runtime files.",
    )
    args = parser.parse_args()

    token = get_token()
    verify_runtime_files()

    api = HfApi(token=token)
    print(f"Creating or reusing Space: {args.repo_id}")
    repo_url = api.create_repo(
        repo_id=args.repo_id,
        repo_type="space",
        space_sdk="gradio",
        private=args.private,
        exist_ok=True,
    )
    print(f"Space URL: {repo_url}")

    allow_patterns = RUNTIME_UPLOAD_PATTERNS
    if args.include_audit_files:
        allow_patterns = [
            *RUNTIME_UPLOAD_PATTERNS,
            "check_gradio_space.py",
            "gradio_space_audit.ipynb",
            "run_local_space.ps1",
            "LOCAL_ENVIRONMENT_NOTE.md",
            "SPACE_UPLOAD_CHECKLIST.md",
            "pipeline_explorer_preview.html",
        ]

    print("Uploading files:")
    for pattern in allow_patterns:
        print(f"  - {pattern}")

    commit = api.upload_folder(
        repo_id=args.repo_id,
        repo_type="space",
        folder_path=SPACE_DIR,
        allow_patterns=allow_patterns,
        commit_message="Deploy PQID Dataset Gateway",
    )
    print(f"Upload complete: {commit.commit_url}")


if __name__ == "__main__":
    main()
