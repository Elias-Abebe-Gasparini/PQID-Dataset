"""
enrich_circuit_family.py
------------------------
Classifies every unique circuit (by circuit_hash) into a semantic circuit
family and intent category using GPT-4.1-mini.

Adds two metadata fields to each entry in the three *_clean.jsonl files:

    circuit_family   bell | ghz | qft | variational | qaoa | teleportation |
                     arithmetic | oracle | ansatz | phase_estimation |
                     error_correction | swap_test | grover | other

    semantic_intent  state_preparation | entanglement_generation |
                     variational_ansatz | algorithmic_subroutine |
                     arithmetic_reversible | oracle_construction |
                     measurement_driven | demonstration | other

Resume-safe: results cached in circuit_family_cache.jsonl.
Only unique circuits not yet in the cache are queried.
After all circuits are classified, the three *_clean.jsonl files are patched
in-place (atomic rename).

Run:
    python enrich_circuit_family.py
"""

import asyncio
import json
import os
import time
from pathlib import Path

from openai import AsyncOpenAI, RateLimitError

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = Path(
    "c:/Users/Abebe/Downloads/CAREER/ACADEMIC CAREER/SCHOOLS/YONSEI/"
    "YONSEI 2023/Yonsei SS 2025/MS Thesis/MS_THESIS_DATASET/PQID/data/processed"
)
API_KEY_FILE = r"C:\Users\Abebe\Downloads\IT\OPENAI\OPENAI_API_KEY_PQID_V2.txt"

INPUT_FILES = [
    BASE / "train_clean.jsonl",
    BASE / "validation_clean.jsonl",
    BASE / "test_clean.jsonl",
]
CACHE_FILE = BASE / "circuit_family_cache.jsonl"

MODEL      = "gpt-4.1-mini"
BATCH_SIZE = 40   # concurrent requests; GPT-4.1-mini handles high concurrency well

VALID_FAMILIES = {
    "bell", "ghz", "qft", "variational", "qaoa", "teleportation",
    "arithmetic", "oracle", "ansatz", "phase_estimation",
    "error_correction", "swap_test", "grover", "other",
}
VALID_INTENTS = {
    "state_preparation", "entanglement_generation", "variational_ansatz",
    "algorithmic_subroutine", "arithmetic_reversible", "oracle_construction",
    "measurement_driven", "demonstration", "other",
}

SYSTEM_MSG = (
    "You are a quantum computing expert. Given a Qiskit circuit implementation, "
    "classify it into exactly one circuit_family and one semantic_intent.\n\n"
    "circuit_family options:\n"
    "  bell, ghz, qft, variational, qaoa, teleportation, arithmetic, oracle,\n"
    "  ansatz, phase_estimation, error_correction, swap_test, grover, other\n\n"
    "semantic_intent options:\n"
    "  state_preparation, entanglement_generation, variational_ansatz,\n"
    "  algorithmic_subroutine, arithmetic_reversible, oracle_construction,\n"
    "  measurement_driven, demonstration, other\n\n"
    "Respond with ONLY a JSON object with keys 'circuit_family' and 'semantic_intent'.\n"
    "Example: {\"circuit_family\": \"ghz\", \"semantic_intent\": \"entanglement_generation\"}"
)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def load_api_key() -> str:
    key = ""
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE) as f:
            key = f.read().strip()
    if not key:
        key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise SystemExit("ERROR: OpenAI API key not found.")
    return key


def load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def save_jsonl(entries: list, path: Path) -> None:
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    tmp.replace(path)


def append_jsonl(record: dict, path: Path) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Collect unique circuits
# ---------------------------------------------------------------------------
def collect_unique_circuits(files: list) -> dict:
    """Return {circuit_hash: code} for all unique circuits."""
    circuits: dict = {}
    for path in files:
        for e in load_jsonl(path):
            ch   = e.get("metadata", {}).get("circuit_hash", "")
            code = e.get("output", "")
            if ch and ch not in circuits:
                circuits[ch] = code
    return circuits


