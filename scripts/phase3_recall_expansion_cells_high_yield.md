# Phase 3 Recall Expansion Cells (High-Yield Variant)

Paste these code cells into `PQID/scripts/scrape_github_unified.ipynb` after the current broad/core checkpoint if you want a third GitHub acquisition campaign that is more reviewer-friendly than the original broad Phase 3 draft.

This variant is intentionally conservative about *where* it looks while still being aggressive about recall:

- it **omits** another large empirical personal-repo sweep
- it **omits** owner-wide sweeps
- it focuses on:
  - trusted tutorial/documentation re-sweeps
  - targeted high-signal search queries
  - notebook-heavy search recovery

Use this when you want to argue that you made a strong, documented attempt to extend GitHub recall, while avoiding a second wave of the noisiest Phase 2 strategy.

Assumption: baseline notebook cells and Phase 2 cells have already been run, so variables/helpers such as `BASE`, `OUTPUT_FILE`, `OUTPUT_FILE_V2`, `API_BASE`, `SCRAPE_DATE`, `session`, `api_get`, `SEARCH_SLEEP`, `load_processed`, `load_seen_hashes`, `load_jsonl_any`, `append_jsonl_to`, `mark_processed_to`, `get_default_branch`, `SCHEMA_NULL_FIELDS`, `extract_circuits_python_aggressive`, and `extract_circuits_notebook_aggressive` already exist in memory.

## Cell 19

