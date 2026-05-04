# Phase 2 Aggressive Rescrape Cells

Paste these code cells into `PQID/scripts/scrape_github_unified.ipynb` after the current summary cell.

These cells are designed to:

- leave Cells 1–10 unchanged
- write aggressive results to separate files
- merge baseline + aggressive outputs into a new file
- add explicit retrieval metadata:
  - `retrieval_mode`
  - `retrieval_strategy`
  - `retrieval_run_id`

Assumption: the original notebook cells have already been run, so variables like `BASE`, `OUTPUT_FILE`, `API_BASE`, `SCRAPE_DATE`, `session`, `api_get`, `get_default_branch`, `load_processed`, and `load_seen_hashes` already exist in memory.

## Cell 11

```python
# Cell 11 — Phase 2 config, manifest, and isolated state
from collections import Counter

PHASE2_LABEL = "aggressive_v1"
RETRIEVAL_MODE_V2 = "aggressive"
RUN_ID_V2 = f"{PHASE2_LABEL}_{SCRAPE_DATE}"

OUTPUT_FILE_V2 = BASE / "circuits_unified_aggressive.jsonl"
PROCESSED_FILE_V2 = BASE / "circuits_unified_aggressive_processed.txt"
MERGED_FILE_V2 = BASE / "circuits_unified_plus_aggressive.jsonl"
MANIFEST_FILE_V2 = BASE / "circuits_unified_aggressive_manifest.json"

MAX_FILE_SIZE_BYTES_V2 = 1_000_000
INCLUDE_DOC_PATHS_V2 = True

SKIP_PATH_SEGMENTS_V2 = (
    "__pycache__", ".egg-info", "node_modules", "build/", "dist/", ".tox/",
)
PREFERRED_PATH_HINTS_V2 = (
    "examples/", "example/", "notebooks/", "tutorial", "demo", "docs/",
)

AGGRESSIVE_CIRCUIT_HINTS = (
    "TwoLocal(", "RealAmplitudes(", "EfficientSU2(", "QFT(",
    "ZZFeatureMap(", "PauliFeatureMap(", "NLocal(", "BlueprintCircuit(",
    "QuantumCircuit.from_qasm_str(", ".compose(", ".append(", ".decompose(",
    "measure_all(", "Sampler(", "Estimator(",
)

CIRCUIT_CONTINUATION_TOKENS_V2 = (
    ".h(", ".cx(", ".ccx(", ".measure", ".barrier", ".ry(", ".rz(", ".rx(",
    ".x(", ".y(", ".z(", ".s(", ".t(", ".p(", ".u(", ".swap(", ".cz(",
    ".ch(", ".cp(", ".append(", ".compose(", ".decompose(", ".draw(",
    ".transpile(", "qc.", "circ.", "circuit.", "ansatz", "feature_map",
    "wavefunction", "var_form", "QuantumRegister(", "ClassicalRegister(",
    "ParameterVector(", "Parameter(",
)

PHASE2_PROMOTED_REPOS = [
    ("PennyLaneAI", "pennylane-qiskit"),
    ("Quantinuum", "pytket-qiskit"),
]

PHASE2_ORGS = [
    "PennyLaneAI",
    "Quantinuum",
]

PHASE2_SEARCH_QUERIES = list(dict.fromkeys([
    "from qiskit.circuit.library import TwoLocal language:python",
    "from qiskit.circuit.library import RealAmplitudes language:python",
    "from qiskit.circuit.library import EfficientSU2 language:python",
    "from qiskit.circuit.library import QFT language:python",
    "from qiskit.circuit.library import ZZFeatureMap language:python",
    "from qiskit.circuit.library import PauliFeatureMap language:python",
    "qc.compose( language:python",
    "qc.append( language:python",
    "measure_all() qiskit language:jupyter-notebook",
]))

SCHEMA_NULL_FIELDS = [
    "content_hash",
    "prompt_type", "quality_flag", "generation_model", "generation_date",
    "paraphrase_source", "original_prompt", "prompt_word_count",
    "prompt_length_chars", "prompt_token_count_cl100k",
    "repo_topics", "is_org_repo",
    "validation_status", "validation_error_type", "circuit_stats_available",
    "openqasm3_export_successful", "openqasm3_export_error", "qiskit_version",
    "api_deprecated_usage", "deprecated_api_patterns", "hallucination_type",
    "extraction_confidence", "contains_demo_scaffolding",
    "cleanup_candidate", "cleanup_rules_triggered",
    "num_qubits", "num_clbits", "quantum_register_count", "gate_count",
    "circuit_depth", "circuit_width", "gate_types", "num_gate_types",
    "avg_gates_per_layer", "has_measurement", "is_parameterized",
    "multi_qubit_gate_count", "has_control_flow", "control_flow_op_count",
    "t_count", "t_depth", "unconnected_qubit_count",
    "has_clifford_only", "has_clifford_t", "has_rotation_gates",
    "has_entangling_gates", "has_barriers", "has_custom_gates", "is_unitary",
    "gate_set_diversity", "circuit_expressiveness", "size_class",
    "benchmark_difficulty", "two_qubit_gate_count", "entangling_gate_ratio",
    "entanglement_depth", "num_parameters", "parameter_density",
    "parameter_reuse", "measurement_count", "measured_qubit_count",
    "reset_usage", "mid_circuit_measurement", "classical_register_count",
    "interaction_graph_edges", "graph_density", "max_qubit_degree",
    "connected_components", "transpiled_depth", "transpiled_gate_count",
    "transpiled_cx_count", "transpiled_single_qubit_count",
    "transpilation_overhead", "transpilation_successful",
    "transpilation_basis_gates", "transpilation_depth_ratio",
    "repo_license", "license_category", "circuit_family", "semantic_intent",
    "semantic_similarity_to_seed", "bert_score_f1", "bleu_score_to_seed",
    "rouge_l_to_seed", "normalized_edit_distance",
    "output_token_count_cl100k",
]

def load_jsonl_any(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def repo_rel_display(path):
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except Exception:
        try:
            return str(Path(path))
        except Exception:
            return str(path)

def append_jsonl_to(entry, path):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def mark_processed_to(url, path):
    with open(path, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def write_manifest_v2(extra=None):
    def _repo_rel(path):
        try:
            return str(path.relative_to(REPO_ROOT))
        except Exception:
            return str(path)

    manifest = {
        "phase": 2,
        "label": PHASE2_LABEL,
        "retrieval_mode": RETRIEVAL_MODE_V2,
        "retrieval_run_id": RUN_ID_V2,
        "scrape_date": SCRAPE_DATE,
        "baseline_output_file": _repo_rel(OUTPUT_FILE),
        "aggressive_output_file": _repo_rel(OUTPUT_FILE_V2),
        "merged_output_file": _repo_rel(MERGED_FILE_V2),
        "processed_file_v2": _repo_rel(PROCESSED_FILE_V2),
        "max_file_size_bytes_v2": MAX_FILE_SIZE_BYTES_V2,
        "include_doc_paths_v2": INCLUDE_DOC_PATHS_V2,
        "promoted_repos_v2": PHASE2_PROMOTED_REPOS,
        "orgs_v2": PHASE2_ORGS,
        "search_queries_v2": PHASE2_SEARCH_QUERIES,
    }
    if extra:
        manifest.update(extra)
    with open(MANIFEST_FILE_V2, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

def metadata_template_v2(
    owner, repo, path, file_url, file_sha, ext,
    start_line, end_line, code, source_tag, retrieval_strategy
):
    meta = {k: None for k in SCHEMA_NULL_FIELDS}
    github_anchor = file_url if start_line is None else f"{file_url}#L{start_line}-L{end_line}"
    meta.update({
        "original_url": file_url,
        "file_path": path,
        "source": source_tag,
        "language": "jupyter" if ext == "ipynb" else "python",
        "circuit_hash": hashlib.md5(code.strip().encode("utf-8")).hexdigest(),
        "hash": file_sha,
        "start_line": start_line,
        "end_line": end_line,
        "github_anchor": github_anchor,
        "repo_owner": owner,
        "repo_name": repo,
        "scrape_date": SCRAPE_DATE,
        "code_lines": len([l for l in code.splitlines() if l.strip()]),
        "retrieval_mode": RETRIEVAL_MODE_V2,
        "retrieval_strategy": retrieval_strategy,
        "retrieval_run_id": RUN_ID_V2,
    })
    return meta

processed_v2 = load_processed(PROCESSED_FILE_V2)
seen_hashes_v2 = load_seen_hashes(OUTPUT_FILE) | load_seen_hashes(OUTPUT_FILE_V2)

write_manifest_v2()

print(f"Phase 2 label       : {PHASE2_LABEL}")
print(f"Phase 2 output      : {repo_rel_display(OUTPUT_FILE_V2)}")
print(f"Phase 2 processed   : {repo_rel_display(PROCESSED_FILE_V2)}")
print(f"Phase 2 merged file : {repo_rel_display(MERGED_FILE_V2)}")
print(f"Combined seen hashes: {len(seen_hashes_v2):,}")
```

