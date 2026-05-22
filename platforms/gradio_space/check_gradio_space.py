from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import re
import sys
from pathlib import Path


SPACE_DIR = Path(__file__).resolve().parent
REQUIRED_FILES = ["app.py", "README.md", "requirements.txt"]
REQUIRED_RUNTIME_PACKAGES = ["gradio", "datasets", "huggingface_hub", "pandas"]
REQUIRED_FIGURE_ASSETS = [
    "fig1_pqid_construction_pipeline_designed.png",
    "fig2_release_stratification_designed.png",
    "fig3_seed_generation_workflow_designed.png",
    "fig4_validation_audit_layers_designed.png",
    "fig5_readiness_statistics.png",
    "fig6_semantic_paraphrase_quality.png",
    "fig7_release_composition.png",
    "suppfig_s4_acquisition_pareto_diminishing_returns.png",
    "suppfig_s5_linguistic_distribution.png",
    "suppfig_s6_license_behavior_panel.png",
]
EXPECTED_PUBLIC_URLS = [
    "https://huggingface.co/datasets/Elias-Abebe-Gasparini/PQID",
    "https://github.com/Elias-Abebe-Gasparini/PQID-Dataset",
    "https://doi.org/10.5281/zenodo.20024477",
]
EXPECTED_DASHBOARD_MARKERS = [
    "_pipeline_explorer_html",
    "_release_flow_html",
    "_license_explorer_html",
    "_quality_audit_html",
    "_release_integrity_html",
    "selected_figure",
    "figure_choice.change",
    "_reviewer_mode_html",
    "Interactive PQID Pipeline Explorer",
    "Release Integrity Panel",
    "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js",
]
FORBIDDEN_PUBLIC_TERMS = [
    "private funding path",
    "unsubmitted publication target",
    "confidential draft",
    "researcher access application",
    "private",
    "internal/no-license rows are redistributed",
]


def ok(message: str) -> None:
    print(f"[OK] {message}")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_files() -> None:
    missing = [name for name in REQUIRED_FILES if not (SPACE_DIR / name).exists()]
    if missing:
        fail(f"Missing required Space files: {', '.join(missing)}")
    ok("Required Space files are present")


def check_figure_assets() -> None:
    asset_dir = SPACE_DIR / "assets" / "figures"
    missing = [name for name in REQUIRED_FIGURE_ASSETS if not (asset_dir / name).exists()]
    if missing:
        fail(f"Missing packaged figure assets: {', '.join(missing)}")
    ok("Packaged figure assets are present")


def check_readme_front_matter() -> None:
    readme = read_text(SPACE_DIR / "README.md")
    if not readme.startswith("---\n"):
        fail("README.md does not start with Hugging Face YAML front matter")
    parts = readme.split("---", 2)
    if len(parts) < 3:
        fail("README.md front matter is not closed")
    front_matter = parts[1]
    required_pairs = {
        "sdk": "gradio",
        "app_file": "app.py",
        "license": "other",
    }
    for key, expected in required_pairs.items():
        pattern = rf"(?m)^{re.escape(key)}:\s*{re.escape(expected)}\s*$"
        if not re.search(pattern, front_matter):
            fail(f"README.md front matter missing `{key}: {expected}`")
    if "Elias-Abebe-Gasparini/PQID" not in front_matter:
        warn("README.md front matter does not declare the Hugging Face dataset dependency")
    ok("README.md Hugging Face Space metadata looks valid")


def check_requirements() -> None:
    requirements = read_text(SPACE_DIR / "requirements.txt").splitlines()
    normalized = "\n".join(line.strip() for line in requirements if line.strip())
    for package in REQUIRED_RUNTIME_PACKAGES:
        if package not in normalized:
            fail(f"requirements.txt does not include `{package}`")
    ok("requirements.txt includes the expected runtime packages")


