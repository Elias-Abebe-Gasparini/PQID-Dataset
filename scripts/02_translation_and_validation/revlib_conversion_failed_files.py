import os
import json
from qiskit import QuantumCircuit
from qiskit.qasm3 import dumps

REVLIB_BASE_URL = "https://www.revlib.org/documents/real/"

def apply_revlib_gate(qc, gate_line, qubit_names, qubit_map):
    gate_parts = gate_line.strip().split()
    gate_type = gate_parts[0].lower()
    try:
        operands = [qubit_map[q] for q in gate_parts[1:]]
    except KeyError as e:
        raise ValueError(f"Unknown variable name '{e.args[0]}' found in line: {gate_line}")

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
    elif gate_type == "pi":
        for i in range(len(operands) - 1):
            qc.swap(operands[i], operands[i + 1])
    else:
        raise NotImplementedError(f"Unsupported gate type: {gate_type} in line: {gate_line}")

def parse_real_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
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

def convert_failed_files(input_dir, output_file, failed_files_list):
    results, failures = [], []

    with open(failed_files_list, 'r') as ff:
        filenames = [line.strip() for line in ff if line.strip()]

    for fname in filenames:
        fpath = os.path.join(input_dir, fname)
        try:
            qc = parse_real_file(fpath)
            qasm3 = dumps(qc)  # Corrected method to get QASM
            results.append({
                "file": fname,
                "revlib_url": f"{REVLIB_BASE_URL}{fname}",
                "circuit_code": qasm3
            })
            print(f"✅ Converted: {fname}")
        except Exception as e:
            error_msg = f"{fname} – {e}"
            print(f"❌ Failed again: {error_msg}")
            failures.append(error_msg)

    with open(output_file, "w") as fout:
        for entry in results:
            fout.write(json.dumps(entry) + "\n")

    if failures:
        with open("remaining_failures.log", "w") as flog:
            for fail in failures:
                flog.write(fail + "\n")

    print(f"\n✅ Done: {len(results)} previously failed circuits converted to {output_file}")
    if failures:
        print(f"❌ Still failing: {len(failures)} files. See remaining_failures.log")
    else:
        print("All previously failed files successfully converted!")

if __name__ == "__main__":
    input_dir = "revlib_gates_extracted"
    output_file = "revlib_failed_files_fixed.jsonl"
    failed_files_list = "revlib_failed_files.txt"

    convert_failed_files(input_dir, output_file, failed_files_list)
