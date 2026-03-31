"""
enrich_semantic_consistency.py
-------------------------------
Adds per-entry semantic consistency metrics to all *_clean.jsonl splits.

For each paraphrase entry (metadata.original_prompt != ""), five scores are
computed against the seed prompt it was derived from:

  semantic_similarity_to_seed  float  cosine similarity (all-MiniLM-L6-v2)
  bert_score_f1                float  BERTScore F1 (bert-base-uncased)
  bleu_score_to_seed           float  BLEU-4 against seed
  rouge_l_to_seed              float  ROUGE-L F1 against seed
  normalized_edit_distance     float  Levenshtein / max(len(seed), len(para))

Seed entries (original_prompt == "") receive null for all five fields.

Resume-safe:
  Results are cached per content_hash in semantic_consistency_cache.jsonl.
  Re-running skips all already-cached entries.  Safe to interrupt at any time.

Performance notes:
  - Sentence-transformer encoding: batched, fast on CPU (~10K texts/min)
  - BERTScore: heavy on CPU; set COMPUTE_BERT_SCORE = False to skip.
    GPU strongly recommended for a full 691K run (~5-10h on CPU otherwise).
  - BLEU-4, ROUGE-L, edit distance: pure-Python, fast.

Dependencies (Python 3.11):
    pip install sentence-transformers bert-score rouge-score nltk
    pip install python-Levenshtein   # optional; falls back to difflib

Run:
    python enrich_semantic_consistency.py
"""

import json
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = Path(
    "c:/Users/Abebe/Downloads/CAREER/ACADEMIC CAREER/SCHOOLS/YONSEI/"
    "YONSEI 2023/Yonsei SS 2025/MS Thesis/MS_THESIS_DATASET/PQID/data/processed"
)

SPLITS = {
    "train":      BASE / "train_clean.jsonl",
    "validation": BASE / "validation_clean.jsonl",
    "test":       BASE / "test_clean.jsonl",
}

CACHE_FILE  = BASE / "semantic_consistency_cache.jsonl"
REPORT_FILE = BASE / "semantic_consistency_report.txt"

# --- Model config ---
ST_MODEL          = "all-MiniLM-L6-v2"   # sentence-transformers model
BERT_SCORE_MODEL  = "bert-base-uncased"   # lighter than default roberta-large
COMPUTE_BERT_SCORE = True                 # set False on CPU-only machines

BATCH_SIZE_ST       = 512    # sentence-transformer encoding batch size
BATCH_SIZE_BERT     = 32     # BERTScore pairs per call (memory-limited on CPU)
BERT_FLUSH_EVERY    = 320    # accumulate this many pairs before one bert call
CACHE_FLUSH_EVERY   = 5_000  # append cache to disk every N new entries


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------
def load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_jsonl(entries: list, path: Path) -> None:
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------
def load_cache(path: Path) -> dict:
    """Returns {content_hash: scores_dict}."""
    cache = {}
    if not path.exists():
        return cache
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                cache[obj["content_hash"]] = obj["scores"]
    return cache


