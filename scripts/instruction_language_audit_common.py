"""
instruction_language_audit_common.py
-----------------------------------
Lightweight, dependency-free helpers for auditing human-language traces in the
PQID instruction corpus.

This module is intentionally heuristic rather than claiming perfect language
identification. It is designed to support corpus-level auditability and to
surface clearly non-English or mixed-language examples without introducing a
new heavyweight runtime dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
import io
import re
import tokenize
from typing import Iterable


LANGUAGE_AUDIT_VERSION = "instruction_language_audit_v1"

WORD_RE = re.compile(r"(?u)\b[^\W\d_]{2,}\b")
ASCII_LETTER_RE = re.compile(r"[A-Za-z]")
BENGALI_CHAR_RE = re.compile(r"[\u0980-\u09FF]")
COMMENT_FALLBACK_RE = re.compile(r"(?m)^\s*#(.*)$")
TRIPLE_STRING_RE = re.compile(r'(?s)(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')')

SCRIPT_RANGES = {
    "hangul": ("\uac00", "\ud7af"),
    "hiragana": ("\u3040", "\u309f"),
    "katakana": ("\u30a0", "\u30ff"),
    "cjk": ("\u4e00", "\u9fff"),
    "arabic": ("\u0600", "\u06ff"),
    "hebrew": ("\u0590", "\u05ff"),
    "cyrillic": ("\u0400", "\u04ff"),
    "greek": ("\u0370", "\u03ff"),
    "bengali": ("\u0980", "\u09ff"),
    "devanagari": ("\u0900", "\u097f"),
    "thai": ("\u0e00", "\u0e7f"),
}


STOPWORDS = {
    "en": {
        "a", "an", "and", "are", "as", "at", "be", "bit", "bits", "build", "circuit",
        "classical", "create", "describe", "for", "gate", "if", "in", "into", "is",
        "it", "measure", "measurements", "of", "on", "or", "output", "place", "put",
        "qubit", "qubits", "return", "single", "the", "then", "this", "to", "use",
        "with", "write",
    },
    "es": {
        "al", "algoritmo", "bit", "bits", "clasico", "clasica", "clasicos", "clasicas",
        "con", "crear", "circuito", "de", "del", "el", "en", "es", "estado", "la",
        "las", "los", "medicion", "medir", "para", "puerta", "qubit", "resultado",
        "superposicion", "un", "una", "y",
    },
    "pt": {
        "algoritmo", "aplica", "backend", "bit", "bits", "circuito", "classico",
        "com", "de", "do", "e", "em", "fim", "hadamard", "mede", "medicao", "no",
        "obtém", "obtem", "para", "porta", "qubit", "resultado", "simulador", "um",
        "uma",
    },
    "fr": {
        "avec", "bit", "bits", "circuit", "classique", "de", "des", "du", "et", "la",
        "le", "les", "mesure", "pour", "porte", "qubit", "un", "une",
    },
}

LANGUAGE_MARKERS = {
    "es": ("ción", "medición", "puerta", "clásico", "algoritmo", "resultado"),
    "pt": ("ção", "ções", "não", "porta", "mede", "simulador", "algoritmo", "obtém"),
    "fr": ("ç", "é", "à", "mesure", "porte", "classique"),
}


@dataclass(frozen=True)
class LanguageAuditResult:
    label: str
    confidence: float
    basis: str
    sample_text: str

    def as_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "basis": self.basis,
            "sample_text": self.sample_text,
        }


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _tokenize_words(text: str) -> list[str]:
    return [token.lower() for token in WORD_RE.findall(text or "")]


def _has_range(text: str, start: str, end: str) -> bool:
    return any(start <= ch <= end for ch in text)


def _count_range(text: str, start: str, end: str) -> int:
    return sum(1 for ch in text if start <= ch <= end)


def detect_script_flags(text: str) -> set[str]:
    sample = _normalize_whitespace(text)
    flags = {name for name, (start, end) in SCRIPT_RANGES.items() if _has_range(sample, start, end)}
    if ASCII_LETTER_RE.search(sample):
        flags.add("latin")
    return flags


def classify_script_bucket(text: str) -> tuple[str, str]:
    sample = _normalize_whitespace(text)
    if not sample:
        return ("none", "empty_text")

    flags = detect_script_flags(sample)
    non_latin = sorted(flag for flag in flags if flag != "latin")
    if not flags:
        return ("none", "no_script_signal")
    if not non_latin:
        return ("latin", "latin_script_detected")
    if len(non_latin) == 1 and "latin" not in flags:
        return (non_latin[0], f"single_script_detected:{non_latin[0]}")
    if len(non_latin) == 1 and "latin" in flags:
        return (
            f"latin_plus_{non_latin[0]}",
            f"mixed_latin_plus_single_script:{non_latin[0]}",
        )
    return ("mixed_scripts", "multiple_scripts_detected:" + ",".join(non_latin))


def resolve_language_label(label: str, text: str) -> tuple[str, str]:
    sample = _normalize_whitespace(text)
    script_bucket, script_basis = classify_script_bucket(sample)
    flags = detect_script_flags(sample)
    words = _tokenize_words(sample)
    cjk_count = _count_range(sample, *SCRIPT_RANGES["cjk"])

    if label != "unknown":
        return (label, f"raw_label_preserved|{script_basis}")

    if {"hiragana", "katakana"} & flags:
        return ("ja_script", f"resolved_from_kana_presence:{script_bucket}")
    if "cjk" in flags:
        if cjk_count >= 2:
            return (
                "zh_likely_han_only",
                f"resolved_from_han_only_without_kana_or_hangul:{script_bucket}",
            )
        return ("han_script_unresolved", f"resolved_from_single_han_character:{script_bucket}")
    if "hangul" in flags:
        return ("ko_script", f"resolved_from_script_bucket:{script_bucket}")
    if "cyrillic" in flags:
        return (
            "cyrillic_script_unresolved",
            f"resolved_from_cyrillic_script_without_language_claim:{script_bucket}",
        )
    if "arabic" in flags:
        return ("arabic_script_unresolved", f"resolved_from_script_bucket:{script_bucket}")
    if "hebrew" in flags:
        return ("hebrew_script_unresolved", f"resolved_from_script_bucket:{script_bucket}")
    if "greek" in flags:
        return ("greek_script_unresolved", f"resolved_from_script_bucket:{script_bucket}")
    if "devanagari" in flags:
        return ("devanagari_script_unresolved", f"resolved_from_script_bucket:{script_bucket}")
    if "thai" in flags:
        return ("thai_script_unresolved", f"resolved_from_script_bucket:{script_bucket}")
    if "bengali" in flags:
        return ("bn", f"resolved_from_script_bucket:{script_bucket}")
    if len(words) < 2 or len(sample) < 12:
        return ("short_fragment", f"resolved_from_short_fragment|{script_basis}")
    if script_bucket == "latin":
        return ("latin_fragment_unknown", f"resolved_from_latin_fragment|{script_basis}")
    if script_bucket == "mixed_scripts":
        return ("mixed_script_unknown", f"resolved_from_mixed_scripts|{script_basis}")
    return ("other_script_unknown", f"unresolved_after_script_check|{script_basis}")


def _iter_triple_strings(code: str) -> Iterable[str]:
    for match in TRIPLE_STRING_RE.finditer(code or ""):
        text = match.group(1) or match.group(2) or ""
        text = _normalize_whitespace(text)
        if len(text.split()) >= 3:
            yield text


def extract_source_code_natural_language(output_text: str) -> str:
    """
    Extract human-language-bearing spans from source-code outputs.

    We intentionally focus on comments and likely docstrings. If no comment-like
    material is found, the caller should treat the row as `code_only`.
    """
    snippets: list[str] = []
    reader = io.StringIO(output_text or "")
    try:
        for token in tokenize.generate_tokens(reader.readline):
            if token.type == tokenize.COMMENT:
                comment = token.string.lstrip("#").strip()
                if comment:
                    snippets.append(comment)
    except tokenize.TokenError:
        pass

    if not snippets:
        snippets.extend(_normalize_whitespace(match.group(1)) for match in COMMENT_FALLBACK_RE.finditer(output_text or "") if _normalize_whitespace(match.group(1)))

    snippets.extend(text for text in _iter_triple_strings(output_text or "") if text)

    deduped: list[str] = []
    seen: set[str] = set()
    for snippet in snippets:
        norm = _normalize_whitespace(snippet)
        if norm and norm not in seen:
            deduped.append(norm)
            seen.add(norm)
    return "\n".join(deduped)


def detect_human_language(text: str) -> LanguageAuditResult:
    sample = _normalize_whitespace(text)[:240]
    if not sample:
        return LanguageAuditResult("none", 1.0, "empty_text", "")

    if len(BENGALI_CHAR_RE.findall(sample)) >= 2:
        return LanguageAuditResult("bn", 0.98, "unicode_script_bengali", sample)

    words = _tokenize_words(sample)
    if len(words) < 2:
        return LanguageAuditResult("unknown", 0.2, "insufficient_lexical_signal", sample)

    lowered = sample.lower()
    scores: dict[str, float] = {}
    detail_bits: list[str] = []
    for lang, stopwords in STOPWORDS.items():
        stop_hits = sum(1 for word in words if word in stopwords)
        unique_hits = len({word for word in words if word in stopwords})
        marker_hits = sum(1 for marker in LANGUAGE_MARKERS.get(lang, ()) if marker in lowered)
        score = stop_hits + (0.6 * unique_hits) + (1.5 * marker_hits)
        scores[lang] = score
        if score > 0:
            detail_bits.append(
                f"{lang}:stop={stop_hits},unique={unique_hits},marker={marker_hits},score={score:.2f}"
            )

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_lang, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    if top_score <= 0:
        if len(ASCII_LETTER_RE.findall(sample)) >= max(6, len(sample) // 8):
            return LanguageAuditResult("en", 0.35, "ascii_fallback_no_stopword_match", sample)
        return LanguageAuditResult("unknown", 0.15, "no_language_signal", sample)

    if top_score >= 2.5 and second_score >= 2.0 and abs(top_score - second_score) < 0.9:
        return LanguageAuditResult(
            "mixed",
            min(0.9, 0.45 + top_score / 12),
            "close_competing_scores|" + ";".join(detail_bits),
            sample,
        )

    confidence = min(0.99, 0.35 + top_score / 10 + max(0.0, top_score - second_score) / 8)
    return LanguageAuditResult(
        top_lang,
        confidence,
        "heuristic_score|" + ";".join(detail_bits),
        sample,
    )


def audit_input_output_languages(
    *,
    input_text: str,
    output_text: str,
    source_branch: str,
) -> dict[str, object]:
    input_result = detect_human_language(input_text)
    input_script_bucket, input_script_basis = classify_script_bucket(input_result.sample_text or input_text)
    input_resolved_label, input_resolution_basis = resolve_language_label(
        input_result.label,
        input_result.sample_text or input_text,
    )

    if source_branch == "source_code":
        extracted = extract_source_code_natural_language(output_text)
        if extracted.strip():
            output_scope = "code_comments_or_docstrings"
            output_result = detect_human_language(extracted)
        else:
            output_scope = "code_only"
            output_result = LanguageAuditResult("none", 1.0, "no_comment_text_detected", "")
    else:
        output_scope = "full_output_text"
        output_result = detect_human_language(output_text)

    output_script_bucket, output_script_basis = classify_script_bucket(
        output_result.sample_text or output_text
    )
    output_resolved_label, output_resolution_basis = resolve_language_label(
        output_result.label,
        output_result.sample_text or output_text,
    )

    return {
        "input_human_language": input_result.label,
        "input_human_language_confidence": round(input_result.confidence, 4),
        "input_human_language_basis": input_result.basis,
        "input_human_language_resolved": input_resolved_label,
        "input_human_language_resolution_basis": input_resolution_basis,
        "input_human_script_bucket": input_script_bucket,
        "input_human_script_basis": input_script_basis,
        "output_human_language": output_result.label,
        "output_human_language_confidence": round(output_result.confidence, 4),
        "output_human_language_basis": output_result.basis,
        "output_human_language_resolved": output_resolved_label,
        "output_human_language_resolution_basis": output_resolution_basis,
        "output_human_script_bucket": output_script_bucket,
        "output_human_script_basis": output_script_basis,
        "output_human_language_scope": output_scope,
        "language_audit_version": LANGUAGE_AUDIT_VERSION,
    }
