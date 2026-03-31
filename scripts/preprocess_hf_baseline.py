"""
preprocess_hf_baseline.py
--------------------------
Converts the Hugging Face baseline dataset (train.jsonl + validation.jsonl,
10,718 entries from the original thesis work) into PQID-compatible *_clean.jsonl
files ready for enrich_metadata.py.

What it does:
  1. Loads hf_download/train.jsonl + hf_download/validation.jsonl
  2. Strips all Python comments from circuit code (tokenizer-safe — does not
     touch # inside string literals)
  3. Prepends standard Qiskit imports to each circuit block
  4. Assigns circuit_hash (MD5 of stripped code) and content_hash (MD5 of
     input+output)
  5. Normalises the metadata schema to PQID format — fills unknown fields with
     None so enrich_metadata.py can populate them
  6. Deduplicates at content_hash level (same instruction + same code = drop)
  7. Writes train_clean.jsonl and validation_clean.jsonl

These outputs are then passed to enrich_metadata.py (Python 3.11 / Qiskit)
which adds all the circuit-level metrics (validation_status, depth, size_class,
transpilation fields, etc.).

Why strip comments?
  Several circuits in the HF dataset contain inline comments with non-ASCII
  characters (e.g. Japanese) that caused UnicodeEncodeError and silent exec()
  failures.  Stripping comments also makes exec() faster and reduces clutter in
  the displayed instruction.

Run:
    python preprocess_hf_baseline.py

Output:
    PQID/data/processed/train_clean.jsonl        (from hf train)
    PQID/data/processed/validation_clean.jsonl   (from hf validation)
    PQID/data/processed/hf_preprocess_report.txt
"""

import hashlib
import io
import json
import tokenize
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = Path(
    "c:/Users/Abebe/Downloads/CAREER/ACADEMIC CAREER/SCHOOLS/YONSEI/"
    "YONSEI 2023/Yonsei SS 2025/MS Thesis/MS_THESIS_DATASET/PQID/data/processed"
)
HF_DIR = BASE.parent / "hf_download"

TRAIN_IN      = HF_DIR / "train.jsonl"
VAL_IN        = HF_DIR / "validation.jsonl"
TRAIN_OUT     = BASE / "train_clean.jsonl"
VAL_OUT       = BASE / "validation_clean.jsonl"
REPORT_FILE   = BASE / "hf_preprocess_report.txt"

# Standard imports prepended to every circuit block.
# Covers the vast majority of Qiskit usage patterns.
STANDARD_IMPORTS = """\
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit import Parameter, ParameterVector
from qiskit.circuit.library import (
    QFT, GroverOperator, PhaseEstimation, HGate, XGate, ZGate,
    RZGate, RYGate, RXGate, CXGate, CCXGate, SwapGate,
    EfficientSU2, TwoLocal, RealAmplitudes, PauliTwoDesign,
)
import numpy as np
from numpy import pi
"""

# Minimum quality thresholds — circuits below these are dropped
MIN_OUTPUT_TOKENS  = 4     # circuit code must have at least 4 whitespace-separated tokens
MIN_OUTPUT_LINES   = 2     # at least 2 non-empty lines (avoids single-line stubs)


# ---------------------------------------------------------------------------
# Comment stripping via tokenize
# ---------------------------------------------------------------------------
def strip_comments(source: str) -> str:
    """
    Remove all Python comments from source using the tokenize module.
    Safe: does not alter string literals that happen to contain '#'.
    Returns the cleaned source, or the original if tokenization fails.
    """
    try:
        result_tokens = []
        prev_end = (1, 0)

        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        for tok_type, tok_string, tok_start, tok_end, tok_line in tokens:
            if tok_type == tokenize.COMMENT:
                continue
            if tok_type == tokenize.ENCODING:
                continue
            # Preserve spacing between tokens
            start_row, start_col = tok_start
            end_row, end_col = prev_end
            if start_row == end_row:
                result_tokens.append(" " * max(0, start_col - end_col))
            else:
                result_tokens.append("\n" * (start_row - end_row))
                result_tokens.append(" " * start_col)
            result_tokens.append(tok_string)
            prev_end = tok_end

        cleaned = "".join(result_tokens)
        # Collapse runs of blank lines to at most one
        import re
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
    except (tokenize.TokenError, IndentationError, Exception):
        # Fallback: simple line-by-line stripping (less safe but better than nothing)
        import re
        lines = []
        for line in source.splitlines():
            stripped = re.sub(r"(?<!\\)#.*$", "", line).rstrip()
            lines.append(stripped)
        return "\n".join(lines).strip()


