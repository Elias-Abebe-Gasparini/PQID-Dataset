"""
check_leakage.py
----------------
Verifies that there is no data leakage across the train / validation / test
splits of the PQID dataset.

Two deduplication keys are checked:

    circuit_hash   MD5 of the output code  — same circuit, different instruction
    hash           MD5 of input + output   — exact duplicate entry

Any overlap across splits is a leakage violation and is written to
leakage_report.txt for manual review.

Run:
    python check_leakage.py
"""

import json
from collections import defaultdict
from pathlib import Path

BASE = Path(
    "c:/Users/Abebe/Downloads/CAREER/ACADEMIC CAREER/SCHOOLS/YONSEI/"
    "YONSEI 2023/Yonsei SS 2025/MS Thesis/MS_THESIS_DATASET/PQID/data/processed"
)

SPLITS = {
    "train":      BASE / "train_clean.jsonl",
    "validation": BASE / "validation_clean.jsonl",
    "test":       BASE / "test_clean.jsonl",
}

REPORT = BASE / "leakage_report.txt"


def load_hashes(path: Path) -> tuple[set, set]:
    """Return (circuit_hashes, content_hashes) for all entries in path."""
    circuit_hashes: set = set()
    content_hashes: set = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            m = d.get("metadata", {})
            ch = m.get("circuit_hash", "")
            hh = m.get("hash", "")
            if ch:
                circuit_hashes.add(ch)
            if hh:
                content_hashes.add(hh)
    return circuit_hashes, content_hashes


def check_pair(
    name_a: str, ch_a: set, hh_a: set,
    name_b: str, ch_b: set, hh_b: set,
) -> dict:
    circuit_overlap = ch_a & ch_b
    content_overlap = hh_a & hh_b
    return {
        "pair":            f"{name_a} ∩ {name_b}",
        "circuit_overlap": len(circuit_overlap),
        "content_overlap": len(content_overlap),
        "circuit_examples": list(circuit_overlap)[:5],
        "content_examples": list(content_overlap)[:5],
    }


def main():
    print("Loading splits...", flush=True)
    data = {}
    sizes = {}
    for split, path in SPLITS.items():
        if not path.exists():
            print(f"  SKIP {split} — file not found", flush=True)
            continue
        ch, hh = load_hashes(path)
        data[split] = (ch, hh)
        sizes[split] = (len(ch), len(hh))
        print(f"  {split:<12} circuit_hashes={len(ch):,}  content_hashes={len(hh):,}", flush=True)

    split_names = list(data.keys())
    results = []
    violations = 0

    for i in range(len(split_names)):
        for j in range(i + 1, len(split_names)):
            a, b = split_names[i], split_names[j]
            res = check_pair(a, *data[a], b, *data[b])
            results.append(res)
            if res["circuit_overlap"] or res["content_overlap"]:
                violations += 1

    print("\n=== LEAKAGE REPORT ===")
    lines = ["PQID Dataset — Cross-Split Leakage Report\n", "=" * 50 + "\n\n"]

    for r in results:
        status = "CLEAN" if (r["circuit_overlap"] == 0 and r["content_overlap"] == 0) else "VIOLATION"
        line = (
            f"{r['pair']}\n"
            f"  circuit_hash overlap : {r['circuit_overlap']:>6,}  [{status}]\n"
            f"  content_hash overlap : {r['content_overlap']:>6,}\n"
        )
        if r["circuit_examples"]:
            line += f"  circuit examples     : {r['circuit_examples']}\n"
        if r["content_examples"]:
            line += f"  content examples     : {r['content_examples']}\n"
        lines.append(line + "\n")
        print(line, end="")

    summary = (
        f"{'=' * 50}\n"
        f"Total split pairs checked : {len(results)}\n"
        f"Violations found          : {violations}\n"
        f"Verdict                   : {'PASS — no leakage detected' if violations == 0 else 'FAIL — see above'}\n"
    )
    lines.append(summary)
    print(summary)

    with open(REPORT, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"\nReport written to {REPORT}", flush=True)


if __name__ == "__main__":
    main()
