"""
generate_seed_drafts_quality_aware.py
-------------------------------------
Draft one quality-aware seed per manifest entry using the role-conditioned
teacher regime defined in SEED_GENERATION_DESIGN.md.

This is intentionally a pilot-friendly script:
- resume-safe
- manifest-driven
- dry-run capable
- writes draft-stage metadata instead of pretending critique/rewrite is done

OpenAI API note:
- this script uses the Responses API (`client.responses.create`) because that
  is the recommended interface for current GPT-5.x models such as `gpt-5.4`
  in the official API documentation.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from openai import AsyncOpenAI, RateLimitError
except ImportError:  # pragma: no cover - enables offline reuse of parsing helpers
    AsyncOpenAI = None  # type: ignore[assignment]

    class RateLimitError(Exception):
        """Fallback placeholder when openai is unavailable for offline utilities."""

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from project_paths import (
    PROCESSED_DIR,
    format_display_path,
    load_openai_api_key,
)

from quality_aware_seed_common import (
    DEFAULT_TEACHER_MODEL,
    QUALITY_AWARE_BASE_SEED_PROMPT_TYPE,
    SEED_CRITIQUE_TEMPLATE_VERSION,
    SEED_TEMPLATE_VERSION,
    format_prompt_payload,
)


DEFAULT_MANIFEST_FILE = PROCESSED_DIR / "seed_role_manifest_v1_source_code.jsonl"
DEFAULT_SOURCE_FILE = PROCESSED_DIR / "pqid_2026_enriched_github_circuits.jsonl"
DEFAULT_OUTPUT_FILE = PROCESSED_DIR / "seed_drafts_quality_aware_v1.jsonl"
DEFAULT_LOG_FILE = PROCESSED_DIR / "seed_drafts_quality_aware_v1_errors.jsonl"

BATCH_SIZE = 12
DEFAULT_MAX_TOKENS = 220
DEFAULT_TEMPERATURE = 0.1


ROLE_INSTRUCTIONS = {
    "gold_generation": (
        "Write one concise, clean, high-quality user instruction that would "
        "naturally lead an assistant to produce the given circuit."
    ),
    "broad_generation": (
        "Write one concise but still natural user instruction for broader "
        "coverage. Keep it useful and grounded, but do not imply that the "
        "example is the highest-trust benchmark gold standard."
    ),
    "mutation_robustness": (
        "Write one task instruction that frames the example as analysis, bug "
        "recognition, mutation-aware comparison, or robustness evaluation. "
        "Do not frame it as an ordinary clean benchmark example."
    ),
    "repair_or_explanation": (
        "Write one task instruction that asks for completion, repair, critique, "
        "or an explanation of why the circuit is not benchmark-ready."
    ),
    "validation_diagnosis": (
        "Write one task instruction that asks for diagnosis, error analysis, "
        "or repair planning. Avoid pretending the source is already correct."
    ),
}


SYSTEM_PROMPT = """You are generating one seed instruction for the PQID project.

Return valid JSON only with exactly these keys:
- "seed_input"
- "seed_quality_note"
- optionally "teacher_output" when the target supervision mode is `teacher_text`

