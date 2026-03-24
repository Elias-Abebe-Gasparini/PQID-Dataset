import json

def merge_jsonl_files(input_files, output_file):
    with open(output_file, "w", encoding="utf-8") as outfile:
        for file in input_files:
            with open(file, "r", encoding="utf-8") as infile:
                for line in infile:
                    try:
                        entry = json.loads(line)
                        outfile.write(json.dumps(entry) + "\n")
                    except json.JSONDecodeError as e:
                        print(f"Skipped invalid line in {file}: {e}")

if __name__ == "__main__":
    input_files = [
        "revlib_gates_converted.jsonl",
        "revlib_failed_files_fixed.jsonl",
        "revlib_remaining_failed_files_fixed.jsonl"
    ]
    output_file = "revlib_full_final_dataset.jsonl"
    merge_jsonl_files(input_files, output_file)

    print(f"✅ All files merged into {output_file}")
    print("🧷 Total unique circuit blocks written: ", sum(1 for _ in open(output_file, "r", encoding="utf-8")))
    print("✅ Merging completed successfully.")
    print("🎉 All operations completed successfully.")
    