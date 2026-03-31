import os
import json

def harmonize_revlib(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as fin, \
        open(output_file, 'w', encoding='utf-8') as fout:

        for line in fin:
            entry = json.loads(line)
            fout.write(json.dumps({
                "source": "revlib",
                "original_url": entry["revlib_url"],
                "circuit_name": entry["file"].replace(".real", ""),
                "circuit_code": entry["circuit_code"],
                "language": "qasm",
                "metadata": {
                    "filename": entry["file"],
                    "revlib_url": entry["revlib_url"]
                }
            }) + "\n")

def harmonize_github(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as fin, \
        open(output_file, 'w', encoding='utf-8') as fout:

        for line in fin:
            entry = json.loads(line)

            harmonized = {
                "source": "github",
                "original_url": entry["github_url"],
                "circuit_name": entry["file"].split("/")[-1].replace(".py", ""),
                "circuit_code": entry["circuit_code"],
                "language": "python",
                "metadata": {
                    "file_path": entry["file"],
                    "start_line": entry.get("start_line"),
                    "end_line": entry.get("end_line"),
                    "hash": entry.get("hash"),
                    "github_anchor": entry.get("github_anchor")
                }
            }

            fout.write(json.dumps(harmonized) + "\n")

def merge_datasets(harmonized_files, output_file):
    all_entries = []
    for file in harmonized_files:
        with open(file, 'r', encoding='utf-8') as f:
            all_entries.extend(json.loads(line) for line in f)

    with open(output_file, 'w', encoding='utf-8') as fout:
        for entry in all_entries:
            fout.write(json.dumps(entry) + "\n")

    print(f"✅ Merged {len(harmonized_files)} datasets into {output_file}")

if __name__ == "__main__":
    harmonize_revlib("revlib_full_final_dataset.jsonl", "revlib_harmonized.jsonl")
    harmonize_github("circuits_with_urls.jsonl", "github_harmonized.jsonl")
    merge_datasets(["revlib_harmonized.jsonl", "github_harmonized.jsonl"], "merged_circuit_dataset.jsonl")
    print("✅ Harmonization and merging completed.")
    print("✅ All datasets harmonized and merged successfully.")