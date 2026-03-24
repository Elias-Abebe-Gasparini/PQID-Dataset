import os
import json
import ast
import nbformat
import autopep8

REPO_DIR = "quantum_repos"
PY_OUTPUT = "extracted_py_blocks.jsonl"
NB_OUTPUT = "extracted_nb_blocks.jsonl"
FINAL_OUTPUT = "all_circuits_structured.jsonl"

def clean_python_files(repo_dir):
    print("🧼 Cleaning Python files...")
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "tests")]
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        code = f.read()
                    fixed = autopep8.fix_code(code)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(fixed)
                except Exception as e:
                    print(f"⚠️ Failed to clean {path}: {e}")
    print("✅ Python formatting complete.\n")

def extract_qc_blocks(source, path):
    results = []
    lines = source.split('\n')
    block = []
    collecting = False
    block_vars = set()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(("\"\"\"", "'''")):
            continue

        if "QuantumCircuit" in stripped:
            collecting = True
            block = [line]
            var_name = stripped.split("=")[0].strip() if "=" in stripped else "circuit"
            block_vars = {var_name}
        elif collecting:
            block.append(line)
            if any(var + "." in stripped for var in block_vars):
                continue
            if any(k in stripped for k in ("draw(", "measure_all()", "depth()", "decompose()", "bind_parameters")):
                results.append({"file": path, "circuit": "\n".join(block).strip()})
                collecting = False
                block = []
                block_vars = set()
    if collecting and block:
        results.append({"file": path, "circuit": "\n".join(block).strip()})
    return results

def extract_from_py(repo_dir, output_path):
    print("🔍 Extracting structured blocks from .py files...")
    extracted = []
    for root, _, files in os.walk(repo_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        source = f.read()
                    extracted.extend(extract_qc_blocks(source, path))
                except Exception as e:
                    print(f"❌ Failed to read {path}: {e}")
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in extracted:
            json.dump(entry, f)
            f.write("\n")
    print(f"✅ Extracted {len(extracted)} circuit blocks from Python files.\n")

def extract_from_ipynb(repo_dir, output_path):
    print("📓 Extracting structured blocks from .ipynb notebooks...")
    extracted = []
    for root, _, files in os.walk(repo_dir):
        for file in files:
            if file.endswith(".ipynb"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        nb = nbformat.read(f, as_version=4)
                    for cell in nb.cells:
                        if cell.cell_type == "code":
                            extracted.extend(extract_qc_blocks(cell.source, path))
                except Exception as e:
                    print(f"❌ Failed to parse notebook {path}: {e}")
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in extracted:
            json.dump(entry, f)
            f.write("\n")
    print(f"✅ Extracted {len(extracted)} circuit blocks from notebooks.\n")

def merge_jsonls(inputs, output_path):
    seen = set()
    count = 0
    with open(output_path, "w", encoding="utf-8") as out:
        for path in inputs:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        key = (entry["file"], entry["circuit"])
                        if key not in seen:
                            seen.add(key)
                            json.dump(entry, out)
                            out.write("\n")
                            count += 1
                    except json.JSONDecodeError:
                        continue
    print(f"🧷 Total unique circuit blocks written: {count} → {output_path}")

if __name__ == "__main__":
    clean_python_files(REPO_DIR)
    extract_from_py(REPO_DIR, PY_OUTPUT)
    extract_from_ipynb(REPO_DIR, NB_OUTPUT)
    merge_jsonls([PY_OUTPUT, NB_OUTPUT], FINAL_OUTPUT)
    print("🎉 All operations completed successfully.")
