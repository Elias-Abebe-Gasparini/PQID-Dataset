"""
compute_paraphrase_diversity.py
--------------------------------
Measures the lexical and semantic diversity of the AI-generated instruction
paraphrases in the PQID dataset.

For each unique source circuit (identified by paraphrase_source, falling back
to circuit_hash for seed entries), this script groups all instructions
(1 seed + up to 5 paraphrases) and computes:

  Per-group metrics:
    bleu_mean        mean pairwise corpus BLEU across all instruction pairs
    bleu_min         minimum pairwise BLEU (most similar pair — worst case)
    ttr_mean         mean type-token ratio across instructions in the group
    length_cv        coefficient of variation of instruction lengths (chars)

  Dataset-level summary:
    Histograms and percentile tables for bleu_mean and ttr_mean
    Fraction of groups where bleu_min > 0.5 (near-duplicate paraphrase pairs)

Output:
    paraphrase_diversity_report.txt  — human-readable summary
    paraphrase_diversity.jsonl       — per-group metrics (for further analysis)

Requirements:
    pip install nltk
    python -m nltk.downloader punkt

Run:
    python compute_paraphrase_diversity.py
        (reads from train_clean.jsonl + validation_clean.jsonl + test_clean.jsonl)
"""

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(
    "c:/Users/Abebe/Downloads/CAREER/ACADEMIC CAREER/SCHOOLS/YONSEI/"
    "YONSEI 2023/Yonsei SS 2025/MS Thesis/MS_THESIS_DATASET/PQID/data/processed"
)

INPUT_FILES = [
    BASE / "train_clean.jsonl",
    BASE / "validation_clean.jsonl",
    BASE / "test_clean.jsonl",
]

REPORT_FILE  = BASE / "paraphrase_diversity_report.txt"
METRICS_FILE = BASE / "paraphrase_diversity.jsonl"

# Sample cap: computing all pairwise BLEUs for 691K entries is slow.
# We sample up to MAX_GROUPS groups uniformly at random.
MAX_GROUPS = 10_000


# ---------------------------------------------------------------------------
# BLEU helpers (sentence-level, no external dep beyond nltk)
# ---------------------------------------------------------------------------
def _ngrams(tokens: list, n: int) -> dict:
    counts: dict = {}
    for i in range(len(tokens) - n + 1):
        gram = tuple(tokens[i:i + n])
        counts[gram] = counts.get(gram, 0) + 1
    return counts


def _modified_precision(reference_tokens: list, hypothesis_tokens: list, n: int) -> tuple[int, int]:
    """Clipped n-gram precision numerator and denominator."""
    hyp_ngrams = _ngrams(hypothesis_tokens, n)
    ref_ngrams = _ngrams(reference_tokens, n)
    clipped = sum(min(cnt, ref_ngrams.get(gram, 0)) for gram, cnt in hyp_ngrams.items())
    total   = max(sum(hyp_ngrams.values()), 0)
    return clipped, total


def sentence_bleu(reference: str, hypothesis: str) -> float:
    """
    Compute corpus BLEU-4 between two strings (tokenised by whitespace).
    Returns 0.0 if either string is empty or shorter than 4 tokens.
    """
    ref_tok = reference.lower().split()
    hyp_tok = hypothesis.lower().split()
    if len(hyp_tok) < 4 or len(ref_tok) < 4:
        return 0.0

    # Brevity penalty
    bp = min(1.0, math.exp(1 - len(ref_tok) / len(hyp_tok)))

    log_avg = 0.0
    for n in range(1, 5):
        num, den = _modified_precision(ref_tok, hyp_tok, n)
        if den == 0 or num == 0:
            return 0.0
        log_avg += math.log(num / den)
    return bp * math.exp(log_avg / 4)


def pairwise_bleu_mean_min(instructions: list[str]) -> tuple[float, float]:
    """Return (mean, min) pairwise BLEU for a list of instructions."""
    scores = []
    for i in range(len(instructions)):
        for j in range(i + 1, len(instructions)):
            scores.append(sentence_bleu(instructions[i], instructions[j]))
    if not scores:
        return 0.0, 0.0
    return statistics.mean(scores), min(scores)


def type_token_ratio(text: str) -> float:
    tokens = text.lower().split()
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


