"""
quality_aware_seed_common.py
----------------------------
Shared constants and helper functions for the quality-aware seed-generation
stack introduced for the 2026 PQID rebuild.

This module keeps the role taxonomy and manifest-building logic in one place so
that the notebook, manifest builder, draft generator, and later critique pass
all use the same definitions.
"""

from __future__ import annotations

import json
from typing import Any


MANIFEST_VERSION = "seed_manifest_v1"
SEED_TEMPLATE_VERSION = "seed_quality_aware_v1"
SEED_CRITIQUE_TEMPLATE_VERSION = "seed_quality_aware_critique_v1"
PARAPHRASE_TEMPLATE_VERSION = "paraphrase_quality_aware_v1"
DEFAULT_TEACHER_MODEL = "gpt-5.4"
DEFAULT_PARAPHRASE_MODEL = "gpt-5.4-mini"
QUALITY_AWARE_BASE_SEED_PROMPT_TYPE = "base_seed_quality_aware"
LEGACY_QUALITY_AWARE_BASE_SEED_PROMPT_TYPE = "human_seed_quality_aware"
QUALITY_AWARE_PARAPHRASE_PROMPT_TYPE = "paraphrased_quality_aware"


ROLE_SPECS: dict[str, dict[str, str]] = {
    "gold_generation": {
        "learning_objective": "canonical high-quality circuit generation",
        "expected_response_mode": "generation",
        "target_supervision_mode": "source_code",
        "role_description": (
            "Use for clean benchmark-strict examples that should teach the model "
            "what a canonical, trustworthy circuit task looks like."
        ),
    },
    "broad_generation": {
        "learning_objective": "broader circuit generation coverage",
        "expected_response_mode": "generation",
        "target_supervision_mode": "source_code",
        "role_description": (
            "Use for still-usable but weaker or less trusted benchmark examples "
            "that expand task coverage without being framed as the gold standard."
        ),
    },
    "mutation_robustness": {
        "learning_objective": "bug-stress robustness and mutation-aware analysis",
        "expected_response_mode": "diagnosis",
        "target_supervision_mode": "teacher_text",
        "role_description": (
            "Use for mutation-suite or bug-stress examples. Do not frame them as "
            "ordinary clean exemplars."
        ),
    },
    "repair_or_explanation": {
        "learning_objective": "completion, repair, critique, or readiness explanation",
        "expected_response_mode": "repair",
        "target_supervision_mode": "source_code",
        "role_description": (
            "Use for validated but weaker examples that are useful as completion, "
            "repair, or explanation tasks."
        ),
    },
    "validation_diagnosis": {
        "learning_objective": "failure diagnosis and correction planning",
        "expected_response_mode": "diagnosis",
        "target_supervision_mode": "teacher_text",
        "role_description": (
            "Use for invalid or incomplete examples where the model should learn "
            "to identify issues rather than hallucinate a clean solution."
        ),
    },
}


def ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            loaded = json.loads(text)
        except Exception:
            return [text]
        if isinstance(loaded, list):
            return [str(v) for v in loaded if str(v).strip()]
        return [text]
    return [str(value)]


def canonicalize_quality_aware_prompt_type(value: Any) -> str:
    text = str(value or "").strip()
    if text == LEGACY_QUALITY_AWARE_BASE_SEED_PROMPT_TYPE:
        return QUALITY_AWARE_BASE_SEED_PROMPT_TYPE
    return text


def summarize_failed_checks(meta: dict[str, Any]) -> list[str]:
    failed_v2 = ensure_list(meta.get("benchmark_failed_checks_v2"))
    if failed_v2:
        return failed_v2
    return ensure_list(meta.get("benchmark_failed_checks"))


def summarize_passed_checks(meta: dict[str, Any]) -> list[str]:
    passed_v2 = ensure_list(meta.get("benchmark_passed_checks_v2"))
    if passed_v2:
        return passed_v2
    return ensure_list(meta.get("benchmark_passed_checks"))


def determine_seed_role(record: dict[str, Any]) -> tuple[str, str]:
    meta = record.get("metadata", {})
    validation_status = meta.get("validation_status")
    tier_v2 = meta.get("benchmark_suitability_tier_v2")
    tier_v1 = meta.get("benchmark_suitability_tier")
    failed_checks = set(summarize_failed_checks(meta))

    if validation_status != "validated":
        return (
            "validation_diagnosis",
            "record is not fully validated and should be used for diagnosis",
        )

    if tier_v2 == "strict_core_candidate":
        return (
            "gold_generation",
            "record is a clean strict-core candidate under the n/8 profile",
        )

    if tier_v2 == "extended_core_candidate":
        return (
            "broad_generation",
            "record is still benchmark-usable but outside the clean strict tier",
        )

    if tier_v2 == "mutation_stress_candidate":
        return (
            "mutation_robustness",
            "record belongs to the mutation-stress block under the n/8 profile",
        )

    if tier_v2 == "validated_broad_candidate":
        if failed_checks & {"minimum_code_lines", "minimum_gate_count"}:
            return (
                "repair_or_explanation",
                "record is validated but fails shallow structural thresholds",
            )
        return (
            "repair_or_explanation",
            "record is validated but outside benchmark-ready subsets",
        )

    if tier_v1 == "strict_core_candidate":
        return (
            "broad_generation",
            "record is strong under n/7 but lacks a clean strict-core n/8 label",
        )

    return (
        "repair_or_explanation",
        "fallback role for validated records outside the main benchmark roles",
    )


