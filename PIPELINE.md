# PQID — Pipeline Master Log

**Parallel Quantum Instruction Dataset**
Parallel corpus: natural-language instructions ↔ Qiskit / OpenQASM quantum circuit code.
Working directory: `PQID/data/processed/` (all JSONL files live here)
Master notebook: `PQID/scripts/03_instruction_generation/instruction_generation_pipeline.ipynb`

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
13. [Publication Plan](#13-publication-plan)
14. [API Keys & Tokens](#14-api-keys--tokens)
15. [Critical Conventions](#15-critical-conventions)

---

## 1. Dataset Overview

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
│   ├── 04_metadata_analysis/            diversity + consistency analysis
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

```
C:\Users\Abebe\AppData\Local\Programs\Python\Python311\python.exe
```

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
2. **Code Search** — 26 query strings targeting Qiskit circuit patterns
3. **Org repos** — Enumerate all repos from `Qiskit` and `qiskit-community` orgs
4. **Topic repos** — 9 topics: `qiskit`, `quantum-computing`, `quantum-circuit`, `quantum-gate`, `quantum-algorithms`, `qiskit-terra`, `quantum-information`, `quantum-error-correction`, `quantum-machine-learning`

Dedup: MD5 of stripped code; processed URLs cached in `circuits_unified_processed.txt`.
Output: `circuits_unified.jsonl`

### generate_seeds.py / generate_seeds_pending.py / generate_seeds_expansion*.py
Generates one natural-language instruction per circuit using `gpt-4.1-mini`.
- BATCH_SIZE: 30 concurrent requests
- MAX_TOKENS: 150
- System prompt: "You are a quantum computing assistant. Given a quantum circuit implementation in Qiskit (Python) or OpenQASM 3.0, write a single concise English instruction (one sentence, under 40 words)..."
- Resume-safe by `circuit_hash`
- Adds `content_hash`, `prompt_word_count`, `prompt_length_chars` to metadata

### generate_paraphrases.py / generate_paraphrases_pending.py / generate_paraphrases_expansion*.py
Generates 5 paraphrased instructions per seed using `gpt-4.1-mini`.
- NUM_PARAPHRASES: 5
- BATCH_SIZE: 30 concurrent requests
- MAX_TOKENS: 600
- Prompt: "Generate {n} different paraphrased versions... output one paraphrase per line, no numbering"
- Stores `paraphrase_source` (circuit_hash of seed) and `original_prompt` in each paraphrase metadata

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
| `source` | str | Source dataset identifier (`"github"`, `"revlib"`, `"hf_baseline"`, etc.) — equivalent to thesis `source_dataset` |
| `language` | str | `"python"` (Qiskit) or `"openqasm"` |
| `circuit_hash` | str | MD5 of stripped output code — primary dedup key |
| `content_hash` | str | MD5 of (input + output) — cross-batch dedup key |
| `hash` | str | GitHub blob SHA of the source file — version traceability (null for RevLib/HF) |
| `start_line` | int\|null | Starting line number of the extracted circuit block in the source file (null for notebooks/RevLib/HF) |
| `end_line` | int\|null | Ending line number of the extracted circuit block in the source file (null for notebooks/RevLib/HF) |
| `github_anchor` | str | URL fragment pointing to the highlighted code lines (e.g. `https://github.com/org/repo/blob/main/file.py#L42-L80`); equals `original_url` when line numbers unavailable |

### 7.2 Instruction Generation Fields (always present)

| Field | Type | Description |
|-------|------|-------------|
| `prompt_type` | str | `"seed"` or `"paraphrased"` |
| `quality_flag` | str | `"clean"` \| `"new_scraped"` \| `"rescraped"` \| `"rescued"` \| `"revlib"` \| `"hf_baseline"` |
| `generation_model` | str | `"gpt-4.1-mini"` (682,575 entries) or `"human_annotated"` (8,476 entries) |
| `generation_date` | str | ISO date string of generation |
| `paraphrase_source` | str | `circuit_hash` of the seed this paraphrase was generated from |
| `original_prompt` | str | The seed instruction text (for paraphrases) |
| `prompt_word_count` | int | Word count of the input instruction |
| `prompt_length_chars` | int | Character count of the input instruction |

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
| `gate_count` | int | Total gate operations (`qc.size()`) |
| `circuit_depth` | int | Circuit depth (`qc.depth()`) |
| `circuit_width` | int | Total qubits + clbits (`qc.width()`) |
| `gate_types` | dict | `{gate_name: count}` for each gate used |
| `num_gate_types` | int | Number of distinct gate types |
| `avg_gates_per_layer` | float | `gate_count / circuit_depth` |
| `has_measurement` | bool | Whether circuit contains measurement operations |
| `is_parameterized` | bool | Whether circuit has free `Parameter` objects |
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

**Use case**: HuggingFace community annotation challenge for human evaluation. Community annotators review and fix circuits, providing human preference signal for RLHF/DPO training (NeurIPS main / Nature Machine Intelligence track).

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

## 13. Publication Plan

| # | Venue | Track | Timeline | Focus |
|---|-------|-------|----------|-------|
| 1 | arXiv preprint | — | Day 1 of public release | Dataset announcement |
| 2 | Scientific Data (Nature) | — | ~2026 Q3 | Methodology + quality + Data Records |
| 3 | NeurIPS D&B | Datasets & Benchmarks | ~May/June 2026 | Dataset + benchmarks + leakage analysis |
| 4 | ACM TQC | — | 6–12 months post-release | Model training results |
| 5 | ICML DCAI Workshop | Data-Centric AI | 2026 | Tier 2 community annotation challenge |
| 6 | NeurIPS main / Nature MI | — | 12–36 months | Human preference data; RLHF/DPO for quantum code generation |

---

## 14. API Keys & Tokens

| Service | Key file |
|---------|----------|
| OpenAI (gpt-4.1-mini) | `C:\Users\Abebe\Downloads\IT\OPENAI\OPENAI_API_KEY_PQID_V2.txt` |
| GitHub (scraping + license) | `C:\Users\Abebe\Downloads\IT\GITHUB\GITHUB_TOKEN_PQID_V1.txt` |

---

## 15. Critical Conventions

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

### Test Split is Sacred
`test_clean.jsonl` (11,548 entries) is the held-out benchmark. Do not use for training, do not inspect during model development. First use only during final evaluation.

### Qiskit Version
enrich_metadata.py requires Qiskit installed under Python 3.11:
```
C:\Users\Abebe\AppData\Local\Programs\Python\Python311\python.exe
```
Transpilation basis: `["cx", "rz", "sx", "x"]`, optimization_level=1, no coupling map.

### Streamlit Explorer
```bash
cd PQID/scripts/06_visualization
streamlit run app.py
```