## Cell 12

```python
# Cell 12 — Aggressive extraction + Phase 2 fetch wrappers
def _extract_function_blocks_aggressive(lines):
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if re.match(r"^def\s+\w+\s*\(", stripped):
            start_idx = i
            indent = len(line) - len(line.lstrip())
            body_lines = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if next_line.strip() == "":
                    body_lines.append(next_line)
                    j += 1
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent > indent:
                    body_lines.append(next_line)
                    j += 1
                else:
                    break
            body = "\n".join(body_lines).rstrip()
            if (
                ("QuantumCircuit(" in body or any(h in body for h in AGGRESSIVE_CIRCUIT_HINTS))
                and len(body.split()) >= MIN_CIRCUIT_TOKENS
            ):
                blocks.append((body, start_idx + 1, j))
            i = j
        else:
            i += 1
    return blocks

def _extract_module_level_blocks_aggressive(lines):
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if (
            not stripped
            or stripped.startswith("#")
            or stripped.startswith("import ")
            or stripped.startswith("from ")
            or re.match(r"^(class|def)\s", stripped)
        ):
            i += 1
            continue

        starts_block = (
            not line.startswith((" ", "\t"))
            and (
                "QuantumCircuit(" in stripped
                or any(h in stripped for h in AGGRESSIVE_CIRCUIT_HINTS)
            )
        )

        if starts_block:
            start_idx = i
            block_lines = [line]
            j = i + 1
            while j < len(lines):
                nl = lines[j]
                ns = nl.strip()

                if not ns or ns.startswith("#"):
                    block_lines.append(nl)
                    j += 1
                    continue

                if nl.startswith((" ", "\t")):
                    block_lines.append(nl)
                    j += 1
                    continue

                if (
                    "QuantumCircuit(" in ns
                    or any(h in ns for h in AGGRESSIVE_CIRCUIT_HINTS)
                    or any(tok in ns for tok in CIRCUIT_CONTINUATION_TOKENS_V2)
                ):
                    block_lines.append(nl)
                    j += 1
                    continue

                break

            block = "\n".join(block_lines).rstrip()
            if len(block.split()) >= MIN_CIRCUIT_TOKENS:
                blocks.append((block, start_idx + 1, j))
            i = j
        else:
            i += 1

    return blocks

def extract_circuits_python_aggressive(code):
    if not any(h in code for h in ("QuantumCircuit",) + AGGRESSIVE_CIRCUIT_HINTS):
        return []

    lines = code.splitlines()
    results = []
    seen_blocks = set()

    for tup in _extract_function_blocks_aggressive(lines):
        if tup[0] not in seen_blocks:
            results.append(tup)
            seen_blocks.add(tup[0])

    for tup in _extract_module_level_blocks_aggressive(lines):
        if tup[0] not in seen_blocks:
            results.append(tup)
            seen_blocks.add(tup[0])

    return results

def extract_circuits_notebook_aggressive(raw_json):
    try:
        nb = json.loads(raw_json)
    except Exception:
        return []

    results = []
    seen_blocks = set()

    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)

        for blk, _sl, _el in extract_circuits_python_aggressive(src):
            if blk not in seen_blocks:
                results.append((blk, None, None))
                seen_blocks.add(blk)

    return results

def get_repo_code_files_v2(session, owner, repo, branch):
    tree_url = f"{API_BASE}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    data = api_get(session, tree_url)
    if not data:
        return []

    files = []
    for item in data.get("tree", []):
        path = item.get("path", "")
        lower = path.lower()
        if item.get("type") != "blob":
            continue
        if not lower.endswith((".py", ".ipynb")):
            continue
        if item.get("size", 0) > MAX_FILE_SIZE_BYTES_V2:
            continue
        if any(seg.lower() in lower for seg in SKIP_PATH_SEGMENTS_V2):
            continue
        if (not INCLUDE_DOC_PATHS_V2) and "docs/" in lower:
            continue
        files.append(path)

    files.sort(
        key=lambda p: (
            0 if any(h in p.lower() for h in PREFERRED_PATH_HINTS_V2) else 1,
            p.lower(),
        )
    )
    return files

def get_org_repos_v2(session, org):
    repos = []
    page = 1
    while True:
        data = api_get(
            session,
            f"{API_BASE}/orgs/{org}/repos",
            params={"type": "public", "per_page": 100, "page": page},
        )
        if not data or not isinstance(data, list):
            break
        repos.extend(r["name"] for r in data if not r.get("archived"))
        if len(data) < 100:
            break
        page += 1
    return repos

def fetch_file_circuits_v2(
    session, owner, repo, path, branch,
    source_tag, retrieval_strategy,
    seen_hashes, processed, processed_file
):
    file_url = f"https://github.com/{owner}/{repo}/blob/{branch}/{path}"
    if file_url in processed:
        return []

    api_url = f"{API_BASE}/repos/{owner}/{repo}/contents/{path}"
    data = api_get(session, api_url, params={"ref": branch})
    mark_processed_to(file_url, processed_file)
    processed.add(file_url)

    if not data or not isinstance(data, dict):
        return []
    if data.get("size", 0) > MAX_FILE_SIZE_BYTES_V2:
        return []

    raw_content = data.get("content", "")
    if not raw_content:
        return []

    try:
        decoded = base64.b64decode(raw_content).decode("utf-8", errors="replace")
    except Exception:
        return []

    file_sha = data.get("sha", "")
    ext = path.lower().split(".")[-1]

    if ext == "ipynb":
        tuples = extract_circuits_notebook_aggressive(decoded)
    else:
        tuples = extract_circuits_python_aggressive(decoded)

    entries = []
    for code, start_line, end_line in tuples:
        circuit_hash = hashlib.md5(code.strip().encode("utf-8")).hexdigest()
        if circuit_hash in seen_hashes:
            continue
        seen_hashes.add(circuit_hash)

        entry = {
            "input": "",
            "output": code,
            "openqasm3_code": None,
            "metadata": metadata_template_v2(
                owner=owner,
                repo=repo,
                path=path,
                file_url=file_url,
                file_sha=file_sha,
                ext=ext,
                start_line=start_line,
                end_line=end_line,
                code=code,
                source_tag=source_tag,
                retrieval_strategy=retrieval_strategy,
            ),
        }
        entries.append(entry)

    return entries

def process_repo_v2(
    session, owner, repo,
    source_tag, retrieval_strategy,
    seen_hashes, processed, processed_file, output_file
):
    branch = get_default_branch(session, owner, repo)
    files = get_repo_code_files_v2(session, owner, repo, branch)
    count = 0

    for path in files:
        for entry in fetch_file_circuits_v2(
            session, owner, repo, path, branch,
            source_tag, retrieval_strategy,
            seen_hashes, processed, processed_file,
        ):
            append_jsonl_to(entry, output_file)
            count += 1

    return count

print("Phase 2 extraction and fetch wrappers ready.")
```

