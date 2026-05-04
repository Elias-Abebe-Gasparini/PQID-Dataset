# PQID — Metadata Schema Reference

Last updated: 2026-04-26

**Dataset**: Parallel Quantum Instruction Dataset (PQID)
**Entry format**:
```json
{
  "input":          "string — natural-language instruction",
  "output":         "string — branch-specific target text",
  "openqasm3_code": "string | null — OpenQASM 3.0 export",
  "metadata":       { "...": "..." }
}
```

Every entry is a **triple parallel representation**:
- `input` — natural-language instruction (e.g. *"Build a 3-qubit QFT circuit"*)
- `output` — target answer associated with the instruction
  - legacy and `source_code`-supervised quality-aware entries use executable Qiskit Python code
  - `teacher_text`-supervised quality-aware entries use a generated diagnosis / repair / robustness-analysis answer
- `openqasm3_code` — OpenQASM 3.0 string obtained via `qiskit.qasm3.dumps(qc)` on the extracted `QuantumCircuit`; `null` for non-validated entries or when export fails
- `metadata` — structured annotations (see below)

**`openqasm3_code` is populated by `enrich_metadata.py`** during the same execution pass that validates the Qiskit code. It is `null` when `validation_status != "validated"` or when the qasm3 export raises an exception.

---

## Field Clusters