def build_source_record(record: dict[str, Any], source_artifact_name: str) -> dict[str, Any]:
    meta = record.get("metadata", {})
    return {
        "artifact_name": source_artifact_name,
        "circuit_hash": meta.get("circuit_hash"),
        "content_hash": meta.get("content_hash"),
        "repo_owner": meta.get("repo_owner"),
        "repo_name": meta.get("repo_name"),
        "original_url": meta.get("original_url"),
        "file_path": meta.get("file_path"),
    }


def build_manifest_entry(record: dict[str, Any], source_artifact_name: str) -> dict[str, Any]:
    meta = record.get("metadata", {})
    role, role_reason = determine_seed_role(record)
    role_spec = ROLE_SPECS[role]

    return {
        "manifest_version": MANIFEST_VERSION,
        "seed_role": role,
        "learning_objective": role_spec["learning_objective"],
        "expected_response_mode": role_spec["expected_response_mode"],
        "target_supervision_mode": role_spec["target_supervision_mode"],
        "role_description": role_spec["role_description"],
        "role_reason": role_reason,
        "source_record": build_source_record(record, source_artifact_name),
        "readiness": {
            "benchmark_checks_passed": meta.get("benchmark_checks_passed"),
            "benchmark_checks_total": meta.get("benchmark_checks_total"),
            "benchmark_checks_ratio": meta.get("benchmark_checks_ratio"),
            "benchmark_suitability_tier": meta.get("benchmark_suitability_tier"),
            "benchmark_failed_checks": summarize_failed_checks(meta),
            "benchmark_passed_checks": summarize_passed_checks(meta),
            "benchmark_checks_passed_v2": meta.get("benchmark_checks_passed_v2"),
            "benchmark_checks_total_v2": meta.get("benchmark_checks_total_v2"),
            "benchmark_checks_ratio_v2": meta.get("benchmark_checks_ratio_v2"),
            "benchmark_suitability_tier_v2": meta.get("benchmark_suitability_tier_v2"),
        },
        "semantic_profile": {
            "circuit_family": meta.get("circuit_family"),
            "semantic_intent": meta.get("semantic_intent"),
            "mutation_suite_candidate": meta.get("mutation_suite_candidate"),
            "retrieval_strategy": meta.get("retrieval_strategy"),
            "license_category": meta.get("license_category"),
        },
        "generation_defaults": {
            "teacher_model": DEFAULT_TEACHER_MODEL,
            "template_version": SEED_TEMPLATE_VERSION,
            "critique_template_version": SEED_CRITIQUE_TEMPLATE_VERSION,
        },
    }


def compact_record_context(record: dict[str, Any]) -> dict[str, Any]:
    meta = record.get("metadata", {})
    return {
        "circuit_family": meta.get("circuit_family"),
        "semantic_intent": meta.get("semantic_intent"),
        "retrieval_strategy": meta.get("retrieval_strategy"),
        "license_category": meta.get("license_category"),
        "benchmark_suitability_tier": meta.get("benchmark_suitability_tier"),
        "benchmark_suitability_tier_v2": meta.get("benchmark_suitability_tier_v2"),
        "benchmark_failed_checks_v2": summarize_failed_checks(meta),
        "mutation_suite_candidate": meta.get("mutation_suite_candidate"),
        "code_lines": meta.get("code_lines"),
        "gate_count": meta.get("gate_count"),
        "n_qubits": meta.get("n_qubits"),
        "depth": meta.get("depth"),
    }


def format_prompt_payload(manifest_entry: dict[str, Any], record: dict[str, Any]) -> str:
    context = {
        "seed_role": manifest_entry["seed_role"],
        "learning_objective": manifest_entry["learning_objective"],
        "expected_response_mode": manifest_entry["expected_response_mode"],
        "role_reason": manifest_entry["role_reason"],
        "source_record": manifest_entry["source_record"],
        "readiness": manifest_entry["readiness"],
        "semantic_profile": compact_record_context(record),
        "output_code": record.get("output", ""),
        "openqasm3_code": record.get("openqasm3_code"),
    }
    return json.dumps(context, ensure_ascii=False, indent=2)


def role_stats_key(manifest_entry: dict[str, Any]) -> tuple[str, str]:
    tier_v2 = manifest_entry.get("readiness", {}).get("benchmark_suitability_tier_v2") or "<missing>"
    return manifest_entry["seed_role"], tier_v2