## Cell 13

```python
# Cell 13 — Optional: empirical promotion suggestions from baseline output
def extract_owner_repo_pair(url):
    url = url.strip()
    if not url.startswith("https://github.com/"):
        return None
    parts = [p for p in url.replace("https://github.com/", "").split("/") if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None

curated_repo_pairs = set()
if GITHUB_URLS_FILE.exists():
    with open(GITHUB_URLS_FILE, encoding="utf-8") as f:
        for line in f:
            pair = extract_owner_repo_pair(line)
            if pair:
                curated_repo_pairs.add(pair)

owner_counts_v2 = Counter()
repo_counts_v2 = Counter()

for entry in load_jsonl_any(OUTPUT_FILE):
    meta = entry.get("metadata", {})
    owner = meta.get("repo_owner")
    repo = meta.get("repo_name")
    if not owner or not repo:
        continue
    if (owner, repo) in curated_repo_pairs:
        continue
    owner_counts_v2[owner] += 1
    repo_counts_v2[(owner, repo)] += 1

print("Top non-curated repo candidates:")
for (owner, repo), n in repo_counts_v2.most_common(15):
    print(f"  {owner}/{repo} -> {n}")

print("\nTop owner candidates:")
for owner, n in owner_counts_v2.most_common(15):
    print(f"  {owner} -> {n}")
```

