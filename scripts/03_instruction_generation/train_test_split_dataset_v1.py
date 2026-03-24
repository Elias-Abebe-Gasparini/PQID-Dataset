import importlib.util
import json
import random
import os
import sys

def split_dataset(input_file, train_file, val_file, val_ratio=0.1):
    with open(input_file, 'r', encoding='utf-8') as fin:
        data = [json.loads(line) for line in fin]
    random.shuffle(data)
    split_idx = int(len(data) * (1 - val_ratio))
    with open(train_file, 'w', encoding='utf-8') as fout:
        for entry in data[:split_idx]:
            fout.write(json.dumps(entry) + "\n")
    with open(val_file, 'w', encoding='utf-8') as fout:
        for entry in data[split_idx:]:
            fout.write(json.dumps(entry) + "\n")

split_dataset(
    "llm_paraphrased_shuffled.jsonl",
    "llm_paraphrased_train.jsonl",
    "llm_paraphrased_val.jsonl",
    val_ratio=0.1
)
print("✅ Split: llm_paraphrased_shuffled.jsonl → llm_paraphrased_train.jsonl + llm_paraphrased_val.jsonl")
# Compare this snippet from openai_prompt_paraphrasing_v1.py: