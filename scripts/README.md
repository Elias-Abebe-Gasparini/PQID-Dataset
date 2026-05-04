# PQID Scripts

This directory contains the active acquisition, validation, tiering, and instruction-generation code for PQID.

Last updated: 2026-04-26

Documentation scope note:
- this file is intentionally a workflow-oriented index, not the full project archive
- `../README.md` is the project-facing overview
- `../PIPELINE.md` is the exhaustive operational log
- `../SCHEMA.md` is the authoritative metadata reference

That means this file should stay readable and navigable, but it should still surface the current headline structure clearly enough that it does not feel like an empty stub.

## Current Workflow Entry Points

### Acquisition and benchmark packaging

- `scrape_github_unified.ipynb`
  - active public notebook used for the 2026 rebuild
  - covers GitHub acquisition, raw-pool enrichment, extraction audit, and strict / extended benchmark exports
- `scrape_github_unified_internal_debug_archive.ipynb`
  - internal archive notebook containing legacy rerun cells, environment diagnostics, cache checks, and gist troubleshooting cells removed from the public notebook
  - not intended for GitHub / Hugging Face publication
- `scrape_github_unified.py`
  - unified GitHub scraper used by the notebook

### Post-acquisition processing

- `enrich_raw_circuits.py`
  - enriches the raw merged circuit pool
- `report_extraction_quality.py`
  - summarizes extraction quality and validation outcomes
- `filter_benchmark_and_tier2.py`
  - produces strict and extended benchmark exports
- `enrich_metadata.py`
  - full Qiskit execution and metadata extraction used in later stages
- `04_metadata_analysis/pqid_metadata_design_and_evaluation.ipynb`
  - additive metadata-design notebook that derives training-facing fields and evaluates them before seed generation
- `04_metadata_analysis/derive_pqid_metadata_design_fields.py`
  - materializes the additive metadata-design overlay and merged corpus view
- `04_metadata_analysis/evaluate_pqid_metadata_design_fields.py`
  - evaluates field coverage, distributions, cross-tabs, and split-group statistics
- `04_metadata_analysis/audit_pqid_license_governance.py`
  - builds a release-governance audit over the merged corpus, including top unresolved no-license repositories and release-bucket summaries
- `project_paths.py`
  - central path helpers and repo-relative display formatting
- `export_license_valid_release_views.py`
  - writes license-filtered public release views under `PQID/data/processed/release_views/`
  - supports `public_open` and `license_valid` profiles

### Instruction generation

- Legacy thesis-style path:
  - `03_instruction_generation/generate_seeds.py`
  - `03_instruction_generation/generate_paraphrases.py`
- Quality-aware rebuild path:
  - `03_instruction_generation/seed_generation_quality_aware_pipeline.ipynb`
  - `03_instruction_generation/build_seed_role_manifest.py`
  - `03_instruction_generation/build_acceptance_remediation_manifest.py`
  - `03_instruction_generation/generate_seed_drafts_quality_aware.py`
  - `03_instruction_generation/prepare_seed_drafts_quality_aware_batch.py`
  - `03_instruction_generation/materialize_seed_drafts_quality_aware_batch.py`
  - `03_instruction_generation/normalize_quality_aware_prompt_types.py`
  - `03_instruction_generation/evaluate_teacher_text_model_calibration.py`
  - `03_instruction_generation/generate_paraphrases_quality_aware.py`
  - `03_instruction_generation/prepare_paraphrases_quality_aware_batch.py`
  - `03_instruction_generation/materialize_paraphrases_quality_aware_batch.py`
  - `03_instruction_generation/materialize_acceptance_remediation_batch.py`
  - `03_instruction_generation/finalize_acceptance_remediation_closeout.py`
  - `03_instruction_generation/run_openai_batch_job.py`
  - `03_instruction_generation/quality_aware_batch_common.py`
  - `03_instruction_generation/quality_aware_seed_common.py`
- `merge_and_split.py`

These belong after the metadata layer, benchmark logic, and publication-facing artifacts are frozen.

Current additive metadata-design layer:

