"""
generate_seeds.py
-----------------
Stage 1 — Generate one seed instruction per circuit in the master processable
corpus when available, otherwise falling back to the richest available
raw/enriched circuit pool.

For each circuit the model receives the raw Qiskit/OpenQASM code and returns
a single concise English sentence (≤ 40 words) describing what the circuit
does and what instruction would lead someone to implement it.

Output: seeds.jsonl  (one entry per circuit, prompt_type="human_seed")

Resume-safe: skips circuits whose circuit_hash already appears in seeds.jsonl.

Run:
    python generate_seeds.py
"""

import argparse
import asyncio
import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from openai import AsyncOpenAI, RateLimitError

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from project_paths import PROCESSED_DIR, load_openai_api_key

try:
    import tiktoken
    _CL100K = tiktoken.get_encoding("cl100k_base")
except Exception:
    _CL100K = None

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE = PROCESSED_DIR

DEFAULT_OUTPUT_FILE = BASE / "seeds.jsonl"
DEFAULT_LOG_FILE    = BASE / "seeds_errors.jsonl"

MODEL       = "gpt-4.1-mini"
BATCH_SIZE  = 30     # concurrent requests
MAX_TOKENS  = 150    # seed instructions are short

GENERATION_DATE = str(datetime.date.today())

SYSTEM_MSG = (
    "You are a quantum computing assistant. "
    "Given a quantum circuit implementation in Qiskit (Python) or OpenQASM 3.0, "
    "and optionally some structural metadata extracted from the same circuit, "
    "write a single concise English instruction (one sentence, under 40 words) "
    "that describes what the circuit does and would lead someone to implement it. "
    "Focus on the circuit's structure and gate operations. "
    "Treat metadata as supporting hints only, and trust the code if there is any mismatch. "
    "Do not include code, backticks, or explanations — only the instruction sentence."
)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def default_input_file() -> Path:
    candidates = [
        BASE / "circuits_unified_plus_phase2_plus_phase3_master_processable_enriched.jsonl",
        BASE / "circuits_unified_plus_phase2_plus_phase3_core_enriched.jsonl",
        BASE / "circuits_unified_plus_aggressive_core_enriched.jsonl",
        BASE / "circuits_unified_plus_phase2_plus_phase3_enriched.jsonl",
        BASE / "circuits_unified_plus_phase2_plus_phase3_broad_enriched.jsonl",
        BASE / "circuits_unified_plus_phase2_plus_phase3.jsonl",
        BASE / "circuits_unified_plus_aggressive_enriched.jsonl",
        BASE / "circuits_unified_plus_aggressive_broad_enriched.jsonl",
        BASE / "circuits_unified_plus_aggressive_broad.jsonl",
        BASE / "circuits_unified_plus_aggressive.jsonl",
        BASE / "circuits_unified_enriched.jsonl",
        BASE / "circuits_unified.jsonl",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate one seed instruction per circuit."
    )
    parser.add_argument(
        "--input-file",
        default=str(default_input_file()),
        help="Path to the master-processable or enriched circuit JSONL pool.",
    )
    parser.add_argument(
        "--output-file",
        default=str(DEFAULT_OUTPUT_FILE),
        help="Path to write seeds.jsonl style output.",
    )
    parser.add_argument(
        "--log-file",
        default=str(DEFAULT_LOG_FILE),
        help="Path to write per-circuit generation errors.",
    )
    parser.add_argument(
        "--no-metadata-anchors",
        action="store_true",
        help="Ignore structural metadata and prompt from code only.",
    )
    return parser.parse_args()


def load_api_key() -> str:
    return load_openai_api_key(__file__)


def load_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def append_jsonl(entry: dict, path: Path) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def content_hash(input_text: str, output_text: str) -> str:
    combined = (input_text + output_text).strip()
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


def token_count_cl100k(text: str):
    if _CL100K is None or not text or not text.strip():
        return None
    try:
        return len(_CL100K.encode(text))
    except Exception:
        return None


