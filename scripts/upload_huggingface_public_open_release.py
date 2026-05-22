"""Upload the PQID public-open release view to Hugging Face.

This script intentionally uploads only the permissive-license public-open split
as the default Hugging Face dataset payload. Broader license-valid artifacts are
left out of the default upload because they include copyleft and reviewed
other-license rows with additional obligations.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from huggingface_hub import HfApi, get_token


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = REPO_ROOT / "data" / "processed" / "release_views"
DATASET_CARD = REPO_ROOT / "HUGGINGFACE_DATASET_CARD.md"


PUBLIC_OPEN_FILES = {
    RELEASE_DIR / "pqid_v1_public_open_train.jsonl": "train.jsonl",
    RELEASE_DIR / "pqid_v1_public_open_validation.jsonl": "validation.jsonl",
    RELEASE_DIR / "pqid_v1_public_open_test.jsonl": "test.jsonl",
    RELEASE_DIR / "pqid_v1_public_open_attribution_manifest.csv": "release/pqid_v1_public_open_attribution_manifest.csv",
    RELEASE_DIR / "pqid_v1_public_open_summary.json": "release/pqid_v1_public_open_summary.json",
    RELEASE_DIR / "pqid_v1_public_open_summary.md": "release/pqid_v1_public_open_summary.md",
    RELEASE_DIR / "pqid_v1_license_valid_summary.json": "release/pqid_v1_license_valid_summary.json",
    RELEASE_DIR / "pqid_v1_license_valid_summary.md": "release/pqid_v1_license_valid_summary.md",
    DATASET_CARD: "README.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-id",
        default="Elias-Abebe-Gasparini/PQID",
        help="Hugging Face dataset repository id.",
    )
    parser.add_argument(
        "--revision",
        default="main",
        help="Target branch or revision on the dataset repository.",
    )
    parser.add_argument(
        "--commit-message",
        default="Update PQID public-open v1 release",
        help="Commit message for the Hugging Face upload.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the upload plan without uploading.",
    )
    parser.add_argument(
        "--skip-create",
        action="store_true",
        help="Do not call create_repo before uploading.",
    )
    return parser.parse_args()


def format_size(path: Path) -> str:
    size = path.stat().st_size
    if size >= 1024**3:
        return f"{size / 1024**3:.2f} GB"
    if size >= 1024**2:
        return f"{size / 1024**2:.2f} MB"
    return f"{size / 1024:.1f} KB"


def main() -> int:
    args = parse_args()
    missing = [path for path in PUBLIC_OPEN_FILES if not path.exists()]
    if missing:
        print("Missing required release files:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 2

    print(f"Target dataset repo: {args.repo_id}")
    print("Upload plan:")
    for local_path, remote_path in PUBLIC_OPEN_FILES.items():
        print(f"  {local_path.relative_to(REPO_ROOT)} -> {remote_path} ({format_size(local_path)})")

    if args.dry_run:
        return 0

    token = get_token()
    if not token:
        print(
            "No Hugging Face token found. Run `hf auth login`, `huggingface-cli login`, "
            "or set HF_TOKEN/HUGGINGFACE_HUB_TOKEN before uploading.",
            file=sys.stderr,
        )
        return 3

    api = HfApi(token=token)
    if not args.skip_create:
        api.create_repo(repo_id=args.repo_id, repo_type="dataset", exist_ok=True)

    for local_path, remote_path in PUBLIC_OPEN_FILES.items():
        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=remote_path,
            repo_id=args.repo_id,
            repo_type="dataset",
            revision=args.revision,
            commit_message=args.commit_message,
        )
        print(f"Uploaded {remote_path}")

    print("Hugging Face public-open release upload complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
