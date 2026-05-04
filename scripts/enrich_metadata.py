"""
enrich_metadata.py
------------------
Enriches train_clean.jsonl and validation_clean.jsonl with circuit-level
metadata extracted by executing each entry's Qiskit code and inspecting
the resulting QuantumCircuit object.

New metadata fields added to each entry:

  Circuit structure (from Qiskit exec):
    num_qubits               int
    num_clbits               int
    gate_count               int      qc.size()
    circuit_depth            int      qc.depth()
    circuit_width            int      qc.width()
    gate_types               dict     qc.count_ops()
    num_gate_types           int      number of distinct gate types used
    avg_gates_per_layer      float    gate_count / circuit_depth (parallelism proxy)
    has_measurement          bool
    is_parameterized         bool
    t_count                  int      T + Tdg gate count
    t_depth                  int      layers containing at least one T/Tdg gate (fault-tolerant cost)

  XAI complexity indicators:
    circuit_expressiveness   str      "clifford" | "parameterized" | "universal"
                                      clifford     = Clifford gates only; classically simulable
                                      parameterized = has free parameters (VQE/QAOA/PQC)
                                      universal    = T/Tdg or rotation gates present
    size_class               str      "trivial"|"simple"|"moderate"|"complex"|"very_complex"
                                      max across: qubits(≤2/3-5/6-10/11-20/≥21),
                                      depth(≤2/3-10/11-30/31-80/≥81),
                                      gates(≤3/4-20/21-60/61-200/≥201)
    benchmark_difficulty     str      "easy" | "medium" | "hard"
                                      composite score: size + expressiveness +
                                      entangling ratio + parameter count

  Gate-set profile flags (derived from gate_types):
    has_clifford_only        bool     only Clifford gates (no T, rotations, custom)
    has_clifford_t           bool     has T or Tdg gates
    has_rotation_gates       bool     has Rx/Ry/Rz/U/P or other continuous rotations
    has_entangling_gates     bool     has CX/CZ/SWAP or other two-qubit gates
    has_barriers             bool     circuit uses barrier instructions
    has_custom_gates         bool     contains gates outside the standard Qiskit set

  Entanglement proxy features:
    two_qubit_gate_count     int      number of ops with ≥2 qubits
    entangling_gate_ratio    float    two_qubit_gate_count / gate_count

  Parameterization metadata:
    num_parameters           int      number of free parameters (qc.num_parameters)
    parameter_density        float    num_parameters / num_qubits
    parameter_reuse          bool     any parameter used in more than one gate

  Measurement / output structure:
    measurement_count        int      number of measure ops
    reset_usage              bool     circuit uses reset ops
    mid_circuit_measurement  bool     non-barrier gate follows a measure op
    classical_register_count int      len(qc.cregs)

  Topology / interaction graph (requires networkx):
    interaction_graph_edges  int      unique qubit-pair interactions
    graph_density            float    edges / max_possible_edges
    max_qubit_degree         int      highest qubit interaction degree
    connected_components     int      connected components in interaction graph

  Transpilation metrics (basis: cx/rz/sx/x, optimization_level=1, no coupling map):
    transpiled_depth              int    depth after basis transpilation
    transpiled_gate_count         int    total gates after transpilation
    transpiled_cx_count           int    CNOT count — primary hardware cost metric
    transpiled_single_qubit_count int    single-qubit gates after transpilation
    transpilation_overhead        float  transpiled_gate_count / original gate_count
    transpilation_successful      bool   False if transpilation raises any exception

  Prompt-side metadata:
    prompt_word_count        int      len(input.split()) — approximate token count
    prompt_length_chars      int      len(input)

  Validation flags:
    materialized_circuit     bool     true iff execution produced a non-placeholder circuit
    circuit_stats_available  bool
    validation_status        str
    validation_error_type    str

Run order: after rebuild_clean.py (or rescrape_broken.py).
Overwrites train_clean.jsonl and validation_clean.jsonl in-place after both
splits complete successfully; writes to *_enriched.jsonl intermediates first.

Usage:
    python enrich_metadata.py
"""

import json
import os
import threading
import time
import re
import warnings

warnings.filterwarnings("ignore")

from project_paths import PROCESSED_DIR

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = str(PROCESSED_DIR)

SPLITS = {
    "train": {
        "input":  f"{BASE}/train_clean.jsonl",
        "tmp":    f"{BASE}/train_clean_enriched.jsonl",
    },
    "validation": {
        "input":  f"{BASE}/validation_clean.jsonl",
        "tmp":    f"{BASE}/validation_clean_enriched.jsonl",
    },
    "test": {
        "input":  f"{BASE}/test_clean.jsonl",
        "tmp":    f"{BASE}/test_clean_enriched.jsonl",
    },
}

# Per-entry resume cache — written after every enrichment so runs are
# fully restartable without re-processing already-done entries.
CACHE_FILE = f"{BASE}/enrich_metadata_cache.jsonl"

# Enrichment-computed fields stored in the cache record (excludes
# identity/provenance fields that are already in the clean files).
_ENRICHMENT_FIELDS = frozenset({
    "validation_status", "validation_error_type", "materialized_circuit",
    "circuit_stats_available",
    "num_qubits", "num_clbits", "gate_count", "circuit_depth", "circuit_width",
    "gate_types", "num_gate_types", "avg_gates_per_layer", "has_measurement",
    "is_parameterized", "t_count", "t_depth",
    "quantum_register_count", "multi_qubit_gate_count",
    "has_control_flow", "control_flow_op_count",
    "circuit_expressiveness", "size_class", "benchmark_difficulty",
    "has_clifford_only", "has_clifford_t", "has_rotation_gates",
    "has_entangling_gates", "has_barriers", "has_custom_gates",
    "two_qubit_gate_count", "entangling_gate_ratio",
    "num_parameters", "parameter_density", "parameter_reuse",
    "measurement_count", "reset_usage", "mid_circuit_measurement",
    "classical_register_count", "measured_qubit_count",
    "interaction_graph_edges", "graph_density", "max_qubit_degree",
    "connected_components",
    "transpiled_depth", "transpiled_gate_count", "transpiled_cx_count",
    "transpiled_single_qubit_count", "transpilation_overhead",
    "transpilation_successful",
    "prompt_word_count", "prompt_length_chars",
    "openqasm3_export_successful", "openqasm3_export_error",
    "qiskit_version", "transpilation_basis_gates",
    "prompt_token_count_cl100k", "output_token_count_cl100k",
    "code_lines",
    "is_unitary", "gate_set_diversity", "entanglement_depth",
    "unconnected_qubit_count",
    "api_deprecated_usage", "deprecated_api_patterns", "hallucination_type",
    "extraction_confidence", "contains_demo_scaffolding",
    "cleanup_candidate", "cleanup_rules_triggered",
    "transpilation_depth_ratio",
})