def check_python_version() -> None:
    version = sys.version_info
    if version.major == 3 and version.minor >= 14:
        warn(
            "This checker is running on Python "
            f"{version.major}.{version.minor}. Local Gradio preview should use "
            "Python 3.11, 3.12, or 3.13. Some runtime dependencies may not "
            "provide Windows wheels for very new Python versions yet."
        )
    else:
        ok(f"Python {version.major}.{version.minor} is suitable for local preview checks")


def missing_runtime_packages() -> list[str]:
    return [
        package
        for package in REQUIRED_RUNTIME_PACKAGES
        if importlib.util.find_spec(package) is None
    ]


def check_runtime_dependencies(require_installed: bool = False) -> bool:
    missing = missing_runtime_packages()
    if missing and require_installed:
        fail(
            "This Python environment is missing runtime packages: "
            f"{', '.join(missing)}. Install them with "
            "`python -m pip install -r requirements.txt`."
        )
    if missing:
        warn(
            "This Python environment is missing runtime packages: "
            f"{', '.join(missing)}. This is OK for the structural audit; "
            "Hugging Face Spaces will install requirements.txt."
        )
        return False
    ok("Runtime packages are installed in this Python environment")
    return True


def check_python_syntax() -> None:
    app_path = SPACE_DIR / "app.py"
    try:
        ast.parse(read_text(app_path), filename=str(app_path))
    except SyntaxError as exc:
        fail(f"app.py has a syntax error: {exc}")
    ok("app.py parses as valid Python")


def check_public_links() -> None:
    combined = read_text(SPACE_DIR / "app.py") + "\n" + read_text(SPACE_DIR / "README.md")
    for url in EXPECTED_PUBLIC_URLS:
        if url not in combined:
            fail(f"Expected public URL is missing: {url}")
    ok("Hugging Face, GitHub, and Zenodo links are present")


def check_interactive_pipeline() -> None:
    app_text = read_text(SPACE_DIR / "app.py")
    for marker in EXPECTED_DASHBOARD_MARKERS:
        if marker not in app_text:
            fail(f"Interactive pipeline marker is missing from app.py: {marker}")
    ok("D3 interactive pipeline explorer markers are present")


def check_for_private_leak_markers() -> None:
    combined = read_text(SPACE_DIR / "app.py") + "\n" + read_text(SPACE_DIR / "README.md")
    leaks = [term for term in FORBIDDEN_PUBLIC_TERMS if term in combined]
    if leaks:
        fail(f"Potential private/internal markers found: {', '.join(leaks)}")
    ok("No configured private-file markers found in app.py or README.md")


def check_app_import() -> None:
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    app_path = SPACE_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("pqid_gradio_space_app", app_path)
    if spec is None or spec.loader is None:
        fail("Could not create import spec for app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        fail(f"Importing app.py failed: {type(exc).__name__}: {exc}")
    if not hasattr(module, "demo"):
        fail("app.py does not expose a `demo` object")
    ok(f"app.py imports and exposes demo object: {type(module.demo).__name__}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the PQID Hugging Face Gradio Space package."
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Skip importing app.py. Kept for compatibility; this is the default unless --require-import is set.",
    )
    parser.add_argument(
        "--require-import",
        action="store_true",
        help="Import app.py and fail if local runtime dependencies are missing.",
    )
    args = parser.parse_args()

    print(f"Checking Gradio Space folder: {SPACE_DIR}")
    check_required_files()
    check_figure_assets()
    check_readme_front_matter()
    check_requirements()
    check_python_version()
    check_python_syntax()
    check_public_links()
    check_interactive_pipeline()
    check_for_private_leak_markers()
    deps_available = check_runtime_dependencies(require_installed=args.require_import)
    if args.require_import:
        check_app_import()
    elif args.skip_import:
        warn("Skipped app import check")
    elif deps_available:
        warn("Skipped app import check by default. Use --require-import for the full local runtime check.")
    else:
        warn("Skipped app import check because local runtime dependencies are missing.")
    ok("Gradio Space package check complete")


if __name__ == "__main__":
    main()