- headline:
  - `metadata_design_v3`
  - **149 metadata fields across 17 documented clusters** in the full PQID schema
  - **146 metadata keys** materialized in the current merged pre-seed corpus view

- source corpus:
  - `PQID/data/processed/pqid_2026_enriched_github_circuits.jsonl`
- readiness overlay:
  - `PQID/data/processed/pqid_2026_master_corpus.jsonl`
- outputs:
  - `PQID/data/processed/pqid_2026_metadata_design_overlay_v3.jsonl`
  - `PQID/data/processed/pqid_2026_enriched_github_circuits_plus_metadata_design_v3.jsonl`
  - `PQID/data/processed/pqid_metadata_design_evaluation_report_v3.json`
  - `PQID/data/processed/pqid_metadata_design_evaluation_report_v3.md`
  - `PQID/data/processed/pqid_license_governance_report_v3.json`
  - `PQID/data/processed/pqid_license_governance_report_v3.md`
- derived fields:
  - `source_snapshot_timestamp`
  - `source_snapshot_granularity`
  - `source_revision_id`
  - `license_evidence_source`
  - `license_detection_method`
  - `release_view_membership`
  - `lineage_parent_id`
  - `benchmark_view_membership`
  - `metadata_design_version`
  - `expected_model_stance`
  - `context_sufficiency_class`
  - `repairability_score`
  - `repairability_band`
  - `evidence_regime`
  - `split_group_id`
  - `split_group_source`
  - `near_duplicate_group_id`
  - `domain_slice`
  - `shift_axis`
  - `review_trace_id`
  - `distribution_rights_status`
  - `license_resolution_status`
  - `public_release_bucket`
  - `license_audit_priority`
  - `contact_outreach_status`
  - `permission_response_status`
  - `manual_license_review_status`
- design purpose:
  - strengthen later training and split-design work without changing or removing upstream corpus records
  - provide a cleaner abstraction layer for later robustness / hallucination / XAI analyses
  - add audit-grade provenance and governance metadata closer to the transparency standards of leading reference datasets
  - make unresolved-license governance explicit inside the same metadata workflow rather than treating it as hidden release debt

Current instruction-layer closure:

- Stage J / K / L / M are complete.
- canonical instruction rows: `550,314`
  - seeds: `91,719`
  - paraphrases: `458,595`
- Stage K pilot review: `256` rows
  - model-assisted second opinion: `192` suggested `accept`, `64` suggested `rewrite`
  - final adjudicated human review: `209` `accept`, `47` `rewrite`
  - K7/K8 reviewed sidecar sync: complete
- Stage K remediation v1:
  - candidates: `282`
  - core rewrite rows: `47`
  - same-lineage neighbors: `235`
  - materialized results: `282 / 282`
  - final remediation decisions: `282` `rewrite`
  - manual closeout overrides: `2`
  - remaining manual-review rows: `0`
  - neighbor policy: `same_review_group_key_lineage_siblings`
  - artifacts:
    - `PQID/data/processed/instruction_acceptance_gate_remediation_candidates_v1.jsonl`
    - `PQID/data/processed/instruction_acceptance_gate_remediation_review_sheet_v1.csv`
    - `PQID/data/processed/instruction_acceptance_gate_remediation_candidates_v1_summary.json`
    - `PQID/data/processed/instruction_acceptance_gate_remediation_batch_requests_v1.jsonl`
    - `PQID/data/processed/instruction_acceptance_gate_remediation_outputs_v1.jsonl`
    - `PQID/data/processed/instruction_acceptance_gate_remediation_outputs_v1.csv`
    - `PQID/data/processed/instruction_acceptance_gate_remediation_outputs_v1_summary.json`
    - `PQID/data/processed/instruction_acceptance_gate_remediation_manual_closeout_v1.json`

Current release-view exports:

- `public_open` profile:
  - rows: `311,724`
  - train / validation / test: `249,420 / 31,386 / 30,918`
  - files: `PQID/data/processed/release_views/pqid_v1_public_open_*`