# ---------------------------------------------------------------------------
# Qiskit imports (done once at module level; torch311env has qiskit installed)
# ---------------------------------------------------------------------------
print("Importing Qiskit...", flush=True)
import qiskit
import numpy as np
from numpy import pi
import math

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit import transpile as qk_transpile
try:
    from qiskit import qasm3 as qk_qasm3
except Exception:
    qk_qasm3 = None
from qiskit.circuit import Parameter, ParameterVector
from qiskit.circuit.library import (
    PermutationGate,
    XGate, YGate, ZGate, HGate, SGate, TGate,
    CXGate, CZGate, CCXGate, SwapGate,
    RXGate, RYGate, RZGate,
    UGate, U1Gate, U2Gate, U3Gate,
)

try:
    import tiktoken
    _CL100K = tiktoken.get_encoding("cl100k_base")
except Exception:
    _CL100K = None

print("Qiskit ready.", flush=True)

# ---------------------------------------------------------------------------
# Complexity classification constants
# ---------------------------------------------------------------------------
CLIFFORD_GATES = {
    "h", "cx", "cy", "cz", "x", "y", "z",
    "s", "sdg", "swap", "iswap", "ecr",
}
UNIVERSAL_GATES = {"t", "tdg", "rz", "rx", "ry", "u", "u1", "u2", "u3", "ccx"}

SIZE_CLASSES = ["trivial", "simple", "moderate", "complex", "very_complex"]

# Transpilation target: IBM standard basis, no coupling map (backend-agnostic)
TRANSPILE_BASIS_GATES = ["cx", "rz", "sx", "x"]

# Deprecated Qiskit API patterns — text-level heuristic for staleness detection
DEPRECATED_PATTERNS = [
    "execute(",
    "Aer.get_backend(",
    "BasicAer",
]

EXTRACTION_DEMO_RULES = [
    ("print_call",            re.compile(r"(?m)^\s*print\s*\(")),
    ("display_call",          re.compile(r"(?m)^\s*display\s*\(")),
    ("draw_call",             re.compile(r"\.draw\s*\(")),
    ("matplotlib_plot",       re.compile(r"(?m)^\s*(?:plt\.\w+|from\s+matplotlib|import\s+matplotlib)")),
    ("matplotlib_magic",      re.compile(r"(?m)^\s*%matplotlib\b")),
    ("package_install",       re.compile(r"(?m)^\s*[!%]pip\b")),
    ("backend_run",           re.compile(r"\bbackend\.run\s*\(", re.IGNORECASE)),
    ("primitive_run",         re.compile(r"\b(?:sampler|estimator)\.run\s*\(", re.IGNORECASE)),
    ("job_result",            re.compile(r"\bjob\.result\s*\(", re.IGNORECASE)),
    ("result_inspection",     re.compile(r"\.(?:get_counts|get_statevector|get_unitary)\s*\(", re.IGNORECASE)),
]
EXTRACTION_CORE_HINTS = (
    "QuantumCircuit(",
    "TwoLocal(",
    "RealAmplitudes(",
    "EfficientSU2(",
    "QFT(",
    "ZZFeatureMap(",
    "PauliFeatureMap(",
    "NLocal(",
    "BlueprintCircuit(",
    "QuantumCircuit.from_qasm_str(",
)
EXTRACTION_GATE_SIGNAL_RE = re.compile(
    r"\.(?:h|x|y|z|s|sdg|t|tdg|cx|cy|cz|swap|ccx|cp|ch|rx|ry|rz|p|u|measure|"
    r"barrier|append|compose|decompose|measure_all|initialize|reset)\s*\(",
    re.IGNORECASE,
)

ROTATION_GATES = {
    "rx", "ry", "rz", "r", "p", "u", "u1", "u2", "u3",
    "rxx", "ryy", "rzz", "rzx", "xx_minus_yy", "xx_plus_yy",
}
ENTANGLING_GATE_NAMES = {
    "cx", "cy", "cz", "ch", "cp", "cu", "cu1", "cu2", "cu3",
    "swap", "iswap", "dcx", "ecr",
    "ccx", "ccz", "cswap", "c3x", "c4x",
}
STANDARD_GATES = (
    CLIFFORD_GATES | UNIVERSAL_GATES | ROTATION_GATES | ENTANGLING_GATE_NAMES
    | {"id", "sx", "sxdg", "x", "y", "z", "measure", "barrier", "reset", "delay"}
)
NON_GATE_OP_NAMES = {"measure", "barrier", "reset", "delay"}
CONTROL_FLOW_OP_NAMES = {
    "if_else", "while_loop", "for_loop", "switch_case",
    "break_loop", "continue_loop",
}


def circuit_snapshot(qc: QuantumCircuit) -> tuple:
    """Return a lightweight structural fingerprint for placeholder detection."""
    return (
        qc.num_qubits,
        qc.num_clbits,
        qc.size(),
        qc.depth(),
        tuple(sorted((str(k), int(v)) for k, v in qc.count_ops().items())),
    )


def token_count_cl100k(text: str):
    """Return cl100k token count or None if unavailable or text is empty."""
    if _CL100K is None or not text or not text.strip():
        return None
    try:
        return len(_CL100K.encode(text))
    except Exception:
        return None


def assess_extraction_quality(output_code: str, validation_status: str | None = None) -> dict:
    """
    Heuristic extraction-quality assessment.

    This does not modify the code. It only annotates whether the extracted block
    appears to contain tutorial/demo scaffolding in addition to circuit logic.
    """
    code = output_code or ""
    lines = [line for line in code.splitlines() if line.strip()]

    triggered = [
        name for name, pattern in EXTRACTION_DEMO_RULES
        if pattern.search(code)
    ]
    contains_demo_scaffolding = bool(triggered)

    has_core_constructor = any(hint in code for hint in EXTRACTION_CORE_HINTS)
    gate_signal_count = sum(
        1 for line in lines if EXTRACTION_GATE_SIGNAL_RE.search(line)
    )
    has_core_signal = has_core_constructor or gate_signal_count >= 2

    cleanup_candidate = contains_demo_scaffolding and has_core_signal

    if validation_status == "validated":
        extraction_confidence = "high" if not contains_demo_scaffolding else "medium"
    elif has_core_signal and validation_status not in {"syntax_error", "import_error"}:
        extraction_confidence = "medium" if not contains_demo_scaffolding else "low"
    else:
        extraction_confidence = "low"

    return {
        "extraction_confidence": extraction_confidence,
        "contains_demo_scaffolding": contains_demo_scaffolding,
        "cleanup_candidate": cleanup_candidate,
        "cleanup_rules_triggered": triggered,
    }


