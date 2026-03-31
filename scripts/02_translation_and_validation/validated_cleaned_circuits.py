import re
import json
import os
import hashlib

# Configuration for GitHub repo mapping
LOCAL_BASE = "quantum_repos"
GITHUB_BASE = "https://github.com"

REPO_MAP = {
    "dsm-swap": "quantumlib/dsm-swap",
    "ffsim": "quantumlib/ffsim",
    "feedback": "yourorg/feedback",  # Replace with real repo/org
}

# ---- Circuit Extraction ----
def extract_filtered_circuit_blocks_with_lines(code: str) -> list:
    pattern = r"(\w+\s*=\s*QuantumCircuit\s*\([^\)]*\).+?)(?=\n\S|\Z)"
    matches = []

    for match in re.finditer(pattern, code, flags=re.DOTALL):
        snippet = match.group(1).strip()
        if re.match(r"^\s*circuit\s*=", snippet):  # Skip internal wrapper circuits
            continue

        start_char = match.start()
        end_char = match.end()
        start_line = code[:start_char].count("\n") + 1
        end_line = code[:end_char].count("\n") + 1

        matches.append({
            "snippet": snippet,
            "start_line": start_line,
            "end_line": end_line
        })

    return matches

# ---- GitHub Link Generator ----
def infer_github_url(file_path: str, start: int, end: int) -> str:
    parts = file_path.split("/")
    if len(parts) < 2 or not file_path.startswith(LOCAL_BASE):
        return None
    repo_name = parts[1]
    github_repo = REPO_MAP.get(repo_name)
    if not github_repo:
        return None
    rel_path = "/".join(parts[2:])
    return f"{GITHUB_BASE}/{github_repo}/blob/main/{rel_path}#L{start}-L{end}"

# ---- Extraction + Saving ----
def extract_and_save_with_lines(file_path: str, output_path: str):
    total_entries = 0
    total_hits = 0
    all_snippets = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            total_entries += 1
            data = json.loads(line)
            code = data.get("circuit_code", "")
            file_path_rel = data.get("file", "").replace("\\", "/")

            blocks = extract_filtered_circuit_blocks_with_lines(code)
            if blocks:
                total_hits += 1
                for block in blocks:
                    snippet = block["snippet"]
                    snippet_hash = hashlib.md5(snippet.encode("utf-8")).hexdigest()
                    github_url = infer_github_url(file_path_rel, block["start_line"], block["end_line"])

                    all_snippets.append({
                        "file": file_path_rel,
                        "start_line": block["start_line"],
                        "end_line": block["end_line"],
                        "github_anchor": f"#L{block['start_line']}-L{block['end_line']}",
                        "github_url": github_url,
                        "hash": snippet_hash,
                        "circuit_code": snippet
                    })

    with open(output_path, "w", encoding="utf-8") as fout:
        for item in all_snippets:
            fout.write(json.dumps(item) + "\n")

    print("✅ Summary:")
    print(f"Total entries scanned : {total_entries}")
    print(f"Valid circuits found  : {len(all_snippets)}")
    print(f"Rejected entries      : {total_entries - total_hits}")
    print(f"✔️ Saved to            : {output_path}")
    print("✅ Done!")

# ---- Run the script ----
if __name__ == "__main__":
    extract_and_save_with_lines("cleaned_circuits.jsonl", "detected_circuit_snippets_with_lines.jsonl")