- `license_valid` profile:
  - rows: `319,782`
  - train / validation / test: `255,852 / 32,088 / 31,842`
  - files: `PQID/data/processed/release_views/pqid_v1_license_valid_*`
  - includes `7,356` copyleft rows marked as `public_open_with_obligations`
  - includes `702` manually reviewed `other` rows marked as `public_open_with_obligations`
- missing-license internal-only view:
  - rows: `18`
  - file: `PQID/data/processed/release_views/pqid_v1_missing_license_internal_only.jsonl`

Current quality-aware seed logic:

- routing source: `PQID/data/processed/pqid_2026_enriched_github_circuits.jsonl`
- readiness overlay source: `PQID/data/processed/pqid_2026_master_corpus.jsonl`
- current live branches:
  - `source_code`
  - `teacher_text`
- current documented source-code artifacts:
  - `seed_drafts_quality_aware_source_code_v1.jsonl`
  - `seed_paraphrases_quality_aware_source_code_v1.jsonl`
- current documented teacher-text artifacts:
  - `seed_drafts_quality_aware_teacher_text_v1.jsonl`
  - `seed_paraphrases_quality_aware_teacher_text_v1.jsonl`
- full-production execution policy:
  - keep synchronous `Responses API` calls for pilots, calibration, and small recovery runs
  - prefer the `Batch API` path for full-corpus source-code seeds, teacher-text seeds, and paraphrase expansion
  - the notebook now includes dedicated fixed-path `create` and `wait/download` batch cells so production continuation does not require in-place flag toggling

## Current Corrected Rebuild Counts

- raw merged circuits: `91,719`
- validated materialized circuits: `14,267`
- validated non-zero-gate circuits: `13,530`
- strict core (`n/7`): `803`
- extended core (`n/7`): `11,999`
- strict core (`n/8`): `415`
- extended core (`n/8`): `734`

Use the enriched corpus as the default upstream source for the new seed-generation regime:

- `PQID/data/processed/pqid_2026_enriched_github_circuits.jsonl`

Use the master corpus as the readiness-overlay and validated source-code branch:

- `PQID/data/processed/pqid_2026_master_corpus.jsonl`

Current implemented draft-stage settings:

- API interface: `Responses API`
- default teacher model: `gpt-5.4`
- temperature: `0.1`
- `max_output_tokens`: `220`
- concurrency: `12`
- first live pilot: balanced `6`-example source-code batch
- `Stage C` dedicated notebook mini-study for `0.1 / 0.3 / 0.5` on a matched balanced `18`-example source-code batch
- `Stage D` documented advanced calibration for `0.1 / 0.2 / 0.3` on the same matched balanced `18`-example study batch
- `Stage E` empirical evaluation of the comparison outputs through automatic semantic checks and pairwise exact sign tests
- `Stage F` high-rigor confirmation protocol with a larger matched batch, a blinded annotation pack, and a predeclared selection rule
- full-production transport:
  - batch request preparation and materialization are now documented in the notebook and supported by dedicated scripts
  - this changes cost and orchestration, not the prompt contract or supervision logic
- release-cleanup note:
  - `base_seed_quality_aware` is now the canonical rebuild base-seed prompt type
  - a small number of early transition artifacts may still contain the deprecated alias `human_seed_quality_aware`
  - the notebook includes a documented normalization step and the helper script `normalize_quality_aware_prompt_types.py` for harmonizing those files before release

Why `temperature = 0.1`:

- selected by the Stage F high-rigor confirmation protocol rather than by rule of thumb
- highest `overall_score_mean` and `strict_pass_rate` in the larger matched confirmation study
- retained as the production default because it was the only non-dominated candidate under the predeclared automatic criteria

Empirical evaluation support:

- `evaluate_seed_temperature_calibration.py` reads the Stage C and Stage D comparison outputs
- it writes `seed_temperature_empirical_evaluation_v1.json`
- and it reports automatic semantic/alignment metrics alongside matched sign-test summaries
- `prepare_seed_temperature_annotation_pack.py` builds a blinded human-rating pack for the later high-rigor selection step
- `TEMPERATURE_ANNOTATION_RUBRIC.md` defines the manual review rubric used in that step