| # | Cluster | Fields | Populated by |
|---|---------|--------|--------------|
| 1 | [Provenance](#1-provenance) | 18 fields | scraper / preprocessor |
| 2 | [Instruction Generation](#2-instruction-generation) | 10 fields | generation scripts / patch_metadata / enrich_metadata |
| 3 | [Repo Context](#3-repo-context) | 2 fields | enrich_repo_topics.py |
| 4 | [Execution / Validation](#4-execution--validation) | 14 fields | enrich_metadata.py |
| 4b | [Benchmark Cleaning / Corpus Role Diagnostics](#4b-benchmark-cleaning--corpus-role-diagnostics) | 2 fields | filter_benchmark_and_tier2_cleaned.py |
| 5 | [Core Circuit Metrics](#5-core-circuit-metrics) | 17 fields | enrich_metadata.py |
| 5b | [Gate-set Profile Flags](#5b-gate-set-profile-flags) | 8 fields | enrich_metadata.py |
| 6 | [XAI Complexity Indicators](#6-xai-complexity-indicators) | 3 fields | enrich_metadata.py |
| 7 | [Entanglement Features](#7-entanglement-features) | 3 fields | enrich_metadata.py |
| 8 | [Parameterization Features](#8-parameterization-features) | 3 fields | enrich_metadata.py |
| 9 | [Measurement / Output Structure](#9-measurement--output-structure) | 5 fields | enrich_metadata.py |
| 10 | [Topology / Interaction Graph](#10-topology--interaction-graph) | 4 fields | enrich_metadata.py |
| 11 | [Transpilation Metrics](#11-transpilation-metrics) | 8 fields | enrich_metadata.py |
| 12 | [License Fields](#12-license-fields) | 2 fields | enrich_repo_license.py |
| 13 | [Circuit Family Fields](#13-circuit-family-fields) | 2 fields | enrich_circuit_family.py |
| 14 | [Semantic Consistency Metrics](#14-semantic-consistency-metrics) | 5 fields | enrich_semantic_consistency.py |
| 15 | [Metadata-Design Overlay Fields](#15-metadata-design-overlay-fields) | 27 fields | derive_pqid_metadata_design_fields.py |

**Documented cluster rows**: 17
**Total metadata fields across the full PQID schema**: 149
**Top-level fields**: 4 (`input`, `output`, `openqasm3_code`, `metadata`)

Fields from clusters 4–11 are `null` until `enrich_metadata.py` runs. Fields from clusters 12–15 are absent until their respective enrichment scripts or notebooks run.

Instruction-level review and language-audit artifacts introduced after Stage J
canonical closure are documented below as **sidecar layers** keyed by
`instruction_key`. They are intentionally **not counted** in the `149` metadata
fields above unless they are later promoted into canonical row metadata.

Important counting note:
- the **full schema** documents `149` distinct metadata fields across all PQID artifact families
- the **merged metadata-design v3 corpus** currently materializes `146` metadata keys, because seed / paraphrase-generation-only fields do not belong to that pre-seed corpus view

---

## 1. Provenance

Core provenance fields are always present. The `retrieval_*` fields are populated by the extended GitHub acquisition notebook (the append-only aggressive rescrape cells) and may be `null` in older artifacts unless backfilled during merge.

| Field | Type | Description |
|-------|------|-------------|
| `original_url` | `str` | GitHub Contents API URL of the source file |
| `file_path` | `str` | File path within the repository (e.g. `src/circuits/bell.py`) |
| `source` | `str` | Fine-grained acquisition source tag or upstream dataset identifier (e.g. `curated`, `search`, `org`, `topic`, `promoted_repo_v2`, `search_v2`, `hf_baseline`, `revlib`). Distinct from `quality_flag` |
| `language` | `str` | `"python"` or `"jupyter"` |
| `circuit_hash` | `str` | MD5 hex of stripped output code — **primary dedup key** |
| `content_hash` | `str` | MD5 hex of (input + output) — **cross-batch dedup key** |
| `hash` | `str\|null` | GitHub blob SHA of the source file; enables exact version traceability. `null` for HF baseline / RevLib entries |
| `start_line` | `int\|null` | 1-indexed starting line of the extracted block in the source file. `null` for notebooks and HF baseline |
| `end_line` | `int\|null` | 1-indexed ending line of the extracted block (inclusive). `null` for notebooks and HF baseline |
| `github_anchor` | `str` | URL with line fragment (e.g. `…/file.py#L42-L80`); falls back to `original_url` when line numbers are unavailable |
| `repo_owner` | `str\|null` | GitHub username or organisation that owns the source repository. `null` for HF baseline entries |
| `repo_name` | `str\|null` | GitHub repository name. `null` for HF baseline entries |
| `scrape_date` | `str\|null` | ISO 8601 date the file was scraped (e.g. `"2026-04-01"`). `null` for HF baseline entries |
| `code_lines` | `int` | Number of non-empty lines in the circuit code (`output`). Set at scrape time; updated by `enrich_metadata.py` |
| `output_token_count_cl100k` | `int\|null` | Token count of `output` using the `cl100k_base` tokenizer (tiktoken). Useful for SFT context-window budgeting and cost analysis. `null` if tiktoken unavailable at enrichment time |
| `retrieval_mode` | `str\|null` | High-level acquisition mode: `"baseline"` for the original Cells 1–10 scraper flow, `"aggressive"` for the append-only Phase 2 rescrape. `null` in legacy artifacts unless backfilled during merge |
| `retrieval_strategy` | `str\|null` | Specific strategy within the retrieval mode (e.g. `curated`, `search`, `org`, `topic`, `promoted_repo`, `expanded_search`). `null` in legacy artifacts unless backfilled |
| `retrieval_run_id` | `str\|null` | Deterministic identifier for a retrieval campaign or merge backfill (e.g. `"aggressive_v1_2026-04-02"`, `"baseline_legacy"`). Enables exact auditability of acquisition runs |

**Interpretation note:**
- `source` = immediate scrape route or upstream dataset label
- `quality_flag` = provenance tier assigned later in the generation / curation pipeline
- `retrieval_mode` / `retrieval_strategy` / `retrieval_run_id` = experimental-control fields used to distinguish baseline vs aggressive acquisition campaigns

---

## 2. Instruction Generation

Always present. Set at generation time; backfilled by `patch_metadata.py` for earlier batches.

| Field | Type | Description |
|-------|------|-------------|
| `prompt_type` | `str` | `"seed"` — legacy thesis seed; `"paraphrased"` — one of 5 legacy rewrites of a seed; `"base_seed_quality_aware"` — canonical quality-aware 2026 rebuild base seed; `"paraphrased_quality_aware"` — paraphrase derived from a quality-aware rebuild seed. Early transition artifacts may still contain the deprecated alias `"human_seed_quality_aware"` and should be normalized before release. |
| `quality_flag` | `str` | Provenance tier — see [Quality Flags](#quality-flags) |
| `generation_model` | `str` | Teacher model used to generate the instruction, e.g. `"gpt-4.1-mini"`, `"gpt-5.4"`, or `"human_annotated"` for the original thesis entries |
| `generation_date` | `str` | ISO 8601 date of generation (e.g. `"2025-11-04"`) |
| `paraphrase_source` | `str` | `circuit_hash` of the seed this paraphrase was generated from; `""` for seeds |
| `original_prompt` | `str` | The seed instruction text this paraphrase was derived from; `""` for seeds |
| `prompt_word_count` | `int` | Word count of `input` |
| `prompt_length_chars` | `int` | Character count of `input` |
| `prompt_token_count_cl100k` | `int\|null` | Token count of `input` using the `cl100k_base` tokenizer (tiktoken); enables precise context-window budget calculations. `null` if tiktoken unavailable at enrichment time |

### 2.1 Quality-Aware Seed Draft Metadata (2026 Rebuild)

Added by the quality-aware seed-generation stack. These fields appear on draft-stage seed outputs produced by `seed_generation_quality_aware_pipeline.ipynb` and `generate_seed_drafts_quality_aware.py`.

| Field | Type | Description |
|-------|------|-------------|
| `seed_role` | `str` | Role assigned by the routing manifest, e.g. `gold_generation`, `broad_generation`, `repair_or_explanation`, `mutation_robustness`, `validation_diagnosis` |
| `seed_learning_objective` | `str` | Human-readable description of the pedagogical objective associated with the role |
| `seed_expected_response_mode` | `str` | Expected downstream response family, currently `generation`, `repair`, or `diagnosis` |
| `seed_role_reason` | `str` | Compact explanation of why this source record was assigned to the role |
| `seed_target_supervision_mode` | `str` | Branch-specific target mode, currently `source_code` or `teacher_text` |
| `seed_quality_note` | `str` | Teacher-model note about the quality or framing of the generated draft |
| `seed_manifest_version` | `str` | Manifest schema version used during routing, currently `seed_manifest_v1` |
| `seed_template_version` | `str` | Draft prompt-template version, currently `seed_quality_aware_v1` |
| `seed_critique_template_version` | `str` | Planned critique/rewrite template version, currently `seed_quality_aware_critique_v1` |
| `seed_generation_stage` | `str` | Current generation stage label, currently `draft` |
| `seed_generation_temperature` | `float` | Temperature used in the teacher-model draft pass, e.g. `0.1` |
| `seed_generation_max_output_tokens` | `int` | `max_output_tokens` used in the Responses API call for the draft pass |
| `seed_rewrite_pass_applied` | `bool` | `false` for current draft-stage outputs; becomes `true` only after a later rewrite pass |
| `seed_source_artifact` | `str` | Upstream artifact name recorded in the manifest, e.g. `pqid_2026_enriched_github_circuits.jsonl` |

### 2.2 Quality-Aware Paraphrase Metadata (2026 Rebuild)

Added by `generate_paraphrases_quality_aware.py` and the corresponding documented notebook stage in `seed_generation_quality_aware_pipeline.ipynb`. These fields appear on paraphrases derived from quality-aware rebuild seeds.

| Field | Type | Description |
|-------|------|-------------|
| `paraphrase_source_content_hash` | `str` | `content_hash` of the source seed instruction this paraphrase was derived from; used for resume-safe source-seed lineage |
| `paraphrase_source_prompt_type` | `str` | Prompt type of the source seed, currently expected to be `base_seed_quality_aware`; early transition artifacts may still contain the deprecated alias `human_seed_quality_aware` before normalization |
| `paraphrase_source_generation_model` | `str` | Teacher model that generated the source seed instruction before paraphrase expansion |
| `paraphrase_source_generation_date` | `str` | ISO date on which the source seed instruction was generated |
| `paraphrase_template_version` | `str` | Paraphrase prompt-template version, currently `paraphrase_quality_aware_v1` |
| `paraphrase_generation_temperature` | `float` | Temperature used in the paraphrase-generation pass |
| `paraphrase_generation_max_output_tokens` | `int` | `max_output_tokens` used in the Responses API call for paraphrase expansion |
| `paraphrase_generation_prompt_mode` | `str` | Prompting mode used for the paraphrase-generation pass. Current values are `standard` for ordinary production and `anti_template` for the documented final-tail residual closure path |
| `paraphrase_variant_index` | `int` | 1-based index of this paraphrase within the generated variant set for the source seed |

---

## 3. Repo Context

Added by `enrich_repo_topics.py`. `null` until that script runs.

| Field | Type | Description |
|-------|------|-------------|
| `repo_topics` | `list[str]\|null` | GitHub topic tags on the source repository (e.g. `["qiskit", "quantum-computing"]`) |
| `is_org_repo` | `bool\|null` | `true` if the source repo belongs to an organisation account |

---

## 4. Execution / Validation

Added by `enrich_metadata.py` (Python 3.11 + Qiskit). `null` until that script runs.

| Field | Type | Description |
|-------|------|-------------|
| `validation_status` | `str\|null` | Execution outcome — see table below |
| `validation_error_type` | `str\|null` | Python exception class name (e.g. `"NameError"`), or `""` for `validated` / `no_circuit` |
| `materialized_circuit` | `bool\|null` | `true` iff execution produced a non-placeholder `QuantumCircuit` object. Seed helper circuits such as pre-populated `qc` / `circ` placeholders do not count unless the snippet actually mutates or replaces them |
| `circuit_stats_available` | `bool\|null` | `true` iff a `QuantumCircuit` was found and all metrics in clusters 5–11 are populated |
| `openqasm3_export_successful` | `bool\|null` | `true` if `qiskit.qasm3.dumps(qc)` completed without error; `false` if export raised an exception; `null` for non-validated entries |
| `openqasm3_export_error` | `str\|null` | Exception class name if `openqasm3_export_successful == false`; `null` otherwise |
| `qiskit_version` | `str` | Value of `qiskit.__version__` at enrichment time (e.g. `"1.0.2"`). Enables reproducibility checks: if a circuit fails to compile in a later Qiskit version, this field proves validation was correct at creation time |
| `api_deprecated_usage` | `bool\|null` | `true` if `output` code contains known deprecated Qiskit API patterns (`execute(`, `Aer.get_backend(`, `BasicAer`). Text-level heuristic — does not require execution. `null` if `output` is empty |
| `deprecated_api_patterns` | `list[str]\|null` | List of matched deprecated pattern strings (e.g. `["execute(", "BasicAer"]`). Empty list if `api_deprecated_usage == false`; `null` if `output` is empty |
| `hallucination_type` | `str\|null` | Structured interpretation of why validation failed. `null` until `enrich_metadata.py` runs. See table below |
| `extraction_confidence` | `str\|null` | Heuristic confidence that the extracted code block primarily represents circuit-construction logic rather than surrounding tutorial/demo scaffolding. Values are `high`, `medium`, or `low` |
| `contains_demo_scaffolding` | `bool\|null` | `true` if the extracted block contains likely non-essential demo/tutorial statements such as `print(...)`, `display(...)`, `.draw(...)`, plotting, backend execution, or result inspection |
| `cleanup_candidate` | `bool\|null` | `true` when demo scaffolding is present but the block still shows clear circuit-construction signals. Useful for building a future derived “cleaned generation view” without modifying the raw scrape artifact |
| `cleanup_rules_triggered` | `list[str]\|null` | Names of heuristic extraction-quality rules that fired (e.g. `print_call`, `draw_call`, `backend_run`). Empty list if no rules fired; `null` until enrichment runs |

### 4.1 Benchmark Suitability Diagnostics

Added by `filter_benchmark_and_tier2.py` after broad-pool enrichment. These fields make the benchmark/readiness logic explicit per circuit instead of relying on informal release labels.

| Field | Type | Description |
|-------|------|-------------|
| `benchmark_profile_version` | `str\|null` | Identifier for the benchmark-suitability profile used when scoring the circuit, including threshold choices such as minimum code lines and minimum gate count. Typical values are `benchmark_v1_7check` and `benchmark_v2_8check` |
| `benchmark_checks_total` | `int\|null` | Number of benchmark-suitability checks considered in the current `n/7` profile |
| `benchmark_checks_passed` | `int\|null` | Number of benchmark-suitability checks passed by this circuit in the `n/7` profile |
| `benchmark_checks_ratio` | `float\|null` | `benchmark_checks_passed / benchmark_checks_total` for the `n/7` profile |
| `benchmark_passed_checks` | `list[str]\|null` | List of benchmark-suitability check identifiers satisfied by the circuit in the `n/7` profile |
| `benchmark_failed_checks` | `list[str]\|null` | List of benchmark-suitability check identifiers not satisfied by the circuit in the `n/7` profile |
| `benchmark_suitability_tier` | `str\|null` | Objective suitability label derived from the original `n/7` check profile. Current values are `strict_core_candidate`, `extended_core_candidate`, `validated_broad_candidate`, and `tier2_unvalidated` |
| `benchmark_profile_version_v2` | `str\|null` | Identifier for the cleanliness-aware benchmark-suitability profile used when scoring the circuit under `n/8` |
| `benchmark_checks_total_v2` | `int\|null` | Number of benchmark-suitability checks considered in the current `n/8` profile |
| `benchmark_checks_passed_v2` | `int\|null` | Number of benchmark-suitability checks passed by this circuit in the `n/8` profile |
| `benchmark_checks_ratio_v2` | `float\|null` | `benchmark_checks_passed_v2 / benchmark_checks_total_v2` |
| `benchmark_passed_checks_v2` | `list[str]\|null` | List of benchmark-suitability check identifiers satisfied by the circuit in the `n/8` profile |
| `benchmark_failed_checks_v2` | `list[str]\|null` | List of benchmark-suitability check identifiers not satisfied by the circuit in the `n/8` profile |
| `benchmark_suitability_tier_v2` | `str\|null` | Objective suitability label derived from the cleanliness-aware `n/8` profile. Current values are `strict_core_candidate`, `extended_core_candidate`, `mutation_stress_candidate`, `validated_broad_candidate`, and `tier2_unvalidated` |

Current `v1` profile checks are:

- `validated_execution`
- `high_extraction_confidence`
- `no_demo_scaffolding`
- `no_cleanup_candidate`
- `minimum_code_lines`
- `minimum_gate_count`
- `trusted_retrieval_strategy`

### Dual-score interpretation

The rebuild keeps two benchmark-readiness interpretations because the mutation-suite finding introduced a second question that should not overwrite the original seven-check analysis.

- `n/7` (`benchmark_v1_7check`) is the historical benchmark-readiness score. It is the score used by the original Phase 3 reports, the strict/extended-core definitions, and the notebook's statistical analysis.
- `n/8` (`benchmark_v2_8check`) is a late-stage cleanliness-aware extension. It retains all seven original checks and adds one more binary criterion: `non_mutation_suite_path`.

The advantage of preserving both views is interpretability:

- `n/7` measures intrinsic benchmark readiness under the original execution, extraction-quality, structural-threshold, and provenance criteria.
- `n/8` measures benchmark readiness plus contamination control for release-facing and benchmark-packaging decisions.
- Mutation-derived entries can therefore remain visible as structurally strong bug-stress examples without being silently conflated with the clean benchmark subset.

**`validation_status` values:**

| Value | Meaning |
|-------|---------|
| `validated` | Executed within 3 s; `QuantumCircuit` found in namespace |
| `timeout` | Exceeded 3.0 s execution limit |
| `no_circuit` | Executed successfully but no `QuantumCircuit` in namespace |
| `import_error` | `ImportError` or `ModuleNotFoundError` |
| `name_error` | `NameError` — unresolved variable or missing dependency |
| `syntax_error` | `SyntaxError` in circuit code |
| `exec_error` | Any other runtime exception |

Only `validated` entries are in **Tier 1**. All others go to **Tier 2** (`community_unvalidated.jsonl`).

## 4b. Benchmark Cleaning / Corpus Role Diagnostics

These fields are introduced by the mutation-cleaning and late-stage benchmark-packaging passes. They are designed to make contamination control explicit instead of hiding it inside undocumented filtering decisions.

| Field | Type | Description |
|-------|------|-------------|
| `mutation_suite_candidate` | `bool\|null` | `true` if the entry's source path matches mutation-suite patterns such as `*/Mutants/*` or related mutation-corpus naming conventions |
| `benchmark_cleaning_flags` | `list[str]\|null` | Explicit cleaning flags triggered for the entry (e.g. `mutation_suite_path`); used to reconstruct benchmark/public filtering decisions from the same processed corpus |

These cleaning fields are what enable the `n/8` cleanliness-aware benchmark view without overwriting the original `n/7` score.

**`hallucination_type` values:**

| Value | Condition |
|-------|-----------|
| `none` | `validation_status == "validated"` |
| `timeout` | `validation_status == "timeout"` |
| `syntax_failure` | `validation_status == "syntax_error"` |
| `dependency_hallucination` | `validation_status == "import_error"` — model referenced a missing module |
| `symbol_resolution_failure` | `validation_status == "name_error"` — unresolved variable or function |
| `non_circuit_execution` | `validation_status == "no_circuit"` — code ran but produced no `QuantumCircuit` |
| `register_index_error` | `exec_error` + `IndexError` / `RegisterError` in traceback |
| `api_hallucination` | `exec_error` + `AttributeError` / `TypeError` — wrong method name or signature |
| `runtime_semantic_failure` | `exec_error` — any other runtime exception |

---

## 5. Structural Circuit Metrics

### Core Circuit Metrics

Populated only when `circuit_stats_available == true`.

| Field | Type | Description |
|-------|------|-------------|
| `num_qubits` | `int` | Number of quantum bits (`qc.num_qubits`) |
| `num_clbits` | `int` | Number of classical bits |
| `quantum_register_count` | `int\|null` | Number of quantum registers (`len(qc.qregs)`). Complements `classical_register_count` and helps distinguish flat circuits from multi-register / ancilla-structured designs |
| `gate_count` | `int` | Total gate operations (`qc.size()`) |
| `circuit_depth` | `int` | Circuit depth (`qc.depth()`) |
| `circuit_width` | `int` | Total qubits + clbits (`qc.width()`) |
| `gate_types` | `dict` | `{gate_name: count}` histogram of all gates used |
| `num_gate_types` | `int` | Number of distinct gate types |
| `avg_gates_per_layer` | `float` | `gate_count / circuit_depth` |
| `has_measurement` | `bool` | Whether circuit contains any measurement operations |
| `is_parameterized` | `bool` | Whether circuit contains free `Parameter` objects |
| `multi_qubit_gate_count` | `int\|null` | Count of gate operations acting on three or more qubits (e.g. `ccx`, `cswap`, multi-controlled constructions). Excludes metadata ops such as `measure`, `barrier`, and `delay` |
| `has_control_flow` | `bool\|null` | `true` if the circuit contains Qiskit control-flow operations such as `if_else`, `while_loop`, `for_loop`, or `switch_case` |
| `control_flow_op_count` | `int\|null` | Number of control-flow operations in the circuit. Useful for identifying dynamic-circuit patterns and stratifying beyond static gate-only circuits |
| `t_count` | `int` | Total T + Tdg gate count |
| `t_depth` | `int\|null` | Depth counting only T/Tdg layers (`null` if `t_count == 0`) |
| `unconnected_qubit_count` | `int\|null` | Number of qubits that appear in no gate operation. Non-zero values indicate register over-allocation or partial circuit extraction; useful for data quality filtering |

---

### Gate-set Profile Flags

Boolean structural fingerprint derived from `gate_types`. Populated only when `circuit_stats_available == true`.

| Field | Type | Description |
|-------|------|-------------|
| `has_clifford_only` | `bool\|null` | All non-metadata gates are Clifford (H, CNOT, S, X, Y, Z, SWAP, etc.); circuit is efficiently classically simulable |
| `has_clifford_t` | `bool\|null` | Circuit contains T or Tdg gates |
| `has_rotation_gates` | `bool\|null` | Circuit contains continuous rotation gates (Rx, Ry, Rz, U, P, etc.) |
| `has_entangling_gates` | `bool\|null` | Circuit contains 2-qubit entangling gates (CX, CZ, SWAP, ECR, etc.) |
| `has_barriers` | `bool\|null` | Circuit uses `barrier` instructions |
| `has_custom_gates` | `bool\|null` | Circuit contains gates outside the standard Qiskit gate set |
| `is_unitary` | `bool\|null` | `true` if the circuit contains no measurements and no resets — i.e. it implements a unitary transformation. Separates state-preparation / algorithmic circuits from measurement-driven ones |
| `gate_set_diversity` | `float\|null` | Shannon entropy (bits) of the gate-type frequency distribution: `H(gate_types)`. `0.0` for single-gate-type circuits; higher values indicate a richer, more varied gate vocabulary |

---

## 6. XAI Complexity Indicators

Derived from core metrics. Human-interpretable complexity labels for benchmarking and dataset stratification.

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `circuit_expressiveness` | `str\|null` | `clifford` \| `universal` \| `parameterized` | Gate-set expressiveness class |
| `size_class` | `str\|null` | `trivial` \| `simple` \| `moderate` \| `complex` \| `very_complex` | Structural complexity class |
| `benchmark_difficulty` | `str\|null` | `easy` \| `medium` \| `hard` | Composite difficulty label |

### circuit_expressiveness

| Value | Condition |
|-------|-----------|
| `parameterized` | `is_parameterized == true` (free `Parameter` objects present) |
| `universal` | Not parameterized; contains T, Tdg, or continuous rotation gates |
| `clifford` | Only Clifford gates (H, CNOT, S, X, Y, Z, SWAP, etc.) |

### size_class

Classification is the **maximum** across three independent dimensions:

| Class | Score | Qubits | Depth | Gates |
|-------|-------|--------|-------|-------|
| `trivial` | 0 | ≤ 2 | ≤ 2 | ≤ 3 |
| `simple` | 1 | 3–5 | 3–10 | 4–20 |
| `moderate` | 2 | 6–10 | 11–30 | 21–60 |
| `complex` | 3 | 11–20 | 31–80 | 61–200 |
| `very_complex` | 4 | ≥ 21 | ≥ 81 | ≥ 201 |

### benchmark_difficulty

Composite score from four components (range 0–10):

| Component | Source | Max |
|-----------|--------|-----|
| `size_score` | size_class score (0–4) | 4 |
| `expr_score` | clifford=0, universal=1, parameterized=2 | 2 |
| `ent_score` | 0 if ratio=0; 1 if ratio < 0.3; 2 if ratio ≥ 0.3 | 2 |
| `param_score` | 0 if none; 1 if ≤ 5; 2 if > 5 | 2 |

Thresholds: **easy** ≤ 3 / **medium** 4–7 / **hard** ≥ 8

---

## 7. Entanglement Features

| Field | Type | Description |
|-------|------|-------------|
| `two_qubit_gate_count` | `int\|null` | Count of 2-qubit gates (CX, CZ, SWAP, etc.) |
| `entangling_gate_ratio` | `float\|null` | `two_qubit_gate_count / gate_count`; `0.0` if `gate_count == 0` |
| `entanglement_depth` | `int\|null` | Number of circuit layers containing at least one 2-qubit gate. Analogous to `t_depth` but for entangling operations; direct NISQ hardware cost proxy |

---

## 8. Parameterization Features

| Field | Type | Description |
|-------|------|-------------|
| `num_parameters` | `int\|null` | Number of free `Parameter` objects |
| `parameter_density` | `float\|null` | `num_parameters / gate_count`; `0.0` if `gate_count == 0` |
| `parameter_reuse` | `bool\|null` | `true` if any parameter appears in more than one gate |

---

## 9. Measurement / Output Structure

| Field | Type | Description |
|-------|------|-------------|
| `measurement_count` | `int\|null` | Number of measurement operations |
| `measured_qubit_count` | `int\|null` | Number of distinct qubits that are measured at least once. Distinguishes full-readout from partial-readout circuits better than raw `measurement_count` alone |
| `reset_usage` | `bool\|null` | Whether circuit uses `reset` operations |
| `mid_circuit_measurement` | `bool\|null` | Whether measurement appears before the final layer |
| `classical_register_count` | `int\|null` | Number of classical registers |

---

## 10. Topology / Interaction Graph

Qubit interaction graph: nodes are qubits, edges connect qubits that share a 2-qubit gate.

| Field | Type | Description |
|-------|------|-------------|
| `interaction_graph_edges` | `int\|null` | Number of edges in the interaction graph |
| `graph_density` | `float\|null` | `2 * edges / (n * (n-1))` where n = num_qubits; `0.0` for n ≤ 1 |
| `max_qubit_degree` | `int\|null` | Maximum degree (edge count) of any qubit node |
| `connected_components` | `int\|null` | Number of connected components in the interaction graph |

---

## 11. Transpilation Metrics

Transpilation target: basis gates `["cx", "rz", "sx", "x"]`, `optimization_level=1`, no coupling map (backend-agnostic).

| Field | Type | Description |
|-------|------|-------------|
| `transpiled_depth` | `int\|null` | Depth after transpilation |
| `transpiled_gate_count` | `int\|null` | Total gates after transpilation |
| `transpiled_cx_count` | `int\|null` | CX gates after transpilation |
| `transpiled_single_qubit_count` | `int\|null` | Single-qubit gates after transpilation |
| `transpilation_overhead` | `float\|null` | `(transpiled_gate_count - gate_count) / gate_count` |
| `transpilation_successful` | `bool\|null` | `true` if transpilation completed without error |
| `transpilation_basis_gates` | `list[str]` | Basis gate set used for transpilation (e.g. `["cx","rz","sx","x"]`). Always present — even when transpilation fails — so all transpilation metrics are self-contextualising without needing to consult documentation |
| `transpilation_depth_ratio` | `float\|null` | `transpiled_depth / circuit_depth`. Ratio > 1 indicates the transpiler expanded the circuit; ratio < 1 indicates depth reduction. `null` if transpilation failed or `circuit_depth == 0` |

---

## 12. License Fields

Added by `enrich_repo_license.py`. Run after `split_validated.py`. `null` until that script runs.

| Field | Type | Description |
|-------|------|-------------|
| `repo_license` | `str\|null` | SPDX license identifier of source repository (e.g. `"MIT"`, `"Apache-2.0"`, `"GPL-3.0"`) |
| `license_category` | `str\|null` | `"permissive"` \| `"copyleft"` \| `"no_license"` \| `"other"` |

---

## 13. Circuit Family Fields

Added by `enrich_circuit_family.py` via GPT-4.1-mini classification. `null` until that script runs.

| Field | Type | Values |
|-------|------|--------|
| `circuit_family` | `str\|null` | `bell` \| `ghz` \| `qft` \| `variational` \| `qaoa` \| `teleportation` \| `arithmetic` \| `oracle` \| `ansatz` \| `phase_estimation` \| `error_correction` \| `swap_test` \| `grover` \| `other` |
| `semantic_intent` | `str\|null` | `state_preparation` \| `entanglement_generation` \| `variational_ansatz` \| `algorithmic_subroutine` \| `arithmetic_reversible` \| `oracle_construction` \| `measurement_driven` \| `demonstration` \| `other` |

---

## 14. Semantic Consistency Metrics

Added by `enrich_semantic_consistency.py`. Evaluates per-entry linguistic similarity between each paraphrase and its original seed prompt. `null` for seed entries such as `prompt_type == "seed"` or `prompt_type == "base_seed_quality_aware"` because they have no upstream seed prompt to compare against.

> **Script status**: implemented by `PQID/scripts/enrich_semantic_consistency.py`. The legacy `semantic_consistency_v1.py` still exists for older aggregate reporting, but the current rebuild now supports per-entry semantic sidecar enrichment and split-layer rewrites.

| Field | Type | Description |
|-------|------|-------------|
| `semantic_similarity_to_seed` | `float\|null` | Cosine similarity (0–1) between this paraphrase and its seed prompt, computed with `all-MiniLM-L6-v2` embeddings. High values confirm intent preservation; low values flag semantic drift |
| `bert_score_f1` | `float\|null` | BERTScore F1 of this paraphrase against the seed prompt. Captures contextual lexical overlap beyond n-gram matching |
| `bleu_score_to_seed` | `float\|null` | BLEU-4 score of this paraphrase relative to the seed prompt. Low values indicate high surface-form diversity (desirable for augmentation) |
| `rouge_l_to_seed` | `float\|null` | ROUGE-L (longest common subsequence F1) of this paraphrase against the seed. Complements BLEU-4 |
| `normalized_edit_distance` | `float\|null` | Character-level Levenshtein distance divided by `max(len(seed), len(paraphrase))`. Values near 1.0 indicate maximal surface variation |

**Interpretation guide:**
- `semantic_similarity_to_seed` ≥ 0.85 + `bleu_score_to_seed` ≤ 0.4 → ideal paraphrase: same intent, different wording
- `semantic_similarity_to_seed` < 0.6 → possible semantic drift; candidate for Tier 2 review
- `bleu_score_to_seed` > 0.7 → near-copy; low augmentation value

---

## 15. Metadata-Design Overlay Fields

Added by `PQID/scripts/04_metadata_analysis/pqid_metadata_design_and_evaluation.ipynb`,
`derive_pqid_metadata_design_fields.py`, and `evaluate_pqid_metadata_design_fields.py`.
These are **additive** fields written into:

- `pqid_2026_metadata_design_overlay_v3.jsonl` — sidecar overlay with only the new fields
- `pqid_2026_enriched_github_circuits_plus_metadata_design_v3.jsonl` — merged corpus view with the new fields inserted into `metadata`

They do not replace upstream validation, readiness, or provenance fields. Their purpose is to make later training and split-design analyses more interpretable and more defensible for role-conditioned supervision, uncertainty-aware behavior, and leakage-aware evaluation.

| Field | Type | Description |
|-------|------|-------------|
| `metadata_design_version` | `str` | Version tag for the additive metadata-design layer, currently `metadata_design_v3` |
| `source_snapshot_timestamp` | `str` | Row-level snapshot date of the source repository state, currently derived from the acquisition-time `scrape_date`. Intended to support provenance reconstruction and later contamination / staleness discussions |
| `source_snapshot_granularity` | `str` | Explicit statement of how precise the snapshot provenance is. Current value in the merged corpus: `day_level_scrape_snapshot_with_blob_sha` |
| `source_revision_id` | `str` | Row-level source revision identifier. Preferentially uses the GitHub blob SHA in `hash`; falls back to a deterministic URL-derived identifier when the blob SHA is unavailable |
| `license_evidence_source` | `str` | Declares where the row’s current license evidence came from. Current values: `github_api`, `github_license_file`, `missing` |
| `license_detection_method` | `str` | Declares how the current license interpretation was obtained. Current values: `api_declared`, `manual_post_freeze_owner_license_update`, `unresolved` |
| `license_evidence_url` | `str\|null` | Optional URL for manually verified license evidence, currently populated for the Q-Bridge post-freeze MIT update |
| `license_evidence_commit` | `str\|null` | Optional commit SHA for manually verified license evidence |
| `license_override_version` | `str\|null` | Optional version tag for post-freeze manual license metadata updates |
| `release_view_membership` | `str` | Explicit release-facing membership label derived from the governance fields. Current values: `public_open`, `public_obligations`, `public_review_required`, `restricted_index` |
| `lineage_parent_id` | `str` | Stable lineage anchor intended to tie later seed, paraphrase, and train/eval artifacts back to the same parent source record |
| `benchmark_view_membership` | `str` | Explicit benchmark-facing membership label derived from the current readiness diagnostics. Current values: `strict_n8`, `extended_n8`, `validated_broad_n8`, `validated_master_only`, `mutation_stress_n8`, `tier2_unvalidated` |
| `expected_model_stance` | `str` | High-level behavioral stance implied by the record’s validation and readiness profile. Current values: `generate`, `repair`, `diagnose`, `robustness_compare` |
| `context_sufficiency_class` | `str` | Coarse class describing how self-sufficient the source context is for downstream modeling. Current values: `complete_executable`, `method_fragment`, `partial_implementation`, `demo_scaffolded`, `mutation_variant` |
| `repairability_score` | `int` | Heuristic 0–8 score derived from validation state, extraction confidence, hallucination type, and context class. Intended for stratified analysis, not as a gold-standard human label |
| `repairability_band` | `str` | Coarse band derived from `repairability_score`. Current values: `low`, `medium`, `high` |
| `evidence_regime` | `str` | Abstraction layer over the source evidence available to the model. Current values include `clean_validated_code`, `benchmark_ready_validated_code`, `validated_code`, `validated_mutation_stress`, `partial_context`, `unvalidated_code` |
| `split_group_id` | `str` | Deterministic group identifier used for provenance-aware train / validation / test splitting. It keeps related rows from the same source context together |
| `split_group_source` | `str` | Provenance basis used to build `split_group_id`. Current values: `repo_file`, `original_url`, `blob_hash`, `circuit_hash` |
| `near_duplicate_group_id` | `str` | Deterministic content-derived grouping key for near-duplicate / leakage-aware analysis beyond source provenance. Built from a normalized circuit-text representation |
| `domain_slice` | `str` | Coarse domain subgroup used for later generalization and subgroup analysis. Current values include `benchmark_candidate`, `mutation_suite`, `tutorial`, `test_fixture`, `library_internal`, `research_proto` |
| `shift_axis` | `str` | Dominant robustness / generalization axis associated with the row. Current values include `mutation_status`, `context_completeness`, `benchmark_tier`, `validation_status`, `repo_family` |
| `review_trace_id` | `str` | Compact audit-trace identifier that ties the row back to retrieval, benchmark-profile, snapshot, and license-detection provenance |
| `distribution_rights_status` | `str` | Derived governance interpretation of redistribution status from the existing repository license metadata. Current values: `redistributable_permissive`, `redistributable_copyleft`, `review_required_other`, `unresolved_no_license` |
| `license_resolution_status` | `str` | Coarse resolution state for release governance. Current values: `resolved`, `review_required_other`, `unresolved_no_license` |
| `public_release_bucket` | `str` | Release-facing bucket that separates clearly redistributable rows from rows that should remain restricted or reviewed first. Current values: `public_open`, `public_open_with_obligations`, `public_review_required`, `restricted_internal_only` |
| `license_audit_priority` | `str` | Heuristic governance priority for follow-up action. Current values: `high`, `medium`, `low` |
| `contact_outreach_status` | `str` | Initial action label for repository-owner follow-up. Current values: `not_required`, `review_first`, `needed` |
| `permission_response_status` | `str` | Conservative workflow state for any repository-owner permission outreach. Current values: `not_contacted`, `review_before_contact`, `not_applicable`, `owner_license_file_added` |
| `manual_license_review_status` | `str` | Conservative workflow state for manual governance review. Current values: `not_started`, `pending_review`, `not_required` |

### Added In `metadata_design_v2`

The first transparency-focused additive pass introduced:

- `source_snapshot_timestamp`
- `source_revision_id`
- `license_evidence_source`
- `license_detection_method`
- `release_view_membership`
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

### Added In `metadata_design_v3`

The second additive pass extends the transparency/governance layer with the previously deferred fields:

- `source_snapshot_granularity`
- `lineage_parent_id`
- `benchmark_view_membership`
- `permission_response_status`
- `manual_license_review_status`

**Interpretation notes:**
- `expected_model_stance` is deliberately behavioral. It is designed to support later claims about when a model should generate, repair, diagnose, or perform robustness-aware comparison.
- `source_snapshot_timestamp` and `source_revision_id` are the core provenance additions. Together they make the merged corpus much easier to reason about in terms of snapshot timing, source traceability, and future contamination discussion.
- `source_snapshot_granularity` makes the provenance semantics more honest. It distinguishes an exact archival/revision-style identifier from a day-level scrape snapshot with a stable blob SHA.
- `license_evidence_source` and `license_detection_method` make the governance layer auditable. They are stronger than a bare `license_category` label because they expose the basis of the current license interpretation.
- `release_view_membership` is release-facing rather than purely descriptive. It is intended to make later public / restricted corpus packaging more reproducible.

### 15.1 License-Filtered Release Views

Produced by `export_license_valid_release_views.py`. These views are the
release-facing instruction splits and should be used instead of uploading the
full internal `train_clean`, `validation_clean`, and `test_clean` construction
splits.

Representative artifacts:

- `release_views/pqid_v1_public_open_train.jsonl`
- `release_views/pqid_v1_public_open_validation.jsonl`
- `release_views/pqid_v1_public_open_test.jsonl`
- `release_views/pqid_v1_public_open_summary.json`
- `release_views/pqid_v1_public_open_attribution_manifest.csv`
- `release_views/pqid_v1_license_valid_train.jsonl`
- `release_views/pqid_v1_license_valid_validation.jsonl`
- `release_views/pqid_v1_license_valid_test.jsonl`
- `release_views/pqid_v1_license_valid_summary.json`
- `release_views/pqid_v1_license_valid_attribution_manifest.csv`
- `release_views/pqid_v1_missing_license_internal_only.jsonl`
- `release_views/pqid_v1_missing_license_internal_only_summary.json`

Release-view summary:

- `public_open`: `311,724` rows, all `license_category == permissive`
- `license_valid`: `319,782` rows, including `311,724` permissive rows,
  `7,356` copyleft rows, and `702` manually reviewed `other` rows
- manually reviewed `other` detected licenses: `EPL-2.0`, `BSD-3-Clause-Clear`,
  `CC-BY-4.0`, and `MulanPSL-2.0`
- excluded from `license_valid`: `230,514` `no_license` and `18`
  missing-license rows
- missing-license rows are preserved as restricted/internal-only records

Export-added metadata fields:

| Field | Type | Description |
|-------|------|-------------|
| `metadata.release_export_version` | `str` | Release export version, currently `pqid_license_valid_release_v1` |
| `metadata.release_export_profile` | `str` | Export profile such as `public_open` or `license_valid` |
| `metadata.release_split` | `str` | Original split name retained in the release view: `train`, `validation`, or `test` |
| `metadata.release_filter_basis` | `str` | Basis used for filtering, currently `license_category` |
| `metadata.release_manual_review_version` | `str\|null` | Manual license-review override version for reviewed `other` rows |
| `metadata.release_obligation_note` | `str\|null` | Release-facing note reminding users to preserve license-specific obligations |
- `lineage_parent_id` is intentionally simpler than the full provenance blob. It is the stable cross-artifact pointer that later seed, paraphrase, and evaluation layers should reuse.
- `benchmark_view_membership` turns benchmark packaging into an explicit row-level field rather than a manuscript-only narrative.
- `context_sufficiency_class` separates “is this valid?” from “is this context complete enough to trust at face value?” That distinction is useful for hallucination-aware training analysis.
- `repairability_score` and `repairability_band` are heuristic and reproducible, not human-annotated truth labels.
- `split_group_id` is intended for future leakage-safe split construction and should be treated as the default grouping key when related rows must remain in the same split.
- `near_duplicate_group_id` complements `split_group_id`. `split_group_id` is provenance-aware; `near_duplicate_group_id` is content-aware. Both are useful for leakage analysis, but they answer different questions.
- `domain_slice` and `shift_axis` are analysis fields, not legal or benchmark labels. They exist to support later subgroup and robustness claims in training papers.
- `review_trace_id` is intentionally compact. It is designed to make manual audit trails reconstructible without duplicating large provenance blobs on every row.
- The seven license-governance and workflow-state fields do not create or infer legal permission. They are conservative release-governance labels derived from the existing `repo_license` / `license_category` metadata so that the full corpus can be analyzed without pretending unresolved repositories are automatically redistributable.
- `permission_response_status` and `manual_license_review_status` are workflow-state fields, not legal conclusions. They exist so the licensing/governance paper can quantify bottlenecks instead of only describing them qualitatively.

---

## 16. Instruction-Level Review And Language-Audit Sidecars

The post-Stage-J instruction pipeline also creates **instruction-level sidecar
artifacts** keyed by `instruction_key`. These fields are not yet part of the
canonical `metadata` object on every PQID row, so they are documented
separately from the `149` metadata-field count above.

These sidecars exist to keep Stage K / Stage M auditability explicit without
forcing repeated rewrites of the already-closed canonical seed/paraphrase
artifacts.

### 16.1 Acceptance-Gate Review Sidecar

Produced by the Stage K pilot-review workflow in
`seed_generation_quality_aware_pipeline.ipynb`.

Representative artifacts:

- `instruction_acceptance_gate_manifest_v1.jsonl`
- `instruction_acceptance_gate_pilot_v1.jsonl`
- `instruction_acceptance_gate_pilot_review_sheet_v1.csv`
- `instruction_acceptance_gate_pilot_reviewed_v1.jsonl`
- `instruction_acceptance_gate_pilot_reviewed_v1_summary.json`
- `instruction_acceptance_gate_pilot_review_sheet_v1_adjudication_summary.json`
- `instruction_acceptance_gate_pilot_model_review_sheet_v1.csv`

Current Stage K status:

- unified acceptance-gate manifest rows: `550,314`
- pilot rows: `256`
- K7/K8 reviewed sidecars have been regenerated after bulk adjudication
- final human review decisions: `209` `accept`, `47` `rewrite`
- rewrite-required counts: `209` `no`, `47` `yes`

Core fields:

| Field | Type | Description |
|-------|------|-------------|
| `instruction_key` | `str` | Stable key for a specific seed or paraphrase instruction row; primary join key for the review sidecar |
| `review_group_key` | `str` | Shared grouping key tying related seed/paraphrase rows back to the same source seed lineage |
| `source_branch` | `str` | `source_code` or `teacher_text` |
| `instruction_kind` | `str` | `seed` or `paraphrase` |
| `acceptance_review_status` | `str` | Review workflow state for the human review layer. Current values in the pilot flow: `pending`, `reviewed` |
| `acceptance_review_stage` | `str` | Review-stage label, currently `post_stage_j_canonical` |
| `acceptance_decision` | `str\|null` | Human decision label. Current values: `accept`, `rewrite`, `reject`, `defer` |
| `acceptance_rewrite_required` | `str\|null` | Human rewrite requirement label. Current values: `yes`, `no` |
| `acceptance_decision_reason` | `str` | Optional short rationale for the acceptance decision |
| `acceptance_reviewer_notes` | `str` | Free-text reviewer note |
| `acceptance_rewrite_guidance` | `str` | Free-text rewrite guidance when `acceptance_decision == "rewrite"` or similar |
| `acceptance_rubric.role_fidelity` | `str\|null` | Human rubric value. Current values: `pass`, `minor_issue`, `major_issue`, `n_a` |
| `acceptance_rubric.semantic_grounding` | `str\|null` | Human rubric value. Current values: `pass`, `minor_issue`, `major_issue`, `n_a` |
| `acceptance_rubric.confidence_discipline` | `str\|null` | Human rubric value. Current values: `pass`, `minor_issue`, `major_issue`, `n_a` |
| `acceptance_rubric.hallucination_risk` | `str\|null` | Human rubric value. Current values: `pass`, `minor_issue`, `major_issue`, `n_a` |
| `acceptance_rubric.teacher_text_answer_quality` | `str\|null` | Human rubric value. Usually `n_a` for `source_code` rows |
| `review_axes` | `list[str]` | Declared review axes for the acceptance-gate stage |
| `review_context` | `dict` | Compact provenance bundle used to review the instruction row without reopening the entire source artifact |
| `pilot_context` | `dict` | Pilot-sampling context for Stage K pilot rows, including stratum labels and selection reason |

### 16.2 Model-Assisted Review Suggestion Sidecar

Produced by `run_model_assisted_acceptance_pilot_review.py`. This layer is
deliberately kept separate from the human review sheet so the paper can
distinguish **human judgments** from **model suggestions**.

Current model-assisted review summary:

- model-reviewed pilot rows: `256`
- model suggestions: `192` `accept`, `64` `rewrite`
- initial model/human decision agreement before adjudication: `192` agree, `64` disagree
- interpretation: the model pass is a second-opinion / targeting layer, not the final human review record

| Field | Type | Description |
|-------|------|-------------|
| `model_review_version` | `str` | Version tag for the model-assisted review layer, currently `instruction_acceptance_gate_pilot_model_review_v1` |
| `model_review_model` | `str` | OpenAI model used for the second-opinion pass, e.g. `gpt-5.4` |
| `model_review_temperature` | `float` | Temperature used for the model-assisted review call |
| `model_review_status` | `str` | Model-review workflow state, typically `pending` or `reviewed` |
| `model_review_raw_text` | `str` | Raw text returned by the model before normalization; retained for auditability in the cache layer |
| `model_review_suggestion.acceptance_decision` | `str` | Model-suggested decision label: `accept`, `rewrite`, `reject`, `defer` |
| `model_review_suggestion.acceptance_rewrite_required` | `str` | Model-suggested rewrite requirement: `yes` or `no` |
| `model_review_suggestion.role_fidelity` | `str` | Model-suggested rubric value |
| `model_review_suggestion.semantic_grounding` | `str` | Model-suggested rubric value |
| `model_review_suggestion.confidence_discipline` | `str` | Model-suggested rubric value |
| `model_review_suggestion.hallucination_risk` | `str` | Model-suggested rubric value |
| `model_review_suggestion.teacher_text_answer_quality` | `str` | Model-suggested rubric value |
| `model_review_suggestion.reviewer_notes` | `str` | Short model-generated note justifying the suggestion |
| `model_review_suggestion.rewrite_guidance` | `str` | Model-generated rewrite guidance where relevant |
| `model_review_suggestion.language_scope_note` | `str` | Optional model note about multilingual traces or language-scope concerns |

### 16.3 Acceptance-Gate Remediation Sidecar

Produced by `build_acceptance_remediation_manifest.py`. This layer builds a
bounded remediation set from the adjudicated Stage K rewrite tail plus nearest
lineage neighbors. It does **not** mutate the canonical acceptance-gate
manifest.

Representative artifacts:

- `instruction_acceptance_gate_remediation_candidates_v1.jsonl`
- `instruction_acceptance_gate_remediation_review_sheet_v1.csv`
- `instruction_acceptance_gate_remediation_candidates_v1_summary.json`
- `instruction_acceptance_gate_remediation_batch_requests_v1.jsonl`
- `instruction_acceptance_gate_remediation_outputs_v1.jsonl`
- `instruction_acceptance_gate_remediation_outputs_v1.csv`
- `instruction_acceptance_gate_remediation_outputs_v1_summary.json`
- `instruction_acceptance_gate_remediation_errors_v1.jsonl`
- `instruction_acceptance_gate_remediation_manual_closeout_v1.json`

Current remediation-v1 status:

- remediation version: `instruction_acceptance_gate_remediation_v1`
- neighbor policy: `same_review_group_key_lineage_siblings`
- total candidates: `282`
- core rewrite rows: `47`
- lineage-neighbor rows: `235`
- unique review groups: `47`
- materialized remediation results: `282 / 282`
- final remediation decisions: `282 rewrite`
- final manual closeout overrides: `2`
- remaining manual-review rows: `0`
- closeout status: `complete`

Core remediation fields:

| Field | Type | Description |
|-------|------|-------------|
| `remediation_context.remediation_version` | `str` | Remediation-sidecar version tag |
| `remediation_context.remediation_status` | `str` | Workflow state, currently `candidate` |
| `remediation_context.remediation_candidate_type` | `str` | `core_rewrite` for final human-adjudicated rewrite rows, `lineage_neighbor` for same-group siblings |
| `remediation_context.remediation_priority` | `str` | Priority tier such as `p0_rewrite_required`, `p1_repair_lineage_neighbor`, or `p2_lineage_neighbor` |
| `remediation_context.remediation_neighbor_policy` | `str` | Neighbor-selection rule used to build the sidecar |
| `remediation_context.source_core_instruction_keys` | `list[str]` | Rewrite-required pilot row(s) that caused this group to enter remediation |
| `remediation_context.source_core_reason_buckets` | `list[str]` | Inherited reason buckets such as `undefined_or_missing_symbol`, `repair_not_done`, or `extra_content_violates_prompt` |
| `remediation_context.original_acceptance_decision` | `str` | Human acceptance decision if this candidate was part of the reviewed pilot |
| `remediation_context.original_acceptance_rewrite_required` | `str` | Human rewrite flag if this candidate was part of the reviewed pilot |
| `remediation_context.adjudication_bucket` | `str` | Bulk-adjudication bucket for core rewrite rows |
| `remediation_context.adjudication_reason_bucket` | `str` | Bulk-adjudication reason bucket for core rewrite rows |
| `remediation_context.reviewer_notes` | `str` | Human/model-derived note carried into remediation |
| `remediation_context.rewrite_guidance` | `str` | Guidance for rewrite or neighbor inspection |

Core remediation-result fields:

| Field | Type | Description |
|-------|------|-------------|
| `remediation_result.remediation_result_version` | `str` | Result-sidecar version tag, currently `instruction_acceptance_gate_remediation_result_v1` |
| `remediation_result.remediation_decision` | `str` | Final normalized remediation decision; after closeout all `282` result rows are `rewrite` |
| `remediation_result.remediated_input` | `str` | Input retained or normalized for the remediated row |
| `remediation_result.remediated_output` | `str` | Final remediated output proposed by the batch or manual closeout |
| `remediation_result.changes_summary` | `str` | Short explanation of the remediation decision |
| `remediation_result.residual_risk_note` | `str` | Remaining risk note after remediation |
| `remediation_result.raw_model_text` | `str` | Preserved raw model response from batch materialization, even when later manual closeout overrides the normalized decision |
| `remediation_result.manual_closeout_version` | `str\|null` | Present only for rows finalized by the manual closeout overlay |
| `remediation_result.manual_closeout_applied_at` | `str\|null` | UTC timestamp for manual closeout application |

### 16.4 Instruction Language-Audit Sidecar

Produced by `audit_instruction_language_distribution.py`. This layer supports a
more honest corpus description: PQID is **English-dominant**, but not strictly
English-only.

The audit is heuristic. It should be interpreted as a transparency layer for
distribution analysis and reviewer-facing caveats, not as a claim of perfect
language identification.

Representative artifacts:

- `instruction_language_audit_v1.jsonl`
- `instruction_language_audit_v1_summary.json`

| Field | Type | Description |
|-------|------|-------------|
| `instruction_key` | `str` | Primary join key back to the acceptance-gate manifest or any later instruction-sidecar layer |
| `source_branch` | `str` | `source_code` or `teacher_text` |
| `instruction_kind` | `str` | `seed` or `paraphrase` |
| `seed_role` | `str\|null` | Role label copied from the review context for grouped audits |
| `input_human_language` | `str` | Heuristic language label for the natural-language `input`. Current values may include `en`, `es`, `pt`, `fr`, `bn`, `mixed`, `unknown`, `none` |
| `input_human_language_confidence` | `float` | Heuristic confidence score for the `input_human_language` label |
| `input_human_language_basis` | `str` | Short audit string describing why the input label was assigned |
| `input_human_language_resolved` | `str` | More interpretable companion label for the input language audit. It preserves ordinary labels such as `en` or `bn`, but can refine raw `unknown` into buckets such as `short_fragment`, `ja_script`, `zh_likely_han_only`, `han_script_unresolved`, or `cyrillic_script_unresolved` when appropriate |
| `input_human_language_resolution_basis` | `str` | Short note describing how `input_human_language_resolved` was derived from the raw heuristic output |
| `input_human_script_bucket` | `str` | Coarse script bucket for the input text. Current values may include `latin`, `bengali`, `hangul`, `cjk`, `cyrillic`, `mixed_scripts`, `none`, and mixed forms such as `latin_plus_hangul` |
| `input_human_script_basis` | `str` | Short audit string describing how the input script bucket was assigned |
| `output_human_language` | `str` | Heuristic language label for the human-language-bearing portion of `output` |
| `output_human_language_confidence` | `float` | Heuristic confidence score for the `output_human_language` label |
| `output_human_language_basis` | `str` | Short audit string describing why the output label was assigned |
| `output_human_language_resolved` | `str` | More interpretable companion label for the output language audit. It preserves ordinary labels such as `en`, `es`, `pt`, and `fr`, but can refine raw `unknown` into buckets such as `ja_script`, `zh_likely_han_only`, `han_script_unresolved`, `ko_script`, `cyrillic_script_unresolved`, or `short_fragment` |
| `output_human_language_resolution_basis` | `str` | Short note describing how `output_human_language_resolved` was derived from the raw heuristic output |
| `output_human_script_bucket` | `str` | Coarse script bucket for the output-side human-language-bearing text |
| `output_human_script_basis` | `str` | Short audit string describing how the output script bucket was assigned |
| `output_human_language_scope` | `str` | Declares which part of the output was audited. Current values: `full_output_text`, `code_comments_or_docstrings`, `code_only` |
| `language_audit_version` | `str` | Version tag for the sidecar language audit, currently `instruction_language_audit_v1` |

**Interpretation notes:**

- `input_human_language` is the field that matters most for any claim about the
  language of the instruction surface.
- `*_human_language_resolved` is the field that should be used when discussing
  the residual non-English or non-Latin-script tail, because it separates raw
  `unknown` outcomes into more interpretable buckets such as `short_fragment`,
  `ja_script`, `zh_likely_han_only`, `han_script_unresolved`, `ko_script`, and
  `cyrillic_script_unresolved`.
- `output_human_language` should be interpreted differently by branch:
  - for `teacher_text`, it covers the full natural-language target answer
  - for `source_code`, it audits only the extracted human-language-bearing
    traces such as comments or docstrings; pure code is marked as `code_only`
- multilingual source-code comments inherited from upstream repositories are
  not automatically defects. They should instead inform how the corpus is
  described in the papers and release notes.

## Quality Flags

The `quality_flag` field records circuit provenance tier.

These values are independent of `source` and the `retrieval_*` fields. `quality_flag` tracks the dataset-quality tier used in downstream generation and curation; `source` and `retrieval_*` track how the raw circuit was acquired.

| Value | Source | `generation_model` |
|-------|--------|-------------------|
| `hf_baseline` | Original MS thesis circuits (HuggingFace) | `gpt-4` |
| `clean` | Curated repo list (`github_urls.txt`) | `gpt-4.1-mini` |
| `new_scraped` | GitHub API expansion (Batches 2–4) | `gpt-4.1-mini` |
| `rescraped` | Re-fetched circuits from earlier batches | `gpt-4.1-mini` |
| `rescued` | Circuits that failed validation and were fixed | `gpt-4.1-mini` |
| `revlib` | RevLib quantum circuit archive (via HF baseline) | `gpt-4.1-mini` |

---

## Legacy / Deprecated Fields

These fields appear in the HF baseline metadata passthrough but are not populated for new GitHub-scraped entries. They are preserved to avoid schema breaks.

| Field | Origin | Note |
|-------|--------|------|
| `filename` | Original RevLib `.real` benchmark filename | Present in RevLib entries via HF baseline; `null` elsewhere |
| `revlib_url` | Direct URL to `.real` source file on RevLib server | Present in RevLib entries via HF baseline; `null` elsewhere |

---

## Flat Field List (alphabetical)

For quick lookup. Cluster numbers reference the sections above.

| Field | Cluster | Type |
|-------|---------|------|
| `api_deprecated_usage` | 4 | `bool\|null` |
| `avg_gates_per_layer` | 5 | `float` |
| `benchmark_difficulty` | 6 | `str` |
| `benchmark_checks_passed` | 4 | `int\|null` |
| `benchmark_checks_ratio` | 4 | `float\|null` |
| `benchmark_checks_total` | 4 | `int\|null` |
| `benchmark_failed_checks` | 4 | `list[str]\|null` |
| `benchmark_passed_checks` | 4 | `list[str]\|null` |
| `benchmark_profile_version` | 4 | `str\|null` |
| `benchmark_suitability_tier` | 4 | `str\|null` |
| `benchmark_view_membership` | 15 | `str` |
| `bert_score_f1` | 14 | `float\|null` |
| `bleu_score_to_seed` | 14 | `float\|null` |
| `circuit_depth` | 5 | `int` |
| `circuit_expressiveness` | 6 | `str` |
| `circuit_family` | 13 | `str` |
| `circuit_hash` | 1 | `str` |
| `circuit_stats_available` | 4 | `bool` |
| `cleanup_candidate` | 4 | `bool\|null` |
| `cleanup_rules_triggered` | 4 | `list[str]\|null` |
| `code_lines` | 1 | `int` |
| `circuit_width` | 5 | `int` |
| `classical_register_count` | 9 | `int` |
| `connected_components` | 10 | `int` |
| `contact_outreach_status` | 15 | `str` |
| `content_hash` | 1 | `str` |
| `contains_demo_scaffolding` | 4 | `bool\|null` |
| `context_sufficiency_class` | 15 | `str` |
| `control_flow_op_count` | 5 | `int\|null` |
| `deprecated_api_patterns` | 4 | `list[str]\|null` |
| `distribution_rights_status` | 15 | `str` |
| `domain_slice` | 15 | `str` |
| `entanglement_depth` | 7 | `int\|null` |
| `entangling_gate_ratio` | 7 | `float` |
| `evidence_regime` | 15 | `str` |
| `extraction_confidence` | 4 | `str\|null` |
| `expected_model_stance` | 15 | `str` |
| `file_path` | 1 | `str` |
| `gate_count` | 5 | `int` |
| `gate_set_diversity` | 5b | `float\|null` |
| `gate_types` | 5 | `dict` |
| `generation_date` | 2 | `str` |
| `generation_model` | 2 | `str` |
| `github_anchor` | 1 | `str` |
| `graph_density` | 10 | `float` |
| `hallucination_type` | 4 | `str\|null` |
| `has_barriers` | 5b | `bool\|null` |
| `has_clifford_only` | 5b | `bool\|null` |
| `has_clifford_t` | 5b | `bool\|null` |
| `has_control_flow` | 5 | `bool\|null` |
| `has_custom_gates` | 5b | `bool\|null` |
| `has_entangling_gates` | 5b | `bool\|null` |
| `has_measurement` | 5 | `bool` |
| `has_rotation_gates` | 5b | `bool\|null` |
| `hash` | 1 | `str\|null` |
| `end_line` | 1 | `int\|null` |
| `interaction_graph_edges` | 10 | `int` |
| `is_org_repo` | 3 | `bool` |
| `is_parameterized` | 5 | `bool` |
| `is_unitary` | 5b | `bool\|null` |
| `language` | 1 | `str` |
| `lineage_parent_id` | 15 | `str` |
| `license_audit_priority` | 15 | `str` |
| `license_category` | 12 | `str` |
| `license_detection_method` | 15 | `str` |
| `license_evidence_source` | 15 | `str` |
| `license_resolution_status` | 15 | `str` |
| `max_qubit_degree` | 10 | `int` |
| `measurement_count` | 9 | `int` |
| `measured_qubit_count` | 9 | `int\|null` |
| `manual_license_review_status` | 15 | `str` |
| `metadata_design_version` | 15 | `str` |
| `mid_circuit_measurement` | 9 | `bool` |
| `multi_qubit_gate_count` | 5 | `int\|null` |
| `near_duplicate_group_id` | 15 | `str` |
| `num_clbits` | 5 | `int` |
| `num_gate_types` | 5 | `int` |
| `num_parameters` | 8 | `int` |
| `num_qubits` | 5 | `int` |
| `openqasm3_export_error` | 4 | `str\|null` |
| `openqasm3_export_successful` | 4 | `bool\|null` |
| `original_prompt` | 2 | `str` |
| `original_url` | 1 | `str` |
| `output_token_count_cl100k` | 1 | `int\|null` |
| `parameter_density` | 8 | `float` |
| `parameter_reuse` | 8 | `bool` |
| `paraphrase_source` | 2 | `str` |
| `permission_response_status` | 15 | `str` |
| `prompt_length_chars` | 2 | `int` |
| `prompt_token_count_cl100k` | 2 | `int\|null` |
| `prompt_type` | 2 | `str` |
| `prompt_word_count` | 2 | `int` |
| `public_release_bucket` | 15 | `str` |
| `qiskit_version` | 4 | `str` |
| `quantum_register_count` | 5 | `int\|null` |
| `quality_flag` | 2 | `str` |
| `release_view_membership` | 15 | `str` |
| `repairability_band` | 15 | `str` |
| `repairability_score` | 15 | `int` |
| `repo_license` | 12 | `str` |
| `repo_name` | 1 | `str\|null` |
| `repo_owner` | 1 | `str\|null` |
| `repo_topics` | 3 | `list[str]` |
| `review_trace_id` | 15 | `str` |
| `normalized_edit_distance` | 14 | `float\|null` |
| `reset_usage` | 9 | `bool` |
| `retrieval_mode` | 1 | `str\|null` |
| `retrieval_run_id` | 1 | `str\|null` |
| `retrieval_strategy` | 1 | `str\|null` |
| `rouge_l_to_seed` | 14 | `float\|null` |
| `seed_critique_template_version` | 2.1 | `str` |
| `seed_expected_response_mode` | 2.1 | `str` |
| `seed_generation_max_output_tokens` | 2.1 | `int` |
| `seed_generation_stage` | 2.1 | `str` |
| `seed_generation_temperature` | 2.1 | `float` |
| `seed_learning_objective` | 2.1 | `str` |
| `seed_manifest_version` | 2.1 | `str` |
| `seed_quality_note` | 2.1 | `str` |
| `seed_rewrite_pass_applied` | 2.1 | `bool` |
| `seed_role` | 2.1 | `str` |
| `seed_role_reason` | 2.1 | `str` |
| `seed_source_artifact` | 2.1 | `str` |
| `seed_template_version` | 2.1 | `str` |
| `semantic_intent` | 13 | `str` |
| `semantic_similarity_to_seed` | 14 | `float\|null` |
| `shift_axis` | 15 | `str` |
| `size_class` | 6 | `str` |
| `scrape_date` | 1 | `str\|null` |
| `source` | 1 | `str` |
| `source_revision_id` | 15 | `str` |
| `source_snapshot_granularity` | 15 | `str` |
| `source_snapshot_timestamp` | 15 | `str` |
| `split_group_id` | 15 | `str` |
| `split_group_source` | 15 | `str` |
| `start_line` | 1 | `int\|null` |
| `t_count` | 5 | `int` |
| `t_depth` | 5 | `int\|null` |
| `transpilation_basis_gates` | 11 | `list[str]` |
| `transpilation_depth_ratio` | 11 | `float\|null` |
| `transpilation_overhead` | 11 | `float` |
| `transpilation_successful` | 11 | `bool` |
| `transpiled_cx_count` | 11 | `int` |
| `transpiled_depth` | 11 | `int` |
| `transpiled_gate_count` | 11 | `int` |
| `transpiled_single_qubit_count` | 11 | `int` |
| `two_qubit_gate_count` | 7 | `int` |
| `unconnected_qubit_count` | 5 | `int\|null` |
| `validation_error_type` | 4 | `str` |
| `validation_status` | 4 | `str` |
