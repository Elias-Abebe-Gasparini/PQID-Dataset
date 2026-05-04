"""
scrape_github_unified.py
------------------------
Comprehensive GitHub API scraper for quantum circuit code.
Replaces scrape_github_expansion.py, _v2.py, and _v3.py (Batches 2–4).

Four complementary strategies executed in order:
  1. Curated repos   — every file in repos listed in github_urls.txt
  2. Code search     — GitHub Code Search API (comprehensive query set)
  3. Org repos       — all public repos in Qiskit and qiskit-community orgs
  4. Topic repos     — repos tagged with qiskit/quantum-related topics

For each file found:
  - Downloads raw content via GitHub Contents API
  - Extracts QuantumCircuit construction blocks (functions + module-level)
  - Deduplicates by MD5 of stripped circuit code
  - Writes to circuits_unified.jsonl

Resume-safe:
  - Processed file URLs cached in circuits_unified_processed.txt
  - Output appended incrementally; re-run skips already-processed files

Requirements:
    pip install requests

Run:
    python scrape_github_unified.py
"""

import base64
import hashlib
import json
import os
import re
import time
from datetime import date
from pathlib import Path

import requests
from project_paths import PROCESSED_DIR, REPO_ROOT, load_github_token

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = PROCESSED_DIR
GITHUB_URLS_FILE = REPO_ROOT / "github_urls.txt"

OUTPUT_FILE    = BASE / "circuits_unified.jsonl"
PROCESSED_FILE = BASE / "circuits_unified_processed.txt"  # file URLs already done

API_BASE    = "https://api.github.com"
SCRAPE_DATE = str(date.today())

# Rate limits (authenticated): Core=5000/hr, Search=30/min
CORE_SLEEP   = 0.25   # 4 req/s — well within 5000/hr
SEARCH_SLEEP = 2.5    # 24 req/min — under 30/min limit

MAX_FILE_SIZE_BYTES = 300_000  # skip files > 300KB (usually generated/test data)
MIN_CIRCUIT_TOKENS  = 3        # reject trivially short extractions

# GitHub Code Search queries — each returns up to 1000 results (10 pages × 100)
SEARCH_QUERIES = [
    "QuantumCircuit( language:python",
    "QuantumCircuit( language:jupyter-notebook",
    "from qiskit import QuantumCircuit language:python",
    "from qiskit.circuit import QuantumCircuit language:python",
    "qiskit.circuit.QuantumCircuit language:python",
    "QuantumCircuit qc.h qc.cx language:python",
    "QuantumCircuit qc.measure language:python",
    "QuantumCircuit transpile language:python",
    "QuantumCircuit ParameterVector language:python",
    "QuantumCircuit qc.barrier language:python",
    "QuantumCircuit num_qubits language:python",
    "QuantumCircuit qreg creg language:python",
    "QuantumCircuit qc.append language:python",
    "QuantumCircuit qc.compose language:python",
    "qiskit variational quantum circuit language:python",
    "qiskit VQE ansatz language:python",
    "qiskit QAOA language:python",
    "qiskit QFT QuantumCircuit language:python",
    "qiskit grover language:python",
    "qiskit teleportation circuit language:python",
    "qiskit error correction language:python",
    "qiskit amplitude estimation language:python",
    "qiskit phase estimation language:python",
    "qiskit swap test language:python",
    "qiskit GHZ state language:python",
    "qiskit bell state language:python",
]

# Orgs to fully enumerate
ORGS = ["Qiskit", "qiskit-community"]