def normalize_code(raw: str) -> str:
    """Strip comments, normalize trailing whitespace, ensure clean line endings."""
    cleaned = strip_comments(raw)
    lines = [l.rstrip() for l in cleaned.splitlines()]
    # Remove leading/trailing blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def add_imports(code: str) -> str:
    """
    Prepend standard imports only if they are not already present.
    Avoids duplicating imports that are already in the code.
    """
    if "from qiskit import" in code or "import qiskit" in code:
        return code
    return STANDARD_IMPORTS + "\n" + code


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------
def circuit_hash(code: str) -> str:
    return hashlib.md5(code.strip().encode("utf-8")).hexdigest()


def content_hash(input_text: str, output_text: str) -> str:
    combined = (input_text.strip() + output_text.strip()).encode("utf-8")
    return hashlib.md5(combined).hexdigest()


# ---------------------------------------------------------------------------
# Quality filter
# ---------------------------------------------------------------------------
def passes_quality_filter(code: str) -> bool:
    """Reject obviously incomplete or trivially short circuits."""
    tokens = code.split()
    if len(tokens) < MIN_OUTPUT_TOKENS:
        return False
    non_empty_lines = [l for l in code.splitlines() if l.strip()]
    if len(non_empty_lines) < MIN_OUTPUT_LINES:
        return False
    # Must actually reference QuantumCircuit somewhere
    if "QuantumCircuit" not in code:
        return False
    return True


# ---------------------------------------------------------------------------
# Schema normalisation
# ---------------------------------------------------------------------------
def normalise_entry(raw: dict, split_name: str) -> dict | None:
    """
    Convert a raw HF entry to PQID schema.
    Returns None if the entry should be dropped.
    """
    input_text  = raw.get("input", "").strip()
    output_raw  = raw.get("output", "").strip()
    old_meta    = raw.get("metadata", {})

    if not input_text or not output_raw:
        return None

    # Clean circuit code
    output_clean = normalize_code(output_raw)
    if not passes_quality_filter(output_clean):
        return None

    # Add imports
    output_with_imports = add_imports(output_clean)

    ch = circuit_hash(output_clean)  # hash WITHOUT imports for consistency
    cc = content_hash(input_text, output_clean)

    # Carry forward provenance fields from old metadata
    original_url = (
        old_meta.get("original_url", "")
        or old_meta.get("github_url", "")
        or old_meta.get("github_anchor", "")
        or ""
    )

    return {
        "input":  input_text,
        "output": output_with_imports,
        "metadata": {
            # Provenance
            "original_url":     original_url,
            "file_path":        old_meta.get("file_path", ""),
            "source":           old_meta.get("source_dataset", "hf_baseline"),
            "language":         "python",

            # Dedup keys
            "circuit_hash":     ch,
            "content_hash":     cc,

            # Instruction generation
            "prompt_type":      old_meta.get("prompt_type", "paraphrased"),
            "quality_flag":     "hf_baseline",
            "generation_model": old_meta.get("generation_model", "unknown"),
            "generation_date":  old_meta.get("generation_date", ""),
            "paraphrase_source": old_meta.get("paraphrase_source", ""),
            "original_prompt":  old_meta.get("original_prompt", ""),

            # Prompt stats
            "prompt_word_count":    len(input_text.split()),
            "prompt_length_chars":  len(input_text),

            # These are filled by enrich_metadata.py (Python 3.11 / Qiskit)
            "validation_status":    None,
            "num_qubits":           None,
            "depth":                None,
            "size":                 None,
            "circuit_expressiveness": None,
            "size_class":           None,
            "benchmark_difficulty": None,
            "num_gate_types":       None,
            "avg_gates_per_layer":  None,
            "t_depth":              None,
            "two_qubit_gate_count": None,
            "entangling_gate_ratio": None,
            "num_parameters":       None,
            "parameter_density":    None,
            "parameter_reuse":      None,
            "measurement_count":    None,
            "reset_usage":          None,
            "mid_circuit_measurement": None,
            "classical_register_count": None,
            "interaction_graph_edges": None,
            "graph_density":        None,
            "max_qubit_degree":     None,
            "connected_components": None,
            "transpiled_depth":     None,
            "transpiled_gate_count": None,
            "transpiled_cx_count":  None,
            "transpiled_single_qubit_count": None,
            "transpilation_overhead": None,
            "transpilation_successful": None,

            # Filled by enrich_repo_license.py
            "repo_license":         None,
            "license_category":     None,

            # Filled by enrich_circuit_family.py
            "circuit_family":       None,
            "semantic_intent":      None,

            # Filled by enrich_repo_topics.py (if run)
            "repo_topics":          None,
            "is_org_repo":          None,
        },
    }