def build_metadata_anchor_text(meta: dict) -> str:
    if not meta:
        return ""

    anchor_lines = []
    ordered_fields = [
        ("num_qubits", "qubits"),
        ("num_clbits", "classical bits"),
        ("quantum_register_count", "quantum registers"),
        ("gate_count", "gate count"),
        ("circuit_depth", "circuit depth"),
        ("circuit_expressiveness", "expressiveness"),
        ("size_class", "size class"),
        ("benchmark_difficulty", "benchmark difficulty"),
        ("is_parameterized", "parameterized"),
        ("num_parameters", "parameter count"),
        ("has_measurement", "has measurement"),
        ("measurement_count", "measurement operations"),
        ("measured_qubit_count", "measured qubits"),
        ("two_qubit_gate_count", "two-qubit gates"),
        ("multi_qubit_gate_count", "three-plus-qubit gates"),
        ("entanglement_depth", "entanglement depth"),
        ("has_control_flow", "has control flow"),
        ("control_flow_op_count", "control-flow ops"),
        ("has_barriers", "has barriers"),
    ]

    for key, label in ordered_fields:
        value = meta.get(key)
        if value is None or value == "":
            continue
        anchor_lines.append(f"- {label}: {value}")

    gate_types = meta.get("gate_types")
    if isinstance(gate_types, dict) and gate_types:
        top_gates = sorted(gate_types.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
        anchor_lines.append(
            "- top gate types: " + ", ".join(f"{name}:{count}" for name, count in top_gates)
        )

    if not anchor_lines:
        return ""

    return (
        "Structural metadata extracted from the circuit "
        "(use only as supporting hints if consistent with the code):\n"
        + "\n".join(anchor_lines)
    )


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------
async def generate_seed(
    client: AsyncOpenAI, circuit_code: str, metadata_anchor: str = "", max_retries: int = 6
) -> tuple[str, int]:
    parts = []
    if metadata_anchor:
        parts.append(metadata_anchor)
    parts.append("Here is the circuit implementation:\n\n" + circuit_code)
    parts.append("Write a suitable one-sentence instruction for this circuit.")
    user_msg = "\n\n".join(parts)
    for attempt in range(max_retries):
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_MSG},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.5,
                max_tokens=MAX_TOKENS,
            )
            text   = resp.choices[0].message.content.strip()
            tokens = resp.usage.total_tokens if resp.usage else 0
            return text, tokens
        except RateLimitError:
            wait = min(120, (2 ** attempt) * 2.0)
            print(f"  Rate limit — waiting {wait:.0f}s...", flush=True)
            await asyncio.sleep(wait)
        except Exception as exc:
            if attempt == max_retries - 1:
                return f"__ERROR__: {exc}", 0
            await asyncio.sleep(2 ** attempt)
    return "__ERROR__: max retries exceeded", 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    args = parse_args()
    api_key = load_api_key()
    client  = AsyncOpenAI(api_key=api_key)

    input_file = Path(args.input_file)
    output_file = Path(args.output_file)
    log_file = Path(args.log_file)

    circuits = load_jsonl(input_file)
    print(f"Input file      : {input_file}", flush=True)
    print(f"Output file     : {output_file}", flush=True)
    print(f"Error log       : {log_file}", flush=True)
    print(f"Metadata anchors: {not args.no_metadata_anchors}", flush=True)
    print(f"Circuits loaded : {len(circuits):,}", flush=True)

    # Resume: build set of already-processed circuit_hashes
    done_hashes = {
        e["metadata"]["circuit_hash"]
        for e in load_jsonl(output_file)
    }
    todo = [
        e for e in circuits
        if e.get("metadata", {}).get("circuit_hash", "") not in done_hashes
    ]
    print(f"Already done    : {len(done_hashes):,}", flush=True)
    print(f"Remaining       : {len(todo):,}", flush=True)

    if not todo:
        print("Nothing to do.", flush=True)
        return

    sem           = asyncio.Semaphore(BATCH_SIZE)
    total_tokens  = 0
    success_count = 0
    error_count   = 0
    t0            = time.time()

    async def process(entry):
        nonlocal total_tokens, success_count, error_count
        async with sem:
            code     = entry["output"]
            meta     = entry.get("metadata", {})
            ch       = meta.get("circuit_hash", "")
            metadata_anchor = ""
            if not args.no_metadata_anchors:
                metadata_anchor = build_metadata_anchor_text(meta)
            prompt, tokens = await generate_seed(client, code, metadata_anchor=metadata_anchor)
            total_tokens += tokens

            if prompt.startswith("__ERROR__"):
                append_jsonl({"circuit_hash": ch, "error": prompt}, log_file)
                error_count += 1
                return

            ch_content = content_hash(prompt, code)
            out = {
                "input":  prompt,
                "output": code,
                "metadata": {
                    **meta,
                    "prompt_type":      "human_seed",
                    "quality_flag":     "pending",
                    "generation_model": MODEL,
                    "generation_date":  GENERATION_DATE,
                    "content_hash":     ch_content,
                    "prompt_word_count":   len(prompt.split()),
                    "prompt_length_chars": len(prompt),
                    "prompt_token_count_cl100k": token_count_cl100k(prompt),
                },
            }
            append_jsonl(out, output_file)
            success_count += 1

    tasks = [process(e) for e in todo]

    chunk = BATCH_SIZE * 5
    for i in range(0, len(tasks), chunk):
        await asyncio.gather(*tasks[i : i + chunk])
        elapsed  = time.time() - t0
        done     = success_count + error_count
        rate     = done / elapsed if elapsed > 0 else 1
        eta_secs = (len(todo) - done) / rate if rate > 0 else 0
        eta      = str(datetime.timedelta(seconds=int(eta_secs)))
        print(
            f"  {done:,}/{len(todo):,} | ok={success_count:,} err={error_count} "
            f"| tokens={total_tokens:,} | ETA {eta}",
            flush=True,
        )

    elapsed = time.time() - t0
    print(f"\nDone in {str(datetime.timedelta(seconds=int(elapsed)))}", flush=True)
    print(f"  Success : {success_count:,}  Errors : {error_count}", flush=True)
    print(f"  Tokens  : {total_tokens:,}", flush=True)
    est_cost = (total_tokens / 1_000_000) * 0.30   # gpt-4o-mini blended ~$0.30/1M
    print(f"  Est. cost : ${est_cost:.3f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
