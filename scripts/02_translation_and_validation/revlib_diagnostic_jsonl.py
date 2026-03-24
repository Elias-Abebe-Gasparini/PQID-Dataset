import json

filename = "revlib_gates_converted.jsonl"

with open(filename, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            print(f"❌ Error on line {i}: {e}")
            break
    else:
        print(f"✅ All lines in {filename} are valid JSON.")