## Cell 14

```python
# Cell 14 — Strategy A: promoted repos
total_promoted_v2 = 0
promoted_counts_v2 = {}

for i, (owner, repo) in enumerate(PHASE2_PROMOTED_REPOS, 1):
    n = process_repo_v2(
        session, owner, repo,
        source_tag="promoted_repo_v2",
        retrieval_strategy="promoted_repo",
        seen_hashes=seen_hashes_v2,
        processed=processed_v2,
        processed_file=PROCESSED_FILE_V2,
        output_file=OUTPUT_FILE_V2,
    )
    promoted_counts_v2[f"{owner}/{repo}"] = n
    total_promoted_v2 += n
    print(f"[{i}/{len(PHASE2_PROMOTED_REPOS)}] {owner}/{repo} -> +{n}")

print(f"\nPromoted repo total: {total_promoted_v2:,}")
```

## Cell 15

```python
# Cell 15 — Strategy B: selective org expansion
total_org_v2 = 0
org_repo_counts_v2 = {}

for org in PHASE2_ORGS:
    repo_names = get_org_repos_v2(session, org)
    org_repo_counts_v2[org] = len(repo_names)
    print(f"{org}: {len(repo_names)} public repos")

    for i, repo_name in enumerate(repo_names, 1):
        n = process_repo_v2(
            session, org, repo_name,
            source_tag="org_v2",
            retrieval_strategy="org",
            seen_hashes=seen_hashes_v2,
            processed=processed_v2,
            processed_file=PROCESSED_FILE_V2,
            output_file=OUTPUT_FILE_V2,
        )
        total_org_v2 += n
        if n:
            print(f"  [{i}/{len(repo_names)}] {org}/{repo_name} -> +{n}")

print(f"\nSelective org total: {total_org_v2:,}")
```

