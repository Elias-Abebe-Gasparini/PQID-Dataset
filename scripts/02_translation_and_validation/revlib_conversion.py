import os
import json
from qiskit import QuantumCircuit
from qiskit.qasm3 import dumps

# Base URL for reference
REVLIB_BASE_URL = "https://www.revlib.org/documents/real/"

# --- Gate translation logic ---
def apply_revlib_gate(qc, gate_line, qubit_names, qubit_map):
    gate_parts = gate_line.strip().split()
    gate_type = gate_parts[0].lower()
    operands = [qubit_map[q] for q in gate_parts[1:]]

    if gate_type == "t1":
        qc.x(operands[0])
    elif gate_type == "t2":
        qc.cx(operands[0], operands[1])
    elif gate_type == "t3":
        qc.ccx(operands[0], operands[1], operands[2])
    elif gate_type.startswith("t") and gate_type[1:].isdigit():
        qc.mcx(operands[:-1], operands[-1])
    elif gate_type == "p":
        if len(operands) == 3:
            qc.ccx(*operands)
        else:
            raise ValueError(f"Unsupported operand count for 'p': {gate_line}")
    elif gate_type == "v":
        qc.s(operands[0])
    elif gate_type in ("v+", "vplus"):
        qc.sdg(operands[0])
    elif gate_type.startswith("f") and gate_type[1:].isdigit():
        control = operands[0]
        targets = operands[1:]
        for target in targets:
            qc.cx(control, target)
    elif gate_type in ("f+", "fplus"):
        control = operands[0]
        targets = operands[1:]
        for target in targets:
            qc.cx(control, target)
    else:
        raise NotImplementedError(f"Unsupported gate type: {gate_type} in line: {gate_line}")

# --- File parser ---
def parse_real_file(filepath):
    with open(filepath, "r") as f:
        lines = f.readlines()

    var_names = []
    gate_lines = []
    reading_gates = False

    for line in lines:
        line = line.strip()
        if line.startswith(".variables"):
            var_names = line.split()[1:]
        elif line == ".begin":
            reading_gates = True
        elif line == ".end":
            reading_gates = False
        elif reading_gates:
            gate_lines.append(line)

    qubit_map = {name: idx for idx, name in enumerate(var_names)}
    qc = QuantumCircuit(len(var_names), name=os.path.basename(filepath).replace(".real", ""))

    for gate_line in gate_lines:
        apply_revlib_gate(qc, gate_line, var_names, qubit_map)

    return qc

# --- Main batch converter ---
def convert_real_folder_to_jsonl(input_dir, output_file, log_file="revlib_conversion_failures.log"):
    results = []
    failures = []

    for fname in sorted(os.listdir(input_dir)):
        if fname.endswith(".real"):
            fpath = os.path.join(input_dir, fname)
            try:
                qc = parse_real_file(fpath)
                qasm3 = dumps(qc)
                results.append({
                    "file": fname,
                    "revlib_url": f"{REVLIB_BASE_URL}{fname}",
                    "circuit_code": qasm3
                })
            except Exception as e:
                error_msg = f"{fname} – {e}"
                print(f"❌ Failed: {error_msg}")
                failures.append(error_msg)

    # Save results
    with open(output_file, "w") as fout:
        for entry in results:
            fout.write(json.dumps(entry) + "\n")

    # Save failures
    if failures:
        with open(log_file, "w") as flog:
            for fail in failures:
                flog.write(fail + "\n")

    print(f"\n✅ Done: {len(results)} circuits written to {output_file}")
    print(f"❌ Failed: {len(failures)} circuits. See {log_file}")
    print("🔄 Conversion complete!")

# --- Run script ---
if __name__ == "__main__":
    input_dir = "revlib_gates_extracted"  # Replace with your actual folder path
    output_file = "revlib_gates_converted.jsonl"
    convert_real_folder_to_jsonl(input_dir, output_file)