# Topics to enumerate repos
TOPICS = [
    "qiskit", "quantum-computing", "quantum-circuit",
    "quantum-machine-learning", "variational-quantum-eigensolver",
    "qaoa", "quantum-algorithms", "qasm", "quantum-simulation",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_token() -> str:
    return load_github_token(__file__)


def make_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    return s


def api_get(session: requests.Session, url: str, params: dict = None,
            sleep: float = CORE_SLEEP) -> dict | list | None:
    """GET with exponential back-off on rate limits. Returns parsed JSON or None."""
    for attempt in range(6):
        try:
            resp = session.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                time.sleep(sleep)
                return resp.json()
            elif resp.status_code in (403, 429):
                reset_ts = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait = max(reset_ts - int(time.time()), 60)
                print(f"  Rate limited — waiting {wait}s", flush=True)
                time.sleep(wait)
            elif resp.status_code == 404:
                return None
            elif resp.status_code == 422:
                # Unprocessable — usually a bad search query
                return None
            else:
                time.sleep(2 ** attempt)
        except Exception as exc:
            print(f"  Request error {url}: {exc}", flush=True)
            time.sleep(2 ** attempt)
    return None


def circuit_hash(code: str) -> str:
    return hashlib.md5(code.strip().encode("utf-8")).hexdigest()


def load_processed(path: Path) -> set:
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        return {l.strip() for l in f if l.strip()}


def mark_processed(url: str, path: Path) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(url + "\n")


def load_seen_hashes(path: Path) -> set:
    """Load circuit_hashes already in output to skip duplicates."""
    seen = set()
    if not path.exists():
        return seen
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                ch = d.get("metadata", {}).get("circuit_hash", "")
                if ch:
                    seen.add(ch)
            except Exception:
                pass
    return seen


def append_circuit(entry: dict, path: Path) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Circuit extraction
# ---------------------------------------------------------------------------
def _extract_function_blocks(lines: list[str]) -> list[tuple]:
    """
    Extract complete function definitions that create a QuantumCircuit.
    Returns list of (code, start_line, end_line) tuples where line numbers
    are 1-indexed to match GitHub's line anchor convention.
    """
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Match function definitions
        if re.match(r"^def\s+\w+\s*\(", stripped):
            start_idx = i
            # Collect the function body
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
            # Only keep if it contains QuantumCircuit construction
            if "QuantumCircuit(" in body and len(body.split()) >= MIN_CIRCUIT_TOKENS:
                blocks.append((body, start_idx + 1, j))  # 1-indexed
            i = j
        else:
            i += 1
    return blocks


def _extract_module_level_blocks(lines: list[str]) -> list[tuple]:
    """
    Extract module-level QuantumCircuit construction blocks
    (sequences of lines at indent=0 that include QuantumCircuit).
    Returns list of (code, start_line, end_line) tuples (1-indexed).
    """
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Skip blank lines, comments, imports, class/def declarations
        if (not stripped or stripped.startswith("#")
                or stripped.startswith("import ")
                or stripped.startswith("from ")
                or re.match(r"^(class|def)\s", stripped)):
            i += 1
            continue
        # Start collecting if QuantumCircuit mentioned
        if "QuantumCircuit(" in stripped and not line.startswith(" "):
            start_idx = i
            block_lines = [line]
            j = i + 1
            while j < len(lines):
                nl = lines[j]
                ns = nl.strip()
                if not ns or ns.startswith("#"):
                    j += 1
                    block_lines.append(nl)
                    continue
                if nl.startswith(" ") or nl.startswith("\t"):
                    block_lines.append(nl)
                    j += 1
                elif ns and not nl[0].isspace():
                    # Module-level continuation lines for same circuit
                    if any(tok in ns for tok in (
                        ".h(", ".cx(", ".ccx(", ".measure", ".barrier",
                        ".ry(", ".rz(", ".rx(", ".x(", ".y(", ".z(", ".s(",
                        ".t(", ".p(", ".u(", ".swap(", ".cz(", ".ch(", ".cp(",
                        ".append(", ".compose(", ".draw(", ".transpile(",
                        "qc.", "circuit.", "qreg", "creg", "QuantumRegister(",
                        "ClassicalRegister(", "ParameterVector(",
                    )):
                        block_lines.append(nl)
                        j += 1
                    else:
                        break
                else:
                    break
            block = "\n".join(block_lines).rstrip()
            if len(block.split()) >= MIN_CIRCUIT_TOKENS:
                blocks.append((block, start_idx + 1, j))  # 1-indexed
            i = j
        else:
            i += 1
    return blocks


def extract_circuits_python(code: str) -> list[tuple]:
    """
    Extract QuantumCircuit construction blocks from Python source.
    Returns a list of (code, start_line, end_line) tuples (1-indexed).
    """
    if "QuantumCircuit" not in code:
        return []
    lines = code.splitlines()
    results = []
    func_codes: set[str] = set()
    # Prefer function-level extraction (more self-contained)
    for tup in _extract_function_blocks(lines):
        results.append(tup)
        func_codes.add(tup[0])
    # Also get module-level blocks not already captured by a function
    for tup in _extract_module_level_blocks(lines):
        if tup[0] not in func_codes:
            results.append(tup)
    return results


def extract_circuits_notebook(raw_json: str) -> list[tuple]:
    """
    Extract QuantumCircuit blocks from each code cell of a Jupyter notebook.
    Returns (code, None, None) tuples — notebooks have no file-level line numbers.
    """
    try:
        nb = json.loads(raw_json)
    except Exception:
        return []
    results = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        # Notebook cells don't have meaningful file-level line numbers
        for (blk, _sl, _el) in extract_circuits_python(src):
            results.append((blk, None, None))
    return results


# ---------------------------------------------------------------------------
# File fetching
# ---------------------------------------------------------------------------
def fetch_file_circuits(
    session: requests.Session,
    owner: str, repo: str, path: str, branch: str,
    source_tag: str, seen_hashes: set, processed: set,
) -> list[dict]:
    """
    Download one file, extract circuits, return new entries.
    Updates seen_hashes and marks file as processed.
    """
    file_url = f"https://github.com/{owner}/{repo}/blob/{branch}/{path}"
    if file_url in processed:
        return []

    api_url = f"{API_BASE}/repos/{owner}/{repo}/contents/{path}"
    data = api_get(session, api_url, params={"ref": branch})
    mark_processed(file_url, PROCESSED_FILE)

    if not data or not isinstance(data, dict):
        return []

    # Size guard
    if data.get("size", 0) > MAX_FILE_SIZE_BYTES:
        return []

    raw_content = data.get("content", "")
    if not raw_content:
        return []

    try:
        decoded = base64.b64decode(raw_content).decode("utf-8", errors="replace")
    except Exception:
        return []

    # GitHub blob SHA — enables exact version traceability (SCHEMA.md field: hash)
    file_sha = data.get("sha", "")

    # Extract circuits
    ext = path.lower().split(".")[-1]
    if ext == "ipynb":
        blocks = extract_circuits_notebook(decoded)
    elif ext == "py":
        blocks = extract_circuits_python(decoded)
    else:
        return []

    entries = []
    for (code, start_line, end_line) in blocks:
        ch = circuit_hash(code)
        if ch in seen_hashes:
            continue
        seen_hashes.add(ch)
        if start_line is not None and end_line is not None:
            github_anchor = f"{file_url}#L{start_line}-L{end_line}"
        else:
            github_anchor = file_url
        entry = {
            "input":          "",
            "output":         code,
            "openqasm3_code": None,   # filled by enrich_metadata.py
            "metadata": {
                # Cluster 1 — Provenance (set here)
                "original_url":  file_url,
                "file_path":     path,
                "source":        source_tag,
                "language":      "jupyter" if ext == "ipynb" else "python",
                "circuit_hash":  ch,
                "content_hash":  None,   # filled by generate_seeds.py (needs instruction)
                "hash":          file_sha,
                "start_line":    start_line,
                "end_line":      end_line,
                "github_anchor": github_anchor,
                # Scraper-internal (used by enrich_repo_topics.py)
                "repo_owner":    owner,
                "repo_name":     repo,
                "scrape_date":   SCRAPE_DATE,
                "code_lines":    len([l for l in code.splitlines() if l.strip()]),

                # Cluster 2 — Instruction Generation (filled by generation scripts)
                "prompt_type":           None,
                "quality_flag":          None,
                "generation_model":      None,
                "generation_date":       None,
                "paraphrase_source":     None,
                "original_prompt":       None,
                "prompt_word_count":     None,
                "prompt_length_chars":   None,
                "prompt_token_count_cl100k": None,

                # Cluster 3 — Repo Context (filled by enrich_repo_topics.py)
                "repo_topics":   None,
                "is_org_repo":   None,

                # Cluster 4 — Execution / Validation (filled by enrich_metadata.py)
                "validation_status":          None,
                "validation_error_type":      None,
                "circuit_stats_available":    None,
                "openqasm3_export_successful": None,
                "openqasm3_export_error":     None,
                "qiskit_version":             None,
                "api_deprecated_usage":       None,
                "deprecated_api_patterns":    None,
                "hallucination_type":         None,

                # Cluster 5 — Core Circuit Metrics (filled by enrich_metadata.py)
                "num_qubits":              None,
                "num_clbits":              None,
                "gate_count":              None,
                "circuit_depth":           None,
                "circuit_width":           None,
                "unconnected_qubit_count": None,
                "gate_types":          None,
                "num_gate_types":      None,
                "avg_gates_per_layer": None,
                "has_measurement":     None,
                "is_parameterized":    None,
                "t_count":             None,
                "t_depth":             None,

                # Cluster 5b — Gate-set Profile Flags (filled by enrich_metadata.py)
                "has_clifford_only":    None,
                "has_clifford_t":       None,
                "has_rotation_gates":   None,
                "has_entangling_gates": None,
                "has_barriers":         None,
                "has_custom_gates":     None,
                "is_unitary":           None,
                "gate_set_diversity":   None,

                # Cluster 6 — XAI Complexity Indicators (filled by enrich_metadata.py)
                "circuit_expressiveness": None,
                "size_class":             None,
                "benchmark_difficulty":   None,

                # Cluster 7 — Entanglement Features (filled by enrich_metadata.py)
                "two_qubit_gate_count":  None,
                "entangling_gate_ratio": None,
                "entanglement_depth":    None,

                # Cluster 8 — Parameterization Features (filled by enrich_metadata.py)
                "num_parameters":    None,
                "parameter_density": None,
                "parameter_reuse":   None,

                # Cluster 9 — Measurement / Output Structure (filled by enrich_metadata.py)
                "measurement_count":       None,
                "reset_usage":             None,
                "mid_circuit_measurement": None,
                "classical_register_count": None,

                # Cluster 10 — Topology / Interaction Graph (filled by enrich_metadata.py)
                "interaction_graph_edges": None,
                "graph_density":           None,
                "max_qubit_degree":        None,
                "connected_components":    None,

                # Cluster 11 — Transpilation Metrics (filled by enrich_metadata.py)
                "transpiled_depth":               None,
                "transpiled_gate_count":          None,
                "transpiled_cx_count":            None,
                "transpiled_single_qubit_count":  None,
                "transpilation_overhead":         None,
                "transpilation_successful":       None,
                "transpilation_basis_gates":      None,
                "transpilation_depth_ratio":      None,

                # Cluster 12 — License Fields (filled by enrich_repo_license.py)
                "repo_license":     None,
                "license_category": None,

                # Cluster 13 — Circuit Family (filled by enrich_circuit_family.py)
                "circuit_family":  None,
                "semantic_intent": None,

                # Cluster 14 — Semantic Consistency (filled by enrich_semantic_consistency.py)
                "semantic_similarity_to_seed": None,
                "bert_score_f1":               None,
                "bleu_score_to_seed":          None,
                "rouge_l_to_seed":             None,
                "normalized_edit_distance":    None,
            },
        }
        entries.append(entry)
    return entries


# ---------------------------------------------------------------------------
# Repo tree enumeration
# ---------------------------------------------------------------------------
def get_default_branch(session: requests.Session, owner: str, repo: str) -> str:
    data = api_get(session, f"{API_BASE}/repos/{owner}/{repo}")
    if data:
        return data.get("default_branch", "main")
    return "main"


def get_repo_py_files(
    session: requests.Session, owner: str, repo: str, branch: str
) -> list[str]:
    """
    Return all .py and .ipynb file paths in repo using the git tree API.
    Falls back to recursive contents listing for large repos.
    """
    tree_url = f"{API_BASE}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    data = api_get(session, tree_url)
    if not data:
        return []
    tree = data.get("tree", [])
    return [
        item["path"] for item in tree
        if item["type"] == "blob"
        and item["path"].lower().endswith((".py", ".ipynb"))
        and item.get("size", 0) <= MAX_FILE_SIZE_BYTES
        # Skip test files, generated artifacts, __pycache__
        and not any(seg in item["path"] for seg in (
            "test", "__pycache__", ".egg-info", "node_modules", "docs/",
            "build/", "dist/", ".tox/",
        ))
    ]


def process_repo(
    session: requests.Session,
    owner: str, repo: str, source_tag: str,
    seen_hashes: set, processed: set,
) -> int:
    """Process all .py/.ipynb files in a repo. Returns count of new circuits."""
    branch = get_default_branch(session, owner, repo)
    files = get_repo_py_files(session, owner, repo, branch)
    count = 0
    for path in files:
        entries = fetch_file_circuits(
            session, owner, repo, path, branch,
            source_tag, seen_hashes, processed,
        )
        for e in entries:
            append_circuit(e, OUTPUT_FILE)
            count += 1
    return count


# ---------------------------------------------------------------------------
# Strategy 1: Curated repos
# ---------------------------------------------------------------------------
def extract_owner_repo(url: str) -> tuple[str, str] | None:
    """Parse 'owner/repo' from a github.com URL."""
    try:
        url = url.strip()
        if not url.startswith("https://github.com/") and not url.startswith("github.com/"):
            return None
        path = url.replace("https://github.com/", "").replace("github.com/", "")
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            # Drop fragment qualifiers like /blob/main/..., /tree/main/...
            return parts[0], parts[1]
    except Exception:
        pass
    return None


def strategy_curated(session, seen_hashes, processed) -> int:
    print("\n[Strategy 1] Curated repos from github_urls.txt", flush=True)
    with open(GITHUB_URLS_FILE, encoding="utf-8") as f:
        raw_urls = [l.strip() for l in f if l.strip()]

    # Deduplicate repos (the file has some duplicates)
    repos_seen = set()
    repos = []
    for url in raw_urls:
        pair = extract_owner_repo(url)
        if pair and pair not in repos_seen:
            repos_seen.add(pair)
            repos.append(pair)

    print(f"  Unique repos: {len(repos)}", flush=True)
    total = 0
    for i, (owner, repo) in enumerate(repos, 1):
        n = process_repo(session, owner, repo, "curated", seen_hashes, processed)
        total += n
        if n or i % 10 == 0:
            print(f"  [{i}/{len(repos)}] {owner}/{repo} → +{n} circuits (total={total})", flush=True)

    print(f"  Strategy 1 done: {total} circuits", flush=True)
    return total


# ---------------------------------------------------------------------------
# Strategy 2: Code Search API
# ---------------------------------------------------------------------------
def strategy_code_search(session, seen_hashes, processed) -> int:
    print("\n[Strategy 2] GitHub Code Search", flush=True)
    total = 0

    for qi, query in enumerate(SEARCH_QUERIES, 1):
        print(f"  Query {qi}/{len(SEARCH_QUERIES)}: {query[:60]}...", flush=True)
        page = 1
        query_total = 0

        while page <= 10:  # GitHub caps at 1000 results = 10 pages
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
                repo  = repo_info.get("name", "")
                path  = item.get("path", "")
                if not (owner and repo and path):
                    continue
                # Get default branch from the repo's full_name
                branch = get_default_branch(session, owner, repo)
                entries = fetch_file_circuits(
                    session, owner, repo, path, branch,
                    "search", seen_hashes, processed,
                )
                for e in entries:
                    append_circuit(e, OUTPUT_FILE)
                    query_total += 1
                    total += 1

            if len(items) < 100:
                break
            page += 1

        print(f"    → {query_total} circuits", flush=True)

    print(f"  Strategy 2 done: {total} circuits", flush=True)
    return total


# ---------------------------------------------------------------------------
# Strategy 3: Org repos
# ---------------------------------------------------------------------------
def get_org_repos(session: requests.Session, org: str) -> list[str]:
    """Return list of repo names for an org."""
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


def strategy_orgs(session, seen_hashes, processed) -> int:
    print("\n[Strategy 3] Org repos", flush=True)
    total = 0

    for org in ORGS:
        print(f"  Org: {org}", flush=True)
        repo_names = get_org_repos(session, org)
        print(f"    Repos found: {len(repo_names)}", flush=True)

        for i, repo_name in enumerate(repo_names, 1):
            n = process_repo(session, org, repo_name, "org", seen_hashes, processed)
            total += n
            if n:
                print(f"    [{i}/{len(repo_names)}] {org}/{repo_name} → +{n}", flush=True)

    print(f"  Strategy 3 done: {total} circuits", flush=True)
    return total


# ---------------------------------------------------------------------------
# Strategy 4: Topic repos
# ---------------------------------------------------------------------------
def get_topic_repos(session: requests.Session, topic: str) -> list[tuple[str, str]]:
    """Return (owner, repo) pairs for a given topic, up to 300."""
    repos = []
    page = 1
    while page <= 3:  # 3 pages × 100 = 300 repos per topic
        data = api_get(
            session,
            f"{API_BASE}/search/repositories",
            params={
                "q": f"topic:{topic} language:python",
                "sort": "stars",
                "order": "desc",
                "per_page": 100,
                "page": page,
            },
            sleep=SEARCH_SLEEP,
        )
        if not data:
            break
        items = data.get("items", [])
        for item in items:
            owner = item.get("owner", {}).get("login", "")
            name  = item.get("name", "")
            if owner and name and not item.get("archived"):
                repos.append((owner, name))
        if len(items) < 100:
            break
        page += 1
    return repos


def strategy_topics(session, seen_hashes, processed) -> int:
    print("\n[Strategy 4] Topic repos", flush=True)
    total = 0

    for topic in TOPICS:
        print(f"  Topic: {topic}", flush=True)
        repo_pairs = get_topic_repos(session, topic)
        print(f"    Repos found: {len(repo_pairs)}", flush=True)

        for i, (owner, repo) in enumerate(repo_pairs, 1):
            n = process_repo(session, owner, repo, "topic", seen_hashes, processed)
            total += n
            if n:
                print(f"    [{i}/{len(repo_pairs)}] {owner}/{repo} → +{n}", flush=True)

    print(f"  Strategy 4 done: {total} circuits", flush=True)
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    BASE.mkdir(parents=True, exist_ok=True)

    token   = load_token()
    session = make_session(token)

    # Load resume state
    processed   = load_processed(PROCESSED_FILE)
    seen_hashes = load_seen_hashes(OUTPUT_FILE)

    print(f"PQID Unified Scraper — {SCRAPE_DATE}", flush=True)
    print(f"  Output         : {OUTPUT_FILE}", flush=True)
    print(f"  Already seen   : {len(seen_hashes):,} unique circuits", flush=True)
    print(f"  Processed files: {len(processed):,}", flush=True)

    t0 = time.time()

    n1 = strategy_curated(session, seen_hashes, processed)
    n2 = strategy_code_search(session, seen_hashes, processed)
    n3 = strategy_orgs(session, seen_hashes, processed)
    n4 = strategy_topics(session, seen_hashes, processed)

    elapsed = time.time() - t0
    total   = n1 + n2 + n3 + n4

    # Count output lines
    out_count = sum(1 for _ in open(OUTPUT_FILE, encoding="utf-8"))

    print(f"\n{'='*50}", flush=True)
    print(f"Scraping complete in {elapsed:.0f}s ({elapsed/3600:.1f}h)", flush=True)
    print(f"  Curated repos  : {n1:,}", flush=True)
    print(f"  Code search    : {n2:,}", flush=True)
    print(f"  Org repos      : {n3:,}", flush=True)
    print(f"  Topic repos    : {n4:,}", flush=True)
    print(f"  NEW circuits   : {total:,}", flush=True)
    print(f"  Total in file  : {out_count:,}", flush=True)


if __name__ == "__main__":
    main()
