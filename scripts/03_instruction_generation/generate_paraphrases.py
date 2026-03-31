"""
generate_paraphrases.py
-----------------------
Stage 2 — Generate 5 paraphrases per seed instruction in seeds.jsonl.

For each seed, the model produces 5 differently-worded instructions that
preserve the original meaning, giving the 1:5 seed-to-paraphrase ratio
that is central to the PQID dataset design.

Output: paraphrases.jsonl  (5 entries per circuit, prompt_type="paraphrased")

Resume-safe: skips circuit_hashes already present in paraphrases.jsonl.

Run:
    python generate_paraphrases.py
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

INPUT_FILE  = BASE / "seeds.jsonl"
OUTPUT_FILE = BASE / "paraphrases.jsonl"
LOG_FILE    = BASE / "paraphrases_errors.jsonl"

MODEL           = "gpt-4o-mini"
BATCH_SIZE      = 30
NUM_PARAPHRASES = 5
MAX_TOKENS      = 600

GENERATION_DATE = str(datetime.date.today())

SYSTEM_MSG = "You are a helpful paraphrasing assistant for technical content."

PARAPHRASE_PROMPT_TEMPLATE = (
    "Generate {n} different paraphrased versions of the following quantum circuit "
    "instruction with varied wording but identical meaning. "
    "Each paraphrase must:\n"
    "  - Be a single sentence under 50 words\n"
    "  - Preserve all technical details (gate types, qubit counts, algorithms)\n"
    "  - Use different phrasing, vocabulary, or sentence structure\n"
    "Output exactly {n} paraphrases, one per line, no numbering or bullets:\n\n"
    "'{instruction}'"
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
async def generate_paraphrases(
    client: AsyncOpenAI,
    instruction: str,
    n: int = NUM_PARAPHRASES,
    max_retries: int = 6,
) -> tuple[list[str], int]:
    prompt = PARAPHRASE_PROMPT_TEMPLATE.format(n=n, instruction=instruction)
    for attempt in range(max_retries):
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_MSG},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.85,
                max_tokens=MAX_TOKENS,
            )
            raw    = resp.choices[0].message.content.strip()
            tokens = resp.usage.total_tokens if resp.usage else 0
            # Clean up numbering, dashes, bullets
            lines = [
                l.strip().lstrip("0123456789.-) ").strip()
                for l in raw.split("\n")
                if l.strip()
            ]
            # Drop lines that look like headers or are too short
            lines = [l for l in lines if len(l.split()) >= 4]
            return lines[:n], tokens
        except RateLimitError:
            wait = min(120, (2 ** attempt) * 2.0)
            print(f"  Rate limit — waiting {wait:.0f}s...", flush=True)
            await asyncio.sleep(wait)
        except Exception as exc:
            if attempt == max_retries - 1:
                return [], 0
            await asyncio.sleep(2 ** attempt)
    return [], 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    api_key = load_api_key()
    client  = AsyncOpenAI(api_key=api_key)

    seeds = load_jsonl(INPUT_FILE)
    print(f"Seeds loaded    : {len(seeds):,}", flush=True)

    # Resume: skip hashes already in output
    done_hashes = {
        e["metadata"]["circuit_hash"]
        for e in load_jsonl(OUTPUT_FILE)
    }
    todo = [
        e for e in seeds
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
            seed_instruction = entry["input"]
            code             = entry["output"]
            meta_base        = dict(entry.get("metadata", {}))
            ch               = meta_base.get("circuit_hash", "")

            paraphrases, tokens = await generate_paraphrases(client, seed_instruction)
            total_tokens += tokens

            if not paraphrases:
                append_jsonl({"circuit_hash": ch, "error": "empty_response"}, LOG_FILE)
                error_count += 1
                return

            for para in paraphrases:
                ch_content = content_hash(para, code)
                out = {
                    "input":  para,
                    "output": code,
                    "metadata": {
                        **meta_base,
                        "prompt_type":        "paraphrased",
                        "quality_flag":       "pending",
                        "paraphrase_source":  ch,        # hash of the seed this came from
                        "original_prompt":    seed_instruction,
                        "generation_model":   MODEL,
                        "generation_date":    GENERATION_DATE,
                        "content_hash":       ch_content,
                        "prompt_word_count":  len(para.split()),
                        "prompt_length_chars": len(para),
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

    elapsed       = time.time() - t0
    total_entries = success_count * NUM_PARAPHRASES
    print(f"\nDone in {str(datetime.timedelta(seconds=int(elapsed)))}", flush=True)
    print(f"  Success : {success_count:,}  Errors : {error_count}", flush=True)
    print(f"  Entries : {total_entries:,}", flush=True)
    print(f"  Tokens  : {total_tokens:,}", flush=True)
    est_cost = (total_tokens / 1_000_000) * 0.30
    print(f"  Est. cost : ${est_cost:.3f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