# ---------------------------------------------------------------------------
# Qiskit-version-safe instruction iterator
# ---------------------------------------------------------------------------
def _iter_instructions(qc):
    """Yield (operation, qubits, clbits) for every instruction in the circuit,
    compatible with both Qiskit < 0.45 (tuple) and ≥ 0.45 (CircuitInstruction)."""
    for item in qc.data:
        if hasattr(item, "operation"):
            yield item.operation, item.qubits, item.clbits
        else:
            yield item[0], item[1], item[2]


# ---------------------------------------------------------------------------
# New feature extractors
# ---------------------------------------------------------------------------
def compute_entanglement_features(qc) -> dict:
    """Count two-qubit gates and compute entangling ratio."""
    two_q = sum(1 for op, qubits, _ in _iter_instructions(qc) if len(qubits) >= 2)
    total = qc.size()
    ratio = round(two_q / total, 4) if total > 0 else 0.0
    return {
        "two_qubit_gate_count":  two_q,
        "entangling_gate_ratio": ratio,
    }


def compute_register_features(qc) -> dict:
    """Count quantum registers declared on the circuit."""
    return {
        "quantum_register_count": len(qc.qregs),
    }


def compute_multi_qubit_features(qc) -> dict:
    """Count non-metadata operations acting on three or more qubits."""
    count = sum(
        1
        for op, qubits, _ in _iter_instructions(qc)
        if len(qubits) >= 3 and op.name not in NON_GATE_OP_NAMES
    )
    return {
        "multi_qubit_gate_count": count,
    }


def compute_parameterization_features(qc) -> dict:
    """Extract parameter count, density, and reuse from a QuantumCircuit."""
    params = list(qc.parameters)
    n_params = len(params)
    density = round(n_params / qc.num_qubits, 4) if qc.num_qubits > 0 else 0.0

    # Parameter reuse: any Parameter object appears in more than one gate
    param_use_count: dict = {}
    for op, _, _ in _iter_instructions(qc):
        for p in op.params:
            if hasattr(p, "name"):           # it is a Parameter / ParameterExpression
                key = str(p)
                param_use_count[key] = param_use_count.get(key, 0) + 1
    reuse = any(v > 1 for v in param_use_count.values())

    return {
        "num_parameters":    n_params,
        "parameter_density": density,
        "parameter_reuse":   reuse,
    }


def compute_measurement_features(qc, gate_types: dict) -> dict:
    """Measurement count, reset usage, mid-circuit measurement, register count."""
    measurement_count = gate_types.get("measure", 0)
    reset_usage       = "reset" in gate_types

    # Mid-circuit measurement heuristic: a non-barrier instruction follows a measure
    mid_circuit = False
    seen_measure = False
    measured_qubits: set = set()
    for op, qubits, _ in _iter_instructions(qc):
        name = op.name
        if name == "measure":
            seen_measure = True
            for q in qubits:
                measured_qubits.add(q)
        elif seen_measure and name != "barrier":
            mid_circuit = True

    return {
        "measurement_count":        measurement_count,
        "measured_qubit_count":     len(measured_qubits),
        "reset_usage":              reset_usage,
        "mid_circuit_measurement":  mid_circuit,
        "classical_register_count": len(qc.cregs),
    }


def compute_gate_profile(gate_types: dict) -> dict:
    """Boolean structural fingerprint derived from gate_types dict."""
    gates = set(gate_types.keys())
    non_meta = gates - {"barrier", "measure", "reset", "delay", "id"}

    clifford_only = bool(non_meta) and non_meta.issubset(CLIFFORD_GATES)

    return {
        "has_clifford_only":    clifford_only,
        "has_clifford_t":       bool(gates & {"t", "tdg"}),
        "has_rotation_gates":   bool(gates & ROTATION_GATES),
        "has_entangling_gates": bool(gates & ENTANGLING_GATE_NAMES),
        "has_barriers":         "barrier" in gates,
        "has_custom_gates":     bool(gates - STANDARD_GATES),
    }


def compute_control_flow_features(qc) -> dict:
    """Flag dynamic / control-flow constructs present in the circuit."""
    count = sum(
        1
        for op, _, _ in _iter_instructions(qc)
        if getattr(op, "name", "") in CONTROL_FLOW_OP_NAMES
    )
    return {
        "has_control_flow": count > 0,
        "control_flow_op_count": count,
    }


def compute_unconnected_qubit_count(qc) -> int:
    """Count qubits declared in the circuit but never referenced by any instruction."""
    used_qubits: set = set()
    for op, qubits, _ in _iter_instructions(qc):
        for q in qubits:
            used_qubits.add(q)
    return max(0, qc.num_qubits - len(used_qubits))


def detect_deprecated_api_usage(output_code: str) -> tuple:
    """
    Scan raw output code for deprecated Qiskit API patterns.

    Returns (api_deprecated_usage, deprecated_api_patterns):
      api_deprecated_usage      bool | None — True if any pattern matched
      deprecated_api_patterns   list[str] | None — matched patterns (empty list if none)
    Returns (None, None) when output_code is empty or unavailable.
    """
    if not output_code or not output_code.strip():
        return None, None
    matched = [p for p in DEPRECATED_PATTERNS if p in output_code]
    return bool(matched), matched


