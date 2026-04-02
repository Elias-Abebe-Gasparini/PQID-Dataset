# PQID — Metadata Schema Reference

**Dataset**: Parallel Quantum Instruction Dataset (PQID)
**Entry format**:
```json
{
  "input":          "string — natural-language instruction",
  "output":         "string — Qiskit Python code",
  "openqasm3_code": "string | null — OpenQASM 3.0 export",
  "metadata":       { "...": "..." }
}
```

Every entry is a **triple parallel representation**:
- `input` — natural-language instruction (e.g. *"Build a 3-qubit QFT circuit"*)
- `output` — executable Qiskit Python code constructing the described circuit
- `openqasm3_code` — OpenQASM 3.0 string obtained via `qiskit.qasm3.dumps(qc)` on the extracted `QuantumCircuit`; `null` for non-validated entries or when export fails
- `metadata` — structured annotations (see below)

**`openqasm3_code` is populated by `enrich_metadata.py`** during the same execution pass that validates the Qiskit code. It is `null` when `validation_status != "validated"` or when the qasm3 export raises an exception.

---

## Field Clusters

| # | Cluster | Fields | Populated by |
|---|---------|--------|--------------|
| 1 | [Provenance](#1-provenance) | 18 fields | scraper / preprocessor |
| 2 | [Instruction Generation](#2-instruction-generation) | 9 fields | generation scripts / patch_metadata / enrich_metadata |
| 3 | [Repo Context](#3-repo-context) | 2 fields | enrich_repo_topics.py |
| 4 | [Execution / Validation](#4-execution--validation) | 13 fields | enrich_metadata.py |
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

**Total metadata fields**: 102
**Top-level fields**: 4 (`input`, `output`, `openqasm3_code`, `metadata`)

Fields from clusters 4–11 are `null` until `enrich_metadata.py` runs. Fields from clusters 12–13 are `null` until their respective enrichment scripts run.

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
| `prompt_type` | `str` | `"seed"` — one instruction per circuit; `"paraphrased"` — one of 5 rewrites of a seed |
| `quality_flag` | `str` | Provenance tier — see [Quality Flags](#quality-flags) |
| `generation_model` | `str` | `"gpt-4.1-mini"` for LLM-generated; `"human_annotated"` for original thesis entries |
| `generation_date` | `str` | ISO 8601 date of generation (e.g. `"2025-11-04"`) |
| `paraphrase_source` | `str` | `circuit_hash` of the seed this paraphrase was generated from; `""` for seeds |
| `original_prompt` | `str` | The seed instruction text this paraphrase was derived from; `""` for seeds |
| `prompt_word_count` | `int` | Word count of `input` |
| `prompt_length_chars` | `int` | Character count of `input` |
| `prompt_token_count_cl100k` | `int\|null` | Token count of `input` using the `cl100k_base` tokenizer (tiktoken); enables precise context-window budget calculations. `null` if tiktoken unavailable at enrichment time |

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

Added by `enrich_semantic_consistency.py`. Evaluates per-entry linguistic similarity between each paraphrase and its original seed prompt. `null` for seed entries (`prompt_type == "seed"` or `"human_seed"`) — they have no seed to compare against.

> **Script status**: requires a new `enrich_semantic_consistency.py` (to be written). The existing `semantic_consistency_v1.py` computes only group-level aggregates into a CSV; it does not write per-entry metadata fields back to the JSONL.

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

## Quality Flags

The `quality_flag` field records circuit provenance tier.

These values are independent of `source` and the `retrieval_*` fields. `quality_flag` tracks the dataset-quality tier used in downstream generation and curation; `source` and `retrieval_*` track how the raw circuit was acquired.

| Value | Source | `generation_model` |
|-------|--------|-------------------|
| `hf_baseline` | Original MS thesis circuits (HuggingFace) | `human_annotated` |
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
| `content_hash` | 1 | `str` |
| `contains_demo_scaffolding` | 4 | `bool\|null` |
| `control_flow_op_count` | 5 | `int\|null` |
| `deprecated_api_patterns` | 4 | `list[str]\|null` |
| `entanglement_depth` | 7 | `int\|null` |
| `entangling_gate_ratio` | 7 | `float` |
| `extraction_confidence` | 4 | `str\|null` |
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
| `license_category` | 12 | `str` |
| `max_qubit_degree` | 10 | `int` |
| `measurement_count` | 9 | `int` |
| `measured_qubit_count` | 9 | `int\|null` |
| `mid_circuit_measurement` | 9 | `bool` |
| `multi_qubit_gate_count` | 5 | `int\|null` |
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
| `prompt_length_chars` | 2 | `int` |
| `prompt_token_count_cl100k` | 2 | `int\|null` |
| `prompt_type` | 2 | `str` |
| `prompt_word_count` | 2 | `int` |
| `qiskit_version` | 4 | `str` |
| `quantum_register_count` | 5 | `int\|null` |
| `quality_flag` | 2 | `str` |
| `repo_license` | 12 | `str` |
| `repo_name` | 1 | `str\|null` |
| `repo_owner` | 1 | `str\|null` |
| `repo_topics` | 3 | `list[str]` |
| `normalized_edit_distance` | 14 | `float\|null` |
| `reset_usage` | 9 | `bool` |
| `retrieval_mode` | 1 | `str\|null` |
| `retrieval_run_id` | 1 | `str\|null` |
| `retrieval_strategy` | 1 | `str\|null` |
| `rouge_l_to_seed` | 14 | `float\|null` |
| `semantic_intent` | 13 | `str` |
| `semantic_similarity_to_seed` | 14 | `float\|null` |
| `size_class` | 6 | `str` |
| `scrape_date` | 1 | `str\|null` |
| `source` | 1 | `str` |
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