```python
# Cell 19 — Phase 3 high-yield config, manifest, and isolated state
from collections import Counter
from pathlib import Path

PHASE3_LABEL = "aggressive_v2_high_yield"
RETRIEVAL_MODE_V3 = "aggressive"
RUN_ID_V3 = f"{PHASE3_LABEL}_{SCRAPE_DATE}"

OUTPUT_FILE_V3 = BASE / "circuits_unified_phase3.jsonl"
PROCESSED_FILE_V3 = BASE / "circuits_unified_phase3_processed.txt"
MERGED_FILE_V3 = BASE / "circuits_unified_plus_phase2_plus_phase3.jsonl"
MANIFEST_FILE_V3 = BASE / "circuits_unified_phase3_manifest.json"

MAX_FILE_SIZE_BYTES_V3 = 1_500_000
INCLUDE_DOC_PATHS_V3 = True
SEARCH_PAGE_LIMIT_V3 = 8

SKIP_PATH_SEGMENTS_V3 = (
    "__pycache__", ".egg-info", "node_modules", "build/", "dist/", ".tox/",
)
PREFERRED_PATH_HINTS_V3 = (
    "examples/", "example/", "notebooks/", "tutorial", "demo", "docs/",
)

# Trusted, tutorial-heavy or bridge-style repos worth a cleaner third-pass sweep.
PHASE3_TRUSTED_RESWEEP_REPOS = [
    ("Qiskit", "documentation"),
    ("PennyLaneAI", "pennylane-qiskit"),
    ("Quantinuum", "pytket-qiskit"),
    ("sethuquantum", "LearnQuantum"),
    ("AayushSarkar", "Qiskit-Experiment-Hub"),
    ("AIComputing101", "quantum-computing-101"),
]

# High-signal indirect-construction patterns that Phase 2 may still under-recover.
PHASE3_SEARCH_QUERIES_V2 = list(dict.fromkeys([
    "from qiskit.circuit.library import NLocal language:python",
    "from qiskit.circuit.library import QAOAAnsatz language:python",
    "from qiskit.circuit.library import ExcitationPreserving language:python",
    "from qiskit.circuit.library import GroverOperator language:python",
    "from qiskit.circuit.library import PhaseEstimation language:python",
    "from qiskit.circuit.library import GraphState language:python",
    "from qiskit.circuit.library import UCCSD language:python",
    "QuantumCircuit.from_qasm_str( qiskit language:python",
    ".to_instruction( qiskit language:python",
    ".control( qiskit language:python",
    "from qiskit_algorithms language:python QuantumCircuit",
    "from qiskit_machine_learning language:python QuantumCircuit",
]))

# Notebook-heavy pass focused on tutorial and example recovery.
PHASE3_NOTEBOOK_QUERY_PACK = list(dict.fromkeys([
    "QuantumCircuit qiskit language:jupyter-notebook path:notebooks",
    "QuantumCircuit qiskit language:jupyter-notebook path:tutorial",
    "QuantumCircuit qiskit language:jupyter-notebook path:examples",
    "from qiskit.circuit.library language:jupyter-notebook",
    "measure_all() qiskit language:jupyter-notebook",
]))

if "REPO_ROOT" in globals():
    REPO_ROOT_V3 = Path(REPO_ROOT)
else:
    REPO_ROOT_V3 = next(
        (p for p in [Path.cwd(), *Path.cwd().parents] if (p / "PQID").exists()),
        Path.cwd(),
    )

def repo_rel_display_v3(path):
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT_V3))
    except Exception:
        try:
            return str(Path(path))
        except Exception:
            return str(path)

def write_manifest_v3(extra=None):
    def _repo_rel(path):
        try:
            return str(Path(path).resolve().relative_to(REPO_ROOT_V3))
        except Exception:
            return str(path)

    manifest = {
        "phase": 3,
        "label": PHASE3_LABEL,
        "retrieval_mode": RETRIEVAL_MODE_V3,
        "retrieval_run_id": RUN_ID_V3,
        "scrape_date": SCRAPE_DATE,
        "baseline_output_file": _repo_rel(OUTPUT_FILE),
        "phase2_output_file": _repo_rel(OUTPUT_FILE_V2),
        "phase3_output_file": _repo_rel(OUTPUT_FILE_V3),
        "merged_output_file": _repo_rel(MERGED_FILE_V3),
        "processed_file_v3": _repo_rel(PROCESSED_FILE_V3),
        "max_file_size_bytes_v3": MAX_FILE_SIZE_BYTES_V3,
        "include_doc_paths_v3": INCLUDE_DOC_PATHS_V3,
        "trusted_resweep_repos_v3": PHASE3_TRUSTED_RESWEEP_REPOS,
        "search_queries_v3": PHASE3_SEARCH_QUERIES_V2,
        "notebook_queries_v3": PHASE3_NOTEBOOK_QUERY_PACK,
        "phase3_variant": "high_yield_only",
    }
    if extra:
        manifest.update(extra)
    with open(MANIFEST_FILE_V3, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

processed_v3 = load_processed(PROCESSED_FILE_V3)
seen_hashes_v3 = (
    load_seen_hashes(OUTPUT_FILE)
    | load_seen_hashes(OUTPUT_FILE_V2)
    | load_seen_hashes(OUTPUT_FILE_V3)
)

write_manifest_v3()

print(f"Phase 3 label       : {PHASE3_LABEL}")
print(f"Phase 3 output      : {repo_rel_display_v3(OUTPUT_FILE_V3)}")
print(f"Phase 3 processed   : {repo_rel_display_v3(PROCESSED_FILE_V3)}")
print(f"Phase 3 merged file : {repo_rel_display_v3(MERGED_FILE_V3)}")
print(f"Combined seen hashes: {len(seen_hashes_v3):,}")
```

## Cell 20