def classify_hallucination_type(
    validation_status: str,
    validation_error_type: str,
    error_text: str = None,
) -> str:
    """
    Map validation outcome to a benchmark-grade diagnostic failure category.

    Priority order:
      validated           → none
      timeout             → timeout
      syntax_error        → syntax_failure
      import_error        → dependency_hallucination
      name_error          → symbol_resolution_failure
      no_circuit          → non_circuit_execution
      exec_error          → refined by error_type / error_text:
          index/register  → register_index_error
          attr/type/api   → api_hallucination
          fallback        → runtime_semantic_failure

    Returns None if validation_status is None or unrecognised.
    """
    if not validation_status:
        return None
    if validation_status == "validated":
        return "none"
    if validation_status == "timeout":
        return "timeout"
    if validation_status == "syntax_error":
        return "syntax_failure"
    if validation_status == "import_error":
        return "dependency_hallucination"
    if validation_status == "name_error":
        return "symbol_resolution_failure"
    if validation_status == "no_circuit":
        return "non_circuit_execution"
    if validation_status == "exec_error":
        combined = " ".join(filter(None, [
            (validation_error_type or "").lower(),
            (error_text or "").lower(),
        ]))
        if any(kw in combined for kw in ("indexerror", "index", "registerror")):
            return "register_index_error"
        if any(kw in combined for kw in ("attributeerror", "typeerror")):
            return "api_hallucination"
        return "runtime_semantic_failure"
    return None


def compute_transpilation_depth_ratio(transpiled_depth, circuit_depth) -> float:
    """
    Ratio of transpiled depth to original circuit depth.
    Returns None when transpilation failed or circuit_depth is zero.
    """
    if transpiled_depth is None or circuit_depth is None or circuit_depth == 0:
        return None
    return round(transpiled_depth / circuit_depth, 4)


def compute_topology_features(qc) -> dict:
    """Interaction graph metrics via networkx. Returns None values if networkx absent."""
    _null = {
        "interaction_graph_edges": None,
        "graph_density":           None,
        "max_qubit_degree":        None,
        "connected_components":    None,
    }
    try:
        import networkx as nx
    except ImportError:
        return _null

    n = qc.num_qubits
    if n == 0:
        return {k: 0 for k in _null}

    G = nx.Graph()
    G.add_nodes_from(range(n))

    # Build qubit-index lookup once
    qubit_index = {q: i for i, q in enumerate(qc.qubits)}
    for op, qubits, _ in _iter_instructions(qc):
        indices = [qubit_index[q] for q in qubits]
        if len(indices) >= 2:
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    G.add_edge(indices[i], indices[j])

    edges       = G.number_of_edges()
    max_poss    = n * (n - 1) / 2
    density     = round(edges / max_poss, 4) if max_poss > 0 else 0.0
    degrees     = [d for _, d in G.degree()]
    max_degree  = max(degrees) if degrees else 0
    components  = nx.number_connected_components(G)

    return {
        "interaction_graph_edges": edges,
        "graph_density":           density,
        "max_qubit_degree":        max_degree,
        "connected_components":    components,
    }


def compute_transpilation_features(qc) -> dict:
    """
    Transpile the circuit to the standard IBM basis gate set (no coupling map)
    and record post-transpilation metrics.

    Using optimization_level=1 and no coupling map gives backend-agnostic
    logical hardware cost — basis gate translation + light peephole optimisation,
    without device-specific routing overhead.

    Fields:
        transpiled_depth              int   depth after transpilation
        transpiled_gate_count         int   total gates after transpilation
        transpiled_cx_count           int   CNOT count (primary hardware cost)
        transpiled_single_qubit_count int   single-qubit gates after transpilation
        transpilation_overhead        float transpiled_gate_count / original gate_count
        transpilation_successful      bool
    """
    _null = {
        "transpiled_depth":               None,
        "transpiled_gate_count":          None,
        "transpiled_cx_count":            None,
        "transpiled_single_qubit_count":  None,
        "transpilation_overhead":         None,
        "transpilation_successful":       False,
        "transpilation_basis_gates":      list(TRANSPILE_BASIS_GATES),
        "transpilation_depth_ratio":      None,
    }
    try:
        tqc = qk_transpile(
            qc,
            basis_gates=TRANSPILE_BASIS_GATES,
            optimization_level=1,
        )
        gate_counts  = tqc.count_ops()
        cx_count     = gate_counts.get("cx", 0)
        total        = sum(gate_counts.values())
        sq_count     = total - cx_count
        original_total = qc.size()
        overhead = (
            round((total - original_total) / original_total, 4)
            if original_total > 0 else None
        )
        _t_depth = tqc.depth()
        return {
            "transpiled_depth":               _t_depth,
            "transpiled_gate_count":          total,
            "transpiled_cx_count":            cx_count,
            "transpiled_single_qubit_count":  sq_count,
            "transpilation_overhead":         overhead,
            "transpilation_successful":       True,
            "transpilation_basis_gates":      list(TRANSPILE_BASIS_GATES),
            "transpilation_depth_ratio":      compute_transpilation_depth_ratio(_t_depth, qc.depth()),
        }
    except Exception:
        return _null


def export_openqasm3(qc) -> tuple:
    """Export a QuantumCircuit to OpenQASM 3 with structured status info."""
    if qk_qasm3 is None:
        return None, False, "ImportError"
    try:
        return qk_qasm3.dumps(qc), True, None
    except Exception as exc:
        return None, False, exc.__class__.__name__


def compute_benchmark_difficulty(
    size_class: str,
    circuit_expressiveness: str,
    entangling_gate_ratio: float,
    num_parameters: int,
) -> str:
    """
    Composite benchmark_difficulty: easy / medium / hard.

    Score contributions:
      size_class (0–4) + expressiveness (0–2) +
      entangling ratio (0–2) + parameter count (0–2)
    Thresholds: easy ≤ 3 | medium 4–7 | hard ≥ 8
    """
    size_score = {
        "trivial": 0, "simple": 1, "moderate": 2,
        "complex": 3, "very_complex": 4,
    }.get(size_class, 2)

    expr_score = {
        "clifford": 0, "parameterized": 1, "universal": 2,
    }.get(circuit_expressiveness, 1)

    ent_score = (
        0 if entangling_gate_ratio < 0.1 else
        1 if entangling_gate_ratio < 0.3 else 2
    )

    param_score = (
        0 if num_parameters == 0 else
        1 if num_parameters <= 5 else 2
    )

    total = size_score + expr_score + ent_score + param_score
    if total <= 3:
        return "easy"
    if total <= 7:
        return "medium"
    return "hard"


def classify_expressiveness(gate_types: dict, is_parameterized: bool) -> str:
    """
    Return quantum computational expressiveness class.
      'parameterized' — circuit has free parameters (variational / PQC)
      'universal'     — contains T/Tdg or continuous rotation gates
      'clifford'      — all gates are Clifford; efficiently classically simulable
    """
    if is_parameterized:
        return "parameterized"
    gates_used = set(gate_types.keys())
    if gates_used & UNIVERSAL_GATES:
        return "universal"
    return "clifford"


