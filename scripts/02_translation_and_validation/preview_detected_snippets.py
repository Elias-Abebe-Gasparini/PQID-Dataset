import json

def preview_detected_snippets(file_path: str, num_preview: int = 5):
    total_entries = 0
    all_snippets = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            total_entries += 1
            data = json.loads(line)
            snippet = data.get("circuit_code", "").strip()
            if snippet:
                all_snippets.append(snippet)

    print("✅ Assignment-Based Circuit Preview")
    print(f"Total entries scanned : {total_entries}")
    print(f"Valid circuits found  : {len(all_snippets)}")
    print("\n--- First {} circuit snippets ---\n".format(min(num_preview, len(all_snippets))))

    for snippet in all_snippets[:num_preview]:
        print(snippet)
        print("-" * 50)

# ---- Run It ----
if __name__ == "__main__":
    preview_detected_snippets("detected_circuit_snippets_with_lines.jsonl", num_preview=20)
