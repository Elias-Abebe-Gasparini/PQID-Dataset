import json

def flatten_circuit_snippets(input_path: str, output_path: str):
    total = 0
    written = 0

    with open(input_path, "r", encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            total += 1
            data = json.loads(line)
            if "circuit_code" in data and data["circuit_code"].strip():
                minimal = {
                    "file": data.get("file", ""),
                    "github_anchor": data.get("github_anchor", ""),
                    "circuit_code": data["circuit_code"].strip()
                }
                fout.write(json.dumps(minimal) + "\n")
                written += 1

    print("✅ Flattening Summary")
    print(f"Total entries processed : {total}")
    print(f"Circuit snippets saved  : {written}")
    print(f"✔️ Output written to     : {output_path}")

if __name__ == "__main__":
    flatten_circuit_snippets("detected_circuit_snippets_with_lines.jsonl", "flat_circuits.jsonl")