def classify_size(num_qubits: int, circuit_depth: int, gate_count: int) -> str:
    """
    Return human-readable size class based on the maximum level implied by
    any of the three metrics.

    Thresholds:
      trivial     : qubits ≤ 2   | depth ≤ 2   | gates ≤ 3
      simple      : qubits 3–5   | depth 3–10  | gates 4–20
      moderate    : qubits 6–10  | depth 11–30 | gates 21–60
      complex     : qubits 11–20 | depth 31–80 | gates 61–200
      very_complex: qubits ≥ 21  | depth ≥ 81  | gates ≥ 201
    """
    def _qubit_level(n: int) -> int:
        if n <= 2:  return 0
        if n <= 5:  return 1
        if n <= 10: return 2
        if n <= 20: return 3
        return 4

    def _depth_level(d: int) -> int:
        if d <= 2:  return 0
        if d <= 10: return 1
        if d <= 30: return 2
        if d <= 80: return 3
        return 4

    def _gate_level(g: int) -> int:
        if g <= 3:   return 0
        if g <= 20:  return 1
        if g <= 60:  return 2
        if g <= 200: return 3
        return 4

    level = max(
        _qubit_level(num_qubits),
        _depth_level(circuit_depth),
        _gate_level(gate_count),
    )
    return SIZE_CLASSES[level]


# ---------------------------------------------------------------------------
# Rich exec namespace (mirrors make_namespace() from rescrape_broken.py /
# rebuild_clean.py, extended with library gate classes so circuits that
# instantiate gates directly can still run)
# ---------------------------------------------------------------------------
def make_namespace() -> dict:
    """Return a fresh dict suitable as exec() globals for circuit code."""
    n = 3
    qc = QuantumCircuit(QuantumRegister(n, "q"), ClassicalRegister(n, "cr"))
    qc2 = QuantumCircuit(QuantumRegister(n, "q"), ClassicalRegister(n, "cr"))
    circ = QuantumCircuit(n)
    ans = QuantumCircuit(n)
    ns = {
        # --- standard library ---
        "np": np, "pi": pi, "math": math,
        # --- Qiskit core ---
        "QuantumCircuit": QuantumCircuit,
        "QuantumRegister": QuantumRegister,
        "ClassicalRegister": ClassicalRegister,
        "Parameter": Parameter,
        "ParameterVector": ParameterVector,
        # --- gate classes ---
        "PermutationGate": PermutationGate,
        "XGate": XGate,  "YGate": YGate,  "ZGate": ZGate,  "HGate": HGate,
        "SGate": SGate,  "TGate": TGate,
        "CXGate": CXGate, "CZGate": CZGate, "CCXGate": CCXGate,
        "SwapGate": SwapGate,
        "RXGate": RXGate, "RYGate": RYGate, "RZGate": RZGate,
        "UGate": UGate,  "U1Gate": U1Gate, "U2Gate": U2Gate, "U3Gate": U3Gate,
        # --- common integer / size variables seen in circuit code ---
        "n": n, "num_qubits": n, "nqubits": n, "N_QUBITS": n,
        "nq": n, "n_qubits": n, "num_q": n, "nQubits": n,
        "Nwires": n, "N": n, "nb_qubits": n, "nb": n,
        "num_trash": 1, "num_latent": 1,
        "var_qubits": n, "output_qubit": n, "qubit": n,
        "REAL_DIST_NQUBITS": n, "number_state": n, "qN": n,
        # --- common angle variables ---
        "theta": pi / 4, "phi": pi / 2, "lam": pi / 3,
        "alpha": pi / 4, "beta": pi / 4, "gamma": pi / 4, "delta": pi / 4,
        "angle": pi / 4, "phase": pi / 4, "omega": 2 * pi / 8,
        # --- math function shortcuts (circuits that omit np. prefix) ---
        "sin": np.sin, "cos": np.cos, "exp": np.exp, "sqrt": np.sqrt,
        # --- common scalar variables (a/b used as qubit indices or angles) ---
        "a": 0.5, "b": 0.5, "t": 0.5, "u": 0.5,
        # --- common list variables ---
        "betas":  [pi / 4] * n,
        "gammas": [pi / 4] * n,
        "params": [pi / 4] * n,
        # --- pre-built registers (avoid NameError for bare register names) ---
        "q":     QuantumRegister(n, "q"),
        "qr":    QuantumRegister(n, "qr"),
        "cr":    ClassicalRegister(n, "cr"),
        "c":     ClassicalRegister(n, "c"),
        "cq":    ClassicalRegister(n, "cq"),
        "creg":  ClassicalRegister(n, "creg"),
        "qreg":  QuantumRegister(n, "qreg"),
        "qreg2": QuantumRegister(n, "qreg2"),
        "creg2": ClassicalRegister(n, "creg2"),
        "qr_state": QuantumRegister(n, "qr_state"),
        "qr_obj":   QuantumRegister(1, "qr_obj"),
        "i_q":  QuantumRegister(n, "i_q"),  "i_c":  ClassicalRegister(n, "i_c"),
        "ii_q": QuantumRegister(n, "ii_q"), "ii_c": ClassicalRegister(n, "ii_c"),
        "q1": QuantumRegister(n, "q1"), "q2": QuantumRegister(n, "q2"),
        "q3": QuantumRegister(n, "q3"),
        "qa": QuantumRegister(n, "qa"), "qb": QuantumRegister(n, "qb"),
        "qcar": QuantumRegister(1, "qcar"), "lq": QuantumRegister(n, "lq"),
        "sb":    QuantumRegister(1, "sb"),
        "ebit0": QuantumRegister(1, "ebit0"), "ebit1": QuantumRegister(1, "ebit1"),
        "c3":   ClassicalRegister(3, "c3"),
        "crx":  ClassicalRegister(n, "crx"), "crz": ClassicalRegister(n, "crz"),
        "qtemp":  QuantumRegister(n, "qtemp"),
        "qNtemp": QuantumRegister(n, "qNtemp"),
        # --- ancilla / auxiliary registers (usually 1 qubit) ---
        "anc":     QuantumRegister(1, "anc"),
        "ancilla": QuantumRegister(1, "ancilla"),
        "aux":     QuantumRegister(1, "aux"),
        "work":    QuantumRegister(1, "work"),
        "flag":    QuantumRegister(1, "flag"),
        # --- pre-built circuit placeholders (get overwritten by most code) ---
        "qc":   qc,
        "qc2":  qc2,
        "circ": circ,
        "ans":  ans,
        # --- common loop / index variables ---
        "i": 0, "j": 0, "k": 0, "m": 0,
        "G": np.eye(4),
        "pair": (0, 1),
    }
    ns["__seed_circuit_snapshots__"] = {
        id(qc): circuit_snapshot(qc),
        id(qc2): circuit_snapshot(qc2),
        id(circ): circuit_snapshot(circ),
        id(ans): circuit_snapshot(ans),
    }
    return ns


