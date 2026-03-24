import json
import traceback
from qiskit import QuantumCircuit
from qiskit.qasm3 import dumps as qasm3_dumps

INPUT_JSONL = "circuits_with_urls.jsonl"
OUTPUT_JSONL = "detected_circuits_with_qasm3.jsonl"

def add_qasm3(snippet_dict):
    try:
        namespace = {}
        exec(snippet_dict["circuit_code"], {}, namespace)
        qc = next((v for v in namespace.values() if isinstance(v, QuantumCircuit)), None)
        if qc is not None:
            snippet_dict["qasm3"] = qasm3_dumps(qc)
        else:
            snippet_dict["qasm3"] = None
    except Exception:
        snippet_dict["qasm3"] = None
        snippet_dict["qasm3_error"] = traceback.format_exc()
    return snippet_dict

def process_all():
    with open(INPUT_JSONL, "r", encoding="utf-8") as fin, \
        open(OUTPUT_JSONL, "w", encoding="utf-8") as fout:
        
        count_total = 0
        count_success = 0
        
        for line in fin:
            count_total += 1
            item = json.loads(line)
            updated = add_qasm3(item)
            if updated["qasm3"]:
                count_success += 1
            fout.write(json.dumps(updated) + "\n")
        
        print("✅ Done!")
        print(f"Total circuits processed : {count_total}")
        print(f"Successfully parsed to QASM3 : {count_success}")
        print(f"❌ Failed to parse         : {count_total - count_success}")
        print(f"📝 Output written to      : {OUTPUT_JSONL}")

if __name__ == "__main__":
    process_all()
