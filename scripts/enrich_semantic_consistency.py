"""
enrich_semantic_consistency.py
------------------------------
Chunked, resume-friendly semantic-consistency enrichment for the quality-aware
instruction corpus.

For each paraphrase entry in the canonical split layer, the script compares the
paraphrase input text against its source seed prompt and writes:

  semantic_similarity_to_seed
  bert_score_f1
  bleu_score_to_seed
  rouge_l_to_seed
  normalized_edit_distance

Design goals:
- avoid all-at-once embedding / BERTScore passes over the full corpus
- write cache progress incrementally so long runs are resumable
- support a CPU-safe default mode where BERTScore is skipped first and
  backfilled later only if needed

Run:
    python enrich_semantic_consistency.py
    python enrich_semantic_consistency.py --compute-bert-score
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from project_paths import PROCESSED_DIR, format_display_path


SEMANTIC_FIELDS = [
    "semantic_similarity_to_seed",
    "bert_score_f1",
    "bleu_score_to_seed",
    "rouge_l_to_seed",
    "normalized_edit_distance",
]

NULL_SCORES = {field: None for field in SEMANTIC_FIELDS}

DEFAULT_TRAIN_FILE = PROCESSED_DIR / "train_clean.jsonl"
DEFAULT_VALIDATION_FILE = PROCESSED_DIR / "validation_clean.jsonl"
DEFAULT_TEST_FILE = PROCESSED_DIR / "test_clean.jsonl"
DEFAULT_CACHE_FILE = PROCESSED_DIR / "semantic_consistency_cache.jsonl"
DEFAULT_REPORT_FILE = PROCESSED_DIR / "semantic_consistency_report.txt"

DEFAULT_ST_MODEL = "all-MiniLM-L6-v2"
DEFAULT_BERT_MODEL = "bert-base-uncased"
DEFAULT_PAIR_CHUNK_SIZE = 2_000
DEFAULT_BATCH_SIZE_ST = 256
DEFAULT_BATCH_SIZE_BERT = 16


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-file", default=str(DEFAULT_TRAIN_FILE))
    parser.add_argument("--validation-file", default=str(DEFAULT_VALIDATION_FILE))
    parser.add_argument("--test-file", default=str(DEFAULT_TEST_FILE))
    parser.add_argument("--cache-file", default=str(DEFAULT_CACHE_FILE))
    parser.add_argument("--report-file", default=str(DEFAULT_REPORT_FILE))
    parser.add_argument("--sentence-model", default=DEFAULT_ST_MODEL)
    parser.add_argument("--bert-model", default=DEFAULT_BERT_MODEL)
    parser.add_argument("--pair-chunk-size", type=int, default=DEFAULT_PAIR_CHUNK_SIZE)
    parser.add_argument("--batch-size-st", type=int, default=DEFAULT_BATCH_SIZE_ST)
    parser.add_argument("--batch-size-bert", type=int, default=DEFAULT_BATCH_SIZE_BERT)

    bert_group = parser.add_mutually_exclusive_group()
    bert_group.add_argument(
        "--compute-bert-score",
        action="store_true",
        help="Compute BERTScore F1 in addition to the lighter semantic metrics.",
    )
    bert_group.add_argument(
        "--skip-bert-score",
        action="store_true",
        help="Skip BERTScore and leave bert_score_f1 null (default CPU-safe mode).",
    )

    return parser.parse_args()


def iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def append_cache_entries(entries: list[tuple[str, dict]], path: Path) -> None:
    if not entries:
        return
    with path.open("a", encoding="utf-8") as handle:
        for content_hash, scores in entries:
            handle.write(
                json.dumps(
                    {"content_hash": content_hash, "scores": scores},
                    ensure_ascii=False,
                )
                + "\n"
            )


def load_cache(path: Path) -> dict[str, dict]:
    cache: dict[str, dict] = {}
    if not path.exists():
        return cache
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            obj = json.loads(line)
            cache[obj["content_hash"]] = obj["scores"]
    return cache


def cache_key_for_meta(meta: dict) -> str:
    value = str(meta.get("content_hash") or "").strip()
    if value:
        return value

    value = str(meta.get("hash") or "").strip()
    if value:
        return f"hash:{value}"

    circuit_hash = str(meta.get("circuit_hash") or "").strip()
    variant = str(meta.get("paraphrase_variant_index") or "").strip()
    if circuit_hash:
        return f"circuit:{circuit_hash}:{variant}"

    return ""


def is_paraphrase_row(meta: dict) -> bool:
    return bool(str(meta.get("original_prompt") or "").strip())


def scores_complete(scores: dict | None, *, require_bert: bool) -> bool:
    if not scores:
        return False

    required_fields = [
        "semantic_similarity_to_seed",
        "bleu_score_to_seed",
        "rouge_l_to_seed",
        "normalized_edit_distance",
    ]
    if require_bert:
        required_fields.append("bert_score_f1")

    return all(scores.get(field) is not None for field in required_fields)


def normalised_edit_distance(a: str, b: str) -> float:
    try:
        import Levenshtein

        dist = Levenshtein.distance(a, b)
    except ImportError:
        import difflib

        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        dist = round((1.0 - ratio) * (len(a) + len(b)) / 2)
    denom = max(len(a), len(b), 1)
    return round(dist / denom, 6)


def bleu4(hypothesis: str, reference: str) -> float:
    from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu

    ref_tokens = reference.lower().split()
    hyp_tokens = hypothesis.lower().split()
    if not ref_tokens or not hyp_tokens:
        return 0.0
    smoothie = SmoothingFunction().method1
    score = sentence_bleu(
        [ref_tokens],
        hyp_tokens,
        weights=(0.25, 0.25, 0.25, 0.25),
        smoothing_function=smoothie,
    )
    return round(float(score), 6)


def rouge_l_f1(hypothesis: str, reference: str, scorer) -> float:
    result = scorer.score(reference, hypothesis)
    return round(float(result["rougeL"].fmeasure), 6)


def build_runtime(*, sentence_model_name: str, bert_model_name: str, compute_bert: bool):
    try:
        import numpy as np
    except ImportError as exc:
        raise SystemExit("Missing dependency: pip install numpy") from exc

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit("Missing dependency: pip install sentence-transformers") from exc

    try:
        from rouge_score import rouge_scorer as rouge_module
    except ImportError as exc:
        raise SystemExit("Missing dependency: pip install rouge-score") from exc

    try:
        import nltk  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Missing dependency: pip install nltk") from exc

    st_model = SentenceTransformer(sentence_model_name)
    rouge_scorer = rouge_module.RougeScorer(["rougeL"], use_stemmer=False)

    bert_scorer = None
    if compute_bert:
        try:
            from bert_score import BERTScorer
        except ImportError as exc:
            raise SystemExit(
                "Missing dependency: pip install bert-score "
                "(or rerun with --skip-bert-score)."
            ) from exc

        bert_scorer = BERTScorer(
            model_type=bert_model_name,
            lang="en",
            rescale_with_baseline=False,
        )

    return {
        "np": np,
        "st_model": st_model,
        "rouge_scorer": rouge_scorer,
        "bert_scorer": bert_scorer,
    }


def cosine_similarity(emb_a, emb_b, *, np_module) -> float:
    denom = float(np_module.linalg.norm(emb_a) * np_module.linalg.norm(emb_b))
    if denom == 0.0:
        return 0.0
    return float(np_module.dot(emb_a, emb_b) / denom)


def score_chunk(
    chunk: list[tuple[str, str, str]],
    *,
    runtime: dict,
    compute_bert: bool,
    batch_size_st: int,
    batch_size_bert: int,
) -> list[tuple[str, dict]]:
    if not chunk:
        return []

    np_module = runtime["np"]
    st_model = runtime["st_model"]
    rouge_scorer = runtime["rouge_scorer"]
    bert_scorer = runtime["bert_scorer"]

    seen_texts: dict[str, None] = {}
    for _, paraphrase, seed in chunk:
        seen_texts[paraphrase] = None
        seen_texts[seed] = None
    unique_texts = list(seen_texts.keys())

    embeddings = st_model.encode(
        unique_texts,
        batch_size=batch_size_st,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    text_to_embedding = {text: embeddings[i] for i, text in enumerate(unique_texts)}

    bert_scores: dict[str, float | None] = {}
    if compute_bert and bert_scorer is not None:
        paraphrases = [item[1] for item in chunk]
        seeds = [item[2] for item in chunk]
        _, _, f1 = bert_scorer.score(
            paraphrases,
            seeds,
            batch_size=batch_size_bert,
            verbose=False,
        )
        for (content_hash, _, _), value in zip(chunk, f1.tolist()):
            bert_scores[content_hash] = round(float(value), 6)

    scored_entries: list[tuple[str, dict]] = []
    for content_hash, paraphrase, seed in chunk:
        emb_para = text_to_embedding[paraphrase]
        emb_seed = text_to_embedding[seed]
        similarity = cosine_similarity(emb_para, emb_seed, np_module=np_module)

        scores = {
            "semantic_similarity_to_seed": round(similarity, 6),
            "bert_score_f1": bert_scores.get(content_hash) if compute_bert else None,
            "bleu_score_to_seed": bleu4(paraphrase, seed),
            "rouge_l_to_seed": rouge_l_f1(paraphrase, seed, rouge_scorer),
            "normalized_edit_distance": normalised_edit_distance(paraphrase, seed),
        }
        scored_entries.append((content_hash, scores))

    return scored_entries


def count_split_work(
    path: Path,
    *,
    cache: dict[str, dict],
    require_bert: bool,
) -> dict[str, int]:
    total_rows = 0
    seed_rows = 0
    paraphrase_rows = 0
    needs_scoring = 0

    for row in iter_jsonl(path) or []:
        total_rows += 1
        meta = row.get("metadata", {})
        if not is_paraphrase_row(meta):
            seed_rows += 1
            continue
        paraphrase_rows += 1
        cache_key = cache_key_for_meta(meta)
        if not scores_complete(cache.get(cache_key), require_bert=require_bert):
            needs_scoring += 1

    return {
        "total_rows": total_rows,
        "seed_rows": seed_rows,
        "paraphrase_rows": paraphrase_rows,
        "needs_scoring": needs_scoring,
    }


def score_split(
    path: Path,
    *,
    cache: dict[str, dict],
    cache_file: Path,
    require_bert: bool,
    pair_chunk_size: int,
    batch_size_st: int,
    batch_size_bert: int,
    runtime: dict,
) -> int:
    chunk: list[tuple[str, str, str]] = []
    processed = 0
    scored = 0

    stats = count_split_work(path, cache=cache, require_bert=require_bert)
    total_to_score = stats["needs_scoring"]
    print(
        f"  {path.name}: {total_to_score:,} paraphrase rows still need scoring",
        flush=True,
    )

    if total_to_score == 0:
        return 0

    def flush_chunk() -> int:
        nonlocal chunk, scored
        if not chunk:
            return 0
        scored_entries = score_chunk(
            chunk,
            runtime=runtime,
            compute_bert=require_bert,
            batch_size_st=batch_size_st,
            batch_size_bert=batch_size_bert,
        )
        append_cache_entries(scored_entries, cache_file)
        for content_hash, scores in scored_entries:
            cache[content_hash] = scores
        count = len(scored_entries)
        scored += count
        chunk = []
        return count

    for row in iter_jsonl(path) or []:
        meta = row.get("metadata", {})
        if not is_paraphrase_row(meta):
            continue
        cache_key = cache_key_for_meta(meta)
        if scores_complete(cache.get(cache_key), require_bert=require_bert):
            continue
        paraphrase = str(row.get("input") or "")
        seed = str(meta.get("original_prompt") or "")
        if not cache_key or not paraphrase or not seed:
            continue
        chunk.append((cache_key, paraphrase, seed))
        processed += 1
        if len(chunk) >= pair_chunk_size:
            flush_chunk()
            print(
                f"    scored {processed:,} / {total_to_score:,} pending rows",
                flush=True,
            )

    if chunk:
        flush_chunk()
        print(
            f"    scored {processed:,} / {total_to_score:,} pending rows",
            flush=True,
        )

    return scored


def rewrite_split_from_cache(
    path: Path,
    *,
    cache: dict[str, dict],
) -> dict[str, int]:
    tmp_path = Path(str(path) + ".tmp")
    seed_rows = 0
    paraphrase_rows = 0
    cache_misses = 0

    with path.open("r", encoding="utf-8") as source, tmp_path.open(
        "w", encoding="utf-8"
    ) as target:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            meta = row.setdefault("metadata", {})
            if not is_paraphrase_row(meta):
                meta.update(NULL_SCORES)
                seed_rows += 1
            else:
                cache_key = cache_key_for_meta(meta)
                cached_scores = cache.get(cache_key)
                if cached_scores:
                    merged_scores = dict(NULL_SCORES)
                    merged_scores.update(cached_scores)
                    meta.update(merged_scores)
                    paraphrase_rows += 1
                else:
                    meta.update(NULL_SCORES)
                    cache_misses += 1
            target.write(json.dumps(row, ensure_ascii=False) + "\n")

    tmp_path.replace(path)
    return {
        "seed_rows": seed_rows,
        "paraphrase_rows": paraphrase_rows,
        "cache_misses": cache_misses,
    }


def main() -> None:
    args = parse_args()
    compute_bert = bool(args.compute_bert_score and not args.skip_bert_score)
    pair_chunk_size = max(1, args.pair_chunk_size)
    batch_size_st = max(1, args.batch_size_st)
    batch_size_bert = max(1, args.batch_size_bert)

    split_files = {
        "train": Path(args.train_file),
        "validation": Path(args.validation_file),
        "test": Path(args.test_file),
    }
    cache_file = Path(args.cache_file)
    report_file = Path(args.report_file)

    t0 = time.time()

    print("Loading cache...", flush=True)
    cache = load_cache(cache_file)
    print(f"  cached entries: {len(cache):,}", flush=True)
    print(
        f"  BERTScore mode: {'enabled' if compute_bert else 'disabled (null backfill deferred)'}",
        flush=True,
    )
    print(f"  pair chunk size: {pair_chunk_size:,}", flush=True)

    split_counts = {
        name: count_split_work(path, cache=cache, require_bert=compute_bert)
        for name, path in split_files.items()
    }
    total_pending = sum(stats["needs_scoring"] for stats in split_counts.values())

    print("\nSemantic-consistency workload:", flush=True)
    for split_name, stats in split_counts.items():
        print(
            f"  {split_name}: rows={stats['total_rows']:,}, "
            f"paraphrases={stats['paraphrase_rows']:,}, "
            f"seeds={stats['seed_rows']:,}, "
            f"pending={stats['needs_scoring']:,}",
            flush=True,
        )

    runtime = None
    total_scored = 0
    if total_pending > 0:
        print("\nLoading semantic metric runtime...", flush=True)
        runtime = build_runtime(
            sentence_model_name=args.sentence_model,
            bert_model_name=args.bert_model,
            compute_bert=compute_bert,
        )

        for split_name, path in split_files.items():
            pending = split_counts[split_name]["needs_scoring"]
            if pending == 0:
                continue
            print(f"\nScoring split: {split_name}", flush=True)
            scored = score_split(
                path,
                cache=cache,
                cache_file=cache_file,
                require_bert=compute_bert,
                pair_chunk_size=pair_chunk_size,
                batch_size_st=batch_size_st,
                batch_size_bert=batch_size_bert,
                runtime=runtime,
            )
            total_scored += scored
            print(f"  {split_name}: scored {scored:,} rows", flush=True)

    report_lines = [
        "PQID — Semantic Consistency Enrichment Report\n",
        "=" * 52 + "\n\n",
        f"Sentence-transformer model : {args.sentence_model}\n",
        f"BERTScore model            : "
        f"{args.bert_model if compute_bert else 'skipped (bert_score_f1 left null)'}\n",
        f"Pair chunk size            : {pair_chunk_size:,}\n",
        f"Sentence batch size        : {batch_size_st:,}\n",
        f"BERT batch size            : {batch_size_bert:,}\n\n",
    ]

    grand_seed_rows = 0
    grand_paraphrase_rows = 0
    grand_cache_misses = 0

    print("\nRewriting split files from cache...", flush=True)
    for split_name, path in split_files.items():
        rewrite_stats = rewrite_split_from_cache(path, cache=cache)
        grand_seed_rows += rewrite_stats["seed_rows"]
        grand_paraphrase_rows += rewrite_stats["paraphrase_rows"]
        grand_cache_misses += rewrite_stats["cache_misses"]

        line = (
            f"{split_name}:\n"
            f"  file                 : {format_display_path(path)}\n"
            f"  seed rows            : {rewrite_stats['seed_rows']:,}\n"
            f"  paraphrase rows      : {rewrite_stats['paraphrase_rows']:,}\n"
            f"  cache misses         : {rewrite_stats['cache_misses']:,}\n\n"
        )
        print(line, flush=True)
        report_lines.append(line)

    elapsed_minutes = (time.time() - t0) / 60.0
    summary = (
        f"{'=' * 52}\n"
        f"Newly scored paraphrases   : {total_scored:,}\n"
        f"Final cached entries       : {len(cache):,}\n"
        f"Total paraphrase rows      : {grand_paraphrase_rows:,}\n"
        f"Total seed rows            : {grand_seed_rows:,}\n"
        f"Final cache misses         : {grand_cache_misses:,}\n"
        f"Elapsed                    : {elapsed_minutes:.1f} min\n"
    )
    print(summary, flush=True)
    report_lines.append(summary)

    with report_file.open("w", encoding="utf-8") as handle:
        handle.writelines(report_lines)
    print(f"\nReport written to {format_display_path(report_file)}", flush=True)


if __name__ == "__main__":
    main()