# ---------------------------------------------------------------------------
# Timeout-guarded exec that also returns the namespace on success
# ---------------------------------------------------------------------------
def exec_with_timeout(code: str, timeout: float = 3.0):
    """
    Execute *code* inside a fresh namespace, with a hard timeout.

    Returns (namespace_dict, None) on success, or (None, error_str) on
    failure / timeout.

    Uses a daemon thread + join(timeout) — the same pattern used by
    rescrape_broken.py.  The thread is left to expire naturally if it hangs
    (daemon=True ensures it won't block interpreter shutdown).
    """
    result_box = [None]   # result_box[0] = ns dict on success
    error_box  = [None]   # error_box[0]  = str on failure

    def _run():
        ns = make_namespace()
        try:
            exec(compile(code, "<string>", "exec"), ns)  # noqa: S102
            result_box[0] = ns
        except Exception as exc:
            error_box[0] = repr(exc)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout)

    if t.is_alive():
        return None, "TimeoutError: execution exceeded 3s"

    if result_box[0] is not None:
        return result_box[0], None

    return None, error_box[0] or "UnknownError"


def classify_validation_status(err: str | None, has_circuit: bool) -> tuple[str, str]:
    """
    Returns (validation_status, validation_error_type).

    validation_status:
      "validated"       — executed, QuantumCircuit found
      "timeout"         — exceeded 3s time limit
      "no_circuit"      — executed but no QuantumCircuit in namespace
      "import_error"    — ImportError / ModuleNotFoundError
      "name_error"      — NameError (missing symbol, often an unresolved dep)
      "syntax_error"    — SyntaxError (malformed code)
      "exec_error"      — any other execution error (likely noise)

    validation_error_type:
      The Python exception class name, or "" for validated/no_circuit.
    """
    if err is None and has_circuit:
        return "validated", ""
    if err is None and not has_circuit:
        return "no_circuit", ""
    if "TimeoutError" in err:
        return "timeout", "TimeoutError"
    # Extract the exception class name from repr()
    error_type = err.split("(")[0].split(".")[-1] if err else "UnknownError"
    if "ImportError" in err or "ModuleNotFoundError" in err:
        return "import_error", error_type
    if "NameError" in err:
        return "name_error", error_type
    if "SyntaxError" in err:
        return "syntax_error", error_type
    return "exec_error", error_type


# ---------------------------------------------------------------------------
# QuantumCircuit extraction from exec namespace
# ---------------------------------------------------------------------------
def is_untouched_seed_circuit(qc: QuantumCircuit, seed_snapshots: dict) -> bool:
    """Return True when *qc* is one of the seeded placeholders and still untouched."""
    baseline = seed_snapshots.get(id(qc))
    if baseline is None:
        return False
    try:
        return circuit_snapshot(qc) == baseline
    except Exception:
        return False


def extract_best_circuit(ns: dict):
    """
    Find all QuantumCircuit instances in the namespace and return the
    'most interesting' one (largest by num_qubits * depth as a proxy for
    the primary output circuit).

    Also searches one level inside lists and tuples to catch patterns like
    ``circuits = [qc1, qc2]`` or ``output = [final_circuit]``.

    Returns None if no QuantumCircuit found.
    """
    seed_snapshots = ns.get("__seed_circuit_snapshots__", {})
    circuits = []
    seen_ids: set[int] = set()

    def consider(item):
        if not isinstance(item, QuantumCircuit):
            return
        if is_untouched_seed_circuit(item, seed_snapshots):
            return
        item_id = id(item)
        if item_id in seen_ids:
            return
        seen_ids.add(item_id)
        circuits.append(item)

    for value in ns.values():
        consider(value)
    # Search inside list/tuple values (one level deep)
    for v in ns.values():
        if isinstance(v, (list, tuple)):
            for item in v:
                consider(item)
    if not circuits:
        return None
    if len(circuits) == 1:
        return circuits[0]

    # Score: prefer larger circuits; use the last one as a tiebreaker (it is
    # typically the final assembled circuit in sequential scripts).
    def score(qc):
        d = qc.depth()
        return qc.num_qubits * (d if d > 0 else 1)

    # Sort ascending, take the last (= largest score).
    circuits.sort(key=score)
    return circuits[-1]


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------
def extract_circuit_stats(qc: QuantumCircuit) -> dict:
    """
    Pull all desired metadata from a QuantumCircuit object and return a
    flat dict ready to be merged into the entry's metadata.
    """
    gate_types = {k: int(v) for k, v in qc.count_ops().items()}

    has_measurement        = "measure" in gate_types
    is_parameterized       = len(qc.parameters) > 0
    t_count                = gate_types.get("t", 0) + gate_types.get("tdg", 0)
    num_gate_types         = len(gate_types)
    _depth                 = qc.depth()
    _size                  = qc.size()
    avg_gates_per_layer    = round(_size / _depth, 4) if _depth > 0 else 0.0
    try:
        t_depth = qc.depth(filter_function=lambda x: x.operation.name in {"t", "tdg"})
    except Exception:
        t_depth = None
    try:
        entanglement_depth = qc.depth(filter_function=lambda x: len(x.qubits) >= 2)
    except Exception:
        entanglement_depth = None

    # Shannon entropy of gate-type distribution (bits); 0.0 for single-gate circuits
    _counts = [v for v in gate_types.values() if v > 0]
    _total  = sum(_counts)
    if _total > 0 and len(_counts) > 1:
        import math as _math
        gate_set_diversity = round(
            -sum((c / _total) * _math.log2(c / _total) for c in _counts), 4
        )
    else:
        gate_set_diversity = 0.0

    circuit_expressiveness = classify_expressiveness(gate_types, is_parameterized)
    size_class             = classify_size(qc.num_qubits, _depth, _size)

    entanglement  = compute_entanglement_features(qc)
    register_meta = compute_register_features(qc)
    multi_meta    = compute_multi_qubit_features(qc)
    params_meta   = compute_parameterization_features(qc)
    measure_meta  = compute_measurement_features(qc, gate_types)
    gate_profile  = compute_gate_profile(gate_types)
    control_meta  = compute_control_flow_features(qc)
    topology      = compute_topology_features(qc)
    transpilation = compute_transpilation_features(qc)

    is_unitary = (
        not measure_meta["measurement_count"]
        and not measure_meta["reset_usage"]
    )

    difficulty = compute_benchmark_difficulty(
        size_class,
        circuit_expressiveness,
        entanglement["entangling_gate_ratio"],
        params_meta["num_parameters"],
    )

    return {
        # ── Core circuit metrics ──────────────────────────────────────────
        "num_qubits":              qc.num_qubits,
        "num_clbits":              qc.num_clbits,
        "gate_count":              _size,
        "circuit_depth":           _depth,
        "circuit_width":           qc.width(),
        "unconnected_qubit_count": compute_unconnected_qubit_count(qc),
        "gate_types":              gate_types,
        "num_gate_types":          num_gate_types,
        "avg_gates_per_layer":     avg_gates_per_layer,
        "has_measurement":         has_measurement,
        "is_parameterized":        is_parameterized,
        "t_count":                 t_count,
        "t_depth":                 t_depth,
        **register_meta,
        **multi_meta,
        **control_meta,
        # ── XAI complexity indicators ─────────────────────────────────────
        "circuit_expressiveness":  circuit_expressiveness,
        "size_class":              size_class,
        "benchmark_difficulty":    difficulty,
        # ── Gate-set profile ──────────────────────────────────────────────
        **gate_profile,
        "is_unitary":          is_unitary,
        "gate_set_diversity":  gate_set_diversity,
        # ── Entanglement proxies ──────────────────────────────────────────
        **entanglement,
        "entanglement_depth":  entanglement_depth,
        # ── Parameterization metadata ─────────────────────────────────────
        **params_meta,
        # ── Measurement / output structure ────────────────────────────────
        **measure_meta,
        # ── Topology / interaction graph ──────────────────────────────────
        **topology,
        # ── Transpilation metrics (basis: cx/rz/sx/x, no coupling map) ────
        **transpilation,
        # ── Sentinel ─────────────────────────────────────────────────────
        "circuit_stats_available": True,
    }


