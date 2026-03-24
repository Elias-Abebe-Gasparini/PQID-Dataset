import os
import json
import numpy as np
from collections import Counter
from nltk.tokenize import WordPunctTokenizer
from nltk import pos_tag
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
import datetime

# Only required for POS tagging
nltk.download("averaged_perceptron_tagger_eng")

# Initialize tokenizer
tokenizer = WordPunctTokenizer()

def load_dataset(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]

def lexical_stats(prompts):
    lengths = [len(tokenizer.tokenize(p)) for p in prompts]
    vocab = Counter()
    for p in prompts:
        vocab.update(tokenizer.tokenize(p.lower()))
    return {
        "avg_length": np.mean(lengths),
        "std_length": np.std(lengths),
        "type_token_ratio": len(vocab) / sum(lengths),
        "vocab_size": len(vocab),
        "total_tokens": sum(lengths)
    }

def pos_distribution(prompts):
    pos_counts = Counter()
    for p in prompts:
        tags = pos_tag(tokenizer.tokenize(p))
        pos_counts.update(tag for _, tag in tags)
    return dict(pos_counts.most_common(15))

def similarity_stats(prompts, max_samples=500):
    subset = prompts[:max_samples]
    vectorizer = CountVectorizer().fit_transform(subset)
    vectors = vectorizer.toarray()
    sim_matrix = cosine_similarity(vectors)
    upper_triangle = sim_matrix[np.triu_indices_from(sim_matrix, k=1)]
    return {
        "avg_cosine_similarity": np.mean(upper_triangle),
        "std_cosine_similarity": np.std(upper_triangle)
    }

def analyze_file(file_path):
    data = load_dataset(file_path)
    prompts = [entry["input"] for entry in data]
    print(f"\n📦 Analyzing: {file_path}")
    print(f"✅ Total prompts: {len(prompts)}")

    lex = lexical_stats(prompts)
    print(f"✏️  Avg length: {lex['avg_length']:.2f} words | Std: {lex['std_length']:.2f}")
    print(f"📚 Vocab size: {lex['vocab_size']} | TTR: {lex['type_token_ratio']:.4f}")

    sim = similarity_stats(prompts)
    print(f"🔁 Cosine similarity (sampled): Avg = {sim['avg_cosine_similarity']:.4f} | Std = {sim['std_cosine_similarity']:.4f}")

    pos = pos_distribution(prompts)
    print("🧠 Top POS tags:")
    for tag, count in pos.items():
        print(f"   {tag:<5} : {count}")

if __name__ == "__main__":
    files = [
        "llm_revlib_paraphrased_v1.jsonl",
        "llm_github_paraphrased_v1.jsonl",
        "llm_paraphrased_train.jsonl",
        "llm_paraphrased_val.jsonl"
    ]
    for f in files:
        if os.path.exists(f):
            analyze_file(f)
        else:
            print(f"❌ File not found: {f}")

