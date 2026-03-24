import os
import json

# Step 1: Load GitHub URLs
def load_repo_urls(url_file):
    repo_map = {}
    with open(url_file, 'r', encoding='utf-8') as f:
        for line in f:
            url = line.strip()
            if not url:
                continue
            repo_name = url.rstrip('/').split('/')[-1]
            repo_map[repo_name] = url
    return repo_map

# Step 2: Generate GitHub links
def build_github_url(file_path, start_line, end_line, repo_map):
    parts = file_path.split('/')
    try:
        repo_index = parts.index("quantum_repos") + 1
        repo_name = parts[repo_index]
        if repo_name not in repo_map:
            return None  # No matching repo
        rel_path = "/".join(parts[repo_index+1:])
        return f"{repo_map[repo_name]}/blob/main/{rel_path}#L{start_line}-L{end_line}"
    except (ValueError, IndexError):
        return None

# Step 3: Augment JSONL with GitHub URLs
def attach_urls_to_circuits(data_file, url_file, output_file):
    repo_map = load_repo_urls(url_file)
    enriched = []
    with open(data_file, 'r', encoding='utf-8') as fin:
        for line in fin:
            item = json.loads(line)
            url = build_github_url(item['file'], item['start_line'], item['end_line'], repo_map)
            if url:
                item['github_url'] = url
            enriched.append(item)

    with open(output_file, 'w', encoding='utf-8') as fout:
        for item in enriched:
            fout.write(json.dumps(item) + '\n')

    print("✅ URLs attached.")
    print(f"✔️ Total entries processed: {len(enriched)}")
    print(f"📄 Output saved to: {output_file}")

# ---------- CONFIGURE AND RUN ----------
if __name__ == "__main__":
    attach_urls_to_circuits(
        data_file="detected_circuit_snippets_with_lines.jsonl",
        url_file="github_urls.txt",  # <-- replace with your actual file
        output_file="circuits_with_urls.jsonl"
    )
