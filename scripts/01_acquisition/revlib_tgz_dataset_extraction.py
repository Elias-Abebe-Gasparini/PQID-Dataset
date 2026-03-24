import tarfile
import os

def extract_tgz(file_path: str, extract_dir: str):
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)
    with tarfile.open(file_path, "r:gz") as tar:
        tar.extractall(path=extract_dir)
    print(f"✅ Extracted to: {extract_dir}")

# Example usage
extract_tgz("Revlib_gates.tgz", "revlib_gates_extracted")
