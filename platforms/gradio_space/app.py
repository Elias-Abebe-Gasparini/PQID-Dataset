from __future__ import annotations

import base64
import json
from html import escape
from itertools import islice
from pathlib import Path
from typing import Any

import gradio as gr
import pandas as pd
from datasets import load_dataset
from huggingface_hub import hf_hub_download


DATASET_ID = "Elias-Abebe-Gasparini/PQID"
SPACE_DIR = Path(__file__).resolve().parent
FIGURE_ASSET_DIR = SPACE_DIR / "assets" / "figures"
HF_DATASET_URL = "https://huggingface.co/datasets/Elias-Abebe-Gasparini/PQID"
GITHUB_URL = "https://github.com/Elias-Abebe-Gasparini/PQID-Dataset"
ZENODO_URL = "https://doi.org/10.5281/zenodo.20024477"
ISSUES_URL = "https://github.com/Elias-Abebe-Gasparini/PQID-Dataset/issues"
RELEASE_VERSION = "v1.0.2"

SUMMARY_FILES = [
    "release/pqid_v1_public_open_summary.json",
    "pqid_v1_public_open_summary.json",
    "release_views/pqid_v1_public_open_summary.json",
]
ATTRIBUTION_FILES = [
    "release/pqid_v1_public_open_attribution_manifest.csv",
    "pqid_v1_public_open_attribution_manifest.csv",
    "release_views/pqid_v1_public_open_attribution_manifest.csv",
]
SUMMARY_FILE = SUMMARY_FILES[0]
ATTRIBUTION_FILE = ATTRIBUTION_FILES[0]

PUBLIC_OPEN_SUMMARY = {
    "profile": "public-open",
    "description": "Default Hugging Face payload; permissive-license rows only.",
    "train": 331908,
    "validation": 41520,
    "test": 41094,
    "total": 414522,
    "restricted_rows": 135792,
}

LICENSE_VALID_SUMMARY = {
    "profile": "license-valid",
    "description": (
        "Auditable release view with permissive, copyleft, and manually reviewed "
        "other-license rows; obligations remain in metadata."
    ),
    "train": 338340,
    "validation": 42222,
    "test": 42018,
    "total": 422580,
    "restricted_rows": 127734,
}

LICENSE_CATEGORY_ROWS = [
    {"license_category": "permissive", "rows": 414522, "row_percent": 75.3186},
    {"license_category": "no_license", "rows": 127734, "row_percent": 23.2111},
    {"license_category": "copyleft", "rows": 7356, "row_percent": 1.3367},
    {"license_category": "other", "rows": 702, "row_percent": 0.1276},
]

LICENSE_BEHAVIOR_ROWS = [
    {
        "behavior_family": "no public licence detected",
        "rows": 127734,
        "row_percent": 23.2111,
        "unique_repositories": 2731,
    },
    {
        "behavior_family": "permissive / low-obligation",
        "rows": 413772,
        "row_percent": 75.1883,
        "unique_repositories": 1630,
    },
    {
        "behavior_family": "weak file/library reciprocity",
        "rows": 1380,
        "row_percent": 0.2508,
        "unique_repositories": 22,
    },
    {
        "behavior_family": "strong or network reciprocity",
        "rows": 7356,
        "row_percent": 1.3367,
        "unique_repositories": 163,
    },
    {
        "behavior_family": "attribution/content",
        "rows": 72,
        "row_percent": 0.0131,
        "unique_repositories": 4,
    },
]

PIPELINE_STAGES = [
    {
        "id": "acquisition",
        "stage": "1. Acquisition",
        "object": "GitHub API collection",
        "audit_value": "Repository, path, URL, source key, and scrape metadata retained.",
        "layer": "Data acquisition",
        "rows": "source corpus",
        "artifact": "GitHub API queries and scrape logs",
    },
    {
        "id": "normalization",
        "stage": "2. Normalization",
        "object": "Qiskit and OpenQASM fragments",
        "audit_value": "Unsafe comments removed; imports, syntax, and schema fields normalized.",
        "layer": "Code normalization",
        "rows": "550,314 rows",
        "artifact": "schema, cleaning scripts, processed JSONL",
    },
    {
        "id": "seed-generation",
        "stage": "3. Seed generation",
        "object": "OpenAI API instruction synthesis",
        "audit_value": "Progressive-temperature retries filled stubborn near-duplicate inputs.",
        "layer": "Instruction synthesis",
        "rows": "instruction pairs",
        "artifact": "seed_generation_quality_aware_pipeline.ipynb",
    },
    {
        "id": "semantic-audit",
        "stage": "4. Semantic audit",
        "object": "Embedding and BERT-F1 checks",
        "audit_value": "GCP backfill accelerated pairwise semantic scoring.",
        "layer": "Quality evidence",
        "rows": "semantic scores",
        "artifact": "enrich_semantic_consistency.py",
    },
    {
        "id": "acceptance-gate",
        "stage": "5. Acceptance gate",
        "object": "Validation quality and remediation",
        "audit_value": "Rewrite-tail remediation closed the pilot review queue.",
        "layer": "Human/LLM audit",
        "rows": "282 rewrites",
        "artifact": "acceptance-gate remediation outputs",
    },
    {
        "id": "release-stratification",
        "stage": "6. Release stratification",
        "object": "License-aware public views",
        "audit_value": "No-license rows are restricted; the default public payload exposes public-open data.",
        "layer": "Release governance",
        "rows": "414,522 public-open",
        "artifact": "export_license_valid_release_views.py",
    },
]

PIPELINE_EXPLORER_STAGES = [
    {
        "id": "acquisition",
        "label": "GitHub API acquisition",
        "short": "Acquisition",
        "layer": "Data acquisition",
        "color": "#2f6f8f",
        "x": 90,
        "y": 210,
        "metric": "source repos",
        "headline": "Repository-scale quantum-code harvesting",
        "detail": (
            "PQID begins with GitHub API collection of Qiskit/OpenQASM-bearing "
            "artifacts. The acquisition layer preserves repository names, file "
            "paths, source URLs, source keys, and scrape metadata so later rows "
            "can be audited back to their public repository context."
        ),
        "evidence": [
            "GitHub API provenance fields",
            "Repository, branch, path, URL, and source-key metadata",
            "Acquisition and recall-expansion notebooks",
        ],
        "artifacts": [
            ["Pipeline documentation", GITHUB_URL],
            ["Archived release", ZENODO_URL],
        ],
    },
    {
        "id": "normalization",
        "label": "Normalization and schema design",
        "short": "Normalization",
        "layer": "Code normalization",
        "color": "#4f7f52",
        "x": 245,
        "y": 112,
        "metric": "550,314 construction rows",
        "headline": "A unified code/instruction object",
        "detail": (
            "Raw code fragments are normalized into a stable schema with cleaned "
            "inputs, outputs, metadata, lineage fields, split assignments, and "
            "governance annotations. This makes the dataset inspectable as a "
            "row-level research object instead of a loose scrape."
        ),
        "evidence": [
            "SCHEMA.md",
            "train/validation/test JSONL construction corpus",
            "Metadata design and evaluation notebook",
        ],
        "artifacts": [
            ["GitHub release snapshot", GITHUB_URL],
            ["Zenodo record", ZENODO_URL],
        ],
    },
    {
        "id": "seed-generation",
        "label": "OpenAI seed generation",
        "short": "Seed generation",
        "layer": "Instruction synthesis",
        "color": "#936a2d",
        "x": 400,
        "y": 210,
        "metric": "quality-aware prompts",
        "headline": "Natural-language instructions from code objects",
        "detail": (
            "Instruction generation uses OpenAI API calls with quality-aware "
            "prompting. Stubborn near-duplicate or low-diversity inputs are "
            "backfilled through progressively higher temperature retries, creating "
            "usable instructions while preserving audit metadata."
        ),
        "evidence": [
            "seed_generation_quality_aware_pipeline.ipynb",
            "Progressive-temperature retry records",
            "Instruction acceptance sidecars",
        ],
        "artifacts": [
            ["Hugging Face dataset", HF_DATASET_URL],
            ["Pipeline snapshot", GITHUB_URL],
        ],
    },
    {
        "id": "semantic-audit",
        "label": "Semantic and BERT-F1 audit",
        "short": "Semantic audit",
        "layer": "Quality evidence",
        "color": "#7a5b9a",
        "x": 555,
        "y": 112,
        "metric": "BERT-F1 and embeddings",
        "headline": "Distributional evidence for paraphrase quality",
        "detail": (
            "Semantic consistency checks compare generated instructions and code "
            "objects through embedding-based similarity and BERT-F1 scoring. GCP "
            "backfill is used to accelerate expensive semantic scoring at corpus "
            "scale."
        ),
        "evidence": [
            "BERT-F1 enrichment script",
            "GCP semantic backfill workflow",
            "Validation-quality metric distributions",
        ],
        "artifacts": [
            ["Scientific Data figures", GITHUB_URL],
            ["Dataset card", HF_DATASET_URL],
        ],
    },
    {
        "id": "acceptance-gate",
        "label": "Acceptance gate and remediation",
        "short": "Acceptance gate",
        "layer": "Human/LLM audit",
        "color": "#b55d5d",
        "x": 710,
        "y": 210,
        "metric": "282 rewrite outputs",
        "headline": "Closing the non-trivial rewrite tail",
        "detail": (
            "The pilot review sheet was adjudicated, then the 47 rewrite rows and "
            "their nearest risk-neighbours were remediated. The final closeout "
            "converted the remaining remediation candidates to rewrite decisions "
            "with no missing outputs."
        ),
        "evidence": [
            "209 accept / 47 rewrite pilot adjudication",
            "47 core rewrites plus lineage neighbours",
            "282 final remediation rewrite outputs",
        ],
        "artifacts": [
            ["Audit trail snapshot", GITHUB_URL],
            ["Issue tracker", ISSUES_URL],
        ],
    },
    {
        "id": "release-stratification",
        "label": "License-aware release stratification",
        "short": "Release",
        "layer": "Release governance",
        "color": "#486b74",
        "x": 865,
        "y": 112,
        "metric": "414,522 public-open rows",
        "headline": "Public release without redistributing no-license rows",
        "detail": (
            "The public-open Hugging Face payload exposes permissive-license rows. "
            "The broader license-valid view documents copyleft and reviewed other "
            "license rows for audit, while no-license rows remain restricted and "
            "are not redistributed."
        ),
        "evidence": [
            "Public-open summary JSON",
            "License-valid summary JSON",
            "Attribution manifest",
            "Zenodo immutable release",
        ],
        "artifacts": [
            ["Hugging Face dataset", HF_DATASET_URL],
            ["Zenodo DOI", ZENODO_URL],
            ["GitHub release snapshot", GITHUB_URL],
        ],
    },
]