## Cell 16

```python
# Cell 16 — Strategy C: expanded search
total_search_v2 = 0
search_query_counts_v2 = {}

for qi, query in enumerate(PHASE2_SEARCH_QUERIES, 1):
    print(f"[{qi}/{len(PHASE2_SEARCH_QUERIES)}] {query}")
    page = 1
    query_total = 0

    while page <= 10:
        data = api_get(
            session,
            f"{API_BASE}/search/code",
            params={"q": query, "per_page": 100, "page": page},
            sleep=SEARCH_SLEEP,
        )
        if not data:
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            repo_info = item.get("repository", {})
            owner = repo_info.get("owner", {}).get("login", "")
            repo = repo_info.get("name", "")
            path = item.get("path", "")
            if not (owner and repo and path):
                continue

            branch = get_default_branch(session, owner, repo)
            for entry in fetch_file_circuits_v2(
                session, owner, repo, path, branch,
                source_tag="search_v2",
                retrieval_strategy="expanded_search",
                seen_hashes=seen_hashes_v2,
                processed=processed_v2,
                processed_file=PROCESSED_FILE_V2,
            ):
                append_jsonl_to(entry, OUTPUT_FILE_V2)
                query_total += 1
                total_search_v2 += 1

        if len(items) < 100:
            break
        page += 1

    search_query_counts_v2[query] = query_total
    print(f"  -> {query_total} circuits (running total={total_search_v2:,})")

print(f"\nExpanded search total: {total_search_v2:,}")
```

## Cell 17