Requirements:
- "seed_input" must be a single natural-language instruction in English.
- The instruction must match the assigned seed role and learning objective.
- Keep the instruction specific, compact, and semantically grounded in the source circuit.
- Vary wording and sentence openings across examples; avoid defaulting to the same opener repeatedly.
- Prefer natural task phrasing over boilerplate formulations such as repeatedly starting with "Using Qiskit" or "Write a Qiskit".
- Do not mention metadata field names directly.
- Do not mention benchmark scores, tier labels, or internal dataset jargon.
- Do not invent capabilities or behavior not supported by the source circuit.
- If the role is mutation or diagnosis oriented, make that analytical framing explicit.
- If the target supervision mode is `teacher_text`, "teacher_output" must answer the generated instruction directly and remain grounded in the source record.
- When the source circuit is large or semantically opaque, keep the instruction as compact as fidelity permits and compress repetitive structure such as one-to-one terminal measurements.
"""


TEACHER_OUTPUT_INSTRUCTIONS = {
    "mutation_robustness": (
        "Also return `teacher_output` as the assistant answer. It should explain "
        "why the example belongs in a mutation-robustness or bug-stress framing, "
        "identify the key semantic risk or mutation effect, and describe how the "
        "canonical behavior would differ or how the example should be repaired."
    ),
    "validation_diagnosis": (
        "Also return `teacher_output` as the assistant answer. It should diagnose "
        "why the example should not be treated as a complete trustworthy implementation, "
        "identify the most important missing or problematic elements, and outline a "
        "cautious repair plan without inventing unsupported behavior."
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-file", default=str(DEFAULT_MANIFEST_FILE))
    parser.add_argument("--source-file", default=str(DEFAULT_SOURCE_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_FILE))
    parser.add_argument("--model", default=DEFAULT_TEACHER_MODEL)
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(entry: dict, path: Path) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def seed_key(manifest_entry: dict) -> tuple[str, str]:
    source = manifest_entry["source_record"]
    return source["circuit_hash"], manifest_entry["seed_role"]


def load_completed_keys(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    completed: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            meta = row.get("metadata", {})
            completed.add((meta.get("circuit_hash"), meta.get("seed_role")))
    return completed


def summarize_seed_artifacts(output_file: Path, log_file: Path) -> dict[str, Any]:
    role_counts = Counter()
    prompt_type_counts = Counter()
    supervision_mode_counts = Counter()
    temperature_counts = Counter()
    circuit_hashes: set[str] = set()
    rows = 0

    if output_file.exists():
        with output_file.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                meta = row.get("metadata", {})
                rows += 1
                role_counts[meta.get("seed_role", "<missing>")] += 1
                prompt_type_counts[meta.get("prompt_type", "<missing>")] += 1
                supervision_mode_counts[meta.get("seed_target_supervision_mode", "<missing>")] += 1
                temperature_counts[str(meta.get("seed_generation_temperature", "<missing>"))] += 1
                circuit_hash = str(meta.get("circuit_hash", "")).strip()
                if circuit_hash:
                    circuit_hashes.add(circuit_hash)

    error_rows = 0
    error_type_counts = Counter()
    if log_file.exists():
        with log_file.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                error_rows += 1
                entry = json.loads(line)
                error_type_counts[entry.get("error_type", "<missing>")] += 1

    return {
        "rows": rows,
        "unique_circuit_hashes": len(circuit_hashes),
        "role_counts": role_counts,
        "prompt_type_counts": prompt_type_counts,
        "supervision_mode_counts": supervision_mode_counts,
        "temperature_counts": temperature_counts,
        "error_rows": error_rows,
        "error_type_counts": error_type_counts,
    }


def content_hash(input_text: str, output_text: str) -> str:
    return hashlib.md5((input_text + "\n" + output_text).encode("utf-8")).hexdigest()


def int_meta(meta: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = meta.get(key)
        if value in (None, ""):
            continue
        try:
            return int(value)
        except Exception:
            continue
    return 0


VALID_JSON_ESCAPES = set('"\\/bfnrtu')
SEED_JSON_FIELD_ORDER = ("seed_input", "seed_quality_note", "teacher_output")


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_candidate(text: str) -> str:
    text = _strip_markdown_fence(text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    start = text.find("{")
    if start != -1:
        return text[start:]
    return text


def _sanitize_json_string_content(raw: str) -> str:
    out: list[str] = []
    escape = False
    for ch in raw:
        if escape:
            if ch in VALID_JSON_ESCAPES:
                out.append("\\")
                out.append(ch)
            else:
                out.append("\\\\")
                out.append(ch)
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            out.append('\\"')
            continue
        if ch == "\n":
            out.append("\\n")
            continue
        if ch == "\r":
            out.append("\\r")
            continue
        if ch == "\t":
            out.append("\\t")
            continue
        out.append(ch)
    if escape:
        out.append("\\\\")
    return "".join(out)


def _decode_json_string_fragment(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('"'):
        raw = raw[1:]
    if raw.endswith('"'):
        raw = raw[:-1]
    sanitized = _sanitize_json_string_content(raw)
    return json.loads('"' + sanitized + '"')


def _sanitize_json_object_text(candidate: str) -> str:
    out: list[str] = []
    in_string = False
    escape = False
    for ch in candidate:
        if in_string:
            if escape:
                if ch in VALID_JSON_ESCAPES:
                    out.append(ch)
                else:
                    out.append("\\")
                    out.append(ch)
                escape = False
                continue
            if ch == "\\":
                out.append(ch)
                escape = True
                continue
            if ch == '"':
                out.append(ch)
                in_string = False
                continue
            if ch == "\n":
                out.append("\\n")
                continue
            if ch == "\r":
                out.append("\\r")
                continue
            if ch == "\t":
                out.append("\\t")
                continue
            out.append(ch)
        else:
            out.append(ch)
            if ch == '"':
                in_string = True
    if escape:
        out.append("\\")
    if in_string:
        out.append('"')
    sanitized = "".join(out)
    balance = sanitized.count("{") - sanitized.count("}")
    if balance > 0:
        sanitized += "}" * balance
    return sanitized


def _manual_extract_seed_fields(candidate: str) -> dict:
    candidate = _extract_json_candidate(candidate)
    result: dict[str, str] = {}
    for index, field in enumerate(SEED_JSON_FIELD_ORDER):
        key_pattern = f'"{field}"'
        key_index = candidate.find(key_pattern)
        if key_index == -1:
            if field == "teacher_output":
                break
            raise ValueError(f"missing field {field}")
        colon_index = candidate.find(":", key_index + len(key_pattern))
        if colon_index == -1:
            raise ValueError(f"missing colon for {field}")
        value_start = candidate.find('"', colon_index)
        if value_start == -1:
            raise ValueError(f"missing opening quote for {field}")
        if index < len(SEED_JSON_FIELD_ORDER) - 1:
            next_field = SEED_JSON_FIELD_ORDER[index + 1]
            boundary = re.search(
                r',\s*"' + re.escape(next_field) + r'"\s*:',
                candidate[value_start + 1:],
                re.DOTALL,
            )
            if boundary:
                value_end = value_start + 1 + boundary.start()
            elif field == "seed_quality_note":
                tail = candidate[value_start + 1:]
                closing = re.search(r'"\s*}\s*$', tail, re.DOTALL)
                if not closing:
                    value_end = len(candidate)
                else:
                    value_end = value_start + 1 + closing.start()
            else:
                raise ValueError(f"missing boundary after {field}")
        else:
            tail = candidate[value_start + 1:]
            closing = re.search(r'"\s*}\s*$', tail, re.DOTALL)
            if closing:
                value_end = value_start + 1 + closing.start()
            elif tail.endswith('"') or tail.endswith("}"):
                value_end = len(candidate) - 1
            else:
                value_end = len(candidate)
        raw_value = candidate[value_start + 1:value_end]
        result[field] = _decode_json_string_fragment(raw_value)
    return result


def extract_json_blob(text: str) -> dict:
    text = _strip_markdown_fence(text)
    try:
        return json.loads(text)
    except Exception as strict_exc:
        candidate = _extract_json_candidate(text)
        try:
            return json.loads(candidate)
        except Exception:
            try:
                return json.loads(_sanitize_json_object_text(candidate))
            except Exception:
                try:
                    return _manual_extract_seed_fields(candidate)
                except Exception:
                    if "{" not in text:
                        raise ValueError("model response did not contain a JSON object") from strict_exc
                    raise


def resolve_request_max_output_tokens(
    manifest_entry: dict,
    source_record: dict,
    configured_max_output_tokens: int,
) -> int:
    meta = source_record.get("metadata", {})
    role = manifest_entry.get("seed_role", "")
    target_mode = manifest_entry.get("target_supervision_mode", "")
    gate_count = int_meta(meta, "gate_count")
    n_qubits = int_meta(meta, "num_qubits", "n_qubits")
    measurement_count = int_meta(meta, "measurement_count")
    has_named_semantics = bool(meta.get("circuit_family") or meta.get("semantic_intent"))

    max_tokens = configured_max_output_tokens

    if target_mode == "teacher_text":
        if role == "validation_diagnosis":
            return max(max_tokens, 420)
        return max(max_tokens, 520)

    if role == "repair_or_explanation":
        return max(max_tokens, 320)

    if role in {"gold_generation", "broad_generation"}:
        if has_named_semantics:
            if gate_count >= 25:
                return max(max_tokens, 360)
            return max_tokens
        if gate_count >= 50 or (gate_count >= 40 and n_qubits >= 8):
            return max(max_tokens, 1200)
        if gate_count >= 30 or n_qubits >= 6:
            return max(max_tokens, 700)
        if gate_count >= 15 or measurement_count >= 8:
            return max(max_tokens, 420)

    return max_tokens


def build_user_prompt(manifest_entry: dict, source_record: dict) -> str:
    role = manifest_entry["seed_role"]
    target_mode = manifest_entry.get("target_supervision_mode")
    meta = source_record.get("metadata", {})
    gate_count = int_meta(meta, "gate_count")
    n_qubits = int_meta(meta, "num_qubits", "n_qubits")
    measurement_count = int_meta(meta, "measurement_count")
    has_named_semantics = bool(meta.get("circuit_family") or meta.get("semantic_intent"))
    extra_output_instruction = ""
    if target_mode == "teacher_text":
        extra_output_instruction = (
            f"\nTeacher-text target instruction:\n"
            f"- {TEACHER_OUTPUT_INSTRUCTIONS[role]}\n"
            "- Keep `teacher_output` concise, direct, and useful as a model answer.\n"
            "- Avoid markdown bullets unless the task strongly requires them.\n"
        )
    large_circuit_instruction = ""
    if (
        role in {"gold_generation", "broad_generation"}
        and not has_named_semantics
        and (gate_count >= 30 or n_qubits >= 6 or measurement_count >= 8)
    ):
        large_circuit_instruction = (
            "Large opaque-circuit reminder:\n"
            "- Fidelity matters more than elegance, but avoid wasting space on commentary.\n"
            "- Compress repetitive end-of-circuit measurements into one compact phrase when they map qubits to matching classical bits.\n"
            "- Prefer grouped wording over repetitive per-gate narration when the task remains faithful.\n"
        )
    return (
        f"Assigned role instructions:\n{ROLE_INSTRUCTIONS[role]}\n\n"
        "Style reminder:\n"
        "- Use a wording pattern that is distinct from generic boilerplate.\n"
        "- If the task is straightforward, keep it compact without sounding templated.\n"
        "- Avoid repeating common openers unless the source strongly requires it.\n"
        f"{extra_output_instruction}"
        f"{large_circuit_instruction}\n"
        "Source record payload:\n"
        f"{format_prompt_payload(manifest_entry, source_record)}\n\n"
        "Return valid JSON only."
    )


async def draft_one(
    *,
    client: AsyncOpenAI,
    model: str,
    temperature: float,
    max_output_tokens: int,
    manifest_entry: dict,
    source_record: dict,
) -> dict:
    response = await client.responses.create(
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(manifest_entry, source_record)},
        ],
    )
    content = getattr(response, "output_text", "") or ""
    parsed = extract_json_blob(content)
    result = {
        "seed_input": str(parsed["seed_input"]).strip(),
        "seed_quality_note": str(parsed.get("seed_quality_note", "")).strip(),
    }
    if manifest_entry.get("target_supervision_mode") == "teacher_text":
        teacher_output = str(parsed.get("teacher_output", "")).strip()
        if not teacher_output:
            raise ValueError("model response did not contain teacher_output for teacher_text mode")
        result["teacher_output"] = teacher_output
    return result


def build_output_entry(
    *,
    manifest_entry: dict,
    source_record: dict,
    seed_input: str,
    seed_quality_note: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    teacher_output: str | None = None,
) -> dict:
    target_mode = manifest_entry.get("target_supervision_mode")
    if target_mode == "source_code":
        output_text = source_record["output"]
    elif target_mode == "teacher_text":
        if not teacher_output:
            raise ValueError("teacher_text entries require a generated teacher_output")
        output_text = teacher_output
    else:
        raise ValueError(f"unsupported target supervision mode: {target_mode}")

    metadata = dict(source_record.get("metadata", {}))
    metadata.update(
        {
            "prompt_type": QUALITY_AWARE_BASE_SEED_PROMPT_TYPE,
            "generation_model": model,
            "generation_date": str(dt.date.today()),
            "seed_generation_temperature": temperature,
            "seed_generation_max_output_tokens": max_output_tokens,
            "paraphrase_source": "",
            "original_prompt": "",
            "seed_role": manifest_entry["seed_role"],
            "seed_learning_objective": manifest_entry["learning_objective"],
            "seed_expected_response_mode": manifest_entry["expected_response_mode"],
            "seed_role_reason": manifest_entry["role_reason"],
            "seed_target_supervision_mode": target_mode,
            "seed_quality_note": seed_quality_note,
            "seed_manifest_version": manifest_entry["manifest_version"],
            "seed_template_version": SEED_TEMPLATE_VERSION,
            "seed_critique_template_version": SEED_CRITIQUE_TEMPLATE_VERSION,
            "seed_generation_stage": "draft",
            "seed_rewrite_pass_applied": False,
            "seed_source_artifact": manifest_entry["source_record"]["artifact_name"],
            "content_hash": content_hash(seed_input, output_text),
        }
    )
    return {
        "input": seed_input,
        "output": output_text,
        "openqasm3_code": source_record.get("openqasm3_code"),
        "metadata": metadata,
    }


async def run_generation(
    *,
    manifest_rows: list[dict],
    source_rows: dict[str, dict],
    output_file: Path,
    log_file: Path,
    model: str,
    temperature: float,
    max_output_tokens: int,
) -> None:
    if AsyncOpenAI is None:
        raise RuntimeError("openai package is required for live seed generation")
    api_key = load_openai_api_key(__file__)
    client = AsyncOpenAI(api_key=api_key)
    completed = load_completed_keys(output_file)
    sem = asyncio.Semaphore(BATCH_SIZE)

    async def worker(entry: dict) -> None:
        key = seed_key(entry)
        if key in completed:
            return
        source_hash = entry["source_record"]["circuit_hash"]
        source_record = source_rows[source_hash]
        request_max_output_tokens = resolve_request_max_output_tokens(
            entry,
            source_record,
            max_output_tokens,
        )
        try:
            async with sem:
                draft = await draft_one(
                    client=client,
                    model=model,
                    temperature=temperature,
                    max_output_tokens=request_max_output_tokens,
                    manifest_entry=entry,
                    source_record=source_record,
                )
            append_jsonl(
                build_output_entry(
                    manifest_entry=entry,
                    source_record=source_record,
                    seed_input=draft["seed_input"],
                    seed_quality_note=draft["seed_quality_note"],
                    model=model,
                    temperature=temperature,
                    max_output_tokens=request_max_output_tokens,
                    teacher_output=draft.get("teacher_output"),
                ),
                output_file,
            )
        except RateLimitError as exc:
            append_jsonl(
                {
                    "error_type": "RateLimitError",
                    "error_message": str(exc),
                    "seed_role": entry["seed_role"],
                    "source_record": entry["source_record"],
                },
                log_file,
            )
        except Exception as exc:
            append_jsonl(
                {
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "seed_role": entry["seed_role"],
                    "source_record": entry["source_record"],
                },
                log_file,
            )

    await asyncio.gather(*(worker(entry) for entry in manifest_rows))


def main() -> None:
    args = parse_args()
    manifest_file = Path(args.manifest_file)
    source_file = Path(args.source_file)
    output_file = Path(args.output_file)
    log_file = Path(args.log_file)

    manifest_rows = load_jsonl(manifest_file)
    if args.max_records is not None:
        manifest_rows = manifest_rows[: args.max_records]

    source_rows = {
        row["metadata"]["circuit_hash"]: row
        for row in load_jsonl(source_file)
        if row.get("metadata", {}).get("circuit_hash")
    }

    if args.dry_run:
        print("dry-run enabled")
        print("manifest file:", format_display_path(manifest_file))
        print("source file:", format_display_path(source_file))
        print("output file:", format_display_path(output_file))
        print("log file:", format_display_path(log_file))
        print("teacher model:", args.model)
        print("temperature:", args.temperature)
        print("max_output_tokens:", args.max_output_tokens)
        print("records selected:", len(manifest_rows))
        if manifest_rows:
            sample = manifest_rows[0]
            sample_record = source_rows[sample["source_record"]["circuit_hash"]]
            print("\n--- sample manifest entry ---\n")
            print(json.dumps(sample, ensure_ascii=False, indent=2)[:4000])
            print("\n--- sample prompt payload ---\n")
            print(build_user_prompt(sample, sample_record)[:6000])
        return

    asyncio.run(
        run_generation(
            manifest_rows=manifest_rows,
            source_rows=source_rows,
            output_file=output_file,
            log_file=log_file,
            model=args.model,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
        )
    )
    print("seed draft generation completed")
    print("output file:", format_display_path(output_file))
    print("error log:", format_display_path(log_file))
    summary = summarize_seed_artifacts(output_file, log_file)
    print("rows materialized:", f"{summary['rows']:,}")
    print("unique circuit_hash values:", f"{summary['unique_circuit_hashes']:,}")
    print("error rows logged:", f"{summary['error_rows']:,}")
    print("\nrole distribution")
    for key, value in summary["role_counts"].most_common():
        print(f"  {key}: {value:,}")
    print("\nprompt types")
    for key, value in summary["prompt_type_counts"].most_common():
        print(f"  {key}: {value:,}")
    print("\ntarget supervision modes")
    for key, value in summary["supervision_mode_counts"].most_common():
        print(f"  {key}: {value:,}")
    print("\nseed draft temperatures present")
    for key, value in summary["temperature_counts"].most_common():
        print(f"  {key}: {value:,}")
    if summary["error_type_counts"]:
        print("\nerror types")
        for key, value in summary["error_type_counts"].most_common():
            print(f"  {key}: {value:,}")


if __name__ == "__main__":
    main()
