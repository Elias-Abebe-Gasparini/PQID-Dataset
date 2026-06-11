# Scientific Data Figure Index

This directory contains both manuscript-facing figure exports and auditable
Mermaid source diagrams. The `_designed.svg/png` files are the recommended main
manuscript schematics; the `.mmd` files remain source-of-record workflow
diagrams for audit and regeneration.

A parallel Calibri-styled export set is available in
`../figures_calibri/`. It is intended for Scientific Data template harmonization
and leaves the original Times-styled exports in this directory untouched.

## Main Figures

| figure | source file | manuscript role | caption draft |
| --- | --- | --- | --- |
| Figure 1. GitHub Acquisition Structure and Diminishing Returns | `figure_1_github_acquisition_structure_diminishing_returns.svg/png` | Acquisition diagnostics | Repository-level acquisition concentration and diminishing returns. The multi-panel figure shows the highest-yield source repositories, cumulative row coverage by repository rank, a descriptive log-log rank-yield decay fit, and rank-band marginal yield with Gini and Herfindahl-Hirschman concentration diagnostics. |
| Figure 2. PQID construction stages and row-level evidence retention | `figure_2_pqid_construction_stages_row_level_evidence_retention.svg/png/pdf` | Main pipeline overview | End-to-end PQID construction as an auditable evidence pipeline. The schematic emphasizes how provenance, execution, instruction generation, review, semantic audit, and release governance accumulate as row-level evidence. |
| Figure 3. Quality-aware instruction-generation flow and branch closure | `figure_3_quality_aware_instruction_generation_flow_branch_closure.svg/png/pdf` | OpenAI seed/paraphrase protocol | Quality-aware instruction generation as a branching flow. The figure shows how the seed-role manifest separates source-code and teacher-text branches and closes them into the canonical instruction object. |
| Figure 4. Release stratification by license evidence and distribution treatment | `figure_4_release_stratification_license_evidence_distribution_treatment.svg/png/pdf` | Release governance overview | Release stratification from the construction-complete instruction object to public views. The alluvial-style figure separates permissive public-open rows, license-valid rows with obligations, and internal-only material. |
| Figure 5. License and release-composition statistics | `figure_5_license_release_composition_statistics.svg/png` | License and release composition | License and public-release composition. The multi-panel figure summarizes internal and public release categories, split-level license-valid composition, the largest restricted-source repositories, and total row counts for internal, license-valid, public-open, and restricted views. |
| Figure 6. Evidence-retention matrix across validation and audit layers | `figure_6_evidence_retention_matrix_validation_audit_layers.svg/png/pdf` | Technical validation overview | Validation and audit evidence matrix. Rows show validation layers and columns show where each layer constrains or annotates the source corpus, seed layer, paraphrase layer, and release views. |
| Figure 7. Benchmark-readiness statistical audit | `figure_7_benchmark_readiness_statistical_audit.svg/png` | Benchmark-readiness statistics | Benchmark-readiness score distributions and check dependencies. The multi-panel figure shows n/7 and n/8 score histograms, observed versus Poisson-binomial expected n/8 scores, and the readiness-check correlation matrix. |
| Figure 8. Semantic and paraphrase-quality statistics | `figure_8_semantic_paraphrase_quality_statistics.svg/png` | Semantic and paraphrase quality | Semantic consistency and paraphrase-diversity diagnostics. The multi-panel figure summarizes BERTScore precision/recall/F1, sentence-transformer similarity, BLEU, ROUGE-L, edit distance, and group-level pairwise BLEU with a near-duplicate threshold. |

## Appendix Figures

| figure | source file | manuscript role | caption draft |
| --- | --- | --- | --- |
| Appendix Figure D1. License behavioral families and release-view composition | `appendix_figure_D1_license_behavioral_families_release_view_composition.svg/png` | License-governance diagnostics | License-behavior and obligation clustering. The multi-panel figure groups detected repository licenses by reuse behavior, exact identifier frequency, release-signal matrix membership, and release-view composition. |
| Appendix Figure H1. Language audit | `appendix_figure_H1_language_audit.svg/png` | Language-audit diagnostics | Linguistic distribution and audit flow. The multi-panel figure summarizes input-language dominance, output language-audit scope, a branch-to-scope-to-resolution alluvial flow, resolved non-English or ambiguous output labels, and non-Latin or mixed-script output buckets. |

## Supplementary Workflow Figures

| figure | source file | manuscript role | caption draft |
| --- | --- | --- | --- |
| Supplementary Figure S1 | `suppfig_s1_metadata_schema_architecture.mmd` | Metadata schema architecture | Metadata schema architecture for PQID. The row-level metadata object combines provenance, repository context, validation, circuit structure, benchmark readiness, metadata-design overlay, generation lineage, semantic metrics, and release metadata. |
| Supplementary Figure S2 | `suppfig_s2_license_governance_decision_tree.mmd` | License-governance details | License-governance decision tree used to translate row-level license categories into distribution-rights status, public release buckets, and release inclusion or exclusion decisions. |
| Supplementary Figure S3 | `suppfig_s3_benchmark_readiness_gate_logic.mmd` | Benchmark-readiness details | Benchmark-readiness gate logic. The n/7 profile measures validation, extraction, cleanup, size, gate, and retrieval evidence; the n/8 companion profile adds mutation-suite cleanliness and routes rows into generation, repair, robustness, or diagnosis-oriented views. |

## Rendering Notes

Submission-facing aliases are generated by:

```powershell
python ..\sync_manuscript_figure_labels.py
```

The alias script preserves the generator-facing filenames while creating the
Figure 1-8 and Appendix D1/H1 filenames listed above in both `figures/` and
`figures_calibri/`.

Rendered Mermaid audit outputs also present:

- `fig1_pqid_construction_pipeline.svg/png`
- `fig2_release_stratification.svg/png`
- `fig3_seed_generation_workflow.svg/png`
- `fig4_validation_audit_layers.svg/png`
- `suppfig_s1_metadata_schema_architecture.svg/png`
- `suppfig_s2_license_governance_decision_tree.svg/png`
- `suppfig_s3_benchmark_readiness_gate_logic.svg/png`

Recommended final render targets:

- SVG for manuscript drafting and clean vector review.
- PNG at journal-required resolution if the submission system does not accept SVG.
- PDF for final production if the venue accepts vector figure uploads.

Reusable local command:

```powershell
.\render_mermaid_figures.ps1
```
