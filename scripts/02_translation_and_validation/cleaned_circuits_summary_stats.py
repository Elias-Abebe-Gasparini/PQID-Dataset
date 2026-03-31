import json

def summarize_cleaned_data(input_file="cleaned_circuits.jsonl", failed_output="failed_circuits.jsonl"):
    total = 0
    success = 0
    failures = []

    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            total += 1
            entry = json.loads(line)
            if "error" in entry:
                failures.append(entry)
            else:
                success += 1

    print(f"\n✅ Summary:")
    print(f"Total cleaned entries: {total}")
    print(f"Successful circuits    : {success}")
    print(f"Failed extractions     : {len(failures)}")
    print(f"\n⚠️ Writing {len(failures)} failures to {failed_output}")

    with open(failed_output, "w", encoding="utf-8") as f_out:
        for fail in failures:
            f_out.write(json.dumps(fail, indent=2) + "\n")

# Run this after cleaning
if __name__ == "__main__":
    summarize_cleaned_data()