# ---------------------------------------------------------------------------
# GPT classification
# ---------------------------------------------------------------------------
async def classify_circuit(
    client: AsyncOpenAI,
    circuit_hash: str,
    code: str,
    max_retries: int = 5,
) -> dict:
    user_msg = f"Classify this circuit:\n\n```python\n{code[:3000]}\n```"
    for attempt in range(max_retries):
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_MSG},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.0,
                max_tokens=60,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content.strip()
            parsed = json.loads(raw)
            family = parsed.get("circuit_family", "other").lower()
            intent = parsed.get("semantic_intent", "other").lower()
            if family not in VALID_FAMILIES:
                family = "other"
            if intent not in VALID_INTENTS:
                intent = "other"
            return {
                "circuit_hash":   circuit_hash,
                "circuit_family": family,
                "semantic_intent": intent,
            }
        except RateLimitError:
            wait = min(120, (2 ** attempt) * 2.0)
            await asyncio.sleep(wait)
        except Exception:
            await asyncio.sleep(2 ** attempt)

    return {
        "circuit_hash":   circuit_hash,
        "circuit_family": "other",
        "semantic_intent": "other",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    api_key = load_api_key()
    client  = AsyncOpenAI(api_key=api_key)

    print("Collecting unique circuits...", flush=True)
    all_circuits = collect_unique_circuits(INPUT_FILES)
    print(f"  Unique circuits: {len(all_circuits):,}", flush=True)

    # Load cache
    cache_records = load_jsonl(CACHE_FILE)
    cache = {r["circuit_hash"]: r for r in cache_records}
    print(f"  Already cached : {len(cache):,}", flush=True)

    pending = [(ch, code) for ch, code in all_circuits.items() if ch not in cache]
    print(f"  To classify    : {len(pending):,}", flush=True)

    # Classify missing
    sem           = asyncio.Semaphore(BATCH_SIZE)
    done          = 0
    t0            = time.time()

    async def process(ch: str, code: str):
        nonlocal done
        async with sem:
            rec = await classify_circuit(client, ch, code)
            cache[ch] = rec
            append_jsonl(rec, CACHE_FILE)
            done += 1
            if done % 500 == 0 or done == len(pending):
                elapsed = time.time() - t0
                print(
                    f"  {done}/{len(pending)} ({100*done/len(pending):.1f}%)  "
                    f"elapsed={elapsed:.0f}s",
                    flush=True,
                )

    tasks = [process(ch, code) for ch, code in pending]
    await asyncio.gather(*tasks)

    # Patch files
    print("\nPatching JSONL files...", flush=True)
    total_patched = 0
    for path in INPUT_FILES:
        entries = load_jsonl(path)
        if not entries:
            continue
        patched = 0
        for entry in entries:
            ch  = entry.get("metadata", {}).get("circuit_hash", "")
            rec = cache.get(ch)
            if rec:
                entry["metadata"]["circuit_family"]  = rec["circuit_family"]
                entry["metadata"]["semantic_intent"] = rec["semantic_intent"]
                patched += 1
        save_jsonl(entries, path)
        total_patched += patched
        print(f"  {path.name}: patched {patched:,} / {len(entries):,}", flush=True)

    # Summary
    family_counts: dict = {}
    intent_counts: dict = {}
    for rec in cache.values():
        f = rec.get("circuit_family", "other")
        i = rec.get("semantic_intent", "other")
        family_counts[f] = family_counts.get(f, 0) + 1
        intent_counts[i] = intent_counts.get(i, 0) + 1

    print("\n=== CIRCUIT FAMILY DISTRIBUTION (unique circuits) ===")
    for fam in sorted(family_counts, key=lambda x: -family_counts[x]):
        print(f"  {fam:<25} {family_counts[fam]:>6,}")

    print("\n=== SEMANTIC INTENT DISTRIBUTION ===")
    for intent in sorted(intent_counts, key=lambda x: -intent_counts[x]):
        print(f"  {intent:<30} {intent_counts[intent]:>6,}")

    print(f"\nTotal entries patched: {total_patched:,}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