```python
# Cell 20 — Phase 3 high-yield helper wrappers
def metadata_template_v3(
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
        "retrieval_mode": RETRIEVAL_MODE_V3,
        "retrieval_strategy": retrieval_strategy,
        "retrieval_run_id": RUN_ID_V3,
    })
    return meta

def get_repo_code_files_v3(session, owner, repo, branch):
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
        if item.get("size", 0) > MAX_FILE_SIZE_BYTES_V3:
            continue
        if any(seg.lower() in lower for seg in SKIP_PATH_SEGMENTS_V3):
            continue
        if (not INCLUDE_DOC_PATHS_V3) and "docs/" in lower:
            continue
        files.append(path)

    files.sort(
        key=lambda p: (
            0 if any(h in p.lower() for h in PREFERRED_PATH_HINTS_V3) else 1,
            p.lower(),
        )
    )
    return files

def fetch_file_circuits_v3(
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
    if data.get("size", 0) > MAX_FILE_SIZE_BYTES_V3:
        return []

    raw_content = data.get("content", "")
    if not raw_content:
        return []

    decoded = base64.b64decode(raw_content).decode("utf-8", errors="replace")
    file_sha = data.get("sha", "")
    ext = path.lower().split(".")[-1]

    tuples = (
        extract_circuits_notebook_aggressive(decoded)
        if ext == "ipynb"
        else extract_circuits_python_aggressive(decoded)
    )

    entries = []
    for code, start_line, end_line in tuples:
        ch = hashlib.md5(code.strip().encode("utf-8")).hexdigest()
        if ch in seen_hashes:
            continue
        seen_hashes.add(ch)

        entries.append({
            "input": "",
            "output": code,
            "openqasm3_code": None,
            "metadata": metadata_template_v3(
                owner, repo, path, file_url, file_sha, ext,
                start_line, end_line, code, source_tag, retrieval_strategy
            ),
        })

    return entries

def process_repo_v3(
    session, owner, repo, source_tag, retrieval_strategy,
    seen_hashes, processed, processed_file, output_file
):
    branch = get_default_branch(session, owner, repo)
    files = get_repo_code_files_v3(session, owner, repo, branch)
    count = 0

    for path in files:
        for entry in fetch_file_circuits_v3(
            session, owner, repo, path, branch,
            source_tag, retrieval_strategy,
            seen_hashes, processed, processed_file,
        ):
            append_jsonl_to(entry, output_file)
            count += 1

    return count

def run_search_queries_v3(query_list, source_tag, retrieval_strategy):
    total = 0
    per_query = {}

    for qi, query in enumerate(query_list, 1):
        print(f"[{qi}/{len(query_list)}] {query}")
        page = 1
        query_total = 0

        while page <= SEARCH_PAGE_LIMIT_V3:
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
                for entry in fetch_file_circuits_v3(
                    session, owner, repo, path, branch,
                    source_tag=source_tag,
                    retrieval_strategy=retrieval_strategy,
                    seen_hashes=seen_hashes_v3,
                    processed=processed_v3,
                    processed_file=PROCESSED_FILE_V3,
                ):
                    append_jsonl_to(entry, OUTPUT_FILE_V3)
                    query_total += 1
                    total += 1

            if len(items) < 100:
                break
            page += 1

        per_query[query] = query_total
        print(f"  -> {query_total} circuits (running total={total:,})")

    return total, per_query

print("Phase 3 high-yield helpers ready.")
```

## Cell 21

```python
# Cell 21 — Strategy D: trusted tutorial/documentation re-sweeps
total_resweep_v3 = 0
resweep_counts_v3 = {}

for i, (owner, repo) in enumerate(PHASE3_TRUSTED_RESWEEP_REPOS, 1):
    n = process_repo_v3(
        session, owner, repo,
        source_tag="trusted_resweep_v3",
        retrieval_strategy="trusted_resweep",
        seen_hashes=seen_hashes_v3,
        processed=processed_v3,
        processed_file=PROCESSED_FILE_V3,
        output_file=OUTPUT_FILE_V3,
    )
    resweep_counts_v3[f"{owner}/{repo}"] = n
    total_resweep_v3 += n
    print(f"[{i}/{len(PHASE3_TRUSTED_RESWEEP_REPOS)}] {owner}/{repo} -> +{n}")

print(f"\nTrusted re-sweep total: {total_resweep_v3:,}")
```

## Cell 22

```python
# Cell 22 — Strategy E: high-signal expanded search v2
total_search_v3, search_query_counts_v3 = run_search_queries_v3(
    PHASE3_SEARCH_QUERIES_V2,
    source_tag="search_v3",
    retrieval_strategy="expanded_search_v2",
)

print(f"\nExpanded search v2 total: {total_search_v3:,}")
```

## Cell 23

```python
# Cell 23 — Strategy F: notebook-heavy query pack
total_notebook_v3, notebook_query_counts_v3 = run_search_queries_v3(
    PHASE3_NOTEBOOK_QUERY_PACK,
    source_tag="search_notebook_v3",
    retrieval_strategy="notebook_search_pack",
)

print(f"\nNotebook-heavy search total: {total_notebook_v3:,}")
```

