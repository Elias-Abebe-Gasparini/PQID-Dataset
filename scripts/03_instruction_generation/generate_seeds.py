"""
generate_seeds.py
-----------------
Stage 1 — Generate one seed instruction per circuit in circuits_unified.jsonl.

For each circuit the model receives the raw Qiskit/OpenQASM code and returns
a single concise English sentence (≤ 40 words) describing what the circuit
does and what instruction would lead someone to implement it.

Output: seeds.jsonl  (one entry per circuit, prompt_type="human_seed")

Resume-safe: skips circuits whose circuit_hash already appears in seeds.jsonl.

Run:
    python generate_seeds.py
"""

import asyncio
import datetime
import hashlib
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

INPUT_FILE  = BASE / "circuits_unified.jsonl"
OUTPUT_FILE = BASE / "seeds.jsonl"
LOG_FILE    = BASE / "seeds_errors.jsonl"

MODEL       = "gpt-4o-mini"
BATCH_SIZE  = 30     # concurrent requests
MAX_TOKENS  = 150    # seed instructions are short

GENERATION_DATE = str(datetime.date.today())

SYSTEM_MSG = (
    "You are a quantum computing assistant. "
    "Given a quantum circuit implementation in Qiskit (Python) or OpenQASM 3.0, "
    "write a single concise English instruction (one sentence, under 40 words) "
    "that describes what the circuit does and would lead someone to implement it. "
    "Focus on the circuit's structure and gate operations. "
    "Do not include code, backticks, or explanations — only the instruction sentence."
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


def append_jsonl(entry: dict, path: Path) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def content_hash(input_text: str, output_text: str) -> str:
    combined = (input_text + output_text).strip()
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------
async def generate_seed(
    client: AsyncOpenAI, circuit_code: str, max_retries: int = 6
) -> tuple[str, int]:
    user_msg = (
        "Here is the circuit implementation:\n\n"
        f"{circuit_code}\n\n"
        "Write a suitable one-sentence instruction for this circuit."
    )
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
    api_key = load_api_key()
    client  = AsyncOpenAI(api_key=api_key)

    circuits = load_jsonl(INPUT_FILE)
    print(f"Circuits loaded : {len(circuits):,}", flush=True)

    # Resume: build set of already-processed circuit_hashes
    done_hashes = {
        e["metadata"]["circuit_hash"]
        for e in load_jsonl(OUTPUT_FILE)
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
            prompt, tokens = await generate_seed(client, code)
            total_tokens += tokens

            if prompt.startswith("__ERROR__"):
                append_jsonl({"circuit_hash": ch, "error": prompt}, LOG_FILE)
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
                },
            }
            append_jsonl(out, OUTPUT_FILE)
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