Current documented paraphrase-stage settings:

- current script: `generate_paraphrases_quality_aware.py`
- current default model: `gpt-5.4-mini`
- current operational temperature: `0.2`
- paraphrases per seed: `5`
- intended upstream input: audited quality-aware seed artifacts from both the `source_code` and `teacher_text` branches
- status note: documented and lineage-preserving, but not yet paraphrase-calibrated to the same standard as the seed draft stage

Why these settings currently differ from the seed-draft defaults:

- seed drafting is the harder role-conditioned task, so it keeps the flagship `gpt-5.4`
- paraphrasing is a narrower reformulation task over an already grounded seed, so the current documented operational choice is `gpt-5.4-mini`
- paraphrase expansion also needs slightly more lexical movement than seed drafting, so its current operational temperature is `0.2` rather than the seed-draft `0.1`
- this explanation is provisional methodology, not a claim that the paraphrase stage is already calibration-closed

## Recommended Order

1. `scrape_github_unified.ipynb`
2. `enrich_raw_circuits.py`
3. `report_extraction_quality.py`
4. `filter_benchmark_and_tier2.py`
5. `04_metadata_analysis/pqid_metadata_design_and_evaluation.ipynb`
   - additive metadata-design overlay and merged corpus view
   - introduces training-facing fields such as `expected_model_stance`, `context_sufficiency_class`, `repairability_band`, `evidence_regime`, and `split_group_id`
6. `03_instruction_generation/seed_generation_quality_aware_pipeline.ipynb`
7. `03_instruction_generation/build_seed_role_manifest.py`
   - builds the full routing manifest from the enriched corpus
8. derive the `source_code` and `teacher_text` branches; build the balanced pilot manifest from `source_code`
9. `03_instruction_generation/generate_seed_drafts_quality_aware.py`
   - live for both supervision branches at present
10. run the teacher-text model calibration gates before full-corpus teacher-text production
   - use `Stage H-Cal-A` for `validation_diagnosis`
   - use `Stage H-Cal-B` for `mutation_robustness`
   - use `evaluate_teacher_text_model_calibration.py` through the notebook’s statistical-evaluation cells so the model decision is supported by matched metrics, sign tests, and bootstrap confidence intervals rather than only descriptive reading
   - then run `Stage H-Cal-C` to export combined CSV and Markdown tables for the paper and release documentation
   - then run `Stage H-Preflight` for an additive integrity check before the expensive teacher-text production run
   - then run `Stage H-Policy` to freeze the role-specific production policy:
     - `validation_diagnosis` -> `gpt-5.4`
     - `mutation_robustness` -> `gpt-5.4-mini`
11. for full-corpus production, prepare batch requests and run Batch API jobs for both seed branches
   - `03_instruction_generation/prepare_seed_drafts_quality_aware_batch.py`
   - `03_instruction_generation/materialize_seed_drafts_quality_aware_batch.py`
   - `03_instruction_generation/run_openai_batch_job.py`
12. later critique / rewrite and acceptance gate
   - preferred upstream before large-scale paraphrase expansion
13. if a seed artifact spans the prompt-type rename boundary, normalize it with:
   - `03_instruction_generation/normalize_quality_aware_prompt_types.py`
14. `03_instruction_generation/generate_paraphrases_quality_aware.py`
   - current documented paraphrase stage for both quality-aware seed branches
15. for full-corpus paraphrase expansion, prepare and materialize Batch API jobs for both branches
   - `03_instruction_generation/prepare_paraphrases_quality_aware_batch.py`
   - `03_instruction_generation/materialize_paraphrases_quality_aware_batch.py`
16. full-corpus coverage audit across both branches
17. `merge_and_split.py`

## Python Environment

Qiskit-dependent scripts should run under Python 3.11.

In practice, this applies to:

- `enrich_raw_circuits.py`
- `enrich_metadata.py`

The non-Qiskit reporting and tiering scripts can be run from the normal project Python environment.

## Historical Material

Legacy thesis-era helpers and historical scripts are still preserved in this repository for provenance, but they should not be treated as the active public benchmark workflow.