## Cell 24

```python
# Cell 24 — Merge baseline + Phase 2 + Phase 3 and backfill retrieval metadata
def normalize_retrieval_metadata_v3(entry, default_mode, default_run_id):
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

def merge_unique_by_circuit_hash_v3(sources, output_path):
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

                    entry = normalize_retrieval_metadata_v3(
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

merged_total_v3 = merge_unique_by_circuit_hash_v3(
    [
        (OUTPUT_FILE, "baseline", "baseline_legacy"),
        (OUTPUT_FILE_V2, "aggressive", globals().get("RUN_ID_V2", "aggressive_v1_legacy")),
        (OUTPUT_FILE_V3, "aggressive", RUN_ID_V3),
    ],
    MERGED_FILE_V3,
)

baseline_count_v3 = len(load_jsonl_any(OUTPUT_FILE))
phase2_count_v3 = len(load_jsonl_any(OUTPUT_FILE_V2))
phase3_count_v3 = len(load_jsonl_any(OUTPUT_FILE_V3))
merged_entries_v3 = load_jsonl_any(MERGED_FILE_V3)

merged_mode_counts_v3 = Counter(
    e.get("metadata", {}).get("retrieval_mode", "<missing>")
    for e in merged_entries_v3
)
merged_strategy_counts_v3 = Counter(
    e.get("metadata", {}).get("retrieval_strategy", "<missing>")
    for e in merged_entries_v3
)

print("=" * 55)
print("PHASE 3 COMPLETE")
print("=" * 55)
print(f"Baseline raw pool           : {baseline_count_v3:,}")
print(f"Phase 2 additions           : {phase2_count_v3:,}")
print(f"Phase 3 additions           : {phase3_count_v3:,}")
print(f"Merged unique circuits      : {merged_total_v3:,}")
print(f"Trusted re-sweeps added     : {total_resweep_v3:,}")
print(f"Expanded search v2 added    : {total_search_v3:,}")
print(f"Notebook query pack added   : {total_notebook_v3:,}")

print("\nMerged retrieval_mode counts:")
for k, v in merged_mode_counts_v3.items():
    print(f"  {k}: {v:,}")

print("\nMerged retrieval_strategy counts:")
for k, v in merged_strategy_counts_v3.most_common():
    print(f"  {k}: {v:,}")

write_manifest_v3({
    "baseline_count": baseline_count_v3,
    "phase2_count": phase2_count_v3,
    "phase3_count": phase3_count_v3,
    "merged_count": merged_total_v3,
    "trusted_resweep_total": total_resweep_v3,
    "search_v2_total": total_search_v3,
    "notebook_search_total": total_notebook_v3,
    "merged_retrieval_mode_counts": dict(merged_mode_counts_v3),
    "merged_retrieval_strategy_counts": dict(merged_strategy_counts_v3),
    "phase3_variant": "high_yield_only",
})

print(f"\nMerged file written to: {repo_rel_display_v3(MERGED_FILE_V3)}")
print(f"Manifest written to   : {repo_rel_display_v3(MANIFEST_FILE_V3)}")
```

## Downstream Note

Before seed generation, run `PQID/scripts/enrich_raw_circuits.py` on the final merged raw pool so the Phase 3 retrieval metadata and structural circuit metrics propagate into the seed-generation stage.

Recommended command:

```powershell
python PQID/scripts/enrich_raw_circuits.py --input-file "PQID/data/processed/circuits_unified_plus_phase2_plus_phase3.jsonl" --output-file "PQID/data/processed/circuits_unified_plus_phase2_plus_phase3_enriched.jsonl"
```

Then rerun:

- `PQID/scripts/report_extraction_quality.py`
- `PQID/scripts/filter_benchmark_and_tier2.py`

This lets you compare:

- Phase 2 broad/core totals
- Phase 3 broad/core totals
- the marginal gain from a cleaner third-pass GitHub acquisition campaign
