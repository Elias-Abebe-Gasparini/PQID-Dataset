import json
from collections import Counter

error_counter = Counter()

with open("rejected_circuits.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        try:
            entry = json.loads(line)
            error = entry.get("error", "unknown_error")
            error_counter[error] += 1
        except Exception:
            error_counter["malformed_json"] += 1

print("🚨 Error Summary:")
for err, count in error_counter.most_common():
    print(f"{err:<30}: {count}")
