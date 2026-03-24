import re
import json

def extract_circuit_assignments(code: str) -> list:
    # This regex looks for any assignment to QuantumCircuit
    pattern = r"(\w+\s*=\s*QuantumCircuit\s*\([^\)]*\).+?)(?=\n\S|\Z)"
    matches = re.findall(pattern, code, flags=re.DOTALL)
    return matches

def preview_assignments(file_path: str):
    total_entries = 0
    total_hits = 0
    all_matches = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            total_entries += 1
            data = json.loads(line)
            code = data.get("circuit_code", "")
            matches = extract_circuit_assignments(code)
            if matches:
                total_hits += 1
                all_matches.extend(matches)

    print("✅ Assignment-Based Circuit Preview")
    print(f"Total entries scanned : {total_entries}")
    print(f"Entries with matches  : {total_hits}")
    print(f"Total snippets found  : {len(all_matches)}")
    print("\n--- First 5 circuit snippets ---\n")
    for snippet in all_matches[:5]:
        print(snippet.strip(), "\n", "-"*50)

# Run this
if __name__ == "__main__":
    preview_assignments("cleaned_circuits.jsonl")