PIPELINE_EXPLORER_EDGES = [
    ["acquisition", "normalization"],
    ["normalization", "seed-generation"],
    ["seed-generation", "semantic-audit"],
    ["semantic-audit", "acceptance-gate"],
    ["acceptance-gate", "release-stratification"],
]

TOP_RESTRICTED_REPOSITORIES = [
    {"rank": 1, "repository": "lockephi/Allentown-L104-Node", "restricted_rows": 29874},
    {"rank": 2, "repository": "dereklin1205/COMM_LAB_Final", "restricted_rows": 4212},
    {"rank": 3, "repository": "peiyi1/nassc_code", "restricted_rows": 1704},
    {"rank": 4, "repository": "Simula-COMPLEX/MutTG-paper", "restricted_rows": 1422},
    {"rank": 5, "repository": "Xzore19/QEMI", "restricted_rows": 1392},
    {"rank": 6, "repository": "AIComputing101/quantum-computing-101", "restricted_rows": 1356},
    {"rank": 7, "repository": "PennyLaneAI/llvm-project", "restricted_rows": 1356},
    {"rank": 8, "repository": "NiloGregginz33/QMGRExperiments", "restricted_rows": 1044},
    {"rank": 9, "repository": "QuantumAmplification/ampamp", "restricted_rows": 678},
    {"rank": 10, "repository": "qiskit-community/qiskit-presentations", "restricted_rows": 582},
]

EXACT_LICENSE_ROWS = [
    {"license_category": "permissive", "license": "MIT", "rows": 229584, "row_percent": 41.7187},
    {"license_category": "permissive", "license": "Apache-2.0", "rows": 133302, "row_percent": 24.2229},
    {"license_category": "no_license", "license": "no detected public license", "rows": 127734, "row_percent": 23.2111},
    {"license_category": "permissive", "license": "BSD-3-Clause", "rows": 49926, "row_percent": 9.0723},
    {"license_category": "copyleft", "license": "GPL-3.0", "rows": 5988, "row_percent": 1.0881},
    {"license_category": "copyleft", "license": "AGPL-3.0", "rows": 876, "row_percent": 0.1592},
    {"license_category": "permissive", "license": "MPL-2.0", "rows": 582, "row_percent": 0.1058},
    {"license_category": "other", "license": "EPL-2.0", "rows": 504, "row_percent": 0.0916},
    {"license_category": "copyleft", "license": "GPL-2.0", "rows": 474, "row_percent": 0.0861},
    {"license_category": "permissive", "license": "CC0-1.0", "rows": 438, "row_percent": 0.0796},
    {"license_category": "permissive", "license": "Unlicense", "rows": 282, "row_percent": 0.0512},
    {"license_category": "permissive", "license": "LGPL-3.0", "rows": 198, "row_percent": 0.0360},
    {"license_category": "permissive", "license": "BSD-2-Clause", "rows": 114, "row_percent": 0.0207},
    {"license_category": "other", "license": "BSD-3-Clause-Clear", "rows": 90, "row_percent": 0.0164},
    {"license_category": "other", "license": "CC-BY-4.0", "rows": 72, "row_percent": 0.0131},
    {"license_category": "permissive", "license": "EUPL-1.2", "rows": 48, "row_percent": 0.0087},
    {"license_category": "permissive", "license": "LGPL-2.1", "rows": 48, "row_percent": 0.0087},
    {"license_category": "other", "license": "MulanPSL-2.0", "rows": 36, "row_percent": 0.0065},
    {"license_category": "copyleft", "license": "CC-BY-SA-4.0", "rows": 18, "row_percent": 0.0033},
]

QUALITY_AUDIT_ROWS = [
    {
        "layer": "Validation readiness",
        "mechanic": "Rows accumulate binary checks into n/7 and n/8 readiness profiles.",
        "evidence": "Score distributions, check-dependency matrix, Poisson-binomial comparison.",
        "platform_value": "Explains why a row is benchmark-ready, partially ready, or repair-oriented.",
    },
    {
        "layer": "Semantic consistency",
        "mechanic": "Generated instructions are compared through embedding similarity and BERTScore F1.",
        "evidence": "BERT-F1, sentence-transformer similarity, BLEU, ROUGE-L, edit distance.",
        "platform_value": "Separates useful paraphrase diversity from near-duplicate or semantically drifting prompts.",
    },
    {
        "layer": "Remediation closeout",
        "mechanic": "The 47 rewrite rows plus nearest lineage risk-neighbours were passed through remediation.",
        "evidence": "282 final rewrite decisions, 0 missing outputs after closeout.",
        "platform_value": "Shows that the non-trivial rewrite tail was closed before release.",
    },
    {
        "layer": "Release audit",
        "mechanic": "Repository-license metadata controls which rows are public-open, license-valid, or restricted.",
        "evidence": "414,522 public-open rows; 422,580 license-valid rows; 127,734 restricted rows.",
        "platform_value": "Makes the public payload auditable without redistributing no-license material.",
    },
]

FIGURE_GALLERY_ROWS = [
    {"figure": "Figure 1", "file": "suppfig_s4_acquisition_pareto_diminishing_returns.png", "role": "GitHub Acquisition Structure and Diminishing Returns"},
    {"figure": "Figure 2", "file": "fig1_pqid_construction_pipeline_designed.png", "role": "PQID construction stages and row-level evidence retention"},
    {"figure": "Figure 3", "file": "fig3_seed_generation_workflow_designed.png", "role": "Quality-aware instruction-generation flow and branch closure"},
    {"figure": "Figure 4", "file": "fig2_release_stratification_designed.png", "role": "Release stratification by license evidence and distribution treatment"},
    {"figure": "Figure 5", "file": "fig7_release_composition.png", "role": "License and release-composition statistics"},
    {"figure": "Figure 6", "file": "fig4_validation_audit_layers_designed.png", "role": "Evidence-retention matrix across validation and audit layers"},
    {"figure": "Figure 7", "file": "fig5_readiness_statistics.png", "role": "Benchmark-readiness statistical audit"},
    {"figure": "Figure 8", "file": "fig6_semantic_paraphrase_quality.png", "role": "Semantic and paraphrase-quality statistics"},
    {"figure": "Appendix Figure D1", "file": "suppfig_s6_license_behavior_panel.png", "role": "License behavioral families and release-view composition"},
    {"figure": "Appendix Figure H1", "file": "suppfig_s5_linguistic_distribution.png", "role": "Language audit"},
]

FIGURE_BY_LABEL = {
    f"{row['figure']} - {row['role']}": row for row in FIGURE_GALLERY_ROWS
}

REVIEWER_CHECKLIST_ROWS = [
    {"review_goal": "Inspect public data", "artifact": "Hugging Face dataset", "link": HF_DATASET_URL},
    {"review_goal": "Verify reproducibility package", "artifact": "GitHub tagged snapshot", "link": GITHUB_URL},
    {"review_goal": "Cite immutable release", "artifact": "Zenodo DOI", "link": ZENODO_URL},
    {"review_goal": "Check row-level provenance", "artifact": "Attribution manifest", "link": HF_DATASET_URL},
    {"review_goal": "Inspect release logic", "artifact": "Public-open and license-valid summaries", "link": HF_DATASET_URL},
    {"review_goal": "Report issues", "artifact": "GitHub issue tracker", "link": ISSUES_URL},
]

