import argparse
import csv
import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPARISON_DIR = ROOT / "data/processed/seed_temperature_comparison"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a blinded human-annotation pack for seed-temperature studies.")
    parser.add_argument("--comparison-dir", type=Path, default=DEFAULT_COMPARISON_DIR)
    parser.add_argument("--label", required=True, help="Study label, e.g. tempstudy_v4_highrigor")
    parser.add_argument("--temps", required=True, help="Comma-separated temperature list, e.g. 0.1,0.2,0.3")
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=None,
        help="Output prefix without extension. Defaults to <comparison-dir>/seed_temperature_annotation_pack_<label>",
    )
    parser.add_argument("--random-seed", type=int, default=20260412)
    return parser.parse_args()


def temp_suffix(temp: float) -> str:
    return f"{temp:.1f}".replace(".", "p")


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def stable_blind_id(label: str, circuit_hash: str, seed_role: str, position: int) -> str:
    base = f"{label}|{circuit_hash}|{seed_role}|{position}"
    digest = hashlib.md5(base.encode("utf-8")).hexdigest()[:10]
    return f"blind_{digest}"


def main() -> None:
    args = parse_args()
    temps = [float(item.strip()) for item in args.temps.split(",") if item.strip()]
    if not temps:
        raise ValueError("No temperatures parsed from --temps.")

    if args.output_prefix is None:
        output_prefix = args.comparison_dir / f"seed_temperature_annotation_pack_{args.label}"
    else:
        output_prefix = args.output_prefix
    output_prefix.parent.mkdir(parents=True, exist_ok=True)

    rows_by_temp = {}
    for temp in temps:
        file_path = args.comparison_dir / f"seed_drafts_quality_aware_{args.label}_temp_{temp_suffix(temp)}.jsonl"
        if not file_path.exists():
            raise FileNotFoundError(f"Missing comparison file: {file_path}")
        rows_by_temp[temp] = load_rows(file_path)

    indexed = {}
    for temp, rows in rows_by_temp.items():
        indexed[temp] = {}
        for row in rows:
            meta = row.get("metadata", {})
            key = (meta.get("circuit_hash"), meta.get("seed_role"))
            indexed[temp][key] = row

    common_keys = sorted(set.intersection(*(set(mapping.keys()) for mapping in indexed.values())))
    if not common_keys:
        raise ValueError("No common matched rows found across the requested temperatures.")

    randomizer = random.Random(args.random_seed)
    annotation_rows = []
    key_position = {key: idx + 1 for idx, key in enumerate(common_keys)}
    for key in common_keys:
        circuit_hash, seed_role = key
        temp_order = temps[:]
        randomizer.shuffle(temp_order)
        for blind_rank, temp in enumerate(temp_order, start=1):
            row = indexed[temp][key]
            meta = row.get("metadata", {})
            annotation_rows.append(
                {
                    "blind_item_id": stable_blind_id(args.label, circuit_hash, seed_role, blind_rank),
                    "study_label": args.label,
                    "circuit_hash": circuit_hash,
                    "seed_role": seed_role,
                    "prompt_text": row.get("input", ""),
                    "source_code": row.get("output", ""),
                    "openqasm3_code": row.get("openqasm3_code", ""),
                    "num_qubits": meta.get("num_qubits"),
                    "gate_types": json.dumps(meta.get("gate_types"), ensure_ascii=False),
                    "has_measurement": meta.get("has_measurement"),
                    "measurement_count": meta.get("measurement_count"),
                    "is_parameterized": meta.get("is_parameterized"),
                    "num_parameters": meta.get("num_parameters"),
                    "semantic_fidelity_1to5": "",
                    "role_fidelity_1to5": "",
                    "clarity_1to5": "",
                    "unnecessary_drift_1to5": "",
                    "benchmark_appropriateness_1to5": "",
                    "overall_preference_1to5": "",
                    "accept_for_seed_bank": "",
                    "reviewer_notes": "",
                    "_hidden_temperature": temp,
                    "_matched_position": key_position[key],
                }
            )

    randomizer.shuffle(annotation_rows)

    jsonl_path = output_prefix.with_suffix(".jsonl")
    csv_path = output_prefix.with_suffix(".csv")
    key_path = output_prefix.with_name(output_prefix.name + "_key.json")

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in annotation_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(annotation_rows[0].keys()))
        writer.writeheader()
        writer.writerows(annotation_rows)

    key_rows = [
        {
            "blind_item_id": row["blind_item_id"],
            "study_label": row["study_label"],
            "circuit_hash": row["circuit_hash"],
            "seed_role": row["seed_role"],
            "hidden_temperature": row["_hidden_temperature"],
            "matched_position": row["_matched_position"],
        }
        for row in annotation_rows
    ]
    with key_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "study_label": args.label,
                "temps": temps,
                "random_seed": args.random_seed,
                "matched_rows": len(common_keys),
                "annotation_rows": len(annotation_rows),
                "key_rows": key_rows,
            },
            handle,
            indent=2,
        )

    print("annotation pack JSONL:", jsonl_path)
    print("annotation pack CSV  :", csv_path)
    print("annotation key JSON  :", key_path)
    print("matched rows         :", len(common_keys))
    print("annotation rows      :", len(annotation_rows))


if __name__ == "__main__":
    main()
