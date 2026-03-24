import json
import os
from collections import Counter, defaultdict
from statistics import mean, stdev

def load_jsonl(path):
    with open(path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

def analyze_errors(log_path):
    print(f"\n🔍 Analyzing error log: {log_path}")
    if not os.path.exists(log_path):
        print("❌ Log file not found.")
        return

    errors = load_jsonl(log_path)
    print(f"❗ Total errors: {len(errors)}")

    error_types = Counter()
    long_entries = []

    for entry in errors:
        msg = entry.get("error", "")
        if "too large" in msg.lower() or "413" in msg:
            error_types["Request Too Large"] += 1
            long_entries.append(entry)
        elif "rate limit" in msg.lower():
            error_types["Rate Limit"] += 1
        elif "timeout" in msg.lower():
            error_types["Timeout"] += 1
        elif "skipped_empty_or_short_code" in msg:
            error_types["Too Short"] += 1
        else:
            error_types["Other"] += 1

    print("📊 Error breakdown:")
    for err, count in error_types.most_common():
        print(f"   {err:<25} {count}")

    if long_entries:
        outpath = log_path.replace(".jsonl", "_long_entries.jsonl")
        with open(outpath, "w", encoding="utf-8") as f:
            for entry in long_entries:
                f.write(json.dumps(entry) + "\n")
        print(f"📄 Exported {len(long_entries)} long entries to: {outpath}")

def analyze_outputs(output_path):
    print(f"\n📦 Analyzing output data: {output_path}")
    if not os.path.exists(output_path):
        print("❌ Output file not found.")
        return

    outputs = load_jsonl(output_path)
    print(f"✅ Total successful records: {len(outputs)}")

    lengths = [len(o["input"].split()) for o in outputs]
    avg_len = mean(lengths)
    std_len = stdev(lengths) if len(lengths) > 1 else 0
    print(f"✏️  Prompt lengths: avg = {avg_len:.2f} words, std = {std_len:.2f}")

    if "trace" in outputs[0] and "paraphrase_index" in outputs[0]["trace"]["metadata"]:
        print("🔁 Dataset includes paraphrases.")

    return outputs

def main():
    # Update these paths as needed
    error_logs = [
        "llm_revlib_paraphrase_log.txt",
        "llm_github_paraphrase_log.txt",  # optional
    ]
    output_files = [
        "llm_revlib_paraphrased_v1.jsonl",
        "llm_github_paraphrased_v1.jsonl",
        "llm_paraphrased_train.jsonl",
        "llm_paraphrased_val.jsonl",
    ]

    for log in error_logs:
        if log.endswith(".jsonl"):
            analyze_errors(log)

    for out in output_files:
        analyze_outputs(out)

if __name__ == "__main__":
    main()
