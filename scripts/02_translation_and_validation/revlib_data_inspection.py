import json
import pandas as pd

revlib_file = "revlib_full_final_dataset.jsonl"

# Read and preview the first 5 entries
samples = []
with open(revlib_file, "r", encoding="utf-8") as f:
    for _ in range(5):
        line = f.readline()
        if line:
            samples.append(json.loads(line))

df = pd.DataFrame(samples)
print(df.head())
print("\n--- DataFrame Info ---")
print(df.info())
print("\n--- DataFrame Description ---")