INTEGRITY_EXPECTATIONS = [
    {
        "check": "Public-open split arithmetic",
        "expected": "train + validation + test = 414,522 rows",
        "evidence": "Configured Hugging Face public-open summary.",
    },
    {
        "check": "License-valid construction accounting",
        "expected": "422,580 license-valid rows and 127,734 restricted rows",
        "evidence": "Release-composition tables and license-distribution analysis.",
    },
    {
        "check": "Figure assets packaged",
        "expected": f"{len(FIGURE_GALLERY_ROWS)} manuscript and supplementary PNG assets",
        "evidence": "assets/figures/*.png in the Space package.",
    },
    {
        "check": "Executable dashboard entry point",
        "expected": "app.py exposes a Gradio Blocks demo",
        "evidence": "Local import check in gradio_space_audit.ipynb and check_gradio_space.py.",
    },
    {
        "check": "Public artifact links",
        "expected": "Hugging Face dataset, GitHub tagged snapshot, Zenodo DOI, issue tracker",
        "evidence": "Top-level dashboard links and Reviewer Mode.",
    },
    {
        "check": "Restricted rows are not redistributed",
        "expected": "No-license material is documented as restricted, not shipped as public data",
        "evidence": "Release governance tab and public-open Hugging Face payload.",
    },
]


CSS = """
.pqid-soft-panel {
    border: 1px solid var(--border-color-primary, #bdccd9) !important;
    border-radius: 8px !important;
    background: var(--block-background-fill, #f7fafc) !important;
    color: var(--body-text-color, #102033) !important;
    padding: 12px !important;
}
.pqid-links {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 8px 0 16px;
}
.pqid-links a {
    border: 1px solid var(--border-color-primary, #c9d3df);
    border-radius: 6px;
    color: var(--body-text-color, #102033);
    font-weight: 650;
    padding: 8px 12px;
    text-decoration: none;
    background: var(--button-secondary-background-fill, #f8fafc);
}
.pqid-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 10px;
    margin: 10px 0 18px;
}
.pqid-metric {
    border-left: 4px solid #2f6f8f;
    background: var(--block-background-fill, #f7f9fb);
    color: var(--body-text-color, #102033);
    padding: 10px 12px;
}
.pqid-metric span {
    display: block;
    color: var(--body-text-color-subdued, #53616f);
    font-size: 13px;
}
.pqid-metric strong {
    display: block;
    color: var(--body-text-color, #111827);
    font-size: 22px;
    line-height: 1.2;
}
.pqid-note {
    color: var(--body-text-color, #243447) !important;
    font-size: 14px;
    line-height: 1.45;
}
.fig-native-note {
    border: 1px solid var(--border-color-primary, #bdccd9) !important;
    border-left: 5px solid #2f6f8f !important;
    border-radius: 7px;
    background: var(--block-background-fill, #f7fafc) !important;
    color: var(--body-text-color, #102033) !important;
    margin: 8px 0 12px;
    padding: 12px;
}
.fig-native-note strong {
    display: block;
    color: var(--body-text-color, #102033) !important;
    font-size: 17px;
    margin-bottom: 3px;
}
.fig-native-note span {
    display: block;
    color: var(--body-text-color-subdued, #243447) !important;
    font-size: 14px;
    margin-bottom: 7px;
}
.fig-native-note code {
    color: var(--body-text-color, #102033) !important;
    background: var(--background-fill-secondary, #f5f8fb) !important;
    border: 1px solid var(--border-color-primary, #c7d3df);
    border-radius: 4px;
    padding: 2px 5px;
}
.fig-native-note p {
    color: var(--body-text-color-subdued, #243447) !important;
    font-size: 13px;
    line-height: 1.42;
    margin: 9px 0 0;
}
"""


def _format_int(value: int) -> str:
    return f"{value:,}"


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("metadata")
    return value if isinstance(value, dict) else {}


def _row_to_preview(row: dict[str, Any], index: int) -> dict[str, Any]:
    metadata = _metadata(row)
    output = row.get("output") or row.get("qiskit_code") or ""
    return {
        "index": index,
        "input": row.get("input") or row.get("instruction") or "",
        "output_preview": output[:700],
        "repo_license": metadata.get("repo_license"),
        "license_category": metadata.get("license_category"),
        "source_repository": (
            metadata.get("source_repository")
            or metadata.get("repo_full_name")
            or metadata.get("original_url")
        ),
        "split": metadata.get("split"),
    }


def _release_table() -> pd.DataFrame:
    rows = []
    for summary in [PUBLIC_OPEN_SUMMARY, LICENSE_VALID_SUMMARY]:
        rows.append(
            {
                "release_view": summary["profile"],
                "train": summary["train"],
                "validation": summary["validation"],
                "test": summary["test"],
                "total_rows": summary["total"],
                "restricted_rows": summary["restricted_rows"],
                "description": summary["description"],
            }
        )
    return pd.DataFrame(rows)


def _metrics_html() -> str:
    total = PUBLIC_OPEN_SUMMARY["total"]
    valid = LICENSE_VALID_SUMMARY["total"]
    restricted = LICENSE_VALID_SUMMARY["restricted_rows"]
    return f"""
    <div class="pqid-metrics">
      <div class="pqid-metric"><span>Hugging Face public-open rows</span><strong>{_format_int(total)}</strong></div>
      <div class="pqid-metric"><span>License-valid construction rows</span><strong>{_format_int(valid)}</strong></div>
      <div class="pqid-metric"><span>Restricted no-license rows</span><strong>{_format_int(restricted)}</strong></div>
      <div class="pqid-metric"><span>Release refresh</span><strong>{RELEASE_VERSION}</strong></div>
    </div>
    """


def _links_html() -> str:
    return f"""
    <div class="pqid-links">
      <a href="{HF_DATASET_URL}" target="_blank">Hugging Face dataset</a>
      <a href="{GITHUB_URL}" target="_blank">GitHub repository</a>
      <a href="{ZENODO_URL}" target="_blank">Zenodo DOI</a>
      <a href="{ISSUES_URL}" target="_blank">Issue tracker</a>
    </div>
    """