```python
# Cell 17 — Merge baseline + aggressive and backfill retrieval metadata
def normalize_retrieval_metadata(entry, default_mode, default_run_id):
    entry = dict(entry)
    entry["metadata"] = dict(entry.get("metadata", {}))
    meta = entry["metadata"]

    if meta.get("retrieval_mode") in (None, ""):
        meta["retrieval_mode"] = default_mode
    if meta.get("retrieval_strategy") in (None, ""):
        meta["retrieval_strategy"] = meta.get("source", "unknown")
    if meta.get("retrieval_run_id") in (None, ""):
        meta["retrieval_run_id"] = default_run_id

    return entry

def merge_unique_by_circuit_hash(sources, output_path):
    seen = set()
    total = 0

    with open(output_path, "w", encoding="utf-8") as out:
        for path, default_mode, default_run_id in sources:
            if not path.exists():
                continue

            with open(path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    entry = normalize_retrieval_metadata(
                        json.loads(line),
                        default_mode=default_mode,
                        default_run_id=default_run_id,
                    )
                    ch = entry.get("metadata", {}).get("circuit_hash", "")
                    if ch and ch in seen:
                        continue
                    if ch:
                        seen.add(ch)

                    out.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    total += 1

    return total

merged_total_v2 = merge_unique_by_circuit_hash(
    [
        (OUTPUT_FILE, "baseline", "baseline_legacy"),
        (OUTPUT_FILE_V2, "aggressive", RUN_ID_V2),
    ],
    MERGED_FILE_V2,
)

baseline_count_v2 = len(load_jsonl_any(OUTPUT_FILE))
aggressive_count_v2 = len(load_jsonl_any(OUTPUT_FILE_V2))
merged_entries_v2 = load_jsonl_any(MERGED_FILE_V2)

merged_mode_counts_v2 = Counter(
    e.get("metadata", {}).get("retrieval_mode", "<missing>")
    for e in merged_entries_v2
)
merged_strategy_counts_v2 = Counter(
    e.get("metadata", {}).get("retrieval_strategy", "<missing>")
    for e in merged_entries_v2
)

print("=" * 55)
print("PHASE 2 COMPLETE")
print("=" * 55)
print(f"Baseline raw pool      : {baseline_count_v2:,}")
print(f"Aggressive additions   : {aggressive_count_v2:,}")
print(f"Merged unique circuits : {merged_total_v2:,}")
print(f"Promoted repos added   : {total_promoted_v2:,}")
print(f"Selective orgs added   : {total_org_v2:,}")
print(f"Expanded search added  : {total_search_v2:,}")

print("\nMerged retrieval_mode counts:")
for k, v in merged_mode_counts_v2.items():
    print(f"  {k}: {v:,}")

print("\nMerged retrieval_strategy counts:")
for k, v in merged_strategy_counts_v2.most_common():
    print(f"  {k}: {v:,}")

write_manifest_v2({
    "baseline_count": baseline_count_v2,
    "aggressive_count": aggressive_count_v2,
    "merged_count": merged_total_v2,
    "promoted_repo_total": total_promoted_v2,
    "org_total": total_org_v2,
    "search_total": total_search_v2,
    "merged_retrieval_mode_counts": dict(merged_mode_counts_v2),
    "merged_retrieval_strategy_counts": dict(merged_strategy_counts_v2),
})

print(f"\nMerged file written to: {repo_rel_display(MERGED_FILE_V2)}")
print(f"Manifest written to   : {repo_rel_display(MANIFEST_FILE_V2)}")
```

## Downstream Note

Before seed generation, run `PQID/scripts/enrich_raw_circuits.py` on the merged raw pool so the retrieval metadata and structural circuit metrics both propagate into the seed-generation stage.

Recommended command:

```powershell
python PQID/scripts/enrich_raw_circuits.py --input-file "PQID/data/processed/circuits_unified_plus_aggressive.jsonl" --output-file "PQID/data/processed/circuits_unified_plus_aggressive_enriched.jsonl"
```

Then point the input of `PQID/scripts/03_instruction_generation/generate_seeds.py` to `circuits_unified_plus_aggressive_enriched.jsonl` for this run.

That way:

- baseline entries in the merged raw pool will carry `retrieval_mode="baseline"`
- aggressive entries will carry `retrieval_mode="aggressive"`
- both will keep `retrieval_strategy` and `retrieval_run_id`
- seed prompts can use structural metadata anchors such as register counts, measurement coverage, control-flow presence, and multi-qubit-gate counts
