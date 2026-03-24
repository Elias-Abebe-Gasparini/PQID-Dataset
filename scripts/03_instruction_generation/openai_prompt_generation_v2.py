import os
import json
import time
import asyncio
import datetime
from openai import AsyncOpenAI, RateLimitError
from tqdm.asyncio import tqdm_asyncio

# Initialize async OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Check if the API key is set
if not client.api_key:
    raise ValueError("❌ OPENAI_API_KEY environment variable is not set.")

# Async prompt generation (new SDK)
async def generate_prompt_from_code_async(code, model="gpt-4"):
    system_msg = (
        "You are a quantum computing assistant. Given a quantum circuit "
        "implementation in either QASM or Qiskit, write a one-sentence prompt "
        "that would lead a language model to generate that circuit. Focus on function and structure."
    )
    user_msg = f"Here is the circuit implementation:\n\n{code}\n\nWhat is a suitable prompt to describe this circuit?"

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.5,
                max_tokens=100
            )
            return response.choices[0].message.content.strip(), response.usage

        except RateLimitError as e:
            wait_time = (2 ** attempt) * 0.5
            print(f"⚠️ Rate limit hit. Retrying in {wait_time:.1f} seconds...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            return f"__ERROR__: {str(e)}", None

    return "__ERROR__: Rate limit exceeded too many times", None

async def process_entry(entry, completed):
    key = entry["metadata"].get("filename") or entry["metadata"].get("file_path")
    if key in completed:
        return None, None, 0

    code = entry["circuit_code"]
    prompt, usage = await generate_prompt_from_code_async(code)
    if prompt.startswith("__ERROR__"):
        return None, {"circuit_name": entry["circuit_name"], "error": prompt}, 0

    record = {
        "input": prompt,
        "output": code,
        "trace": {
            "source": entry["source"],
            "original_url": entry["original_url"],
            "metadata": entry["metadata"]
        }
    }
    total_tokens = usage.total_tokens if usage else 0
    return record, None, total_tokens

async def build_instruction_dataset_async(input_file, output_file, log_file, max_entries=None, batch_size=5):
    with open(input_file, 'r', encoding='utf-8') as fin:
        lines = [json.loads(line) for line in fin]

    if max_entries is not None:
        lines = lines[:max_entries]

    completed = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line)
                    key = item["trace"]["metadata"].get("filename") or item["trace"]["metadata"].get("file_path")
                    if key:
                        completed.add(key)
                except Exception:
                    continue

    generated = []
    errors = []
    total_tokens_used = 0
    sem = asyncio.Semaphore(batch_size)
    start_time = time.time()
    perf_log_path = output_file.replace(".jsonl", "_perf_log.txt")

    async def sem_task(entry):
        async with sem:
            return await process_entry(entry, completed)

    total_batches = range(0, len(lines), batch_size)
    print(f"🚀 Starting async processing of {len(lines)} entries in {len(total_batches)} batches...")

    for i in tqdm_asyncio(total_batches):
        batch = lines[i:i+batch_size]
        tasks = [sem_task(entry) for entry in batch]
        results = await asyncio.gather(*tasks)

        for record, error, tokens in results:
            if record:
                with open(output_file, "a", encoding="utf-8") as fout:
                    fout.write(json.dumps(record) + "\n")
                generated.append(record)
                total_tokens_used += tokens
            if error:
                with open(log_file, "a", encoding="utf-8") as ferr:
                    ferr.write(json.dumps(error) + "\n")
                errors.append(error)

        elapsed = time.time() - start_time
        processed = len(generated) + len(errors)
        remaining = len(lines) - processed
        rate = processed / elapsed if elapsed > 0 else 0
        eta = str(datetime.timedelta(seconds=int(remaining / rate))) if rate > 0 else "Unknown"

        progress_log = (
            f"⏱ Batch {i//batch_size + 1}/{len(total_batches)} | "
            f"Processed: {processed} | ETA: {eta} | Elapsed: {int(elapsed)}s | "
            f"Total tokens used: {total_tokens_used}\n"
        )
        print(progress_log)
        with open(perf_log_path, "a", encoding="utf-8") as plog:
            plog.write(progress_log)

    summary = (
        f"\n✅ Completed {len(generated)} entries\n"
        f"⚠️ Logged {len(errors)} errors\n"
        f"📊 Total tokens used: {total_tokens_used}\n"
        f"⏱ Total elapsed time: {str(datetime.timedelta(seconds=int(time.time() - start_time)))}\n"
    )
    print(summary)
    with open(perf_log_path, "a", encoding="utf-8") as plog:
        plog.write(summary)

async def run_promptgen_batch():
    await build_instruction_dataset_async(
        "revlib_harmonized.jsonl",
        "llm_revlib_natural_v1.jsonl",
        "revlib_promptgen_log_v1.jsonl",
        max_entries=None,
        batch_size=10
    )
    await build_instruction_dataset_async(
        "github_harmonized.jsonl",
        "llm_github_natural_v1.jsonl",
        "github_promptgen_log_v1.jsonl",
        max_entries=None,
        batch_size=10
    )