def _image_data_uri(filename: str) -> str:
    path = FIGURE_ASSET_DIR / filename
    if not path.exists():
        placeholder = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480" '
            'viewBox="0 0 800 480">'
            '<rect width="800" height="480" fill="#f8fafc"/>'
            '<rect x="24" y="24" width="752" height="432" fill="none" '
            'stroke="#cbd5df" stroke-width="3"/>'
            '<text x="400" y="230" text-anchor="middle" '
            'font-family="Calibri, Arial, sans-serif" font-size="28" '
            'fill="#526174">Figure asset not packaged</text>'
            '<text x="400" y="270" text-anchor="middle" '
            'font-family="Calibri, Arial, sans-serif" font-size="18" '
            f'fill="#526174">{escape(filename)}</text>'
            '</svg>'
        )
        encoded = base64.b64encode(placeholder.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def figure_options() -> list[str]:
    return list(FIGURE_BY_LABEL.keys())


def selected_figure(label: str) -> tuple[str | None, str]:
    row = FIGURE_BY_LABEL.get(label) or next(iter(FIGURE_BY_LABEL.values()))
    figure_file = row["file"]
    path = FIGURE_ASSET_DIR / figure_file
    image_value = str(path) if path.exists() else None
    note = f"""
    <div class="fig-native-note">
      <strong>{escape(row["figure"])}</strong>
      <span>{escape(row["role"])}</span>
      <code>{escape(figure_file)}</code>
      <p>
        The preview is served as a native Gradio image component so the selected
        figure updates through Gradio events rather than browser-side scripts.
        Use the image viewer controls to inspect the panel at larger size.
      </p>
    </div>
    """
    return image_value, note


def _iframe(srcdoc: str, title: str, height: int = 720) -> str:
    return (
        f'<iframe title="{escape(title, quote=True)}" '
        f'srcdoc="{escape(srcdoc, quote=True)}" '
        f'style="width:100%; height:{height}px; border:0; display:block;" '
        'loading="lazy"></iframe>'
    )


def _release_flow_html() -> str:
    flow = {
        "nodes": [
            {"id": "construction", "label": "Construction corpus", "rows": 550314, "x": 60, "y": 185, "color": "#2f6f8f", "detail": "All rows available to the construction and audit pipeline before public release filtering."},
            {"id": "license_valid", "label": "License-valid rows", "rows": 422580, "x": 350, "y": 105, "color": "#4f7f52", "detail": "Rows with resolved permissive, copyleft, or manually reviewed other licenses. Obligations remain in metadata."},
            {"id": "restricted", "label": "Restricted rows", "rows": 127734, "x": 350, "y": 268, "color": "#b55d5d", "detail": "No detected public license. Retained for internal audit context and not redistributed."},
            {"id": "public_open", "label": "Public-open HF view", "rows": 414522, "x": 650, "y": 92, "color": "#486b74", "detail": "Default Hugging Face payload. Public-open release rows only."},
            {"id": "obligation_view", "label": "Obligation-preserved rows", "rows": 8058, "x": 650, "y": 220, "color": "#936a2d", "detail": "Copyleft and reviewed other-license rows documented in license-valid release summaries, not in the default public-open payload."},
            {"id": "train", "label": "Train", "rows": 331908, "x": 890, "y": 62, "color": "#557c55", "detail": "Public-open training split."},
            {"id": "validation", "label": "Validation", "rows": 41520, "x": 890, "y": 138, "color": "#7a5b9a", "detail": "Public-open validation split."},
            {"id": "test", "label": "Test", "rows": 41094, "x": 890, "y": 214, "color": "#936a2d", "detail": "Public-open test split."},
        ],
        "links": [
            {"source": "construction", "target": "license_valid", "rows": 422580, "label": "license resolved"},
            {"source": "construction", "target": "restricted", "rows": 127734, "label": "restricted"},
            {"source": "license_valid", "target": "public_open", "rows": 414522, "label": "public-open"},
            {"source": "license_valid", "target": "obligation_view", "rows": 8058, "label": "obligations retained"},
            {"source": "public_open", "target": "train", "rows": 331908, "label": "train"},
            {"source": "public_open", "target": "validation", "rows": 41520, "label": "validation"},
            {"source": "public_open", "target": "test", "rows": 41094, "label": "test"},
        ],
    }
    flow_json = json.dumps(flow)
    doc = f"""
<!doctype html><html><head><meta charset="utf-8" />
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<style>
body{{margin:0;font-family:Calibri,Arial,sans-serif;color:#e8eef6;background:#101827}}
.wrap{{border:1px solid #314154;border-radius:8px;padding:16px;background:#152131}}
h2{{font-size:20px;margin:0 0 4px;color:#f3f7fb}} p{{margin:0;color:#b7c4d2;font-size:14px}}
.grid{{display:grid;grid-template-columns:minmax(620px,1.4fr) minmax(280px,.75fr);gap:14px;margin-top:12px}}
svg{{width:100%;height:430px;border:1px solid #314154;border-radius:8px;background:#101827}}
.node rect{{fill:#f4f7fb;stroke-width:2.5;filter:drop-shadow(0 3px 5px rgba(0,0,0,.22));cursor:pointer}}
.node text{{pointer-events:none;fill:#102033}} .label{{font-size:13px;font-weight:700}} .rows{{font-size:12px;fill:#59677a}}
.flow{{fill:none;stroke-opacity:.32;cursor:pointer}} .flow.active{{stroke-opacity:.72}} .node.active rect{{stroke-width:4}}
.detail{{border:1px solid #314154;border-left:5px solid var(--accent,#2f6f8f);border-radius:8px;padding:16px;background:#101827;min-height:430px}}
.detail h3{{font-size:22px;margin:0 0 8px;color:#f3f7fb}} .metric{{font-size:26px;font-weight:800;margin:8px 0;color:#f3f7fb}} .muted{{color:#b7c4d2;font-size:13px}}
@media(max-width:760px){{.grid{{grid-template-columns:1fr}}svg{{height:540px}}}}
</style></head><body><div class="wrap">
<h2>Interactive Release-Flow Explorer</h2>
<p>Click a node or flow to trace how the construction corpus becomes the public Hugging Face view.</p>
<div class="grid"><svg id="svg" viewBox="0 0 1040 430"></svg><aside class="detail" id="detail"></aside></div>
</div>
<script>
const FLOW={flow_json};
const byId=new Map(FLOW.nodes.map(d=>[d.id,d]));
const svg=d3.select("#svg");
function fmt(x){{return d3.format(",")(x)}}
function detail(d,label){{
  const node=d.target?byId.get(d.target):d;
  const color=node.color||"#2f6f8f";
  document.getElementById("detail").style.setProperty("--accent",color);
  document.getElementById("detail").innerHTML=`<h3>${{node.label}}</h3><div class="metric">${{fmt(d.rows||node.rows)}} rows</div><p>${{d.label?`Flow: ${{d.label}}.`:""}} ${{node.detail}}</p><p class="muted">Public-open rows: 414,522. License-valid rows: 422,580. Restricted rows: 127,734.</p>`;
  d3.selectAll(".node").classed("active", n=>n.id===node.id || (d.source&&n.id===d.source));
  d3.selectAll(".flow").classed("active", l=>l===d || l.source===node.id || l.target===node.id);
}}
svg.append("g").selectAll("path").data(FLOW.links).join("path")
 .attr("class","flow")
 .attr("stroke",d=>byId.get(d.target).color)
 .attr("stroke-width",d=>Math.max(3, Math.sqrt(d.rows)/22))
 .attr("d",d=>{{const s=byId.get(d.source),t=byId.get(d.target); const sx=s.x+115, tx=t.x-115, mx=(sx+tx)/2; return `M${{sx}},${{s.y}} C${{mx}},${{s.y}} ${{mx}},${{t.y}} ${{tx}},${{t.y}}`;}})
 .on("click",(e,d)=>detail(d,d.label))
 .append("title").text(d=>`${{d.label}}: ${{fmt(d.rows)}} rows`);
const g=svg.append("g").selectAll("g").data(FLOW.nodes).join("g").attr("class","node").attr("transform",d=>`translate(${{d.x}},${{d.y}})`).on("click",(e,d)=>detail(d));
g.append("rect").attr("x",-112).attr("y",-33).attr("width",224).attr("height",66).attr("rx",7).attr("stroke",d=>d.color);
g.append("text").attr("class","label").attr("text-anchor","middle").attr("y",-5).text(d=>d.label);
g.append("text").attr("class","rows").attr("text-anchor","middle").attr("y",17).text(d=>fmt(d.rows)+" rows");
detail(FLOW.nodes[0]);
</script></body></html>
"""
    return _iframe(doc, "Interactive release-flow explorer", 700)


def _license_explorer_html() -> str:
    exact_json = json.dumps(EXACT_LICENSE_ROWS)
    family_json = json.dumps(LICENSE_BEHAVIOR_ROWS)
    doc = f"""
<!doctype html><html><head><meta charset="utf-8" />
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<style>
body{{margin:0;font-family:Calibri,Arial,sans-serif;color:#e8eef6;background:#101827}}
.wrap{{border:1px solid #314154;border-radius:8px;padding:16px;background:#152131}}
h2{{font-size:20px;margin:0 0 4px;color:#f3f7fb}}p{{margin:0 0 10px;color:#b7c4d2;font-size:14px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}svg{{width:100%;height:460px;border:1px solid #314154;border-radius:8px;background:#101827}}
.detail{{border:1px solid #314154;border-radius:8px;padding:12px;background:#101827;margin-top:12px;color:#e8eef6}}.bar{{cursor:pointer}}svg text{{fill:#e8eef6}}.chart-title{{fill:#f3f7fb;font-size:14px;font-weight:800}}.label{{font-size:12px;fill:#e8eef6}}.value{{font-size:12px;fill:#b7c4d2}}
@media(max-width:860px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">
<h2>Interactive License-Behaviour Explorer</h2>
<p>Click bars to inspect exact license identifiers and behaviour families used for release governance.</p>
<div class="grid"><svg id="exact" viewBox="0 0 560 460"></svg><svg id="family" viewBox="0 0 560 460"></svg></div><div class="detail" id="detail">Select a bar.</div>
</div><script>
const exact={exact_json}; const family={family_json};
const colors={{permissive:"#4f7f52",copyleft:"#936a2d",other:"#7a5b9a",no_license:"#b55d5d"}};
function fmt(x){{return d3.format(",")(x)}} function pct(x){{return d3.format(".2f")(x)+"%"}}
function detail(title,rows,pctv,extra){{document.getElementById("detail").innerHTML=`<strong>${{title}}</strong><br>${{fmt(rows)}} rows (${{pct(pctv)}}). ${{extra||""}}`;}}
function bars(svgId,data,title,labelKey,colorFn){{const svg=d3.select(svgId); svg.append("text").attr("class","chart-title").attr("x",18).attr("y",28).text(title); const max=d3.max(data,d=>d.rows); const x=d3.scaleLinear().domain([0,max]).range([0,300]); const g=svg.append("g").attr("transform","translate(18,48)");
g.selectAll("g").data(data).join("g").attr("transform",(d,i)=>`translate(0,${{i*21}})`).each(function(d){{const row=d3.select(this); row.append("text").attr("class","label").attr("x",0).attr("y",12).text(d[labelKey]).append("title").text(d[labelKey]); row.append("rect").attr("class","bar").attr("x",190).attr("y",1).attr("height",13).attr("width",x(d.rows)).attr("fill",colorFn(d)).on("click",()=>detail(d[labelKey],d.rows,d.row_percent||d.row_percent, d.license_category?`Category: ${{d.license_category}}.`:`Repositories: ${{d.unique_repositories}}.`)); row.append("text").attr("class","value").attr("x",198+x(d.rows)).attr("y",12).text(pct(d.row_percent)); }});}}
bars("#exact", exact, "Exact repository-license identifiers", "license", d=>colors[d.license_category]||"#486b74");
bars("#family", family, "Behaviour families", "behavior_family", d=>d.behavior_family.includes("no public")?"#b55d5d":d.behavior_family.includes("strong")?"#936a2d":d.behavior_family.includes("weak")?"#7a5b9a":d.behavior_family.includes("attribution")?"#486b74":"#4f7f52");
detail("Public-open release",414522,75.3186,"Default Hugging Face payload contains permissive-license rows only.");
</script></body></html>
"""
    return _iframe(doc, "Interactive license-behaviour explorer", 720)


def _quality_audit_html() -> str:
    cards = []
    for row in QUALITY_AUDIT_ROWS:
        cards.append(
            f"""
            <article class="qa-card">
              <h3>{escape(row["layer"])}</h3>
              <p><strong>Mechanic:</strong> {escape(row["mechanic"])}</p>
              <p><strong>Evidence:</strong> {escape(row["evidence"])}</p>
              <p><strong>Dashboard value:</strong> {escape(row["platform_value"])}</p>
            </article>
            """
        )
    return f"""
    <div class="qa-wrap">
      <h2>Quality and Remediation Explorer</h2>
      <p class="pqid-note">This panel summarizes the audit layers that turn PQID from a scraped corpus into a release-ready dataset object.</p>
      <div class="qa-grid">{''.join(cards)}</div>
    </div>
    <style>
      .qa-wrap {{ border:1px solid var(--border-color-primary,#bdccd9) !important; border-radius:8px; padding:16px; background:var(--block-background-fill,#f7fafc) !important; color:var(--body-text-color,#102033) !important; }}
      .qa-wrap * {{ color:var(--body-text-color,#102033) !important; }}
      .qa-wrap h2 {{ margin:0 0 6px; font-size:20px; color:var(--body-text-color,#102033) !important; }}
      .qa-wrap .pqid-note {{ color:var(--body-text-color-subdued,#243447) !important; }}
      .qa-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:12px; margin-top:12px; }}
      .qa-card {{ border:1px solid var(--border-color-primary,#c7d3df) !important; border-left:5px solid #2f6f8f !important; border-radius:7px; padding:12px; background:var(--background-fill-secondary,#f7fafc) !important; box-shadow:0 1px 2px rgba(16,32,51,.08); }}
      .qa-card h3 {{ margin:0 0 8px; font-size:17px; color:var(--body-text-color,#102033) !important; }}
      .qa-card p {{ margin:6px 0; font-size:13px; line-height:1.42; color:var(--body-text-color-subdued,#243447) !important; }}
      .qa-card strong {{ color:var(--body-text-color,#102033) !important; }}
    </style>
    """


def _figure_gallery_html() -> str:
    cards = []
    for row in FIGURE_GALLERY_ROWS:
        image_src = _image_data_uri(row["file"])
        cards.append(
            f"""
            <article class="fig-card" data-figure="{escape(row["figure"], quote=True)}" data-role="{escape(row["role"], quote=True)}" data-src="{image_src}">
              <img src="{image_src}" alt="{escape(row["figure"])} preview" loading="lazy" />
              <h3>{escape(row["figure"])}</h3>
              <p>{escape(row["role"])}</p>
              <button type="button">Open large view</button>
            </article>
            """
        )
    return f"""
    <div class="fig-wrap">
      <h2>Scientific Data Figure Gallery</h2>
      <p class="pqid-note">Manuscript-facing visual evidence. Each preview links to the archived figure asset in the public GitHub release snapshot.</p>
      <div class="fig-viewer" id="fig-viewer">
        <div class="fig-viewer-head">
          <div>
            <h3 id="fig-viewer-title">{escape(FIGURE_GALLERY_ROWS[0]["figure"])}</h3>
            <p id="fig-viewer-role">{escape(FIGURE_GALLERY_ROWS[0]["role"])}</p>
          </div>
          <a id="fig-viewer-link" href="{_image_data_uri(FIGURE_GALLERY_ROWS[0]["file"])}" target="_blank">Open image in new tab</a>
        </div>
        <img id="fig-viewer-img" src="{_image_data_uri(FIGURE_GALLERY_ROWS[0]["file"])}" alt="Selected figure large preview" />
      </div>
      <div class="fig-grid">{''.join(cards)}</div>
    </div>
    <style>
      .fig-wrap {{ border:1px solid #c7d3df !important; border-radius:8px; padding:16px; background:#f4f7fa !important; color:#102033 !important; }}
      .fig-wrap * {{ color:#102033 !important; }}
      .fig-wrap h2 {{ margin:0 0 6px; font-size:20px; color:#102033 !important; }}
      .fig-wrap .pqid-note {{ color:#243447 !important; }}
      .fig-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap:12px; margin-top:12px; }}
      .fig-card {{ border:1px solid #d6dee8 !important; border-radius:7px; padding:10px; background:#fbfdff !important; box-shadow:0 1px 2px rgba(16,32,51,.06); }}
      .fig-card img {{ width:100%; height:175px; object-fit:contain; background:#ffffff !important; border:1px solid #d9e2ec !important; border-radius:5px; display:block; }}
      .fig-card h3 {{ margin:8px 0 4px; font-size:15px; color:#102033 !important; }}
      .fig-card p {{ margin:0; font-size:13px; color:#243447 !important; line-height:1.35; }}
      .fig-card button {{ margin-top:8px; width:100%; border:1px solid #b9c8d6; border-radius:5px; padding:7px 8px; background:#eef3f7; color:#102033 !important; font-weight:700; cursor:pointer; }}
      .fig-card:hover {{ border-color:#9fb2c4 !important; }}
      .fig-viewer {{ border:1px solid #c7d3df; border-radius:8px; padding:12px; background:#fbfdff; margin-top:12px; }}
      .fig-viewer-head {{ display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:10px; }}
      .fig-viewer h3 {{ margin:0 0 4px; font-size:18px; color:#102033 !important; }}
      .fig-viewer p {{ margin:0; color:#243447 !important; font-size:13px; }}
      .fig-viewer a {{ color:#124e78 !important; font-weight:700; font-size:13px; white-space:nowrap; }}
      .fig-viewer img {{ width:100%; max-height:680px; object-fit:contain; background:#ffffff; border:1px solid #d9e2ec; border-radius:6px; display:block; }}
      @media(max-width:760px) {{ .fig-viewer-head {{ display:block; }} .fig-viewer a {{ display:inline-block; margin-top:8px; }} }}
    </style>
    <script>
      (() => {{
        const root = document.currentScript.closest(".fig-wrap");
        if (!root) return;
        const title = root.querySelector("#fig-viewer-title");
        const role = root.querySelector("#fig-viewer-role");
        const img = root.querySelector("#fig-viewer-img");
        const link = root.querySelector("#fig-viewer-link");
        root.querySelectorAll(".fig-card").forEach((card) => {{
          const activate = () => {{
            title.textContent = card.dataset.figure || "";
            role.textContent = card.dataset.role || "";
            img.src = card.dataset.src || "";
            link.href = card.dataset.src || "";
            root.querySelectorAll(".fig-card").forEach((c) => c.classList.remove("active"));
            card.classList.add("active");
            root.querySelector("#fig-viewer").scrollIntoView({{ behavior: "smooth", block: "nearest" }});
          }};
          card.querySelector("button").addEventListener("click", activate);
          card.querySelector("img").addEventListener("click", activate);
        }});
      }})();
    </script>
    """


def _reviewer_mode_html() -> str:
    items = []
    for row in REVIEWER_CHECKLIST_ROWS:
        items.append(
            f"""
            <tr>
              <td>{escape(row["review_goal"])}</td>
              <td>{escape(row["artifact"])}</td>
              <td><a href="{escape(row["link"], quote=True)}" target="_blank">Open</a></td>
            </tr>
            """
        )
    return f"""
    <div class="review-wrap">
      <h2>Reviewer Mode</h2>
      <p class="pqid-note">A compact route through the artifacts a reviewer or auditor is most likely to inspect.</p>
      <table>
        <thead><tr><th>Review goal</th><th>Artifact</th><th>Link</th></tr></thead>
        <tbody>{''.join(items)}</tbody>
      </table>
      <div class="review-notes">
        <strong>Suggested review path:</strong>
        start with the Hugging Face payload, inspect the release summaries and attribution manifest,
        check the GitHub snapshot for scripts/notebooks, then cite the Zenodo DOI for the immutable record.
      </div>
    </div>
    <style>
      .review-wrap {{ border:1px solid var(--border-color-primary,#bdccd9) !important; border-radius:8px; padding:16px; background:var(--block-background-fill,#f7fafc) !important; color:var(--body-text-color,#102033) !important; }}
      .review-wrap * {{ color:var(--body-text-color,#102033) !important; }}
      .review-wrap h2 {{ margin:0 0 6px; font-size:20px; color:var(--body-text-color,#102033) !important; }}
      .review-wrap .pqid-note {{ color:var(--body-text-color-subdued,#243447) !important; }}
      .review-wrap table {{ width:100%; border-collapse:collapse; margin-top:12px; font-size:14px; }}
      .review-wrap th, .review-wrap td {{ border-bottom:1px solid var(--border-color-primary,#d4dee8) !important; padding:9px; text-align:left; vertical-align:top; color:var(--body-text-color,#102033) !important; background:var(--background-fill-secondary,#f7fafc) !important; }}
      .review-wrap th {{ background:var(--background-fill-primary,#dbe6ef) !important; font-weight:800; color:var(--body-text-color,#102033) !important; }}
      .review-wrap a {{ color:#124e78 !important; font-weight:700; }}
      .review-notes {{ margin-top:12px; padding:12px; border-left:5px solid #486b74 !important; background:var(--background-fill-secondary,#dbe6ef) !important; font-size:14px; line-height:1.45; color:var(--body-text-color,#102033) !important; }}
    </style>
    """


def _release_integrity_html() -> str:
    return f"""
    <div class="integrity-wrap">
      <h2>Release Integrity Panel</h2>
      <p class="pqid-note">
        This panel records the checks a reviewer can use to confirm that the
        public dashboard, Hugging Face payload, GitHub snapshot, and Zenodo DOI
        describe the same release object.
      </p>
      <div class="integrity-grid">
        <article>
          <strong>Public-open rows</strong>
          <span>{PUBLIC_OPEN_SUMMARY["total"]:,}</span>
        </article>
        <article>
          <strong>License-valid rows</strong>
          <span>{LICENSE_VALID_SUMMARY["total"]:,}</span>
        </article>
        <article>
          <strong>Restricted rows</strong>
          <span>{LICENSE_VALID_SUMMARY["restricted_rows"]:,}</span>
        </article>
        <article>
          <strong>Figure assets</strong>
          <span>{len(FIGURE_GALLERY_ROWS)}</span>
        </article>
      </div>
    </div>
    <style>
      .integrity-wrap {{ border:1px solid var(--border-color-primary,#bdccd9) !important; border-radius:8px; padding:16px; background:var(--block-background-fill,#f7fafc) !important; color:var(--body-text-color,#102033) !important; }}
      .integrity-wrap h2 {{ margin:0 0 6px; font-size:20px; color:var(--body-text-color,#102033) !important; }}
      .integrity-wrap .pqid-note {{ color:var(--body-text-color-subdued,#243447) !important; }}
      .integrity-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:10px; margin-top:12px; }}
      .integrity-grid article {{ border:1px solid var(--border-color-primary,#c7d3df); border-left:5px solid #2f6f8f; border-radius:7px; padding:10px 12px; background:var(--background-fill-secondary,#f7fafc); }}
      .integrity-grid strong {{ display:block; font-size:13px; color:var(--body-text-color-subdued,#53616f); }}
      .integrity-grid span {{ display:block; margin-top:3px; font-size:22px; font-weight:800; color:var(--body-text-color,#102033); }}
    </style>
    """


def _pipeline_explorer_html() -> str:
    stages_json = json.dumps(PIPELINE_EXPLORER_STAGES)
    edges_json = json.dumps(PIPELINE_EXPLORER_EDGES)
    iframe_doc = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
  <style>
    :root {
      color-scheme: dark;
      --ink: #e8eef6;
      --muted: #b7c4d2;
      --line: #314154;
      --panel: #101827;
      --panel-strong: #1b2838;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: Calibri, Arial, sans-serif;
      background: #101827;
    }
    .shell {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #152131;
    }
    .header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 10px;
    }
    h2 {
      font-size: 20px;
      line-height: 1.15;
      margin: 0 0 4px;
    }
    .sub {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.35;
      margin: 0;
      max-width: 760px;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 7px 10px;
      font-size: 12px;
      color: var(--muted);
      min-width: 270px;
    }
    .legend span {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      white-space: nowrap;
    }
    .swatch {
      width: 18px;
      height: 8px;
      border-radius: 2px;
      display: inline-block;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(520px, 1.45fr) minmax(300px, 0.8fr);
      gap: 14px;
      align-items: stretch;
    }
    .canvas {
      border: 1px solid var(--line);
      border-radius: 8px;
      min-height: 430px;
      background:
        linear-gradient(180deg, rgba(21,33,49,0.96), rgba(16,24,39,0.98));
      overflow: hidden;
      position: relative;
    }
    svg {
      width: 100%;
      height: 390px;
      display: block;
    }
    .node rect {
      fill: #f4f7fb;
      stroke-width: 2;
      filter: drop-shadow(0 3px 5px rgba(0, 0, 0, 0.22));
      transition: stroke-width 160ms ease, filter 160ms ease;
    }
    .node text {
      pointer-events: none;
      fill: #102033;
    }
    .node .label {
      font-size: 13px;
      font-weight: 700;
    }
    .node .metric {
      fill: #59677a;
      font-size: 11px;
    }
    .node.active rect {
      stroke-width: 4;
      filter: drop-shadow(0 5px 8px rgba(21, 32, 43, 0.18));
    }
    .node.dimmed {
      opacity: 0.46;
    }
    .node {
      cursor: pointer;
    }
    .edge {
      fill: none;
      stroke: #6e7f91;
      stroke-width: 2.4;
      opacity: 0.8;
    }
    .edge.active {
      stroke: #2f6f8f;
      stroke-width: 4;
      opacity: 1;
    }
    .arrow {
      fill: #6e7f91;
    }
    .detail {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 16px 16px 14px;
      min-height: 430px;
    }
    .detail h3 {
      font-size: 21px;
      line-height: 1.15;
      margin: 0 0 7px;
    }
    .chip {
      display: inline-block;
      color: #fff;
      font-size: 12px;
      font-weight: 700;
      border-radius: 4px;
      padding: 4px 7px;
      margin-bottom: 10px;
    }
    .metric-box {
      background: var(--panel-strong);
      border: 1px solid var(--line);
      border-left: 4px solid var(--accent, #2f6f8f);
      border-radius: 6px;
      padding: 8px 10px;
      margin: 8px 0 12px;
      font-size: 14px;
      font-weight: 700;
    }
    .detail p {
      color: var(--ink);
      font-size: 14px;
      line-height: 1.45;
      margin: 0 0 12px;
    }
    .detail h4 {
      font-size: 13px;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      margin: 13px 0 6px;
      color: var(--muted);
    }
    ul {
      margin: 0;
      padding-left: 18px;
      color: var(--ink);
      font-size: 13px;
      line-height: 1.42;
    }
    .artifacts {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-top: 8px;
    }
    .artifacts a {
      border: 1px solid var(--line);
      border-radius: 5px;
      color: var(--ink);
      background: var(--panel-strong);
      padding: 6px 8px;
      font-weight: 700;
      font-size: 12px;
      text-decoration: none;
    }
    .stage-buttons {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 4px 12px 12px;
    }
    .stage-buttons button {
      border: 1px solid var(--line);
      border-radius: 5px;
      background: var(--panel-strong);
      color: var(--ink);
      cursor: pointer;
      font-family: inherit;
      font-size: 12px;
      font-weight: 700;
      padding: 7px 9px;
    }
    .stage-buttons button.active {
      background: #2f6f8f;
      border-color: #2f6f8f;
      color: #ffffff;
    }
    .fallback {
      padding: 22px;
      color: var(--muted);
      font-size: 14px;
    }
    @media (max-width: 760px) {
      .header { display: block; }
      .legend { justify-content: flex-start; margin-top: 10px; }
      .layout { grid-template-columns: 1fr; }
      svg { height: 520px; }
      .detail { min-height: auto; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="header">
      <div>
        <h2>Interactive PQID Pipeline Explorer</h2>
        <p class="sub">Click a stage to inspect the object being transformed, the audit evidence retained, and the public artifact that lets reviewers verify the step.</p>
      </div>
      <div class="legend" id="legend"></div>
    </div>
    <div class="layout">
      <div class="canvas">
        <svg id="pipeline-svg" viewBox="0 0 960 350" role="img" aria-label="Interactive PQID construction and release pipeline"></svg>
        <div class="stage-buttons" id="stage-buttons"></div>
      </div>
      <aside class="detail" id="detail"></aside>
    </div>
  </div>
  <script>
    const STAGES = __STAGES__;
    const EDGES = __EDGES__;
    const layers = Array.from(new Map(STAGES.map(d => [d.layer, d.color])).entries());
    let selected = STAGES[0].id;

    function htmlEscape(value) {
      return String(value).replace(/[&<>"']/g, s => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[s]));
    }

    function isConnected(edge, id) {
      return edge[0] === id || edge[1] === id;
    }

    function updateDetail(stage) {
      const detail = document.getElementById("detail");
      const evidence = stage.evidence.map(item => `<li>${htmlEscape(item)}</li>`).join("");
      const artifacts = stage.artifacts.map(([label, url]) =>
        `<a href="${htmlEscape(url)}" target="_blank" rel="noopener noreferrer">${htmlEscape(label)}</a>`
      ).join("");
      detail.style.setProperty("--accent", stage.color);
      detail.innerHTML = `
        <span class="chip" style="background:${stage.color}">${htmlEscape(stage.layer)}</span>
        <h3>${htmlEscape(stage.headline)}</h3>
        <div class="metric-box">${htmlEscape(stage.metric)}</div>
        <p>${htmlEscape(stage.detail)}</p>
        <h4>Audit evidence</h4>
        <ul>${evidence}</ul>
        <h4>Public verification links</h4>
        <div class="artifacts">${artifacts}</div>
      `;
    }

    function chooseStage(id) {
      selected = id;
      const stage = STAGES.find(d => d.id === id);
      updateDetail(stage);
      d3.selectAll(".node")
        .classed("active", d => d.id === selected)
        .classed("dimmed", d => d.id !== selected && !EDGES.some(edge => isConnected(edge, d.id) && isConnected(edge, selected)));
      d3.selectAll(".edge")
        .classed("active", d => isConnected(d, selected));
      document.querySelectorAll(".stage-buttons button").forEach(button => {
        button.classList.toggle("active", button.dataset.stageId === selected);
      });
    }

    function wrapText(text, width) {
      text.each(function() {
        const textEl = d3.select(this);
        const words = textEl.text().split(/\s+/).reverse();
        const y = textEl.attr("y");
        const x = textEl.attr("x");
        let line = [];
        let lineNumber = 0;
        let word;
        let tspan = textEl.text(null).append("tspan").attr("x", x).attr("y", y);
        while ((word = words.pop())) {
          line.push(word);
          tspan.text(line.join(" "));
          if (tspan.node().getComputedTextLength() > width && line.length > 1) {
            line.pop();
            tspan.text(line.join(" "));
            line = [word];
            tspan = textEl.append("tspan")
              .attr("x", x)
              .attr("y", y)
              .attr("dy", `${++lineNumber * 1.1}em`)
              .text(word);
          }
        }
      });
    }

    function render() {
      if (!window.d3) {
        document.querySelector(".canvas").innerHTML = `<div class="fallback">D3 did not load. The rest of the dashboard still works, but the interactive flow needs access to the D3 JavaScript library.</div>`;
        updateDetail(STAGES[0]);
        return;
      }

      const byId = new Map(STAGES.map(d => [d.id, d]));
      const svg = d3.select("#pipeline-svg");
      svg.selectAll("*").remove();

      svg.append("defs").append("marker")
        .attr("id", "arrowhead")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 9)
        .attr("refY", 0)
        .attr("markerWidth", 8)
        .attr("markerHeight", 8)
        .attr("orient", "auto")
        .append("path")
        .attr("class", "arrow")
        .attr("d", "M0,-5L10,0L0,5");

      svg.append("g")
        .attr("class", "edges")
        .selectAll("path")
        .data(EDGES)
        .join("path")
        .attr("class", "edge")
        .attr("marker-end", "url(#arrowhead)")
        .attr("d", ([sourceId, targetId]) => {
          const source = byId.get(sourceId);
          const target = byId.get(targetId);
          const sx = source.x + 62;
          const sy = source.y;
          const tx = target.x - 62;
          const ty = target.y;
          const mx = (sx + tx) / 2;
          return `M${sx},${sy} C${mx},${sy} ${mx},${ty} ${tx},${ty}`;
        });

      const node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("g")
        .data(STAGES)
        .join("g")
        .attr("class", "node")
        .attr("tabindex", 0)
        .attr("role", "button")
        .attr("aria-label", d => d.label)
        .attr("transform", d => `translate(${d.x},${d.y})`)
        .on("click", (event, d) => chooseStage(d.id))
        .on("keydown", (event, d) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            chooseStage(d.id);
          }
        });

      node.append("rect")
        .attr("x", -64)
        .attr("y", -35)
        .attr("width", 128)
        .attr("height", 78)
        .attr("rx", 8)
        .attr("stroke", d => d.color);

      node.append("text")
        .attr("class", "label")
        .attr("text-anchor", "middle")
        .attr("x", 0)
        .attr("y", -12)
        .text(d => d.short)
        .call(wrapText, 106);

      node.append("text")
        .attr("class", "metric")
        .attr("text-anchor", "middle")
        .attr("x", 0)
        .attr("y", 24)
        .text(d => d.metric)
        .call(wrapText, 108);

      d3.select("#legend")
        .selectAll("span")
        .data(layers)
        .join("span")
        .html(([layer, color]) => `<i class="swatch" style="background:${color}"></i>${htmlEscape(layer)}`);

      d3.select("#stage-buttons")
        .selectAll("button")
        .data(STAGES)
        .join("button")
        .attr("type", "button")
        .attr("data-stage-id", d => d.id)
        .text(d => d.short)
        .on("click", (event, d) => chooseStage(d.id));

      chooseStage(selected);
    }

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", render);
    } else {
      render();
    }
  </script>
</body>
</html>
"""
    iframe_doc = iframe_doc.replace("__STAGES__", stages_json).replace("__EDGES__", edges_json)
    return (
        '<iframe title="Interactive D3 PQID pipeline explorer" '
        f'srcdoc="{escape(iframe_doc, quote=True)}" '
        'style="width:100%; height:760px; border:0; display:block;" '
        'loading="lazy"></iframe>'
    )


def load_rows(split: str, start: int, limit: int) -> pd.DataFrame:
    start = max(0, int(start))
    limit = max(1, min(50, int(limit)))
    dataset = load_dataset(DATASET_ID, split=split, streaming=True)
    rows = [
        _row_to_preview(row, start + offset)
        for offset, row in enumerate(islice(dataset, start, start + limit))
    ]
    return pd.DataFrame(rows)


def _candidate_path_label(paths: list[str]) -> str:
    return " or ".join(paths)


def _download_first_available(paths: list[str]) -> tuple[str, str]:
    errors: list[str] = []
    for path_in_repo in paths:
        try:
            local_path = hf_hub_download(DATASET_ID, path_in_repo, repo_type="dataset")
            return local_path, path_in_repo
        except Exception as exc:
            errors.append(f"{path_in_repo}: {type(exc).__name__}")
    raise FileNotFoundError(
        "Could not find any expected release file on Hugging Face. Checked "
        f"{', '.join(paths)}. Last errors: {'; '.join(errors[-3:])}"
    )


def _load_hub_summary_with_path() -> tuple[dict[str, Any], str]:
    path, path_in_repo = _download_first_available(SUMMARY_FILES)
    return pd.read_json(path, typ="series").to_dict(), path_in_repo


def _format_count(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    return "" if value is None else str(value)


def _format_counts(value: Any) -> str:
    if not isinstance(value, dict):
        return _format_count(value)
    return ", ".join(f"{key}: {_format_count(count)}" for key, count in value.items())


def _summary_audit_table(summary: dict[str, Any], source_file: str) -> pd.DataFrame:
    rows: list[dict[str, str]] = [
        {"section": "source", "field": "source_file", "value": source_file},
        {
            "section": "profile",
            "field": "export_version",
            "value": _format_count(summary.get("export_version")),
        },
        {
            "section": "profile",
            "field": "profile",
            "value": _format_count(summary.get("profile")),
        },
        {
            "section": "profile",
            "field": "description",
            "value": _format_count(summary.get("profile_description")),
        },
        {
            "section": "profile",
            "field": "included_license_categories",
            "value": ", ".join(summary.get("included_license_categories", [])),
        },
        {
            "section": "totals",
            "field": "total_input_rows",
            "value": _format_count(summary.get("total_input_rows")),
        },
        {
            "section": "totals",
            "field": "total_exported_rows",
            "value": _format_count(summary.get("total_exported_rows")),
        },
        {
            "section": "totals",
            "field": "total_excluded_rows",
            "value": _format_count(summary.get("total_excluded_rows")),
        },
        {
            "section": "license",
            "field": "exported_license_category_counts",
            "value": _format_counts(summary.get("exported_license_category_counts")),
        },
        {
            "section": "license",
            "field": "excluded_license_category_counts",
            "value": _format_counts(summary.get("excluded_license_category_counts")),
        },
        {
            "section": "license",
            "field": "missing_license_internal_rows",
            "value": _format_count(summary.get("missing_license_internal_rows")),
        },
    ]

    for split_name, split_summary in summary.get("splits", {}).items():
        if not isinstance(split_summary, dict):
            continue
        rows.extend(
            [
                {
                    "section": f"split:{split_name}",
                    "field": "input_rows",
                    "value": _format_count(split_summary.get("input_rows")),
                },
                {
                    "section": f"split:{split_name}",
                    "field": "exported_rows",
                    "value": _format_count(split_summary.get("exported_rows")),
                },
                {
                    "section": f"split:{split_name}",
                    "field": "excluded_rows",
                    "value": _format_count(split_summary.get("excluded_rows")),
                },
            ]
        )

    rows.append(
        {
            "section": "rule",
            "field": "release_rule",
            "value": _format_count(summary.get("release_rule")),
        }
    )
    return pd.DataFrame(rows)


def load_hub_summary_table() -> pd.DataFrame:
    try:
        summary, summary_path = _load_hub_summary_with_path()
    except Exception as exc:
        return pd.DataFrame(
            [
                {
                    "section": "error",
                    "field": "live_summary_fetch",
                    "value": f"{type(exc).__name__}: {exc}",
                }
            ]
        )
    return _summary_audit_table(summary, summary_path)


def _integrity_static_rows() -> list[dict[str, str]]:
    split_total = (
        PUBLIC_OPEN_SUMMARY["train"]
        + PUBLIC_OPEN_SUMMARY["validation"]
        + PUBLIC_OPEN_SUMMARY["test"]
    )
    missing_figures = [
        row["file"]
        for row in FIGURE_GALLERY_ROWS
        if not (FIGURE_ASSET_DIR / row["file"]).exists()
    ]
    rows: list[dict[str, str]] = []
    for item in INTEGRITY_EXPECTATIONS:
        status = "OK"
        observed = item["evidence"]
        if item["check"] == "Public-open split arithmetic":
            observed = f"{split_total:,} rows from configured splits."
            status = "OK" if split_total == PUBLIC_OPEN_SUMMARY["total"] else "CHECK"
        elif item["check"] == "Figure assets packaged":
            found = len(FIGURE_GALLERY_ROWS) - len(missing_figures)
            observed = f"{found}/{len(FIGURE_GALLERY_ROWS)} figure assets found."
            status = "OK" if not missing_figures else "CHECK"
        rows.append(
            {
                "status": status,
                "check": item["check"],
                "expected": item["expected"],
                "observed_or_evidence": observed,
            }
        )
    return rows


def run_live_release_integrity_check() -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        summary, summary_path = _load_hub_summary_with_path()
    except Exception as exc:
        rows = _integrity_static_rows()
        rows.append(
            {
                "status": "CHECK",
                "check": "Live Hugging Face summary fetch",
                "expected": _candidate_path_label(SUMMARY_FILES),
                "observed_or_evidence": f"{type(exc).__name__}: {exc}",
            }
        )
        summary_rows = pd.DataFrame(
            [
                {
                    "section": "error",
                    "field": "live_summary_fetch",
                    "value": f"{type(exc).__name__}: {exc}",
                }
            ]
        )
        return pd.DataFrame(rows), summary_rows

    expected_total = PUBLIC_OPEN_SUMMARY["total"]
    observed_total = int(summary.get("total_rows", summary.get("total", -1)))
    rows = _integrity_static_rows()
    rows.append(
        {
            "status": "OK" if observed_total == expected_total else "CHECK",
            "check": "Live Hugging Face public-open total",
            "expected": f"{expected_total:,} rows",
            "observed_or_evidence": f"{observed_total:,} rows from {summary_path}",
        }
    )
    return pd.DataFrame(rows), _summary_audit_table(summary, summary_path)


def load_attribution_sample(query: str, limit: int) -> pd.DataFrame:
    limit = max(1, min(200, int(limit)))
    path, _ = _download_first_available(ATTRIBUTION_FILES)
    frame = pd.read_csv(path)
    if query and query.strip():
        needle = query.strip().casefold()
        mask = frame.apply(
            lambda col: col.astype(str).str.casefold().str.contains(needle, na=False)
        ).any(axis=1)
        frame = frame.loc[mask]
    return frame.head(limit)


def release_view_table() -> pd.DataFrame:
    return _release_table()


def license_category_table() -> pd.DataFrame:
    return pd.DataFrame(LICENSE_CATEGORY_ROWS)


def license_behavior_table() -> pd.DataFrame:
    return pd.DataFrame(LICENSE_BEHAVIOR_ROWS)


def exact_license_table() -> pd.DataFrame:
    return pd.DataFrame(EXACT_LICENSE_ROWS)


def quality_audit_table() -> pd.DataFrame:
    return pd.DataFrame(QUALITY_AUDIT_ROWS)


def release_integrity_table() -> pd.DataFrame:
    return pd.DataFrame(_integrity_static_rows())


def figure_gallery_table() -> pd.DataFrame:
    return pd.DataFrame(FIGURE_GALLERY_ROWS)


def pipeline_table() -> pd.DataFrame:
    return pd.DataFrame(PIPELINE_STAGES)


def restricted_repository_table() -> pd.DataFrame:
    return pd.DataFrame(TOP_RESTRICTED_REPOSITORIES)


def citation_text() -> str:
    return f"""@dataset{{gasparini_2026_pqid,
  author    = {{Gasparini, Elias Abebe}},
  title     = {{PQID v1.0.2: Parallel Quantum Instruction Dataset}},
  year      = {{2026}},
  publisher = {{Zenodo}},
  doi       = {{10.5281/zenodo.20024477}},
  url       = {{{ZENODO_URL}}}
}}"""


with gr.Blocks(title="PQID Dataset Gateway", fill_width=True) as demo:
    gr.Markdown(
        """
        # PQID Dataset Gateway

        Interactive entry point for the public Parallel Quantum Instruction Dataset
        release, its provenance package, and its archived reproducibility record.
        """
    )
    gr.HTML(_links_html())
    gr.HTML(_metrics_html())

    with gr.Tab("Release Overview"):
        gr.Markdown(
            """
            The Hugging Face dataset exposes the public-open release view. The
            broader license-valid view is documented for audit and reproducibility.
            """
        )
        gr.Dataframe(
            value=release_view_table(),
            label="Release views",
            interactive=False,
            wrap=True,
        )
        with gr.Row():
            gr.Dataframe(
                value=license_category_table(),
                label="License categories across the construction corpus",
                interactive=False,
                wrap=True,
            )
            gr.Dataframe(
                value=license_behavior_table(),
                label="License behaviour families",
                interactive=False,
                wrap=True,
            )

    with gr.Tab("Release Flow"):
        gr.HTML(_release_flow_html())

    with gr.Tab("License Explorer"):
        gr.HTML(_license_explorer_html())
        gr.Dataframe(
            value=exact_license_table(),
            label="Exact license distribution",
            interactive=False,
            wrap=True,
        )

    with gr.Tab("Pipeline Map"):
        gr.HTML(_pipeline_explorer_html())
        gr.Dataframe(
            value=pipeline_table(),
            label="Auditable construction stages",
            interactive=False,
            wrap=True,
        )
        gr.Markdown(
            """
            Release governance is part of the pipeline rather than a post-hoc
            note: rows without detected public licenses are retained only in
            restricted internal audit materials and are not redistributed here.
            """
        )

    with gr.Tab("Quality Audit"):
        gr.HTML(_quality_audit_html())
        gr.Dataframe(
            value=quality_audit_table(),
            label="Quality and remediation evidence layers",
            interactive=False,
            wrap=True,
        )

    with gr.Tab("Dataset Rows"):
        with gr.Row():
            split = gr.Dropdown(["train", "validation", "test"], value="train", label="Split")
            start = gr.Number(value=0, precision=0, label="Start index")
            limit = gr.Slider(1, 50, value=10, step=1, label="Rows")
        row_button = gr.Button("Load rows", variant="primary")
        row_table = gr.Dataframe(label="Public-open row preview", wrap=True)
        row_button.click(load_rows, inputs=[split, start, limit], outputs=row_table)

    with gr.Tab("Attribution"):
        with gr.Row():
            attribution_query = gr.Textbox(
                label="Filter attribution manifest",
                placeholder="Repository, license, URL, or source key",
            )
            attribution_limit = gr.Slider(1, 200, value=25, step=1, label="Rows")
        attribution_button = gr.Button("Load attribution rows", variant="primary")
        attribution_table = gr.Dataframe(label="Attribution manifest sample", wrap=True)
        attribution_button.click(
            load_attribution_sample,
            inputs=[attribution_query, attribution_limit],
            outputs=attribution_table,
        )

    with gr.Tab("Governance"):
        gr.Dataframe(
            value=restricted_repository_table(),
            label="Largest restricted no-license contributors",
            interactive=False,
            wrap=True,
        )
        summary_button = gr.Button("Load live Hugging Face summary", variant="secondary")
        summary_table = gr.Dataframe(
            label="Live public-open summary from Hugging Face",
            interactive=False,
            wrap=True,
        )
        summary_button.click(load_hub_summary_table, outputs=summary_table)

    with gr.Tab("Release Integrity"):
        gr.HTML(_release_integrity_html())
        gr.Dataframe(
            value=release_integrity_table(),
            label="Static release-integrity checks",
            interactive=False,
            wrap=True,
        )
        integrity_button = gr.Button("Run live Hugging Face summary check", variant="secondary")
        live_integrity_table = gr.Dataframe(
            label="Live integrity check",
            interactive=False,
            wrap=True,
        )
        live_integrity_summary = gr.Dataframe(
            label="Live Hugging Face release summary",
            interactive=False,
            wrap=True,
        )
        integrity_button.click(
            run_live_release_integrity_check,
            outputs=[live_integrity_table, live_integrity_summary],
        )

    with gr.Tab("Figures"):
        with gr.Group(elem_classes=["pqid-soft-panel"]):
            gr.Markdown(
                """
                Select a manuscript figure and inspect it in the large preview.
                The selector uses native Gradio events, so it does not depend on
                browser-side JavaScript embedded in an HTML block.
                """
            )
            figure_choices = figure_options()
            initial_image, initial_note = selected_figure(figure_choices[0])
            figure_choice = gr.Dropdown(
                choices=figure_choices,
                value=figure_choices[0],
                label="Figure",
            )
            figure_image = gr.Image(
                value=initial_image,
                label="Large figure preview",
                interactive=False,
                height=720,
            )
            figure_note = gr.HTML(value=initial_note)
            gr.Dataframe(
                value=figure_gallery_table(),
                label="Figure index",
                interactive=False,
                wrap=True,
            )
            figure_choice.change(
                selected_figure,
                inputs=figure_choice,
                outputs=[figure_image, figure_note],
            )

    with gr.Tab("Reviewer Mode"):
        gr.HTML(_reviewer_mode_html())

    with gr.Tab("Citation"):
        gr.Textbox(
            value=citation_text(),
            label="Zenodo citation",
            lines=10,
            interactive=False,
        )
        gr.Markdown(
            f"""
            Release refresh: `{RELEASE_VERSION}`.

            Dataset URL: {HF_DATASET_URL}

            Archived release: {ZENODO_URL}
            """
        )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        prevent_thread_lock=False,
        css=CSS,
        allowed_paths=[str(FIGURE_ASSET_DIR)],
        ssr_mode=False,
    )