# ---------------------------------------------------------------------------
# Per-entry enrichment
# ---------------------------------------------------------------------------
def enrich_entry(entry: dict) -> dict:
    """
    Attempt to execute the circuit code in *entry['output']* and append
    circuit stats to *entry['metadata']*.

    Always returns a (possibly unchanged) entry — never raises.
    """
    code  = entry.get("output", "")
    instr = entry.get("input", "")
    entry = dict(entry)                          # shallow copy
    entry["metadata"] = dict(entry["metadata"])  # copy metadata too

    # Prompt-side metadata (always computable, regardless of exec outcome)
    entry["metadata"]["prompt_word_count"]   = len(instr.split())
    entry["metadata"]["prompt_length_chars"] = len(instr)
    entry["metadata"]["prompt_token_count_cl100k"] = token_count_cl100k(instr)
    entry["metadata"]["output_token_count_cl100k"] = token_count_cl100k(code)
    entry["metadata"]["code_lines"]          = len([l for l in code.splitlines() if l.strip()])
    entry["metadata"]["qiskit_version"]      = getattr(qiskit, "__version__", "")

    # Deprecated-API detection — text-level, always computable from raw code
    dep_used, dep_patterns = detect_deprecated_api_usage(code)
    entry["metadata"]["api_deprecated_usage"]    = dep_used
    entry["metadata"]["deprecated_api_patterns"] = dep_patterns
    entry["metadata"]["openqasm3_export_successful"] = None
    entry["metadata"]["openqasm3_export_error"] = None
    entry["openqasm3_code"] = entry.get("openqasm3_code")

    if not code or not code.strip():
        entry["metadata"]["materialized_circuit"]     = False
        entry["metadata"]["circuit_stats_available"] = False
        entry["metadata"]["validation_status"]       = "exec_error"
        entry["metadata"]["validation_error_type"]   = "EmptyCode"
        entry["metadata"]["hallucination_type"]      = "runtime_semantic_failure"
        entry["metadata"].update(assess_extraction_quality(code, "exec_error"))
        return entry

    ns, err = exec_with_timeout(code, timeout=3.0)

    qc = extract_best_circuit(ns) if ns is not None else None
    v_status, v_err_type = classify_validation_status(err, qc is not None)

    entry["metadata"]["materialized_circuit"]   = qc is not None
    entry["metadata"]["validation_status"]     = v_status
    entry["metadata"]["validation_error_type"] = v_err_type
    entry["metadata"]["hallucination_type"]    = classify_hallucination_type(
        v_status, v_err_type, error_text=err
    )
    entry["metadata"].update(assess_extraction_quality(code, v_status))

    if qc is None:
        entry["metadata"]["circuit_stats_available"] = False
        return entry

    # Merge extracted stats into metadata
    stats = extract_circuit_stats(qc)
    entry["metadata"].update(stats)
    qasm_code, qasm_ok, qasm_err = export_openqasm3(qc)
    entry["openqasm3_code"] = qasm_code
    entry["metadata"]["openqasm3_export_successful"] = qasm_ok
    entry["metadata"]["openqasm3_export_error"] = qasm_err
    return entry


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def load_jsonl(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(entries: list, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Resume cache helpers
# ---------------------------------------------------------------------------
def load_cache(path: str) -> dict:
    """Load enrich_metadata_cache.jsonl. Returns dict keyed by circuit_hash."""
    cache: dict = {}
    if not os.path.exists(path):
        return cache
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                ch = rec.get("circuit_hash", "")
                if ch:
                    cache[ch] = rec
            except json.JSONDecodeError:
                pass
    return cache


def append_to_cache(entry: dict, path: str) -> None:
    """Append one enriched entry's computed fields to the cache file."""
    ch = entry.get("metadata", {}).get("circuit_hash", "")
    if not ch:
        return
    meta = entry.get("metadata", {})
    record = {
        "circuit_hash":   ch,
        "openqasm3_code": entry.get("openqasm3_code"),
        "enriched_meta":  {k: meta[k] for k in _ENRICHMENT_FIELDS if k in meta},
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def apply_cache_record(entry: dict, rec: dict) -> dict:
    """Patch an entry with cached enrichment results (no re-exec needed)."""
    entry = dict(entry)
    entry["metadata"] = dict(entry["metadata"])
    entry["metadata"].update(rec.get("enriched_meta", {}))
    entry["openqasm3_code"] = rec.get("openqasm3_code")
    return entry


def cache_record_is_complete(rec: dict, required_fields=None) -> bool:
    """Return True iff the cache record contains all required enrichment fields."""
    enriched_meta = rec.get("enriched_meta", {})
    fields = _ENRICHMENT_FIELDS if required_fields is None else set(required_fields)
    return all(field in enriched_meta for field in fields)


# ---------------------------------------------------------------------------
# Process a single split
# ---------------------------------------------------------------------------
def process_split(split_name: str, paths: dict, cache: dict) -> tuple:
    """
    Load, enrich, and write one split.

    Entries whose circuit_hash already exists in *cache* are restored from
    the cache instead of re-executed — making the run fully resume-safe.

    Returns (enriched_list, n_enriched, n_skipped, n_from_cache, complexity_counts).
    """
    print(f"\n[{split_name}] Loading {paths['input']} ...", flush=True)
    entries = load_jsonl(paths["input"])
    total = len(entries)
    print(f"[{split_name}] {total} entries to process.", flush=True)

    enriched_entries = []
    n_enriched    = 0
    n_skipped     = 0
    n_from_cache  = 0
    complexity_counts: dict = {}
    t0 = time.time()

    for idx, entry in enumerate(entries):
        ch = entry.get("metadata", {}).get("circuit_hash", "")
        if ch and ch in cache and cache_record_is_complete(cache[ch]):
            enriched = apply_cache_record(entry, cache[ch])
            n_from_cache += 1
        else:
            enriched = enrich_entry(entry)
            append_to_cache(enriched, CACHE_FILE)

        enriched_entries.append(enriched)

        if enriched["metadata"].get("circuit_stats_available"):
            n_enriched += 1
            cc = enriched["metadata"].get("size_class", "unknown")
            complexity_counts[cc] = complexity_counts.get(cc, 0) + 1
        else:
            n_skipped += 1

        # Progress every 500 entries
        if (idx + 1) % 500 == 0:
            elapsed = time.time() - t0
            pct = 100 * (idx + 1) / total
            print(
                f"  [{split_name}] {idx+1}/{total} ({pct:.1f}%)  "
                f"enriched={n_enriched}  skipped={n_skipped}  "
                f"cached={n_from_cache}  elapsed={elapsed:.0f}s",
                flush=True,
            )

    elapsed = time.time() - t0
    print(
        f"[{split_name}] Done in {elapsed:.1f}s  "
        f"enriched={n_enriched}  skipped={n_skipped}  cached={n_from_cache}",
        flush=True,
    )

    # Write to tmp path first — we rename to overwrite originals only after
    # ALL splits complete without crashing.
    print(f"[{split_name}] Writing tmp → {paths['tmp']}", flush=True)
    write_jsonl(enriched_entries, paths["tmp"])

    return enriched_entries, n_enriched, n_skipped, n_from_cache, complexity_counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    overall_t0 = time.time()

    # Load per-entry resume cache (empty dict if first run)
    print(f"Loading resume cache from {CACHE_FILE} ...", flush=True)
    cache = load_cache(CACHE_FILE)
    print(f"  Cache entries loaded: {len(cache):,}", flush=True)

    results = {}  # split_name → (n_enriched, n_skipped, n_from_cache, complexity_counts)

    # --- Process all splits (skip missing files, e.g. test_clean before split step) ---
    active_splits = {k: v for k, v in SPLITS.items() if os.path.exists(v["input"])}
    for split_name, paths in active_splits.items():
        _, n_enriched, n_skipped, n_from_cache, cc_counts = process_split(
            split_name, paths, cache
        )
        results[split_name] = (n_enriched, n_skipped, n_from_cache, cc_counts)

    # --- All splits completed; atomically rename tmp → original ---
    print(f"\n{len(active_splits)} split(s) complete. Renaming tmp files...",
          flush=True)

    for split_name, paths in active_splits.items():
        tmp_path  = paths["tmp"]
        orig_path = paths["input"]
        os.replace(tmp_path, orig_path)
        print(f"  Renamed {tmp_path} -> {orig_path}", flush=True)

    # --- Final summary ---
    total_enriched   = sum(v[0] for v in results.values())
    total_skipped    = sum(v[1] for v in results.values())
    total_from_cache = sum(v[2] for v in results.values())
    total_entries    = total_enriched + total_skipped
    overall_elapsed  = time.time() - overall_t0

    combined_cc: dict = {}
    for _, (_, _, _, cc_counts) in results.items():
        for cc, cnt in cc_counts.items():
            combined_cc[cc] = combined_cc.get(cc, 0) + cnt

    print("\n" + "=" * 55, flush=True)
    print("=== ENRICHMENT SUMMARY ===", flush=True)
    print(f"Total entries  : {total_entries}", flush=True)
    print(f"Enriched (OK)  : {total_enriched}  "
          f"({100 * total_enriched / max(total_entries, 1):.1f}%)", flush=True)
    print(f"From cache     : {total_from_cache}  "
          f"({100 * total_from_cache / max(total_entries, 1):.1f}%)", flush=True)
    print(f"Skipped        : {total_skipped}  "
          f"({100 * total_skipped  / max(total_entries, 1):.1f}%)", flush=True)
    print(f"Elapsed        : {overall_elapsed:.1f}s", flush=True)

    print("\nBy split:", flush=True)
    for split_name, (n_enriched, n_skipped, n_from_cache, _) in results.items():
        n_total = n_enriched + n_skipped
        print(f"  {split_name:<12} enriched={n_enriched}  "
              f"cached={n_from_cache}  skipped={n_skipped}  total={n_total}", flush=True)

    print("\nBy size_class (enriched entries only):", flush=True)
    for cc in ["trivial", "simple", "moderate", "complex", "very_complex", "unknown"]:
        cnt = combined_cc.get(cc, 0)
        if cnt:
            print(f"  {cc:<16} {cnt}", flush=True)

    print("=" * 55, flush=True)


if __name__ == "__main__":
    main()
