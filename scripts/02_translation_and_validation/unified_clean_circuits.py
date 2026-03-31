import re
import json
import hashlib
import argparse
from typing import List, Dict, Any
from qiskit import QuantumCircuit, transpile
from qiskit.converters import circuit_to_dag

# ---- Normalization ----
def normalize_code(code: str) -> str:
    lines = [line.rstrip() for line in code.strip().split('\n')]
    return '\n'.join(lines)

# ---- Static Analysis ----
def extract_static_metadata(code: str) -> Dict[str, Any]:
    metadata = {
        "num_qubits": None,
        "has_measurement": False,
        "gate_types": set(),
    }

    match = re.search(r"QuantumCircuit\((\d+)", code)
    if match:
        metadata["num_qubits"] = int(match.group(1))

    if re.search(r"\.measure\(|\.measure_all\(|c_if", code):
        metadata["has_measurement"] = True

    gates = [
        'cx', 'cz', 'x', 'y', 'z', 'h', 't', 'tdg', 'rz', 'ry', 'rx', 'u3', 'swap', 'ccx',
        's', 'sdg', 'rxx', 'rzz', 'rxy', 'rccx', 'rcrz', 'crx', 'crz', 'cu1', 'cu3', 'cu2',
        'phase', 'iswap', 'cswap', 'rcrx', 'rccz', 'rccy', 'p', 'sx'
    ]
    for gate in gates:
        if re.search(rf"\.{gate}\(", code):
            metadata["gate_types"].add(gate)

    return metadata

# ---- Hashing ----
def compute_hash(code: str) -> str:
    return hashlib.md5(code.encode('utf-8')).hexdigest()

# ---- Extract Circuits ----
def extract_circuits(code: str) -> List[QuantumCircuit]:
    local_vars = {}
    try:
        exec(code, {}, local_vars)
        return [v for v in local_vars.values() if isinstance(v, QuantumCircuit)]
    except Exception:
        return []

# ---- Dynamic Metadata ----
def enrich_with_dynamic_metadata(qc: QuantumCircuit) -> Dict[str, Any]:
    try:
        transpiled = transpile(qc, basis_gates=["cx", "u3"], optimization_level=2)
        qasm3 = transpiled.qasm()

        try:
            QuantumCircuit.from_qasm_str(qasm3)  # Validate QASM round trip
        except Exception:
            qasm3 = None  # Invalidate if it fails

        return {
            "depth": transpiled.depth(),
            "size": transpiled.size(),
            "width": transpiled.num_qubits,
            "cnots": transpiled.count_ops().get("cx", 0),
            "qasm3": qasm3,
        }
    except Exception as e:
        return {"error": f"transpile_error: {str(e)}"}

# ---- Main Cleaning Logic ----
def clean_dataset(raw_data: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    cleaned = []
    seen_hashes = set()

    for entry in raw_data:
        raw_code = entry.get("circuit", "")
        normalized_code = normalize_code(raw_code)
        code_hash = compute_hash(normalized_code)

        if code_hash in seen_hashes:
            continue
        seen_hashes.add(code_hash)

        static_meta = extract_static_metadata(normalized_code)
        circuits = extract_circuits(normalized_code)

        if not circuits:
            cleaned.append({
                "file": entry.get("file", ""),
                "function": "extracted#0",
                "hash": code_hash,
                "circuit_code": normalized_code,
                "num_qubits": static_meta["num_qubits"],
                "has_measurement": static_meta["has_measurement"],
                "gate_types": sorted(static_meta["gate_types"]),
                "error": "no_quantum_circuit_found"
            })
            continue

        for idx, qc in enumerate(circuits):
            dynamic_meta = enrich_with_dynamic_metadata(qc)

            record = {
                "file": entry.get("file", ""),
                "function": f"extracted#{idx}",
                "circuit_code": normalized_code,
                "hash": f"{code_hash}_{idx}",
                "num_qubits": static_meta["num_qubits"],
                "has_measurement": static_meta["has_measurement"],
                "gate_types": sorted(static_meta["gate_types"]),
                "source_type": "exec"
            }
            record.update(dynamic_meta)
            cleaned.append(record)

    return cleaned

# ---- CLI Entrypoint ----
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="all_circuits_structured.jsonl", help="Input .jsonl file")
    parser.add_argument("--output", default="cleaned_circuits.jsonl", help="Output .jsonl file")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        raw_data = [json.loads(line) for line in f]

    cleaned = clean_dataset(raw_data)

    with open(args.output, "w", encoding="utf-8") as f_out:
        for item in cleaned:
            f_out.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"✅ Saved {len(cleaned)} cleaned circuits to {args.output}")


if __name__ == "__main__":
    main()