# ---------------------------------------------------------------------------
# Load + process
# ---------------------------------------------------------------------------
def load_jsonl(path: Path) -> list:
    if not path.exists():
        print(f"  WARNING: not found: {path}")
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def save_jsonl(entries: list, path: Path) -> None:
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    BASE.mkdir(parents=True, exist_ok=True)

    sources = [
        ("train",      TRAIN_IN,  TRAIN_OUT),
        ("validation", VAL_IN,    VAL_OUT),
    ]

    report_lines = [
        "PQID — HF Baseline Preprocessing Report\n",
        "=" * 50 + "\n\n",
    ]

    # Global seen sets for dedup across both splits
    seen_content: set = set()

    stats = {}

    for split_name, in_path, out_path in sources:
        raw = load_jsonl(in_path)
        print(f"\n[{split_name}]  Loaded {len(raw):,} raw entries", flush=True)

        processed = []
        n_dropped_quality  = 0
        n_dropped_dedup    = 0
        n_stripped_comments = 0

        for entry in raw:
            # Detect if comments were present
            raw_output = entry.get("output", "")
            had_comments = "#" in raw_output

            norm = normalise_entry(entry, split_name)

            if norm is None:
                n_dropped_quality += 1
                continue

            cc = norm["metadata"]["content_hash"]
            if cc in seen_content:
                n_dropped_dedup += 1
                continue
            seen_content.add(cc)

            if had_comments:
                n_stripped_comments += 1

            processed.append(norm)

        save_jsonl(processed, out_path)

        line = (
            f"{split_name}:\n"
            f"  Input entries        : {len(raw):,}\n"
            f"  Dropped (quality)    : {n_dropped_quality:,}\n"
            f"  Dropped (dedup)      : {n_dropped_dedup:,}\n"
            f"  Comment strips       : {n_stripped_comments:,}\n"
            f"  Output entries       : {len(processed):,}\n"
            f"  Written to           : {out_path.name}\n\n"
        )
        print(line, flush=True)
        report_lines.append(line)
        stats[split_name] = len(processed)

    total = sum(stats.values())
    summary = (
        f"{'='*50}\n"
        f"Total output entries : {total:,}\n"
        f"  train              : {stats.get('train', 0):,}\n"
        f"  validation         : {stats.get('validation', 0):,}\n\n"
        f"Next step:\n"
        f"  Run enrich_metadata.py (Python 3.11) to add Qiskit metrics.\n"
        f"  The *_clean.jsonl files are ready as input.\n"
    )
    print(summary, flush=True)
    report_lines.append(summary)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.writelines(report_lines)
    print(f"Report written to {REPORT_FILE}", flush=True)


if __name__ == "__main__":
    main()
