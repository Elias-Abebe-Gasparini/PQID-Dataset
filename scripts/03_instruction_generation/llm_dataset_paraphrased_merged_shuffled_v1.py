import json
import random

def shuffle_jsonl(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as fin:
        data = [json.loads(line) for line in fin]
    random.shuffle(data)
    with open(output_file, 'w', encoding='utf-8') as fout:
        for entry in data:
            fout.write(json.dumps(entry) + "\n")

shuffle_jsonl("llm_paraphrased_merged.jsonl", "llm_paraphrased_shuffled.jsonl")
print("✅ Shuffled: llm_paraphrased_merged.jsonl → llm_paraphrased_shuffled.jsonl")