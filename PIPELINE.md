# PQID — Pipeline Master Log

**Parallel Quantum Instruction Dataset**
Parallel corpus: natural-language instructions ↔ Qiskit / OpenQASM quantum circuit code.
Working directory: `PQID/data/processed/` (all JSONL files live here)
Active rebuild notebook: `PQID/scripts/scrape_github_unified.ipynb`
Quality-aware seed notebook: `PQID/scripts/03_instruction_generation/seed_generation_quality_aware_pipeline.ipynb`

---

## Table of Contents

1. [Dataset Overview](#1-dataset-overview)
2. [Repository & File Structure](#2-repository--file-structure)
3. [Python Environment](#3-python-environment)
4. [Pipeline Stages](#4-pipeline-stages)
   - [Stage 0 — Thesis Baseline (HF Dataset)](#stage-0--thesis-baseline-hf-dataset)
   - [Stage 1 — Batch 1: Original Circuits](#stage-1--batch-1-original-circuits)
   - [Stage 2 — Batch 2: GitHub Expansion](#stage-2--batch-2-github-expansion)
   - [Stage 3 — Batch 3: Qiskit Official + Extra Queries](#stage-3--batch-3-qiskit-official--extra-queries)
   - [Stage 4 — Batch 4: Topics API + Org Scraping](#stage-4--batch-4-topics-api--org-scraping)
   - [Stage 5 — Final Enrichment & Splitting](#stage-5--final-enrichment--splitting)
5. [Master Notebook Cell Map (40 cells)](#5-master-notebook-cell-map-40-cells)
6. [Script Reference](#6-script-reference)
7. [Metadata Schema](#7-metadata-schema)
8. [Data Records (Key Files)](#8-data-records-key-files)
9. [Quality Flags & Provenance](#9-quality-flags--provenance)
10. [Split Design](#10-split-design)
11. [Tier System](#11-tier-system)
12. [XAI Design Principles](#12-xai-design-principles)
13. [API Keys & Tokens](#13-api-keys--tokens)
14. [Critical Conventions](#14-critical-conventions)

---

## 1. Dataset Overview

### 2026 Rebuild Checkpoint

The active 2026 rebuild pipeline now has a separate GitHub acquisition and benchmark-packaging flow from the older thesis-scale instruction corpus documented later in this file.

Current corrected public-state counts:

| Metric | Count | Notes |
|---|---:|---|
| Final merged raw circuits | 91,719 | `circuits_unified_plus_phase2_plus_phase3.jsonl` |
| Validated materialized circuits | 14,267 | `validation_status == "validated"` and `materialized_circuit == True` |
| Validated non-zero-gate circuits | 13,530 | `validated` and `gate_count > 0` |
| Master processable corpus | 13,530 | `circuits_unified_plus_phase2_plus_phase3_master_processable_enriched.jsonl`; default downstream generation corpus |
| Strict benchmark core | 803 | `circuits_unified_plus_phase2_plus_phase3_core_enriched.jsonl` |
| Extended benchmark core | 11,999 | `circuits_unified_plus_phase2_plus_phase3_core_extended_enriched.jsonl` |

Current documentation-facing metadata headline:
- full PQID schema: **149 metadata fields across 17 documented clusters**
- active merged `metadata_design_v3` corpus view: **146 materialized metadata keys**
- difference: the remaining schema fields are generation-stage fields that appear later on seed / paraphrase artifacts rather than on the pre-seed merged corpus

Important methodology note:
- a discrepancy investigation after Phase 3 showed that earlier broad `validated` totals were inflated by placeholder seed circuits such as pre-populated `qc` / `circ` objects in the enrichment namespace
- `enrich_metadata.py` now records `materialized_circuit`
- public-facing counts should use `materialized_circuit`, `validated and gate_count > 0`, or the strict / extended core exports rather than raw pre-fix `validated` headlines

Verification-stage note:
- `Master B` in the notebook is an intermediate structural snapshot taken before pre-seed metadata refresh; it confirms that the master processable corpus has the expected size and readiness composition
- `Pre-Seed D` is a targeted completeness check for newly populated metadata fields
- `Master C` is the final post-refresh metadata-freeze checkpoint and should be treated as the authoritative master-corpus summary before seed generation

### Dual Benchmark-Readiness Views

The active rebuild keeps two benchmark-readiness views because they answer different questions and should not be collapsed into a single opaque score.

- `n/7` is the original benchmark-readiness metric used in the Phase 3 reports and statistical analysis. It captures the seven established checks: execution validity, extraction quality, minimum structural thresholds, and provenance trust.
- `n/8` is a late-stage cleanliness-aware extension that adds one additional binary criterion: `non_mutation_suite_path`.

Both views are retained intentionally.

- Keep `n/7` for analytical continuity. It preserves comparability with the original strict/extended-core counts and with the notebook's existing statistical tests.
- Add `n/8` for release and benchmarking hygiene. It lets users distinguish intrinsically strong circuits from mutation-suite or bug-stress entries without erasing the original seven-check profile.
- Use the full master processable corpus first, and derive benchmark/public subsets later. In that workflow, `n/7` is the continuity score and `n/8` is the cleanliness-aware packaging score.

### Seed-Generation Note

Seed generation is intentionally deferred until after the metadata layer, benchmark logic, and release-facing artifacts are frozen. The quality-aware regime is documented in the notebook and companion scripts so that the instruction layer is reproducible and auditable in the same way as the upstream acquisition and benchmark-construction phases.

The current implemented logic is:

- run a separate additive metadata-design stage before seed generation
  - notebook: `PQID/scripts/04_metadata_analysis/pqid_metadata_design_and_evaluation.ipynb`
  - scripts:
    - `derive_pqid_metadata_design_fields.py`
    - `evaluate_pqid_metadata_design_fields.py`
    - `audit_pqid_license_governance.py`
  - outputs:
    - `pqid_2026_metadata_design_overlay_v3.jsonl`
    - `pqid_2026_enriched_github_circuits_plus_metadata_design_v3.jsonl`
    - `pqid_metadata_design_evaluation_report_v3.json`
    - `pqid_metadata_design_evaluation_report_v3.md`
    - `pqid_license_governance_report_v3.json`
    - `pqid_license_governance_report_v3.md`
  - purpose:
    - derive interpretable training-facing metadata such as `expected_model_stance`, `context_sufficiency_class`, `repairability_band`, `evidence_regime`, `split_group_id`, and `near_duplicate_group_id`
    - add audit-grade transparency fields such as `source_snapshot_timestamp`, `source_snapshot_granularity`, `source_revision_id`, `license_evidence_source`, `license_detection_method`, `lineage_parent_id`, `benchmark_view_membership`, `domain_slice`, `shift_axis`, and `review_trace_id`
    - expand the raw license metadata into conservative release-governance fields such as `distribution_rights_status`, `release_view_membership`, `public_release_bucket`, and `license_audit_priority`
    - track governance workflow explicitly through `permission_response_status` and `manual_license_review_status`
    - keep this layer distinct from both scraping and the operational seed-generation notebook
- build a full routing manifest from `pqid_2026_enriched_github_circuits.jsonl`
- overlay master-corpus readiness metadata where available from `pqid_2026_master_corpus.jsonl`
- split the routing manifest by supervision mode
- run the live draft generator on both supervision branches
- generate documented production source-code seed drafts after calibration is frozen
- run documented teacher-text model-calibration gates before launching majority-corpus teacher-text production
  - `Stage H-Cal-A` for `validation_diagnosis`
  - `Stage H-Cal-B` for `mutation_robustness`
  - each gate now has a statistical-evaluation step based on matched automatic metrics, paired exact sign tests, and bootstrap confidence intervals
  - `Stage H-Cal-C` exports combined CSV and Markdown summary tables for paper-ready reporting of both calibration gates
- run `Stage H-Preflight` as an additive integrity gate before the expensive teacher-text production run
  - verifies split-manifest integrity, source alignment, calibration-policy consistency, and non-blocking metadata drift
- freeze the role-specific teacher-text production policy in `Stage H-Policy`
  - `validation_diagnosis` -> `gpt-5.4` at `0.1`
  - `mutation_robustness` -> `gpt-5.4-mini` at `0.1`
  - materialize separate production manifests for the two teacher-text roles before any full-corpus Stage H run
- generate documented production teacher-text seeds for `validation_diagnosis` and `mutation_robustness`
- generate documented quality-aware paraphrases across both seed branches
- keep synchronous execution for pilots and calibration, but prefer the `Batch API` path for full-corpus production runs
- the quality-aware notebook now includes fixed-purpose batch `create` and `wait/download` cells so full production does not depend on editing control flags in place

Pedagogical mechanics:

- the first split is `validated` vs `unvalidated`
- validated records are then stratified by benchmark readiness, especially the cleanliness-aware `n/8` profile
- this produces role-conditioned supervision rather than a single flat prompt family
- clean validated records teach desirable canonical generation
- weaker validated records teach repair, critique, or readiness explanation
- mutation-stress records teach robustness and boundary recognition
- unvalidated records teach diagnosis and anti-hallucination discipline
- a later extension can turn these strata into preference-style or contrastive learning signals, but that is downstream of the currently implemented routing layer

Current draft-stage generation settings:

- API interface: `Responses API`
- default teacher model: `gpt-5.4`
- temperature: `0.1`
- base `max_output_tokens`: `220`
- concurrency: `12`
- first manual-review pilot: balanced `6`-example source-code batch
- `Stage C` notebook mini-study comparing `0.1`, `0.3`, and `0.5` on a matched balanced `18`-example source-code manifest
- `Stage D` notebook advanced calibration comparing `0.1`, `0.2`, and `0.3` on the same matched balanced `18`-example study manifest
- `Stage E` notebook-backed empirical evaluation using automatic semantic checks and pairwise exact sign tests over the Stage C and Stage D outputs
- `Stage F` high-rigor confirmation protocol using a larger matched batch, custom empirical evaluation, and a blinded human-annotation pack

Current documented paraphrase-stage settings:

- current script: `PQID/scripts/03_instruction_generation/generate_paraphrases_quality_aware.py`
- current default model: `gpt-5.4-mini`
- paraphrases per seed: `5`
- current operational temperature: `0.2`
- intended upstream input: audited quality-aware seed artifacts from both the `source_code` and `teacher_text` branches
- status note: implemented and documented, but not yet frozen by a dedicated paraphrase-specific calibration ladder
- production transport note: the notebook now documents batch preparation, submission, download, and materialization for full-corpus paraphrase expansion

Residual closure note:

- the notebook also now documents a separate residual-closure path after full-corpus paraphrase materialization
- base paraphrase production still uses the documented operating point of `0.2`
- token-safe retry recovery keeps the same operating point where possible, but reduces each request to one paraphrase per call
- final canonical duplicate-remediation rounds may temporarily escalate to `0.4` and `0.6`
- the last anti-template tail for a tiny residual teacher-text subset may use `0.8` or `0.9`
- these elevated temperatures are **not** replacement production defaults; they are repair-stage settings for a very small audited residual subset
- repaired rows preserve their own metadata, including `paraphrase_generation_temperature` and `paraphrase_generation_prompt_mode`, so the closure process remains separable from the original operating-point rationale

Acceptance-gate transition note:

- after Stage J canonical closure, the next local component was a unified acceptance-gate manifest built from the canonical seed and paraphrase artifacts
- this manifest is a review-stage corpus for later critique / rewrite and acceptance decisions
- it does not modify the canonical Stage J artifacts and should be audited separately from the generation stages
- pilot review can be supplemented by a **model-assisted second-opinion pass**, but that layer should remain separate from human review judgments rather than silently overwriting them
- the Stage K pilot review sheet has now been adjudicated and synced into the reviewed JSONL / summary sidecars by rerunning notebook cells `K7` and `K8`
- language scope should also be audited separately: PQID is best described as **English-dominant**, not English-only, because source-grounded outputs can preserve multilingual comments or docstrings from upstream repositories
- the language audit is recorded as a sidecar metadata layer keyed by `instruction_key`, with fields such as `input_human_language`, `output_human_language`, `*_human_language_resolved`, `*_human_script_bucket`, and `output_human_language_scope`
- the current resolved-label policy is intentionally conservative and reproducible:
  - `ja_script` only when kana is present
  - `zh_likely_han_only` for multi-character Han-only text without kana or hangul
  - `han_script_unresolved` for genuinely tiny Han-only leftovers
  - `ko_script` for hangul-bearing text
  - `cyrillic_script_unresolved` for Cyrillic-script text without a stronger language claim
  - `short_fragment` for comment/docstring snippets too short to support a meaningful language label
- current pilot-review and language-audit snapshot:
  - acceptance-gate pilot size: `256`
  - observed strata: `10`
  - balanced sample: `25` per stratum, plus `6` forced anti-template tail rows
  - model-assisted pilot second opinion:
    - `192` model `accept`
    - `64` model `rewrite`
    - `192` human/model agreements
    - `64` human/model disagreements
  - this disagreement block should be treated as a targeted follow-up review queue rather than as an automatic failure finding
  - final adjudicated human review sheet:
    - `209` `accept`
    - `47` `rewrite`
    - reviewed sidecar sync status: complete after `K7` / `K8`
  - remediation v1 sidecar:
    - core rewrite rows: `47`
    - same-lineage neighbors: `235`
    - total remediation candidates: `282`
    - materialized remediation results: `282 / 282`
    - final remediation decisions: `282` `rewrite`
    - final manual closeout overrides: `2`
    - remaining manual-review rows: `0`
    - neighbor policy: `same_review_group_key_lineage_siblings`
  - current language-audit totals over the unified acceptance-gate manifest (`550,314` rows):
    - resolved input languages:
      - `en`: `550,300`
      - `bn`: `14`
    - resolved output languages:
      - `en`: `539,544`
      - `es`: `216`
      - `pt`: `132`
      - `fr`: `78`
      - `ja_script`: `156`
      - `ko_script`: `90`
      - `cyrillic_script_unresolved`: `12`
      - `mixed`: `96`
      - `short_fragment`: `330`
      - `none`: `9,660`

Public release note:

- the full `550,314`-row instruction layer is a construction-complete internal artifact
- public upload should use license-filtered release views under `PQID/data/processed/release_views/`
- current public-open release view:
  - total rows: `311,724`
  - rule: permissive-license rows only
- current license-valid release view:
  - total rows: `319,782`
  - includes `311,724` permissive rows
  - includes `7,356` copyleft rows with downstream obligations preserved
  - includes `702` manually reviewed `other` rows with downstream obligations preserved
- excluded from public release:
  - no-license rows remain restricted/internal
  - the former `18` missing-license-category rows have been normalized to explicit `no_license`
  - the current missing-license internal-only summary contains `0` rows
    - output scopes:
      - `full_output_text`: `532,302`
      - `code_comments_or_docstrings`: `8,352`
      - `code_only`: `9,660`
  - no `zh_likely_han_only` rows were observed in the current resolved output distribution

Current full-corpus supervision coverage:

- `source_code` branch:
  - `gold_generation`
  - `broad_generation`
  - `repair_or_explanation`
- `teacher_text` branch:
  - `validation_diagnosis`
  - `mutation_robustness`

The branch split is operational only. Full corpus coverage means that both branches have been generated.

Current rationale for the paraphrase-stage settings:

- the seed-draft stage uses `gpt-5.4` because it must translate circuit code plus readiness-conditioned role metadata into a pedagogically aligned seed instruction
- the paraphrase stage is narrower: it reformulates an already grounded seed while preserving the same role, semantics, and deliverables
- that narrower task is the reason the current paraphrase stage uses `gpt-5.4-mini` as a provisional lower-risk reformulation model
- the paraphrase temperature is currently `0.2`, not `0.1`, because the paraphrase objective requires a little more surface-form variation than the seed-draft objective
- this is still an operational rationale, not a frozen calibration result
- later higher-temperature retries for residual canonical closure should be described as post-production repair interventions rather than as evidence against the original `0.2` operating-point rationale

Temperature rationale:

- the seed stage needs controlled variation, not maximum creativity
- the final draft-stage default is now `0.1`
- that choice was frozen by the Stage F automatic high-rigor confirmation protocol rather than by heuristic preference
- `0.1` emerged as the only non-dominated candidate on the primary automatic criteria in the larger matched confirmation study

Calibration note:

- `Stage C` is intentionally preserved as the first broader screen
- `Stage D` is added as a more granular low-temperature refinement rather than an overwrite
- `Stage E` evaluates the resulting comparison batches more formally through semantic-fidelity heuristics and matched statistical summaries
- `Stage F` is the first stage intended to support a final publication-grade temperature freeze
- after Stage F, the documented draft default is frozen to `0.1`
- this should be described as an automatic protocol selection, not as a human-reviewed optimum
- the seed generator now treats `220` as a default floor and applies truncation-aware dynamic up-allocation for larger opaque circuits or longer `teacher_text` answers, while preserving the same routing and prompt contract
- the canonical rebuild base-seed prompt type is now `base_seed_quality_aware`; early artifacts that still contain `human_seed_quality_aware` should be harmonized through the documented normalization step before release packaging

### Publication-Facing Artifact Names

The rebuild deliberately separates internal pipeline filenames from final publication-facing artifact names.

Internal filenames such as `circuits_unified_plus_phase2_plus_phase3_master_processable_enriched.jsonl` are intentionally verbose because they encode lineage: they show which acquisition stages were merged, whether enrichment has already been applied, and how the file relates to neighboring intermediates. This is valuable for development, reruns, and auditability.

For publication, however, those same names are too noisy. They make the artifact inventory harder to scan in the notebook, manuscript, and dataset card. The final release layer therefore uses a clean alias system generated only at the end of the pipeline.

The rule is:

- keep the internal lineage-preserving filenames unchanged inside the working pipeline;
- generate short public aliases only after the final artifacts have been produced.

Examples of publication-facing aliases are:

- `pqid_2026_master_corpus.jsonl`
- `pqid_2026_benchmark_strict.jsonl`
- `pqid_2026_benchmark_extended_clean.jsonl`
- `pqid_2026_master_corpus_report.md`

This design is important methodologically. It preserves reproducibility because the internal names still carry the detailed provenance, while the public names remain professional and stable for readers. The public notebook and release package should therefore present the `pqid_2026_*` names, while the internal lineage names remain the implementation layer behind them.

### Legacy Thesis Instruction Corpus (Archival)

The larger instruction corpus documented below belongs to the earlier thesis-era generation pipeline. It remains useful for provenance and historical reproducibility, but it is not the current benchmark headline for the rebuilt dataset.

| Attribute | Value |
|-----------|-------|
| Name | PQID — Parallel Quantum Instruction Dataset |
| Format | JSONL, UTF-8, one entry per line |
| Entry schema | `{ "input": str, "output": str, "metadata": { ... } }` |
| Total entries | **691,051** (all 4 batches merged) |
| Primary dedup key | `circuit_hash` — MD5 of stripped output code |
| Cross-batch dedup key | `content_hash` — MD5 of (input + output) |
| Generation model | `gpt-4.1-mini` (682,575 entries); `human_annotated` (8,476 thesis baseline) |
| Languages | Python (Qiskit), OpenQASM 3.0 |
| Splits | train 604,666 (87.5%) / val 74,837 (10.8%) / test 11,548 (1.7%) |
| HuggingFace repo | `Elias-Abebe-Gasparini/PQID` |

**Split breakdown by quality flag (Cell 31 output):**

| quality_flag | count |
|-------------|-------|
| new_scraped | 551,432 |
| paraphrased (thesis baseline) | 8,476 |
| rescraped | ~50,000 (approx) |
| rescued | ~30,000 (approx) |
| revlib | ~50,000 (approx) |
| clean | ~1,143 (original cleaned) |

---

## 2. Repository & File Structure

```
PQID/
├── PIPELINE.md                          ← this file
├── data/
│   └── processed/                       ← all active JSONL files
│       ├── train_clean.jsonl            604,666 entries
│       ├── validation_clean.jsonl       74,837 entries
│       ├── test_clean.jsonl             11,548 entries (hold-out)
│       ├── train_validated.jsonl        [pending split_validated.py]
│       ├── validation_validated.jsonl   [pending]
│       ├── test_validated.jsonl         [pending]
│       ├── community_unvalidated.jsonl  [pending — Tier 2 HF challenge]
│       ├── circuit_family_cache.jsonl   [resume-safe GPT cache]
│       ├── repo_license_cache.jsonl     [resume-safe license cache]
│       ├── leakage_report.txt           [pending check_leakage.py]
│       └── paraphrase_diversity_report.txt [pending compute_paraphrase_diversity.py]
│   └── hf_download/                     ← original HF baseline (read-only)
│       ├── train.jsonl                  9,645 entries
│       └── validation.jsonl             1,073 entries
├── scripts/
│   ├── 01_acquisition/                  circuit scraping utilities (legacy)
│   ├── 02_translation_and_validation/   exec-based validation (legacy)
│   ├── 03_instruction_generation/       seed + paraphrase generation
│   │   └── instruction_generation_pipeline.ipynb   ← MASTER NOTEBOOK
│   ├── 04_metadata_analysis/            metadata design + diversity + consistency analysis
│   ├── scrape_github_unified.py         unified GitHub circuit scraper
│   ├── enrich_metadata.py               Qiskit exec + full metadata (Python 3.11)
│   ├── enrich_circuit_family.py         GPT-4.1-mini circuit family classifier
│   ├── enrich_repo_license.py           GitHub license enrichment
│   ├── merge_and_split.py               merge seeds+paraphrases → train/val/test
│   ├── split_validated.py               Tier 1 / Tier 2 partition
│   ├── preprocess_hf_baseline.py        HF baseline → PQID schema conversion
│   ├── check_leakage.py                 cross-split leakage verification
│   └── compute_paraphrase_diversity.py  pairwise BLEU-4 + TTR diversity report
└── legacy_github/                       full clone of original GitHub repo
```

---

## 3. Python Environment

**CRITICAL**: Qiskit scripts MUST run under Python 3.11, not the system default.

Use a Python 3.11 interpreter available on your machine, for example from a
virtual environment or a local Python 3.11 installation.

The master notebook's Cell 1 defines `run_script()` via `subprocess.Popen` pointing at this binary. Never run `enrich_metadata.py` with Python 3.13/3.14 — Qiskit is not installed there and will fail silently or with import errors.

Scripts that require Python 3.11:
- `enrich_metadata.py`

Scripts that run on any Python (no Qiskit):
- `scrape_github_unified.py`, `generate_seeds.py`, `generate_paraphrases.py`
- `merge_and_split.py`, `enrich_circuit_family.py`, `enrich_repo_license.py`
- `split_validated.py`, `check_leakage.py`, `compute_paraphrase_diversity.py`
- `preprocess_hf_baseline.py`

---

## 4. Pipeline Stages

### Stage 0 — Thesis Baseline (HF Dataset)

**Source**: `Elias-Abebe-Gasparini/PQID` on HuggingFace (uploaded 2026-03-26)
**Contents**: 10,718 entries from the original MS thesis work (pre-PQID schema)
**Status**: Preprocessed → 9,134 entries (1,584 dropped for quality)

The HF dataset used the old thesis schema (`input`, `output`, `metadata` with limited fields). The baseline circuits contained:
- Non-ASCII inline comments (Japanese, Korean) causing `UnicodeEncodeError` in exec()
- Missing or inconsistent Qiskit imports
- Truncated or trivially short circuit stubs

**Script**: `preprocess_hf_baseline.py`

Processing steps:
1. Load `hf_download/train.jsonl` + `hf_download/validation.jsonl`
2. Strip all Python comments via `tokenize` module (safe for `#` inside string literals; falls back to regex on `TokenError`/`IndentationError`)
3. Prepend standard Qiskit import block if not already present
4. Assign `circuit_hash` (MD5 of stripped code) and `content_hash` (MD5 of input+output)
5. Normalise to PQID metadata schema (all enrich fields initialised to `None`)
6. Quality filter: ≥4 tokens, ≥2 non-empty lines, must contain `QuantumCircuit`
7. Deduplicate by `content_hash`
8. Write `train_clean.jsonl` and `validation_clean.jsonl`

**Result**: 8,243 train + 891 validation = 9,134 entries; 1,135 comment-stripped entries

**Standard imports block** prepended when missing:
```python
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit import Parameter, ParameterVector
from qiskit.circuit.library import (
    QFT, GroverOperator, PhaseEstimation, HGate, XGate, ZGate,
    RZGate, RYGate, RXGate, CXGate, CCXGate, SwapGate,
    EfficientSU2, TwoLocal, RealAmplitudes, PauliTwoDesign,
)
import numpy as np
from numpy import pi
```

**RevLib circuits — design decision:**
The full RevLib `.tgz` archive is available locally and the extraction script (`01_acquisition/revlib_tgz_dataset_extraction.py`) is intact. However, re-extraction was deliberately skipped for the following reasons:

1. **Size problem**: RevLib benchmarks are designed for reversible Boolean circuit synthesis. Many contain thousands to millions of Toffoli gates, producing a raw JSONL output exceeding 2 GB — too large to store, version, or process efficiently.
2. **Validation failure rate**: Circuits of this size universally time out in `enrich_metadata.py`'s 3-second exec sandbox, making them Tier 2 entries regardless. They contribute little to the validated benchmark.
3. **Low instruction diversity**: RevLib circuits share a restricted gate vocabulary (Toffoli, CNOT, NOT) and implement reversible Boolean functions. The GitHub API scraping provides far more varied and pedagogically representative Qiskit circuits.
4. **Baseline already preserved**: The RevLib circuits that survived the original thesis filtering (size-bounded, validated) are already present in the HF baseline and carried forward into `train_clean.jsonl` / `validation_clean.jsonl` via `preprocess_hf_baseline.py`. Their `source` field retains the original `"revlib"` provenance.

**Consequence for schema**: The fields `filename` (original `.real` benchmark filename) and `revlib_url` (direct URL to the `.real` source file on the RevLib server) are present in legacy RevLib entries via the HF baseline metadata passthrough. New entries do not add RevLib-specific fields; these remain `null` for all GitHub-sourced circuits.

---

### Stage 1 — Batch 1: Original Circuits

**Source**: Curated list of GitHub repos in `github_source_repositories.txt`, local clones in `quantum_repos/`, plus RevLib `.tgz` archive

**Scripts (legacy — in `01_acquisition/` and `02_translation_and_validation/`)**:
- `extract_circuits_from_repos.py` — walks local `quantum_repos/`, extracts `QuantumCircuit` blocks from `.py` and `.ipynb` files
- `revlib_tgz_dataset_extraction.py` — extracts circuits from RevLib archive
- `unified_clean_circuits.py` — exec() + transpile validation, dedup by hash
- `datasets_harmonisation.py` — normalises revlib + github to common schema

**Master notebook cells**: 2–8

| Cell | Script | Result |
|------|--------|--------|
| 2 | `generate_seeds_pending.py` | 2,298 seeds from `circuits_pending_instructions.jsonl` |
| 3 | *(check seeds)* | — |
| 4 | `generate_paraphrases_pending.py` | 11,490 paraphrases |
| 5 | *(check paraphrases)* | — |
| 6 | `merge_new_entries.py` | 22,264 entries (train 17,946 / val 4,318) |
| 7 | *(summary after Batch 1)* | — |
| 8 | `enrich_metadata.py` | First partial enrichment (Batch 1 only; 59.8% validated) |

---

### Stage 2 — Batch 2: GitHub Expansion

**Source**: GitHub Code Search API + GitHub Contents API

| Cell | Script | Result |
|------|--------|--------|
| 9  | `scrape_github_expansion.py` | Batch 2 circuit scraping |
| 10 | `generate_seeds_expansion.py` | Seeds from `circuits_expansion.jsonl` |
| 11 | *(check)* | — |
| 12 | `generate_paraphrases_expansion.py` | Paraphrases |
| 13 | *(check)* | — |
| 14 | `merge_expansion_entries.py` | Merged into train/val_clean |
| 15 | *(summary after Batch 2)* | — |

---

### Stage 3 — Batch 3: Qiskit Official + Extra Queries

**Source**: Qiskit official repos + additional code search queries

| Cell | Script | Result |
|------|--------|--------|
| 16 | `scrape_github_expansion_v2.py` | Batch 3 scraping |
| 17 | `generate_seeds_expansion_v2.py` | 7,810 seeds / 0 errors / ~$4.39 / 23 min |
| 18 | *(check)* | — |
| 19 | `generate_paraphrases_expansion_v2.py` | 39,050 paraphrases / 3 errors |
| 20 | *(check)* | — |
| 21 | `merge_expansion_v2_entries.py` | +46,626 entries merged |
| 22 | *(summary after Batch 3)* | Train 95,055 / Val 30,964 / Total 126,019 |

---

### Stage 4 — Batch 4: Topics API + Org Scraping + New Queries

**Source**: GitHub Topics API (9 quantum topics) + org repos (Qiskit, qiskit-community) + additional code search queries

| Cell | Script | Result |
|------|--------|--------|
| 23 | `scrape_github_expansion_v3.py` | **DONE** — 94,321 circuits / 47,483 files / 17,458s |
| 24 | `generate_seeds_expansion_v3.py` | **DONE** — seeds_expansion_v3.jsonl |
| 25 | *(check seeds)* | — |
| 26 | `generate_paraphrases_expansion_v3.py` | **DONE** — paraphrases_expansion_v3.jsonl |
| 27 | *(check paraphrases)* | — |
| 28 | `merge_expansion_v3_entries.py` | **DONE** — 691,051 total entries |
| 29 | *(summary after Batch 4)* | train 604,666 / val 74,837 → split_test → +test 11,548 |

---

### Stage 5 — Final Enrichment & Splitting

| Cell | Script | Purpose | Status |
|------|--------|---------|--------|
| 30 | `enrich_repo_topics.py` | GitHub repo topics + `is_org_repo` flag | **DONE** |
| 31 | `split_test.py` | Carve 10% of val → test (circuit-aware) | **DONE** |
| 32 | `patch_metadata.py` | XAI backfill: generation_model, generation_date, paraphrase_source | **DONE** |
| 33 | `enrich_metadata.py` | Qiskit exec + all metadata fields (full 691K) | **RE-RUN REQUIRED** |
| 34 | `enrich_circuit_family.py` | GPT-4.1-mini circuit_family + semantic_intent | pending Cell 33 |
| 35 | `split_validated.py` | Tier 1 / Tier 2 partition | pending Cell 34 |
| — | `enrich_repo_license.py` | SPDX license per repo → repo_license, license_category | after Cell 35 |
| — | `enrich_semantic_consistency.py` | Per-entry semantic similarity, BERTScore, BLEU-4, ROUGE-L, edit distance vs seed | after Cell 35 |
| — | `check_leakage.py` | Verify no hash overlap across splits | run any time |
| — | `compute_paraphrase_diversity.py` | Pairwise BLEU-4 + TTR diversity report (10K sample) | run any time |

Execution note for the rebuilt quality-aware corpus:

- `enrich_semantic_consistency.py` should now be treated as a **two-pass
  semantic-analysis step**
- first pass:
  - local chunked CPU-safe run
  - computes the lighter semantic metrics and leaves `bert_score_f1` null
- second pass:
  - GPU-backed backfill of `bert_score_f1`
  - preferred current target: Google Cloud
- detailed operational note:
  - `PQID/GCP_BERT_BACKFILL_STRATEGY.md`

---

## 5. Master Notebook Cell Map (40 cells)

| Cell | Type | Description |
|------|------|-------------|
| 1 | Setup | `run_script()` helper, API key load, BASE path definition |
| 2 | Script | `generate_seeds_pending.py` |
| 3 | Check | Inspect seeds output |
| 4 | Script | `generate_paraphrases_pending.py` |
| 5 | Check | Inspect paraphrases output |
| 6 | Script | `merge_new_entries.py` |
| 7 | Summary | Batch 1 stats |
| 8 | Script | `enrich_metadata.py` (Batch 1 pass) |
| 9 | Script | `scrape_github_expansion.py` |
| 10 | Script | `generate_seeds_expansion.py` |
| 11 | Check | — |
| 12 | Script | `generate_paraphrases_expansion.py` |
| 13 | Check | — |
| 14 | Script | `merge_expansion_entries.py` |
| 15 | Summary | Batch 2 stats |
| 16 | Script | `scrape_github_expansion_v2.py` |
| 17 | Script | `generate_seeds_expansion_v2.py` |
| 18 | Check | — |
| 19 | Script | `generate_paraphrases_expansion_v2.py` |
| 20 | Check | — |
| 21 | Script | `merge_expansion_v2_entries.py` |
| 22 | Summary | Batch 3 stats |
| 23 | Script | `scrape_github_expansion_v3.py` |
| 24 | Script | `generate_seeds_expansion_v3.py` |
| 25 | Check | — |
| 26 | Script | `generate_paraphrases_expansion_v3.py` |
| 27 | Check | — |
| 28 | Script | `merge_expansion_v3_entries.py` |
| 29 | Summary | Batch 4 stats |
| 30 | Script | `enrich_repo_topics.py` (**DONE**) |
| 31 | Script | `split_test.py` (**DONE**) |
| 32 | Script | `patch_metadata.py` (**DONE**) |
| 33 | Script | `enrich_metadata.py` — full 691K run (**RE-RUN REQUIRED**) |
| 34 | Script | `enrich_circuit_family.py` (pending) |
| 35 | Script | `split_validated.py` (pending) |
| 36 | Script | `enrich_repo_license.py` (pending) |
| 37 | Script | `check_leakage.py` |
| 38 | Script | `compute_paraphrase_diversity.py` |
| 39 | Check | Final dataset statistics |
| 40 | Export | HuggingFace upload preparation |

---

## 6. Script Reference

### scrape_github_unified.py
Unified GitHub circuit scraper replacing all Batch 2–4 individual scrapers.
Four parallel strategies via GitHub REST API (no local cloning):
1. **Curated repos** — Contents API walk of repos listed in `github_urls.txt`
2. **Code Search** — core + extended Qiskit-targeted query sets (63 queries in the current notebook build)
3. **Org repos** — Enumerate all repos from `Qiskit` and `qiskit-community` orgs
4. **Topic repos** — core + extended GitHub topics spanning qiskit, algorithms, simulation, error correction, and quantum machine learning

Dedup: MD5 of stripped code; processed URLs cached in `circuits_unified_processed.txt`.
Baseline output: `circuits_unified.jsonl`

**Optional append-only Phase 2 (aggressive rescrape)**:
- Adds notebook cells after the original summary cell so the baseline acquisition remains frozen
- Writes aggressive-only output to `circuits_unified_aggressive.jsonl`
- Merges baseline + aggressive pools into `circuits_unified_plus_aggressive.jsonl`
- Writes / backfills `metadata.retrieval_mode`, `metadata.retrieval_strategy`, and `metadata.retrieval_run_id` so downstream stages can audit which acquisition campaign produced each circuit

**Optional append-only Phase 3 (high-yield recall expansion)**:
- Keeps the baseline and Phase 2 acquisition logic unchanged
- Writes Phase 3-only output to `circuits_unified_phase3.jsonl`
- Merges baseline + Phase 2 + Phase 3 into `circuits_unified_plus_phase2_plus_phase3.jsonl`
- Was used as a final recall-expansion campaign focused on trusted saturation checks, targeted search blind spots, and a small optional gist pass
- Empirically showed that the remaining useful yield came from targeted search patterns rather than additional trusted repo re-sweeps

### enrich_raw_circuits.py
Backfills raw-circuit metadata before seed generation so structural features can act as prompt anchors.
- Default input: `circuits_unified.jsonl`
- Default output: `circuits_unified_enriched.jsonl`
- Cache-aware and safe to rerun after schema expansion because incomplete cache records are automatically recomputed
- Adds lightweight extraction-quality diagnostics such as `extraction_confidence`, `contains_demo_scaffolding`, `cleanup_candidate`, and `cleanup_rules_triggered` without modifying the raw scraped code
- Recommended to run on `circuits_unified_plus_aggressive.jsonl` after the optional aggressive phase, producing `circuits_unified_plus_aggressive_enriched.jsonl`

### report_extraction_quality.py
Optional pre-seed audit pass for inspecting extraction quality on the enriched raw pool.
- Default input: `circuits_unified_enriched.jsonl`
- Default outputs: `extraction_quality_report.md` and `extraction_quality_samples.jsonl`
- Read-only with respect to dataset entries: it summarizes the enriched pool and writes deterministic sample subsets for manual inspection
- Useful for checking whether low-confidence entries or cleanup candidates should be studied further before seed generation

### generate_seeds.py / generate_seeds_pending.py / generate_seeds_expansion*.py
Generates one natural-language instruction per circuit using `gpt-4.1-mini`.
- BATCH_SIZE: 30 concurrent requests
- MAX_TOKENS: 150
- System prompt: "You are a quantum computing assistant. Given a quantum circuit implementation in Qiskit (Python) or OpenQASM 3.0, write a single concise English instruction (one sentence, under 40 words)..."
- Resume-safe by `circuit_hash`
- Can incorporate precomputed structural metadata as prompt anchors when present
- Adds `content_hash`, `prompt_word_count`, `prompt_length_chars`, and `prompt_token_count_cl100k` to metadata
- Input file defaults to the richest available raw pool in this order: `circuits_unified_plus_phase2_plus_phase3_enriched.jsonl`, `circuits_unified_plus_phase2_plus_phase3.jsonl`, `circuits_unified_plus_aggressive_enriched.jsonl`, `circuits_unified_plus_aggressive.jsonl`, `circuits_unified_enriched.jsonl`, then `circuits_unified.jsonl`

### generate_paraphrases.py / generate_paraphrases_pending.py / generate_paraphrases_expansion*.py
Generates 5 paraphrased instructions per seed using `gpt-4.1-mini`.
- NUM_PARAPHRASES: 5
- BATCH_SIZE: 30 concurrent requests
- MAX_TOKENS: 600
- Prompt: "Generate {n} different paraphrased versions... output one paraphrase per line, no numbering"
- Stores `paraphrase_source` (circuit_hash of seed) and `original_prompt` in each paraphrase metadata

### generate_paraphrases_quality_aware.py
Generates lineage-preserving paraphrases from quality-aware seed instructions using the Responses API.
- Default input: `seed_drafts_quality_aware_source_code_v1.jsonl` when present, otherwise the smaller quality-aware seed draft file
- Default output: `seed_paraphrases_quality_aware_source_code_v1.jsonl`
- Default model: `gpt-5.4-mini`
- Default temperature: `0.2`
- NUM_PARAPHRASES: 5
- Resume-safe at the source-seed level through `paraphrase_source_content_hash`
- Preserves seed role metadata and adds paraphrase provenance fields such as `paraphrase_template_version`, `paraphrase_generation_temperature`, and `paraphrase_variant_index`
- Supports explicit prompt modes such as `standard` and `anti_template` so the final residual tail can be repaired without redefining the main production temperature
- The notebook now runs this script separately for the `source_code` and `teacher_text` seed artifacts so the whole routed corpus can be paraphrase-expanded without collapsing the two supervision modes into one opaque file

### prepare_seed_drafts_quality_aware_batch.py
Builds Batch API request JSONL for quality-aware seed generation.
- Reuses the same prompt builders and temperature settings as `generate_seed_drafts_quality_aware.py`
- Supports both `source_code` and `teacher_text` manifests
- Intended for full-corpus production runs after pilot settings are frozen

### materialize_seed_drafts_quality_aware_batch.py
Converts downloaded Batch API seed responses into the standard PQID seed artifact.
- Uses the same output-entry logic as the synchronous generator
- Writes the normal PQID seed JSONL plus a compatible error log

### prepare_paraphrases_quality_aware_batch.py
Builds Batch API request JSONL for quality-aware paraphrase expansion.
- Reuses the same paraphrase prompt builder and branch-preserving lineage logic as the synchronous paraphrase stage
- Supports resume-aware paraphrase-slot filling by checking existing paraphrase artifacts
- For documented residual closure, can forward prompt-mode switches such as `anti_template` into the batch request body

### materialize_paraphrases_quality_aware_batch.py
Converts downloaded Batch API paraphrase responses into the standard PQID paraphrase artifact.
- Preserves `paraphrase_variant_index`
- Keeps branch-specific seed-role lineage intact
- Preserves repair-stage provenance such as the actual paraphrase-generation temperature and prompt mode used for the finalized row

### run_openai_batch_job.py
Uploads a Batch API request file, creates or inspects a batch job, and optionally downloads output/error files.
- Used by the quality-aware notebook for full-production source-code seeds, teacher-text seeds, and paraphrase expansion
- Changes orchestration and cost only; does not change the underlying pedagogical prompt contract

### merge_and_split.py
Merges `seeds.jsonl` + `paraphrases.jsonl` → canonical train/val/test splits.
- Circuit-aware split: all instructions for a given circuit land in the same split
- Split assignment: last hex digit of `circuit_hash` → 0-7=train (80%), 8=val (10%), 9=test (10%)
- Content-level dedup: entries with identical `content_hash` are dropped
- Deterministic shuffle within each split (seed=42)

### enrich_metadata.py (Python 3.11 required)
Executes each circuit in a sandboxed namespace and extracts all Qiskit metrics.
- Timeout: 3.0s per circuit (daemon thread + join)
- Namespace: n=3 qubits; includes np, pi, math, all Qiskit core, ~40 common aliases for qubit counts, angles, registers, circuits
- **No per-entry resume safety** — holds all entries in RAM, writes atomically at end via tmp rename
- Processes all splits present in `data/processed/`
- Transpilation basis: `["cx", "rz", "sx", "x"]`, optimization_level=1, no coupling map

**Circuit selection heuristic** (when multiple QuantumCircuits found in namespace):
Score = `num_qubits * max(depth, 1)` → select highest; last circuit wins on ties (typically the final assembled circuit).

### enrich_circuit_family.py
GPT-4.1-mini classifier for circuit family and semantic intent.
- BATCH_SIZE: 40 concurrent requests
- Classifies by unique `circuit_hash` (not per entry)
- Resume-safe via `circuit_family_cache.jsonl`
- Uses `response_format={"type": "json_object"}`
- Patches `*_clean.jsonl` files in-place after all circuits classified

### enrich_repo_license.py
Fetches SPDX license identifier per GitHub repository.
- Resume-safe via `repo_license_cache.jsonl`
- Patches `repo_license` and `license_category` in all `*_clean.jsonl` files
- Run after `split_validated.py`

### split_validated.py
Partitions each `*_clean.jsonl` into Tier 1 and Tier 2.
- Tier 1: `validation_status == "validated"` → `*_validated.jsonl`
- Tier 2: all other statuses → `community_unvalidated.jsonl` (merged across all splits)
- Reads from `*_clean.jsonl` files, NOT from `*_validated.jsonl` — run it last

### filter_benchmark_and_tier2.py
Derives benchmark-oriented views from an enriched broad raw pool and records transparent readiness metadata. In the current workflow these exports are no longer the default instruction-generation input; they are late-stage benchmark and release derivations built on top of the frozen master corpus.
- Annotates each entry with transparent benchmark-suitability metadata:
  - `benchmark_profile_version`
  - `benchmark_checks_total`
  - `benchmark_checks_passed`
  - `benchmark_checks_ratio`
  - `benchmark_passed_checks`
  - `benchmark_failed_checks`
  - `benchmark_suitability_tier`
- Uses an explicit check-count profile rather than informal release labels
- Current suitability checks include validated execution, extraction cleanliness, minimum code size, minimum gate count, and retrieval-strategy trust
- Can optionally include validated high-confidence `empirical_promoted_repo` entries in the core set via `--include-empirical-in-core`

### preprocess_hf_baseline.py
Converts HF baseline dataset to PQID-compatible schema.
- Comment stripping via `tokenize` module; fallback to regex on failure
- Prepends standard Qiskit imports if not present
- Quality filter: ≥4 tokens, ≥2 lines, must contain `QuantumCircuit`
- All enrich fields initialised to `None`

### check_leakage.py
Verifies zero overlap of `circuit_hash` and `content_hash` across train/val/test splits.
No Qiskit required; run any time.

### compute_paraphrase_diversity.py
Pairwise BLEU-4 and Type-Token Ratio (TTR) across paraphrase groups.
Samples 10,000 circuit groups; no Qiskit required; run any time.

### Why This Execution Order Was Chosen
The script order is not arbitrary. It is chosen by a combination of **hard data dependencies** and **compute-efficiency / reproducibility considerations**.

- `enrich_raw_circuits.py` runs before seed generation because a small subset of circuit-derived metadata is useful as prompt-generation anchors and can be computed directly from the raw circuit pool.
- `report_extraction_quality.py` is optional but recommended immediately after raw enrichment when you want a documented inspection pass before prompt generation. It stays read-only so the provenance-preserving raw scrape artifact is not altered.
- `filter_benchmark_and_tier2.py` computes the per-entry benchmark-suitability profile and lets the project distinguish a strict evaluation core from a broader validated reserve and a repair-oriented Tier 2 pool. In the current rebuild, this logic feeds late-stage benchmark and release derivation rather than serving as the default upstream object for seed generation.
- `generate_seeds.py` must run before `generate_paraphrases.py` because paraphrases depend on an existing seed instruction.
- `merge_and_split.py` runs before the late-stage enrichments because it creates the canonical train / validation / test artifacts. Running expensive enrichments only after this point avoids repeatedly patching transient pre-split files.
- `enrich_metadata.py` is intentionally late because full Qiskit execution, metric extraction, and transpilation are among the most computationally expensive steps. Performing this pass on the canonical split files reduces wasted work and ensures the reported metrics correspond exactly to the released dataset artifacts.
- `enrich_repo_topics.py`, `enrich_repo_license.py`, and `enrich_circuit_family.py` now run on the full broad pool and the master processable corpus before seed generation. This keeps the metadata layer attached to the working corpus itself so that later benchmark, release, and training artifacts can all be reconstructed from the same processed records.
- `enrich_semantic_consistency.py` is the one late-stage enrichment that truly depends on instruction generation, because it compares each paraphrase against its seed prompt via `original_prompt`.

In short, the execution order is **dependency-aware first**, then **resource-efficient**, with the additional goal that each expensive enrichment is applied to the smallest stable artifact that will actually be released.

---

## 7. Metadata Schema

Every entry is a **triple parallel representation**:
```json
{
  "input":          "string — natural-language instruction",
  "output":         "string — Qiskit Python code",
  "openqasm3_code": "string | null — OpenQASM 3.0 export",
  "metadata":       { "...": "..." }
}
```
`openqasm3_code` is a top-level field (not inside metadata), populated by `enrich_metadata.py` via `qiskit.qasm3.dumps(qc)`. It is `null` for non-validated entries or when the export raises an exception. See also `metadata.openqasm3_export_successful`.

### 7.1 Provenance Fields (always present)

| Field | Type | Description |
|-------|------|-------------|
| `original_url` | str | GitHub URL of source file |
| `file_path` | str | File path within the repository |
| `source` | str | Fine-grained acquisition source tag or upstream dataset identifier (e.g. `curated`, `search`, `org`, `topic`, `promoted_repo_v2`, `search_v2`, `hf_baseline`, `revlib`) |
| `language` | str | `"python"` or `"jupyter"` |
| `circuit_hash` | str | MD5 of stripped output code — primary dedup key |
| `content_hash` | str | MD5 of (input + output) — cross-batch dedup key |
| `hash` | str | GitHub blob SHA of the source file — version traceability (null for RevLib/HF) |
| `start_line` | int\|null | Starting line number of the extracted circuit block in the source file (null for notebooks/RevLib/HF) |
| `end_line` | int\|null | Ending line number of the extracted circuit block in the source file (null for notebooks/RevLib/HF) |
| `github_anchor` | str | URL fragment pointing to the highlighted code lines (e.g. `https://github.com/org/repo/blob/main/file.py#L42-L80`); equals `original_url` when line numbers unavailable |
| `repo_owner` | str\|null | GitHub owner (user or organisation) of the source repository |
| `repo_name` | str\|null | GitHub repository name |
| `scrape_date` | str\|null | ISO date the file was scraped |
| `code_lines` | int | Number of non-empty lines in the extracted circuit code |
| `output_token_count_cl100k` | int\|null | Token count of the circuit code (`output`) under `cl100k_base`; useful for context-budgeting and training-cost analysis |
| `retrieval_mode` | str\|null | High-level acquisition mode: `"baseline"` or `"aggressive"`; may be null in older artifacts unless backfilled during merge |
| `retrieval_strategy` | str\|null | Specific strategy within the mode, such as `curated`, `search`, `org`, `topic`, `promoted_repo`, or `expanded_search` |
| `retrieval_run_id` | str\|null | Deterministic identifier for the acquisition campaign or merge backfill, used for exact reproducibility |

`source`, `quality_flag`, and the `retrieval_*` fields are intentionally different:
- `source` records the immediate scrape route or upstream dataset label
- `quality_flag` records the downstream provenance / curation tier
- `retrieval_mode`, `retrieval_strategy`, and `retrieval_run_id` distinguish baseline vs aggressive acquisition campaigns

### 7.2 Instruction Generation Fields (always present)

| Field | Type | Description |
|-------|------|-------------|
| `prompt_type` | str | Legacy values: `"seed"` or `"paraphrased"`; rebuild values: `"base_seed_quality_aware"` or `"paraphrased_quality_aware"`. A small number of transition artifacts may still contain the deprecated alias `"human_seed_quality_aware"` before normalization. |
| `quality_flag` | str | `"clean"` \| `"new_scraped"` \| `"rescraped"` \| `"rescued"` \| `"revlib"` \| `"hf_baseline"` |
| `generation_model` | str | `"gpt-4.1-mini"` (682,575 entries) or `"human_annotated"` (8,476 entries) |
| `generation_date` | str | ISO date string of generation |
| `paraphrase_source` | str | `circuit_hash` of the seed this paraphrase was generated from |
| `original_prompt` | str | The seed instruction text (for paraphrases) |
| `prompt_word_count` | int | Word count of the input instruction |
| `prompt_length_chars` | int | Character count of the input instruction |
| `prompt_token_count_cl100k` | int\|null | Token count of the input instruction under `cl100k_base` |

### 7.3 Repo Context Fields (added by enrich_repo_topics.py)

| Field | Type | Description |
|-------|------|-------------|
| `repo_topics` | list[str] | GitHub topic tags on the source repository |
| `is_org_repo` | bool | Whether the source repo belongs to an organisation |

### 7.4 Execution / Validation Fields (added by enrich_metadata.py)

| Field | Type | Description |
|-------|------|-------------|
| `validation_status` | str | `"validated"` \| `"timeout"` \| `"no_circuit"` \| `"import_error"` \| `"name_error"` \| `"syntax_error"` \| `"exec_error"` |
| `validation_error_type` | str | Python exception class name, or `""` for validated/no_circuit |
| `circuit_stats_available` | bool | `True` iff a QuantumCircuit was successfully extracted |
| `openqasm3_export_successful` | bool\|null | `True` if `qiskit.qasm3.dumps(qc)` completed without error; `null` for non-validated entries |
| `openqasm3_export_error` | str\|null | Exception class name if export failed; `null` otherwise |
| `extraction_confidence` | str\|null | Heuristic confidence that the extracted block primarily represents circuit-construction logic rather than surrounding tutorial/demo scaffolding (`high`, `medium`, `low`) |
| `contains_demo_scaffolding` | bool\|null | Whether the extracted block contains likely non-essential tutorial/demo statements such as `print`, `display`, plotting, `.draw`, backend execution, or result inspection |
| `cleanup_candidate` | bool\|null | Whether demo scaffolding is present but the block still contains clear circuit-construction signals, making it a candidate for a future derived cleaned-generation view |
| `cleanup_rules_triggered` | list[str]\|null | Names of heuristic extraction-quality rules that fired, such as `print_call`, `draw_call`, or `backend_run` |

**Validation status semantics:**
- `validated` — executed within 3s; QuantumCircuit found in namespace
- `timeout` — exceeded 3.0s execution limit
- `no_circuit` — executed successfully but no QuantumCircuit found
- `import_error` — `ImportError` or `ModuleNotFoundError`
- `name_error` — `NameError` (unresolved dependency or variable)
- `syntax_error` — `SyntaxError` in circuit code
- `exec_error` — any other runtime exception

### 7.5 Core Circuit Metrics (added by enrich_metadata.py, circuit_stats_available=True)

| Field | Type | Description |
|-------|------|-------------|
| `num_qubits` | int | Number of quantum bits |
| `num_clbits` | int | Number of classical bits |
| `quantum_register_count` | int\|null | Number of quantum registers |
| `gate_count` | int | Total gate operations (`qc.size()`) |
| `circuit_depth` | int | Circuit depth (`qc.depth()`) |
| `circuit_width` | int | Total qubits + clbits (`qc.width()`) |
| `gate_types` | dict | `{gate_name: count}` for each gate used |
| `num_gate_types` | int | Number of distinct gate types |
| `avg_gates_per_layer` | float | `gate_count / circuit_depth` |
| `has_measurement` | bool | Whether circuit contains measurement operations |
| `is_parameterized` | bool | Whether circuit has free `Parameter` objects |
| `multi_qubit_gate_count` | int\|null | Count of gate operations acting on three or more qubits |
| `has_control_flow` | bool\|null | Whether the circuit contains Qiskit control-flow operations |
| `control_flow_op_count` | int\|null | Number of control-flow operations in the circuit |
| `t_count` | int | Total T + Tdg gate count |
| `t_depth` | int\|null | Depth counting only T/Tdg gates |

### 7.6 XAI Complexity Indicators (added by enrich_metadata.py)

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `circuit_expressiveness` | str | `clifford` \| `universal` \| `parameterized` | Expressiveness class |
| `size_class` | str | `trivial` \| `simple` \| `moderate` \| `complex` \| `very_complex` | Complexity class |
| `benchmark_difficulty` | str | `easy` \| `medium` \| `hard` | Composite difficulty score |

**circuit_expressiveness classification:**
- `parameterized` — has free `Parameter` objects (highest expressiveness)
- `universal` — no free parameters but contains T, Tdg, or continuous rotation gates
- `clifford` — only Clifford gates (H, CNOT, S, X, Y, Z, SWAP, etc.)

**size_class thresholds** (max across three independent dimensions):

| Level | Dimension | Qubits | Depth | Gates |
|-------|-----------|--------|-------|-------|
| trivial (0) | — | ≤2 | ≤2 | ≤3 |
| simple (1) | — | 3–5 | 3–10 | 4–20 |
| moderate (2) | — | 6–10 | 11–30 | 21–60 |
| complex (3) | — | 11–20 | 31–80 | 61–200 |
| very_complex (4) | — | ≥21 | ≥81 | ≥201 |

**benchmark_difficulty composite score:**

| Component | Source | Max contribution |
|-----------|--------|-----------------|
| size_score | 0=trivial → 4=very_complex (mapped) | 4 |
| expr_score | clifford=0, universal=1, parameterized=2 | 2 |
| ent_score | 0 if ratio=0, 1 if ratio<0.3, 2 if ratio≥0.3 | 2 |
| param_score | 0 if none, 1 if ≤5, 2 if >5 | 2 |

Total range: 0–10. Thresholds: **easy** ≤3 / **medium** 4–7 / **hard** ≥8

### 7.7 Entanglement Features (added by enrich_metadata.py)

| Field | Type | Description |
|-------|------|-------------|
| `two_qubit_gate_count` | int | Count of 2-qubit gates (CX, CZ, SWAP, etc.) |
| `entangling_gate_ratio` | float | `two_qubit_gate_count / gate_count` |

### 7.8 Parameterization Features (added by enrich_metadata.py)

| Field | Type | Description |
|-------|------|-------------|
| `num_parameters` | int | Number of free `Parameter` objects |
| `parameter_density` | float | `num_parameters / gate_count` |
| `parameter_reuse` | bool | Whether any parameter appears more than once |

### 7.9 Measurement / Output Structure (added by enrich_metadata.py)

| Field | Type | Description |
|-------|------|-------------|
| `measurement_count` | int | Number of measurement operations |
| `measured_qubit_count` | int\|null | Number of distinct qubits measured at least once |
| `reset_usage` | bool | Whether circuit uses `reset` operations |
| `mid_circuit_measurement` | bool | Whether measurement appears before final layer |
| `classical_register_count` | int | Number of classical registers |

### 7.10 Topology / Interaction Graph (added by enrich_metadata.py)

| Field | Type | Description |
|-------|------|-------------|
| `interaction_graph_edges` | int | Edges in qubit interaction graph |
| `graph_density` | float | Edge density of interaction graph |
| `max_qubit_degree` | int | Maximum degree of any qubit node |
| `connected_components` | int | Number of connected components |

### 7.11 Transpilation Metrics (added by enrich_metadata.py)

Basis gates: `["cx", "rz", "sx", "x"]`, optimization_level=1, no coupling map (backend-agnostic).

| Field | Type | Description |
|-------|------|-------------|
| `transpiled_depth` | int\|null | Depth after transpilation |
| `transpiled_gate_count` | int\|null | Total gates after transpilation |
| `transpiled_cx_count` | int\|null | CX gates after transpilation |
| `transpiled_single_qubit_count` | int\|null | Single-qubit gates after transpilation |
| `transpilation_overhead` | float\|null | `(transpiled_gate_count - gate_count) / gate_count` |
| `transpilation_successful` | bool | Whether transpilation completed without error |

### 7.12 License Fields (added by enrich_repo_license.py, run after split_validated)

| Field | Type | Description |
|-------|------|-------------|
| `repo_license` | str\|null | SPDX license identifier (e.g. `"MIT"`, `"Apache-2.0"`) |
| `license_category` | str\|null | `"permissive"` \| `"copyleft"` \| `"no_license"` \| `"other"` |

### 7.13 Circuit Family Fields (added by enrich_circuit_family.py)

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `circuit_family` | str | bell \| ghz \| qft \| variational \| qaoa \| teleportation \| arithmetic \| oracle \| ansatz \| phase_estimation \| error_correction \| swap_test \| grover \| other | Structural circuit family |
| `semantic_intent` | str | state_preparation \| entanglement_generation \| variational_ansatz \| algorithmic_subroutine \| arithmetic_reversible \| oracle_construction \| measurement_driven \| demonstration \| other | Semantic purpose of the circuit |

---

## 8. Data Records (Key Files)

| File | Location | Status | Entries | Notes |
|------|----------|--------|---------|-------|
| `train_clean.jsonl` | `data/processed/` | ✅ exists | 604,666 | All 4 batches |
| `validation_clean.jsonl` | `data/processed/` | ✅ exists | 74,837 | All 4 batches |
| `test_clean.jsonl` | `data/processed/` | ✅ exists | 11,548 | ⚠️ hold-out — do not use for training |
| `circuits_expansion_v3.jsonl` | `data/processed/` | ✅ exists | 94,321 | Batch 4 raw circuits |
| `train_validated.jsonl` | `data/processed/` | ⏳ pending | — | Tier 1 train (after split_validated) |
| `validation_validated.jsonl` | `data/processed/` | ⏳ pending | — | Tier 1 val |
| `test_validated.jsonl` | `data/processed/` | ⏳ pending | — | Tier 1 test |
| `community_unvalidated.jsonl` | `data/processed/` | ⏳ pending | — | Tier 2 HF annotation challenge |
| `circuit_family_cache.jsonl` | `data/processed/` | ⏳ pending | — | GPT-4.1-mini classification cache |
| `repo_license_cache.jsonl` | `data/processed/` | ⏳ pending | — | GitHub license cache |
| `leakage_report.txt` | `data/processed/` | ⏳ pending | — | Cross-split hash overlap verification |
| `paraphrase_diversity_report.txt` | `data/processed/` | ⏳ pending | — | Pairwise BLEU-4 + TTR report |
| `hf_preprocess_report.txt` | `data/processed/` | ✅ exists | — | HF baseline preprocessing stats |
| `train.jsonl` | `data/hf_download/` | ✅ read-only | 9,645 | Original HF baseline |
| `validation.jsonl` | `data/hf_download/` | ✅ read-only | 1,073 | Original HF baseline |

---

## 9. Quality Flags & Provenance

`quality_flag` is independent of `source` and the `retrieval_*` fields. It tracks dataset-quality tier after generation / curation rather than the exact raw acquisition strategy.

| quality_flag | Source | Generation model |
|-------------|--------|-----------------|
| `hf_baseline` | Original MS thesis circuits (HuggingFace) | `human_annotated` |
| `clean` | Curated repo list + local quantum_repos/ | `gpt-4.1-mini` |
| `new_scraped` | GitHub API expansion (Batches 2–4) | `gpt-4.1-mini` |
| `rescraped` | Re-fetched circuits from earlier batches | `gpt-4.1-mini` |
| `rescued` | Circuits that failed validation and were fixed | `gpt-4.1-mini` |
| `revlib` | RevLib quantum circuit archive | `gpt-4.1-mini` |

---

## 10. Split Design

### Circuit-Aware Split
All instructions generated from the same circuit (seed + all paraphrases) land in the same split. This prevents instruction-level leakage where the same circuit appears in both train and test.

### Deterministic Assignment
Split assignment by last hex digit of `circuit_hash`:
```
0–7  → train      (~80% of circuits)
8    → validation  (~10% of circuits)
9    → test        (~10% of circuits)
```

### Actual Final Split (Cell 31 output)
Due to the organic growth of the dataset and merge order:
- **train**: 604,666 entries (87.5%)
- **validation**: 74,837 entries (10.8%)
- **test**: 11,548 entries (1.7%)

The test split is intentionally tiny as a held-out benchmark; it was carved from validation in `split_test.py` (Cell 31) after all batches were merged.

---

## 11. Tier System

### 11.0 Acquisition-Time Quality Tiers (Final Phase 3 Post-Fix Checkpoint)

Before the final train / validation / test release split, PQID maintains an internal quality tiering view over the **broad enriched raw pool**. This is separate from the later `split_validated.py` Tier 1 / Tier 2 release partition.

The purpose of this intermediate tiering is to distinguish:
- a very small, ultra-conservative **strict core candidate**
- a larger **extended core candidate** suitable for benchmark construction
- the broader validated reserve
- the broad repair / challenge pool
- and, after the `n/8` extension, a separate **mutation-stress candidate** block that remains visible without being silently merged into the clean benchmark subset

Each circuit is now intended to carry a transparent **benchmark suitability profile** rather than an opaque marketing-style label. Concretely, the filtering step records how many benchmark checks a circuit satisfies, which checks it passed, which checks it failed, and the resulting suitability class.

These counts are the **corrected post-fix Phase 3 checkpoint** taken after the `materialized_circuit` rerun on **2026-04-06**.

| Internal tier | Current count | Defining rule | Intended use |
|---|---:|---|---|
| Raw broad pool | 91,719 | All merged raw entries after baseline + Phase 2 + Phase 3 merge | Full reproducible GitHub acquisition artifact |
| Broad validated materialized pool | 14,267 | `validation_status == "validated"` and `materialized_circuit == True` | Corrected executable-circuit pool |
| Broad validated non-zero-gate pool | 13,530 | `validated` and `gate_count > 0` | Cleaner broad validated headline |
| Strict core export (`n/7`) | 803 | Passes all original benchmark-suitability checks (`7/7`) | Historical highest-trust benchmark slice |
| Extended core export (`n/7`) | 11,999 | Strict core plus validated high-quality empirical entries | Historical broad benchmark-facing subset |
| Strict core export (`n/8`) | 415 | Passes all cleanliness-aware benchmark-suitability checks (`8/8`) | Clean reviewer-safe benchmark slice |
| Extended core export (`n/8`) | 734 | Cleanliness-aware benchmark subset before later balancing | Clean benchmark-facing subset |
| Strict Tier 2 remainder | 90,916 | Everything not exported by the strict-core run | Repair, review, and challenge pool |
| Extended Tier 2 remainder | 79,720 | Everything not exported by the extended-core run | Broader challenge / reserve pool |

**Interpretation**

- The **803-circuit strict core** is intentionally a hard intersection of trust filters under the original `n/7` view. It is a benchmark subset, not the only useful data in PQID.
- The **11,999-circuit extended core** is the historical broad benchmark-facing subset under the original `n/7` view, not the default downstream generation corpus.
- The **13,530-entry master processable corpus** is now the default downstream object for later instruction generation.
- The **415 / 734 cleanliness-aware benchmark views** are late-stage benchmark and release derivations under `n/8`.
- The difference between the old inflated `validated` count and the corrected broad validated pool comes from placeholder-circuit leakage that is now blocked by `materialized_circuit`.
- The broad validated pool remains useful as a reserve set even when not all entries are promoted into the benchmark core.
- Under the original `n/7` view, the large gap between the strict and extended cores is still driven primarily by the exclusion of `retrieval_strategy == "empirical_promoted_repo"` in the strict export.
- Under the cleanliness-aware `n/8` view, explicit mutation-suite control creates a separate mutation-stress block rather than hiding those entries inside the benchmark-facing subsets.

### 11.0b Phase 3 Raw Acquisition Completion Checkpoint

After the final high-yield Phase 3 campaign, the GitHub acquisition stage reached the following **raw** checkpoint on **2026-04-05**:

| Raw acquisition artifact | Count | Notes |
|---|---:|---|
| Baseline raw pool | 21,632 | Cells 1–10 original scraper flow |
| Phase 2 additions | 65,680 | Aggressive append-only expansion |
| Phase 3 additions | 4,407 | Final high-yield recall expansion |
| Final merged unique raw circuits | 91,719 | `circuits_unified_plus_phase2_plus_phase3.jsonl` |

Phase 3 strategy outcomes:

| Phase 3 strategy | Added circuits | Interpretation |
|---|---:|---|
| trusted re-sweeps | 0 | trusted repos were already saturated under the current extractor |
| expanded search v2 | 4,404 | remaining useful recall came from targeted blind-spot search patterns |
| notebook-heavy search | 0 | indexed notebook search was saturated or low-yield |
| gist | 3 | small but real incremental GitHub surface-area recovery |

**Interpretation**

- The GitHub acquisition stage should be treated as **complete** at this point.
- The final recall-expansion gains came almost entirely from targeted search over under-covered Qiskit construction idioms such as circuit-library abstractions, `QuantumCircuit.from_qasm_str`, `.to_instruction`, `.control`, and algorithm-package usage.
- The project therefore reached a practical upper-bound GitHub scrape under a documented and reproducible retrieval setup.
- The next meaningful work is no longer more scraping, but Phase-3 post-processing: enrichment, extraction audit, benchmark-suitability recomputation, and benchmark packaging.

### 11.1 Strict Core Rule (Current Notebook Cell 19 / filter_benchmark_and_tier2.py)

The current strict-core rule used to derive the gold benchmark slice is:

- `validation_status == "validated"`
- `extraction_confidence == "high"`
- `contains_demo_scaffolding == False`
- `cleanup_candidate == False`
- `code_lines >= 5`
- `gate_count >= 2`
- `retrieval_strategy != "empirical_promoted_repo"`

The last condition is the strongest precision gate. Removing only that condition increases the current core size from **803** to **11,999** exported entries, while leaving the other quality checks intact.

### 11.2 Benchmark Suitability Metrics

`filter_benchmark_and_tier2.py` now annotates each circuit with a transparent benchmark-suitability profile so that release decisions can be explained per entry. The current fields are:

| Field | Meaning |
|---|---|
| `benchmark_profile_version` | Which suitability profile and thresholds were used |
| `benchmark_checks_total` | Number of checks considered |
| `benchmark_checks_passed` | Number of checks passed |
| `benchmark_checks_ratio` | Passed / total |
| `benchmark_passed_checks` | Exact checks satisfied |
| `benchmark_failed_checks` | Exact checks not satisfied |
| `benchmark_suitability_tier` | Objective class such as `strict_core_candidate`, `extended_core_candidate`, `validated_broad_candidate`, or `tier2_unvalidated` |

Current benchmark suitability checks:

- `validated_execution`
- `high_extraction_confidence`
- `no_demo_scaffolding`
- `no_cleanup_candidate`
- `minimum_code_lines`
- `minimum_gate_count`
- `trusted_retrieval_strategy`

### Tier 1 — Validated Dataset
Entries where `validation_status == "validated"`:
- Successfully executed in sandboxed namespace within 3s
- QuantumCircuit object found and extracted
- All circuit metrics computed

Files: `train_validated.jsonl`, `validation_validated.jsonl`, `test_validated.jsonl`

**Use case**: Fine-tuning LLMs for quantum circuit generation; benchmarking code generation models.

### Tier 2 — Community Annotation Challenge
All entries with any other validation status (timeout, no_circuit, import_error, name_error, syntax_error, exec_error):
- May contain valid circuits that failed due to missing dependencies
- May contain partial circuits, stubs, or algorithm fragments
- Rich source of natural circuit variation and complexity

File: `community_unvalidated.jsonl`

**Use case**: community annotation and human evaluation. Community annotators can review and fix circuits, providing human preference signal for later repair, critique, or preference-learning experiments.

---

## 12. XAI Design Principles

Every metadata field answers a specific explainability question:

| Category | Questions answered |
|----------|--------------------|
| **Source provenance** | Where did this circuit come from? What repo? What file? |
| **License traceability** | Can this circuit be used commercially? What license applies? |
| **Repo context** | Is this from an org? What topics does the repo cover? |
| **Generation provenance** | What model generated this instruction? When? Is it a seed or paraphrase? |
| **Execution accountability** | Did the circuit execute successfully? If not, why? |
| **Circuit structure** | How large is this circuit? How deep? How many qubits? |
| **Expressiveness** | Is this Clifford-only, universal, or parameterized? |
| **Entanglement** | How entangled is this circuit? What fraction are 2-qubit gates? |
| **Parameterization** | Does this circuit have free parameters? How many? Are they reused? |
| **Classical interaction** | Does the circuit measure mid-circuit? Use classical feedback? |
| **Topology** | What is the qubit connectivity graph? Are there isolated qubits? |
| **Hardware cost** | What is the transpiled CX count and depth for standard basis gates? |
| **Classification** | What algorithm family does this circuit implement? What is its purpose? |

---

## 13. API Keys & Tokens

| Service | Preferred secret source |
|---------|--------------------------|
| OpenAI (gpt-4.1-mini) | `OPENAI_API_KEY` or a local untracked `.openai_api_key` file |
| GitHub (scraping + license) | `GITHUB_TOKEN` or a local untracked `.github_token` file |

---

## 14. Critical Conventions

### Resume Safety
- All scripts are resume-safe: re-running skips already-processed entries via `circuit_hash` or `content_hash` checks. Never delete intermediate output files before a run completes.
- **Exception**: `enrich_metadata.py` has NO per-entry resume safety within a single run. It holds all entries in RAM and writes atomically at the end via tmp→rename. Stopping mid-run loses in-memory progress, but the original `*_clean.jsonl` files are never touched until the rename step completes safely.

### Atomic Writes
All scripts write to a `.tmp` file first, then use `os.replace()` or `Path.rename()` to atomically replace the target. Original files are never partially overwritten.

### Deduplication
- Within a batch: deduplicate by `content_hash` (same instruction + same code = drop)
- Across batches: deduplicate by `circuit_hash` (same circuit, different instruction = keep all; same circuit, same instruction = drop)
- `enrich_circuit_family.py` operates on unique `circuit_hash` values only, then patches all entries

### Running Order for Final Steps
```
Cell 33: enrich_metadata.py              (Python 3.11 — full 691K, Qiskit required)
Cell 34: enrich_circuit_family.py        (GPT-4.1-mini, after Cell 33)
Cell 35: split_validated.py              (after Cell 34)
Cell 36: enrich_repo_license.py          (after Cell 35, no Qiskit)
Cell 37: enrich_semantic_consistency.py  (after Cell 35, no Qiskit, GPU recommended)
Cell 38: check_leakage.py                (any time, no deps)
Cell 39: compute_paraphrase_diversity.py (any time, no deps)
```

This ordering should be read as an implementation policy for the released PQID pipeline, not as a claim that every later script is mathematically impossible to run earlier. Some stages are delayed deliberately so that expensive enrichment is applied only to canonical post-split artifacts rather than to transient intermediate files.

### Test Split is Sacred
`test_clean.jsonl` (11,548 entries) is the held-out benchmark. Do not use for training, do not inspect during model development. First use only during final evaluation.

### Qiskit Version
enrich_metadata.py requires Qiskit installed under Python 3.11:
```
python3.11
```
Transpilation basis: `["cx", "rz", "sx", "x"]`, optimization_level=1, no coupling map.

### Streamlit Explorer
```bash
cd PQID/scripts/06_visualization
streamlit run app.py
```
