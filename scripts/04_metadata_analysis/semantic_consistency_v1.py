import os
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from collections import defaultdict
from sentence_transformers import SentenceTransformer

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')

def load_prompts(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

def group_by_original_prompt(entries):
    groups = defaultdict(list)
    for entry in entries:
        original = entry["trace"].get("original_prompt", entry["input"])
        groups[original].append(entry["input"])
    return groups

def compute_semantic_consistency(groups):
    results = {}
    skipped = 0
    for original, paraphrases in groups.items():
        if not paraphrases:
            skipped += 1
            continue
        try:
            embeddings = model.encode([original] + paraphrases)
            similarities = cosine_similarity([embeddings[0]], embeddings[1:])[0]
            results[original] = {
                "avg_similarity": float(np.mean(similarities)),
                "std_similarity": float(np.std(similarities)),
                "min_similarity": float(np.min(similarities)),
                "max_similarity": float(np.max(similarities)),
                "n_paraphrases": len(paraphrases)
            }
        except Exception as e:
            results[original] = {"error": str(e)}
    print(f"🔁 Semantic consistency: {len(results)} valid, {skipped} skipped")
    return results

def compute_diversity(groups):
    results = {}
    skipped = 0
    for original, paraphrases in groups.items():
        if len(paraphrases) < 2:
            skipped += 1
            continue
        try:
            embeddings = model.encode(paraphrases)
            sim_matrix = cosine_similarity(embeddings)
            upper_triangle = sim_matrix[np.triu_indices_from(sim_matrix, k=1)]
            diversity = 1 - upper_triangle
            results[original] = {
                "avg_diversity": float(np.mean(diversity)),
                "std_diversity": float(np.std(diversity)),
                "n_pairs": len(upper_triangle)
            }
        except Exception as e:
            results[original] = {"error": str(e)}
    print(f"🌱 Diversity: {len(results)} valid, {skipped} skipped")
    return results


if __name__ == "__main__":
    file_path = "llm_paraphrased_train.jsonl"  # or your dataset
    entries = load_prompts(file_path)
    grouped = group_by_original_prompt(entries)
    consistency = compute_semantic_consistency(grouped)
    diversity = compute_diversity(grouped)

    df_consistency = pd.DataFrame.from_dict(consistency, orient="index")
    df_diversity = pd.DataFrame.from_dict(diversity, orient="index")
    df_combined = df_consistency.join(df_diversity)

    df_combined.to_csv("paraphrase_semantic_analysis.csv")
    print("✅ Analysis complete. Output saved to 'paraphrase_semantic_analysis.csv'")
    #     "llm_paraphrased_test.jsonl",