def flush_cache_entries(entries: list[tuple], path: Path) -> None:
    """Append (content_hash, scores_dict) pairs to the cache file."""
    with open(path, "a", encoding="utf-8") as f:
        for ch, scores in entries:
            f.write(json.dumps({"content_hash": ch, "scores": scores},
                                ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------
def normalised_edit_distance(a: str, b: str) -> float:
    """Character-level Levenshtein distance normalised by max string length."""
    try:
        import Levenshtein
        dist = Levenshtein.distance(a, b)
    except ImportError:
        # stdlib fallback via SequenceMatcher (approximate but adequate)
        import difflib
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        dist = round((1.0 - ratio) * (len(a) + len(b)) / 2)
    denom = max(len(a), len(b), 1)
    return round(dist / denom, 6)


def bleu4(hypothesis: str, reference: str) -> float:
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    ref_tokens = reference.lower().split()
    hyp_tokens = hypothesis.lower().split()
    if not ref_tokens or not hyp_tokens:
        return 0.0
    smoothie = SmoothingFunction().method1
    score = sentence_bleu(
        [ref_tokens], hyp_tokens,
        weights=(0.25, 0.25, 0.25, 0.25),
        smoothing_function=smoothie,
    )
    return round(float(score), 6)


def rouge_l_f1(hypothesis: str, reference: str, scorer) -> float:
    result = scorer.score(reference, hypothesis)
    return round(float(result["rougeL"].fmeasure), 6)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    t0 = time.time()

    # ---- Import heavy libraries ----
    print("Loading libraries...", flush=True)

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise SystemExit("Missing: pip install sentence-transformers")

    try:
        from sklearn.metrics.pairwise import cosine_similarity as cos_sim
        import numpy as np
    except ImportError:
        raise SystemExit("Missing: pip install scikit-learn numpy")

    try:
        import nltk
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)
    except ImportError:
        raise SystemExit("Missing: pip install nltk")

    try:
        from rouge_score import rouge_scorer as rouge_module
    except ImportError:
        raise SystemExit("Missing: pip install rouge-score")

    rouge_sc = rouge_module.RougeScorer(["rougeL"], use_stemmer=False)

    if COMPUTE_BERT_SCORE:
        try:
            from bert_score import score as bert_score_fn
            print(f"  BERTScore enabled  : {BERT_SCORE_MODEL}", flush=True)
        except ImportError:
            raise SystemExit("Missing: pip install bert-score  (or set COMPUTE_BERT_SCORE=False)")
    else:
        bert_score_fn = None
        print("  BERTScore disabled : bert_score_f1 will be null", flush=True)

    print(f"  Sentence-transformer: {ST_MODEL}", flush=True)
    st_model = SentenceTransformer(ST_MODEL)

    # ---- Load cache ----
    print("\nLoading cache...", flush=True)
    cache = load_cache(CACHE_FILE)
    print(f"  {len(cache):,} entries already cached.", flush=True)

    # ---- Collect entries that need scoring ----
    print("\nScanning splits for uncached paraphrase entries...", flush=True)
    all_split_data: dict[str, list] = {}
    to_score: list[tuple] = []   # (content_hash, paraphrase_text, seed_text)

    for split_name, path in SPLITS.items():
        entries = load_jsonl(path)
        all_split_data[split_name] = entries
        if not entries:
            print(f"  {split_name}: not found / empty — skipping", flush=True)
            continue
        needs = 0
        for e in entries:
            meta            = e.get("metadata", {})
            ch              = meta.get("content_hash", "")
            original_prompt = meta.get("original_prompt", "")
            if not original_prompt:   # seed entry — will be null
                continue
            if ch in cache:           # already scored
                continue
            to_score.append((ch, e["input"], original_prompt))
            needs += 1
        print(f"  {split_name}: {len(entries):,} entries, {needs:,} need scoring",
              flush=True)

    # Deduplicate by content_hash (same instruction may exist in multiple splits)
    seen_ch: set = set()
    to_score_unique: list[tuple] = []
    for item in to_score:
        if item[0] not in seen_ch:
            seen_ch.add(item[0])
            to_score_unique.append(item)

    total_to_score = len(to_score_unique)
    print(f"\nTotal unique pairs to score: {total_to_score:,}", flush=True)

    if total_to_score > 0:

        # ---- Encode all unique texts with sentence-transformer ----
        print(f"\nEncoding texts with {ST_MODEL}...", flush=True)
        text_set: dict[str, None] = {}
        for _, para, seed in to_score_unique:
            text_set[para] = None
            text_set[seed] = None
        unique_texts = list(text_set.keys())
        print(f"  {len(unique_texts):,} unique texts to encode", flush=True)

        embeddings = st_model.encode(
            unique_texts,
            batch_size=BATCH_SIZE_ST,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        text_to_emb: dict[str, object] = {
            t: embeddings[i] for i, t in enumerate(unique_texts)
        }
        print("  Encoding complete.", flush=True)

        # ---- BERTScore (optional, batched) ----
        bert_f1_map: dict[str, float | None] = {}

        if COMPUTE_BERT_SCORE and bert_score_fn is not None:
            print(f"\nComputing BERTScore ({BERT_SCORE_MODEL})...", flush=True)

            def _run_bert_batch(hashes, hyps, refs):
                _, _, F1 = bert_score_fn(
                    hyps, refs,
                    model_type=BERT_SCORE_MODEL,
                    batch_size=BATCH_SIZE_BERT,
                    verbose=False,
                )
                for ch, f1 in zip(hashes, F1.tolist()):
                    bert_f1_map[ch] = round(float(f1), 6)

            h_buf, hyp_buf, ref_buf = [], [], []
            for i, (ch, para, seed) in enumerate(to_score_unique):
                h_buf.append(ch)
                hyp_buf.append(para)
                ref_buf.append(seed)
                if len(h_buf) >= BERT_FLUSH_EVERY:
                    _run_bert_batch(h_buf, hyp_buf, ref_buf)
                    h_buf, hyp_buf, ref_buf = [], [], []
                    print(f"  BERTScore: {i + 1:,} / {total_to_score:,}", flush=True)
            if h_buf:
                _run_bert_batch(h_buf, hyp_buf, ref_buf)
            print("  BERTScore complete.", flush=True)

        # ---- Compute all 5 scores per entry, flush cache incrementally ----
        print(f"\nComputing BLEU-4, ROUGE-L, edit distance ({total_to_score:,} entries)...",
              flush=True)
        new_entries: list[tuple] = []

        for i, (ch, para, seed) in enumerate(to_score_unique):
            emb_para = text_to_emb[para].reshape(1, -1)
            emb_seed = text_to_emb[seed].reshape(1, -1)
            sim = float(cos_sim(emb_para, emb_seed)[0][0])

            scores = {
                "semantic_similarity_to_seed": round(sim, 6),
                "bert_score_f1":               bert_f1_map.get(ch) if COMPUTE_BERT_SCORE else None,
                "bleu_score_to_seed":          bleu4(para, seed),
                "rouge_l_to_seed":             rouge_l_f1(para, seed, rouge_sc),
                "normalized_edit_distance":    normalised_edit_distance(para, seed),
            }

            cache[ch] = scores
            new_entries.append((ch, scores))

            # Flush cache periodically
            if len(new_entries) % CACHE_FLUSH_EVERY == 0:
                flush_cache_entries(new_entries[-CACHE_FLUSH_EVERY:], CACHE_FILE)
                print(f"  {i + 1:,} / {total_to_score:,} scored & cached", flush=True)

        # Flush remainder
        remainder = len(new_entries) % CACHE_FLUSH_EVERY
        if remainder:
            flush_cache_entries(new_entries[-remainder:], CACHE_FILE)

        print(f"  Scoring complete. {len(new_entries):,} new entries written to cache.",
              flush=True)

    # ---- Patch all splits from cache ----
    NULL_SCORES = {
        "semantic_similarity_to_seed": None,
        "bert_score_f1":               None,
        "bleu_score_to_seed":          None,
        "rouge_l_to_seed":             None,
        "normalized_edit_distance":    None,
    }

    print("\nPatching splits...", flush=True)
    report_lines = [
        "PQID — Semantic Consistency Enrichment Report\n",
        "=" * 52 + "\n\n",
        f"Sentence-transformer model : {ST_MODEL}\n",
        f"BERTScore model            : "
        f"{BERT_SCORE_MODEL if COMPUTE_BERT_SCORE else 'skipped (null)'}\n\n",
    ]

    grand_paraphrases = 0
    grand_seeds       = 0
    grand_misses      = 0

    for split_name, entries in all_split_data.items():
        if not entries:
            continue
        n_para = n_seed = n_miss = 0
        for e in entries:
            meta            = e.get("metadata", {})
            ch              = meta.get("content_hash", "")
            original_prompt = meta.get("original_prompt", "")
            if not original_prompt:
                e["metadata"].update(NULL_SCORES)
                n_seed += 1
            elif ch in cache:
                e["metadata"].update(cache[ch])
                n_para += 1
            else:
                # Should not happen after scoring step — safe fallback
                e["metadata"].update(NULL_SCORES)
                n_miss += 1

        save_jsonl(entries, SPLITS[split_name])
        grand_paraphrases += n_para
        grand_seeds       += n_seed
        grand_misses      += n_miss

        line = (
            f"{split_name}:\n"
            f"  Total entries      : {len(entries):,}\n"
            f"  Seeds (null)       : {n_seed:,}\n"
            f"  Paraphrases scored : {n_para:,}\n"
            f"  Cache misses       : {n_miss:,}\n\n"
        )
        print(line, flush=True)
        report_lines.append(line)

    elapsed = time.time() - t0
    summary = (
        f"{'=' * 52}\n"
        f"Grand total paraphrases scored : {grand_paraphrases:,}\n"
        f"Grand total seeds (null)       : {grand_seeds:,}\n"
        f"Grand total cache misses       : {grand_misses:,}\n"
        f"Elapsed                        : {elapsed / 60:.1f} min\n"
    )
    print(summary, flush=True)
    report_lines.append(summary)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.writelines(report_lines)
    print(f"\nReport written to {REPORT_FILE}", flush=True)


if __name__ == "__main__":
    main()
