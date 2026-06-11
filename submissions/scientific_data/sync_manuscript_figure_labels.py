from __future__ import annotations

import shutil
from pathlib import Path


SCI_DATA_DIR = Path(__file__).resolve().parent
FIGURE_DIRS = (SCI_DATA_DIR / "figures", SCI_DATA_DIR / "figures_calibri")

# Preserve generator-facing filenames and create stable submission-facing aliases.
FIGURE_ALIASES = {
    "figure_1_github_acquisition_structure_diminishing_returns": (
        "suppfig_s4_acquisition_pareto_diminishing_returns",
        ("svg", "png"),
    ),
    "figure_2_pqid_construction_stages_row_level_evidence_retention": (
        "fig1_pqid_construction_pipeline_designed",
        ("svg", "png", "pdf"),
    ),
    "figure_3_quality_aware_instruction_generation_flow_branch_closure": (
        "fig3_seed_generation_workflow_designed",
        ("svg", "png", "pdf"),
    ),
    "figure_4_release_stratification_license_evidence_distribution_treatment": (
        "fig2_release_stratification_designed",
        ("svg", "png", "pdf"),
    ),
    "figure_5_license_release_composition_statistics": (
        "fig7_release_composition",
        ("svg", "png"),
    ),
    "figure_6_evidence_retention_matrix_validation_audit_layers": (
        "fig4_validation_audit_layers_designed",
        ("svg", "png", "pdf"),
    ),
    "figure_7_benchmark_readiness_statistical_audit": (
        "fig5_readiness_statistics",
        ("svg", "png"),
    ),
    "figure_8_semantic_paraphrase_quality_statistics": (
        "fig6_semantic_paraphrase_quality",
        ("svg", "png"),
    ),
    "appendix_figure_D1_license_behavioral_families_release_view_composition": (
        "suppfig_s6_license_behavior_panel",
        ("svg", "png"),
    ),
    "appendix_figure_H1_language_audit": (
        "suppfig_s5_linguistic_distribution",
        ("svg", "png"),
    ),
}


def sync_manuscript_figure_labels() -> list[Path]:
    written: list[Path] = []
    for figure_dir in FIGURE_DIRS:
        for alias, (source_stem, suffixes) in FIGURE_ALIASES.items():
            for suffix in suffixes:
                source = figure_dir / f"{source_stem}.{suffix}"
                if not source.exists():
                    continue
                target = figure_dir / f"{alias}.{suffix}"
                shutil.copy2(source, target)
                written.append(target)
    return written


def main() -> None:
    written = sync_manuscript_figure_labels()
    for target in written:
        print(f"synced {target}")


if __name__ == "__main__":
    main()
