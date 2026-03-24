import os
import json
import time
import asyncio
import datetime
from openai import AsyncOpenAI, RateLimitError
from tqdm.asyncio import tqdm_asyncio

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_paraphrases(prompt, num=5, max_retries=8):
    instruction = (
        f"Generate {num} different paraphrased versions of the following sentence "
        "with slight variations in wording but the same meaning. Keep each under 50 words:\n\n"
        f"'{prompt}'"
    )

    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": "You are a helpful paraphrasing assistant."},
                    {"role": "user", "content": instruction}
                ],
                temperature=0.8,
                max_tokens=400
            )
            outputs = response.choices[0].message.content.strip()
            token_usage = response.usage.total_tokens
            lines = [line.strip("0123456789. ").strip() for line in outputs.split("\n") if line.strip()]
            return lines[:num], token_usage
        except RateLimitError:
            wait = min(60, (2 ** attempt) * 0.8)
            print(f"⚠️ Rate limit (attempt {attempt+1}). Waiting {wait:.1f}s...")
            await asyncio.sleep(wait)
        except Exception as e:
            print(f"❌ Error: {e}")
            return [], 0
    return [], 0

async def process_entry(entry, num=5):
    original = entry['input']
    paraphrases, tokens = await generate_paraphrases(original, num=num)

    records = []
    for i, para in enumerate(paraphrases):
        record = {
            "input": para,
            "output": entry["output"],
            "trace": {
                "source": entry["trace"]["source"],
                "original_url": entry["trace"]["original_url"],
                "metadata": entry["trace"]["metadata"],
                "paraphrase_index": i,
                "original_prompt": original
            }
        }
        records.append(record)

    return records, tokens

async def paraphrase_prompts_batch(input_file, output_file, log_file, batch_size=5, num_paraphrases=5):
    with open(input_file, 'r', encoding='utf-8') as f:
        entries = [json.loads(line) for line in f]

    sem = asyncio.Semaphore(batch_size)
    start_time = time.time()
    total_tokens = 0

    async def sem_task(entry):
        async with sem:
            return await process_entry(entry, num=num_paraphrases)

    with open(output_file, 'w', encoding='utf-8') as fout, open(log_file, 'w', encoding='utf-8') as flog:
        for i in tqdm_asyncio(range(0, len(entries), batch_size)):
            batch = entries[i:i + batch_size]
            tasks = [sem_task(e) for e in batch]
            results = await asyncio.gather(*tasks)

            for records, tokens in results:
                for r in records:
                    fout.write(json.dumps(r) + "\n")
                total_tokens += tokens

                if records:
                    log_entry = f"✅ {r['trace']['metadata'].get('filename') or r['trace']['metadata'].get('file_path')} | Paraphrases: {len(records)} | Tokens: {tokens}"
                    print(log_entry)
                    flog.write(log_entry + "\n")

    duration = str(datetime.timedelta(seconds=int(time.time() - start_time)))
    summary = f"\n✅ Done. Total tokens used: {total_tokens}\n⏱ Total time: {duration}\n"
    print(summary)
    with open(log_file, 'a', encoding='utf-8') as flog:
        flog.write(summary)

# ✅ This is the function you call from the notebook
async def run_promptgen_batch():
    await paraphrase_prompts_batch(
        input_file="llm_github_natural_v1.jsonl",
        output_file="llm_github_paraphrased_v1.jsonl",
        log_file="llm_github_paraphrase_log.txt",
        batch_size=5,
        num_paraphrases=5
    )
    await paraphrase_prompts_batch(
        input_file="llm_revlib_natural_v1.jsonl",
        output_file="llm_revlib_paraphrased_v1.jsonl",
        log_file="llm_revlib_paraphrase_log.txt",
        batch_size=5,
        num_paraphrases=5
    )

if __name__ == "__main__":
    asyncio.run(run_promptgen_batch())   