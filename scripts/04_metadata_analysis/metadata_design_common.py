"""
metadata_design_common.py
-------------------------
Shared helpers for the additive metadata-design layer used between the
post-acquisition corpus build and downstream seed generation / training work.

The goal of this layer is not to relabel the corpus from scratch. Instead, it
derives a small set of interpretable, behavior-oriented fields from metadata
that already exists in the enriched and master corpora.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


METADATA_DESIGN_VERSION = "metadata_design_v3"

DEFAULT_BASE_INPUT_FILE = "pqid_2026_enriched_github_circuits.jsonl"
DEFAULT_MASTER_OVERLAY_FILE = "pqid_2026_master_corpus.jsonl"
DEFAULT_OVERLAY_OUTPUT_FILE = "pqid_2026_metadata_design_overlay_v3.jsonl"
DEFAULT_MERGED_OUTPUT_FILE = "pqid_2026_enriched_github_circuits_plus_metadata_design_v3.jsonl"
DEFAULT_EVAL_JSON_FILE = "pqid_metadata_design_evaluation_report_v3.json"
DEFAULT_EVAL_MD_FILE = "pqid_metadata_design_evaluation_report_v3.md"


DERIVED_FIELD_NAMES = [
    "metadata_design_version",
    "source_snapshot_timestamp",
    "source_snapshot_granularity",
    "source_revision_id",
    "license_evidence_source",
    "license_detection_method",
    "release_view_membership",
    "lineage_parent_id",
    "benchmark_view_membership",
    "expected_model_stance",
    "context_sufficiency_class",
    "repairability_score",
    "repairability_band",
    "evidence_regime",
    "split_group_id",
    "split_group_source",
    "near_duplicate_group_id",
    "domain_slice",
    "shift_axis",
    "review_trace_id",
    "distribution_rights_status",
    "license_resolution_status",
    "public_release_bucket",
    "license_audit_priority",
    "contact_outreach_status",
    "permission_response_status",
    "manual_license_review_status",
]


MASTER_OVERLAY_KEYS = [
    "benchmark_checks_passed",
    "benchmark_checks_total",
    "benchmark_checks_ratio",
    "benchmark_suitability_tier",
    "benchmark_failed_checks",
    "benchmark_passed_checks",
    "benchmark_profile_version",
    "benchmark_checks_passed_v2",
    "benchmark_checks_total_v2",
    "benchmark_checks_ratio_v2",
    "benchmark_suitability_tier_v2",
    "benchmark_failed_checks_v2",
    "benchmark_passed_checks_v2",
    "benchmark_profile_version_v2",
    "mutation_suite_candidate",
    "benchmark_cleaning_flags",
    "benchmark_difficulty",
    "circuit_family",
    "semantic_intent",
    "license_category",
    "repo_license",
    "repo_topics",
    "is_org_repo",
    "retrieval_strategy",
    "materialized_circuit",
    "code_lines",
    "gate_count",
    "num_qubits",
    "circuit_depth",
    "size_class",
    "gate_types",
]


METHOD_FRAGMENT_PATTERNS = [
    re.compile(r"(?m)^\s*def\s+\w+\s*\("),
    re.compile(r"(?m)^\s*class\s+\w+"),
    re.compile(r"\bself\."),
    re.compile(r"\bcls\."),
    re.compile(r"\bsuper\("),
]


TUTORIAL_PATH_PATTERNS = [
    re.compile(r"(^|/)(notebooks?|tutorials?|examples?|demos?)(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)(docs?)(/|$)", re.IGNORECASE),
]


TEST_PATH_PATTERNS = [
    re.compile(r"(^|/)(tests?|testing|fixtures?)(/|$)", re.IGNORECASE),
    re.compile(r"(^|/).*(_test|test_).*\.(py|ipynb)$", re.IGNORECASE),
]


LIBRARY_REPO_NAMES = {
    "qiskit",
    "cirq",
    "pennylane",
    "braket",
    "cuda-quantum",
    "qsharp",
    "qibo",
    "qulacs",
    "stim",
}


LIBRARY_REPO_OWNERS = {
    "qiskit",
    "quantumlib",
    "pennylaneai",
    "dwavesystems",
    "rigetti",
    "amazon-braket",
}


COMMENT_ONLY_PATTERNS = [
    re.compile(r"(?m)^\s*#.*$"),
    re.compile(r"(?m)^\s*//.*$"),
]


HALLUCINATION_PENALTIES = {
    "none": 0,
    "runtime_semantic_failure": -1,
    "symbol_resolution_failure": -1,
    "register_index_error": -1,
    "api_hallucination": -2,
    "non_circuit_execution": -2,
    "syntax_failure": -3,
    "dependency_hallucination": -3,
    "timeout": -1,
}


def jsonl_rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_jsonl_row(handle, row: dict[str, Any]) -> None:
    handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_master_overlay_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    overlay_index: dict[str, dict[str, Any]] = {}
    for row in jsonl_rows(path):
        meta = row.get("metadata", {})
        circuit_hash = meta.get("circuit_hash")
        if circuit_hash:
            overlay_index[str(circuit_hash)] = meta
    return overlay_index


def merge_master_overlay(base_meta: dict[str, Any], overlay_meta: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base_meta)
    if not overlay_meta:
        return merged

    for key in MASTER_OVERLAY_KEYS:
        value = overlay_meta.get(key)
        if value is not None:
            merged[key] = value
    return merged


def detect_method_fragment(output_code: str) -> bool:
    text = output_code or ""
    for pattern in METHOD_FRAGMENT_PATTERNS:
        if pattern.search(text):
            return True
    return False


def derive_source_snapshot_timestamp(meta: dict[str, Any]) -> str:
    return str(meta.get("scrape_date") or "").strip()


def derive_source_snapshot_granularity(meta: dict[str, Any], source_snapshot_timestamp: str) -> str:
    has_blob_sha = bool(str(meta.get("hash") or "").strip())
    has_original_url = bool(str(meta.get("original_url") or "").strip())

    if source_snapshot_timestamp and has_blob_sha:
        return "day_level_scrape_snapshot_with_blob_sha"
    if source_snapshot_timestamp and has_original_url:
        return "day_level_scrape_snapshot_with_url_fallback"
    if source_snapshot_timestamp:
        return "day_level_scrape_snapshot_only"
    if has_blob_sha:
        return "blob_sha_only"
    return "unknown"


def derive_source_revision_id(meta: dict[str, Any]) -> str:
    revision = str(meta.get("hash") or "").strip()
    if revision:
        return revision
    original_url = str(meta.get("original_url") or "").strip()
    if original_url:
        return "url_" + hashlib.sha1(original_url.encode("utf-8")).hexdigest()[:16]
    return ""


def derive_license_evidence_source(meta: dict[str, Any]) -> str:
    repo_license = str(meta.get("repo_license") or "").strip()
    if repo_license:
        return "github_api"
    return "missing"


def derive_license_detection_method(meta: dict[str, Any]) -> str:
    repo_license = str(meta.get("repo_license") or "").strip()
    if repo_license:
        return "api_declared"
    return "unresolved"


def derive_expected_model_stance(meta: dict[str, Any]) -> str:
    validation_status = str(meta.get("validation_status") or "")
    tier_v2 = str(meta.get("benchmark_suitability_tier_v2") or "")

    if validation_status != "validated":
        return "diagnose"
    if tier_v2 in {"strict_core_candidate", "extended_core_candidate"}:
        return "generate"
    if tier_v2 == "mutation_stress_candidate":
        return "robustness_compare"
    return "repair"


def derive_context_sufficiency_class(record: dict[str, Any], meta: dict[str, Any]) -> str:
    if bool(meta.get("mutation_suite_candidate")):
        return "mutation_variant"
    if bool(meta.get("contains_demo_scaffolding")):
        return "demo_scaffolded"
    if str(meta.get("validation_status") or "") == "validated" and bool(meta.get("materialized_circuit")):
        return "complete_executable"
    if detect_method_fragment(record.get("output", "")):
        return "method_fragment"
    return "partial_implementation"


def derive_repairability_score(
    meta: dict[str, Any],
    expected_model_stance: str,
    context_sufficiency_class: str,
) -> int:
    score = 0

    stance_bonus = {
        "generate": 5,
        "repair": 4,
        "robustness_compare": 4,
        "diagnose": 3,
    }
    score += stance_bonus.get(expected_model_stance, 2)

    if str(meta.get("validation_status") or "") == "validated":
        score += 2
    if bool(meta.get("materialized_circuit")):
        score += 1

    extraction_confidence = str(meta.get("extraction_confidence") or "")
    score += {"high": 2, "medium": 1, "low": 0}.get(extraction_confidence, 0)

    if context_sufficiency_class == "mutation_variant":
        score += 1
    elif context_sufficiency_class == "demo_scaffolded":
        score += 0
    elif context_sufficiency_class == "method_fragment":
        score += 0
    elif context_sufficiency_class == "partial_implementation":
        score -= 1

    if bool(meta.get("cleanup_candidate")):
        score -= 1

    hallucination_type = str(meta.get("hallucination_type") or "")
    score += HALLUCINATION_PENALTIES.get(hallucination_type, -1 if hallucination_type else 0)

    return max(0, min(score, 8))


def derive_repairability_band(repairability_score: int) -> str:
    if repairability_score >= 6:
        return "high"
    if repairability_score >= 3:
        return "medium"
    return "low"


def derive_evidence_regime(
    meta: dict[str, Any],
    expected_model_stance: str,
    context_sufficiency_class: str,
) -> str:
    validation_status = str(meta.get("validation_status") or "")
    tier_v2 = str(meta.get("benchmark_suitability_tier_v2") or "")

    if bool(meta.get("mutation_suite_candidate")):
        return "validated_mutation_stress"
    if validation_status == "validated" and tier_v2 == "strict_core_candidate":
        return "clean_validated_code"
    if validation_status == "validated" and tier_v2 == "extended_core_candidate":
        return "benchmark_ready_validated_code"
    if validation_status == "validated":
        return "validated_code"
    if expected_model_stance == "diagnose" and context_sufficiency_class in {
        "method_fragment",
        "partial_implementation",
        "demo_scaffolded",
    }:
        return "partial_context"
    return "unvalidated_code"


def derive_lineage_parent_id(meta: dict[str, Any]) -> str:
    content_hash = str(meta.get("content_hash") or "").strip()
    if content_hash:
        return f"lp_{content_hash}"
    circuit_hash = str(meta.get("circuit_hash") or "").strip()
    if circuit_hash:
        return f"lp_{circuit_hash}"
    original_url = str(meta.get("original_url") or "").strip()
    if original_url:
        return "lp_" + hashlib.sha1(original_url.encode("utf-8")).hexdigest()[:16]
    return ""


def normalize_output_for_near_duplicate_group(record: dict[str, Any]) -> str:
    text = str(record.get("openqasm3_code") or record.get("output") or "").strip()
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for pattern in COMMENT_ONLY_PATTERNS:
        text = pattern.sub("", text)
    text = re.sub(r"\s+", "", text)
    return text


def build_split_group_fields(meta: dict[str, Any]) -> tuple[str, str]:
    repo_owner = str(meta.get("repo_owner") or "").strip()
    repo_name = str(meta.get("repo_name") or "").strip()
    file_path = str(meta.get("file_path") or "").strip()
    original_url = str(meta.get("original_url") or "").strip()
    blob_hash = str(meta.get("hash") or "").strip()
    circuit_hash = str(meta.get("circuit_hash") or "").strip()

    if repo_owner and repo_name and file_path:
        source = "repo_file"
        canonical_key = f"{repo_owner}/{repo_name}::{file_path}"
    elif original_url:
        source = "original_url"
        canonical_key = original_url
    elif blob_hash:
        source = "blob_hash"
        canonical_key = blob_hash
    else:
        source = "circuit_hash"
        canonical_key = circuit_hash

    digest = hashlib.sha1(canonical_key.encode("utf-8")).hexdigest()[:16]
    return f"sg_{digest}", source


def build_near_duplicate_group_id(record: dict[str, Any], meta: dict[str, Any]) -> str:
    normalized = normalize_output_for_near_duplicate_group(record)
    if not normalized:
        normalized = str(meta.get("circuit_hash") or "").strip()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    return f"nd_{digest}"


def derive_benchmark_view_membership(meta: dict[str, Any]) -> str:
    tier_v2 = str(meta.get("benchmark_suitability_tier_v2") or "").strip()
    tier_v1 = str(meta.get("benchmark_suitability_tier") or "").strip()
    validation_status = str(meta.get("validation_status") or "").strip()

    if tier_v2 == "strict_core_candidate":
        return "strict_n8"
    if tier_v2 == "extended_core_candidate":
        return "extended_n8"
    if tier_v2 == "mutation_stress_candidate":
        return "mutation_stress_n8"
    if tier_v2 == "validated_broad_candidate":
        return "validated_broad_n8"

    if tier_v1 == "strict_core_candidate":
        return "strict_n7_only"
    if tier_v1 == "extended_core_candidate":
        return "extended_n7_only"
    if tier_v1 == "validated_broad_candidate":
        return "validated_broad_n7_only"

    if validation_status == "validated":
        return "validated_master_only"
    return "tier2_unvalidated"


def derive_distribution_rights_status(meta: dict[str, Any]) -> str:
    license_category = str(meta.get("license_category") or "").strip()
    if license_category == "permissive":
        return "redistributable_permissive"
    if license_category == "copyleft":
        return "redistributable_copyleft"
    if license_category == "other":
        return "review_required_other"
    return "unresolved_no_license"


def derive_license_resolution_status(distribution_rights_status: str) -> str:
    if distribution_rights_status in {"redistributable_permissive", "redistributable_copyleft"}:
        return "resolved"
    if distribution_rights_status == "review_required_other":
        return "review_required_other"
    return "unresolved_no_license"


def derive_public_release_bucket(distribution_rights_status: str) -> str:
    if distribution_rights_status == "redistributable_permissive":
        return "public_open"
    if distribution_rights_status == "redistributable_copyleft":
        return "public_open_with_obligations"
    if distribution_rights_status == "review_required_other":
        return "public_review_required"
    return "restricted_internal_only"


def derive_release_view_membership(public_release_bucket: str) -> str:
    if public_release_bucket == "public_open":
        return "public_open"
    if public_release_bucket == "public_open_with_obligations":
        return "public_obligations"
    if public_release_bucket == "public_review_required":
        return "public_review_required"
    return "restricted_index"


def derive_license_audit_priority(
    meta: dict[str, Any],
    expected_model_stance: str,
    distribution_rights_status: str,
) -> str:
    validation_status = str(meta.get("validation_status") or "")

    if distribution_rights_status == "unresolved_no_license":
        if validation_status == "validated" or expected_model_stance in {
            "generate",
            "repair",
            "robustness_compare",
        }:
            return "high"
        return "medium"

    if distribution_rights_status == "review_required_other":
        if validation_status == "validated":
            return "medium"
        return "low"

    return "low"


def derive_contact_outreach_status(distribution_rights_status: str) -> str:
    if distribution_rights_status == "unresolved_no_license":
        return "needed"
    if distribution_rights_status == "review_required_other":
        return "review_first"
    return "not_required"


def derive_permission_response_status(contact_outreach_status: str) -> str:
    if contact_outreach_status == "needed":
        return "not_contacted"
    if contact_outreach_status == "review_first":
        return "review_before_contact"
    return "not_applicable"


def derive_manual_license_review_status(distribution_rights_status: str) -> str:
    if distribution_rights_status == "review_required_other":
        return "pending_review"
    if distribution_rights_status == "unresolved_no_license":
        return "not_started"
    return "not_required"


def derive_domain_slice(
    meta: dict[str, Any],
    context_sufficiency_class: str,
    evidence_regime: str,
) -> str:
    file_path = str(meta.get("file_path") or "").strip()
    repo_owner = str(meta.get("repo_owner") or "").strip().lower()
    repo_name = str(meta.get("repo_name") or "").strip().lower()

    if bool(meta.get("mutation_suite_candidate")):
        return "mutation_suite"
    if evidence_regime in {"clean_validated_code", "benchmark_ready_validated_code"}:
        return "benchmark_candidate"
    if bool(meta.get("contains_demo_scaffolding")) or any(pattern.search(file_path) for pattern in TUTORIAL_PATH_PATTERNS):
        return "tutorial"
    if any(pattern.search(file_path) for pattern in TEST_PATH_PATTERNS):
        return "test_fixture"
    if (
        repo_name in LIBRARY_REPO_NAMES
        or repo_owner in LIBRARY_REPO_OWNERS
        or (bool(meta.get("is_org_repo")) and context_sufficiency_class == "method_fragment")
    ):
        return "library_internal"
    return "research_proto"


def derive_shift_axis(
    meta: dict[str, Any],
    context_sufficiency_class: str,
    domain_slice: str,
) -> str:
    if bool(meta.get("mutation_suite_candidate")):
        return "mutation_status"
    if context_sufficiency_class in {"method_fragment", "partial_implementation", "demo_scaffolded"}:
        return "context_completeness"
    if str(meta.get("benchmark_suitability_tier_v2") or ""):
        return "benchmark_tier"
    if str(meta.get("validation_status") or "") != "validated":
        return "validation_status"
    if domain_slice in {"library_internal", "test_fixture", "research_proto"}:
        return "repo_family"
    return "validation_status"


def derive_review_trace_id(
    meta: dict[str, Any],
    source_snapshot_timestamp: str,
    license_detection_method: str,
) -> str:
    retrieval_run_id = str(meta.get("retrieval_run_id") or "").strip() or "unknown_retrieval"
    benchmark_profile = (
        str(meta.get("benchmark_profile_version_v2") or "").strip()
        or str(meta.get("benchmark_profile_version") or "").strip()
        or "no_benchmark_profile"
    )
    snapshot = source_snapshot_timestamp or "unknown_snapshot"
    return f"review::{retrieval_run_id}::{benchmark_profile}::{snapshot}::{license_detection_method}"


def derive_metadata_design_fields(record: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    source_snapshot_timestamp = derive_source_snapshot_timestamp(meta)
    source_snapshot_granularity = derive_source_snapshot_granularity(meta, source_snapshot_timestamp)
    source_revision_id = derive_source_revision_id(meta)
    license_evidence_source = derive_license_evidence_source(meta)
    license_detection_method = derive_license_detection_method(meta)
    lineage_parent_id = derive_lineage_parent_id(meta)
    benchmark_view_membership = derive_benchmark_view_membership(meta)
    expected_model_stance = derive_expected_model_stance(meta)
    context_sufficiency_class = derive_context_sufficiency_class(record, meta)
    repairability_score = derive_repairability_score(
        meta,
        expected_model_stance=expected_model_stance,
        context_sufficiency_class=context_sufficiency_class,
    )
    evidence_regime = derive_evidence_regime(
        meta,
        expected_model_stance=expected_model_stance,
        context_sufficiency_class=context_sufficiency_class,
    )
    split_group_id, split_group_source = build_split_group_fields(meta)
    near_duplicate_group_id = build_near_duplicate_group_id(record, meta)
    distribution_rights_status = derive_distribution_rights_status(meta)
    license_resolution_status = derive_license_resolution_status(distribution_rights_status)
    public_release_bucket = derive_public_release_bucket(distribution_rights_status)
    release_view_membership = derive_release_view_membership(public_release_bucket)
    contact_outreach_status = derive_contact_outreach_status(distribution_rights_status)
    domain_slice = derive_domain_slice(
        meta,
        context_sufficiency_class=context_sufficiency_class,
        evidence_regime=evidence_regime,
    )
    shift_axis = derive_shift_axis(
        meta,
        context_sufficiency_class=context_sufficiency_class,
        domain_slice=domain_slice,
    )

    return {
        "metadata_design_version": METADATA_DESIGN_VERSION,
        "source_snapshot_timestamp": source_snapshot_timestamp,
        "source_snapshot_granularity": source_snapshot_granularity,
        "source_revision_id": source_revision_id,
        "license_evidence_source": license_evidence_source,
        "license_detection_method": license_detection_method,
        "release_view_membership": release_view_membership,
        "lineage_parent_id": lineage_parent_id,
        "benchmark_view_membership": benchmark_view_membership,
        "expected_model_stance": expected_model_stance,
        "context_sufficiency_class": context_sufficiency_class,
        "repairability_score": repairability_score,
        "repairability_band": derive_repairability_band(repairability_score),
        "evidence_regime": evidence_regime,
        "split_group_id": split_group_id,
        "split_group_source": split_group_source,
        "near_duplicate_group_id": near_duplicate_group_id,
        "domain_slice": domain_slice,
        "shift_axis": shift_axis,
        "review_trace_id": derive_review_trace_id(
            meta,
            source_snapshot_timestamp=source_snapshot_timestamp,
            license_detection_method=license_detection_method,
        ),
        "distribution_rights_status": distribution_rights_status,
        "license_resolution_status": license_resolution_status,
        "public_release_bucket": public_release_bucket,
        "license_audit_priority": derive_license_audit_priority(
            meta,
            expected_model_stance=expected_model_stance,
            distribution_rights_status=distribution_rights_status,
        ),
        "contact_outreach_status": contact_outreach_status,
        "permission_response_status": derive_permission_response_status(contact_outreach_status),
        "manual_license_review_status": derive_manual_license_review_status(distribution_rights_status),
    }