# ---------------------------------------------------------------------------
# Load and group
# ---------------------------------------------------------------------------
def load_groups(files: list, max_groups: int) -> dict:
    """
    Return {group_key: [instruction_text, ...]} where group_key is
    paraphrase_source if available, else circuit_hash.

    Reservoir-samples up to max_groups unique group keys.
    """
    import random
    random.seed(42)

    groups: dict = defaultdict(list)

    for path in files:
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                m = d.get("metadata", {})
                key = m.get("paraphrase_source") or m.get("circuit_hash", "")
                if not key:
                    continue
                instr = d.get("input", "").strip()
                if not instr:
                    continue
                groups[key].append(instr)

    # Keep only groups with >= 2 instructions (need pairs for BLEU)
    groups = {k: v for k, v in groups.items() if len(v) >= 2}

    # Sample
    keys = list(groups.keys())
    if len(keys) > max_groups:
        keys = random.sample(keys, max_groups)
    return {k: groups[k] for k in keys}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"Loading and grouping instructions (sample cap: {MAX_GROUPS:,})...", flush=True)
    groups = load_groups(INPUT_FILES, MAX_GROUPS)
    print(f"  Groups loaded: {len(groups):,}", flush=True)

    bleu_means = []
    bleu_mins  = []
    ttr_means  = []
    length_cvs = []
    metrics_rows = []

    t0 = __import__("time").time()
    for i, (key, instructions) in enumerate(groups.items(), 1):
        bm, bmin = pairwise_bleu_mean_min(instructions)
        ttrs     = [type_token_ratio(t) for t in instructions]
        lengths  = [len(t) for t in instructions]
        mean_len = statistics.mean(lengths)
        lcv = (statistics.stdev(lengths) / mean_len) if mean_len > 0 and len(lengths) > 1 else 0.0

        bleu_means.append(bm)
        bleu_mins.append(bmin)
        ttr_means.append(statistics.mean(ttrs))
        length_cvs.append(lcv)

        metrics_rows.append({
            "group_key":    key,
            "n_instructions": len(instructions),
            "bleu_mean":    round(bm, 4),
            "bleu_min":     round(bmin, 4),
            "ttr_mean":     round(statistics.mean(ttrs), 4),
            "length_cv":    round(lcv, 4),
        })

        if i % 1000 == 0 or i == len(groups):
            elapsed = __import__("time").time() - t0
            print(f"  {i}/{len(groups)} groups processed  elapsed={elapsed:.0f}s", flush=True)

    # Save per-group metrics
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        for row in metrics_rows:
            f.write(json.dumps(row) + "\n")
    print(f"\nPer-group metrics saved to {METRICS_FILE}", flush=True)

    # Summary statistics
    def percentile(data: list, p: float) -> float:
        data = sorted(data)
        idx = (len(data) - 1) * p / 100
        lo, hi = int(idx), min(int(idx) + 1, len(data) - 1)
        return data[lo] + (data[hi] - data[lo]) * (idx - lo)

    near_dup_threshold = 0.5
    near_dups = sum(1 for b in bleu_mins if b > near_dup_threshold)

    lines = [
        "PQID — Paraphrase Diversity Report\n",
        "=" * 55 + "\n\n",
        f"Groups analysed       : {len(groups):,}  (sampled from full dataset)\n",
        f"Near-duplicate pairs  : {near_dups:,} ({100*near_dups/len(groups):.1f}%)  "
        f"[bleu_min > {near_dup_threshold}]\n\n",
        "Pairwise BLEU-4 (mean per group):\n",
        f"  mean   {statistics.mean(bleu_means):.4f}\n",
        f"  median {percentile(bleu_means, 50):.4f}\n",
        f"  p10    {percentile(bleu_means, 10):.4f}\n",
        f"  p90    {percentile(bleu_means, 90):.4f}\n",
        f"  max    {max(bleu_means):.4f}\n\n",
        "Pairwise BLEU-4 (min per group — worst-case near-duplicate):\n",
        f"  mean   {statistics.mean(bleu_mins):.4f}\n",
        f"  median {percentile(bleu_mins, 50):.4f}\n",
        f"  p90    {percentile(bleu_mins, 90):.4f}\n",
        f"  max    {max(bleu_mins):.4f}\n\n",
        "Type-Token Ratio (mean per group — lexical richness):\n",
        f"  mean   {statistics.mean(ttr_means):.4f}\n",
        f"  median {percentile(ttr_means, 50):.4f}\n",
        f"  p10    {percentile(ttr_means, 10):.4f}\n\n",
        "Instruction Length CoV (within-group length variation):\n",
        f"  mean   {statistics.mean(length_cvs):.4f}\n",
        f"  median {percentile(length_cvs, 50):.4f}\n\n",
        "Interpretation:\n",
        "  BLEU-4 mean < 0.3  → paraphrases are lexically diverse (good)\n",
        "  BLEU-4 mean > 0.6  → paraphrases are near-copies (concern)\n",
        "  TTR > 0.6          → rich vocabulary\n",
        "  Near-dup % < 5%    → minimal paraphrase collapse\n",
    ]

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("".join(lines))
    print(f"Report saved to {REPORT_FILE}", flush=True)


if __name__ == "__main__":
    main()
