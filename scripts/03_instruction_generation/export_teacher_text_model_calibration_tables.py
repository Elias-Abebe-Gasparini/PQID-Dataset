"""
export_teacher_text_model_calibration_tables.py
-----------------------------------------------
Export notebook- and paper-friendly CSV/Markdown summary tables from one or
more teacher-text model-calibration evaluation reports.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPARISON_DIR = ROOT / "data/processed/teacher_text_model_comparison"
DEFAULT_VALIDATION_REPORT = DEFAULT_COMPARISON_DIR / "teacher_text_model_calibration_validation_eval.json"
DEFAULT_MUTATION_REPORT = DEFAULT_COMPARISON_DIR / "teacher_text_model_calibration_mutation_eval.json"
DEFAULT_OUTPUT_PREFIX = DEFAULT_COMPARISON_DIR / "teacher_text_model_calibration"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-files",
        nargs="*",
        type=Path,
        default=[DEFAULT_VALIDATION_REPORT, DEFAULT_MUTATION_REPORT],
        help="Evaluation JSON reports to aggregate into publication-ready tables.",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=DEFAULT_OUTPUT_PREFIX,
        help="Prefix for the exported CSV/Markdown tables.",
    )
    return parser.parse_args()


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def max_opener_share(summary: dict[str, Any]) -> float | None:
    rows = int(summary.get("rows") or 0)
    if rows == 0:
        return None
    repeated = summary.get("repeated_openers") or {}
    max_count = max(repeated.values()) if repeated else 1
    return max_count / rows


def to_markdown(headers: list[str], rows: list[list[Any]]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header_line, divider, *body]) + "\n"


def write_csv(path: Path, headers: list[str], rows: list[list[Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    reports: list[dict[str, Any]] = []
    used_files: list[Path] = []
    for path in args.report_files:
        if path.exists():
            reports.append(load_report(path))
            used_files.append(path)

    if not reports:
        raise FileNotFoundError("no teacher-text calibration reports were found to export")

    summary_headers = [
        "study_label",
        "role",
        "model",
        "rows",
        "expected_rows",
        "completion_rate",
        "overall_score_mean",
        "strict_pass_rate",
        "source_specificity_score_mean",
        "caution_score_mean",
        "actionability_score_mean",
        "overclaim_clean_rate",
        "avg_input_words",
        "avg_output_words",
        "max_opener_share",
    ]
    summary_rows: list[list[Any]] = []

    pairwise_headers = [
        "study_label",
        "role",
        "model_left",
        "model_right",
        "metric",
        "wins",
        "losses",
        "ties",
        "mean_diff",
        "p_value_sign_test",
        "bootstrap_ci_low",
        "bootstrap_ci_high",
        "matched_rows",
    ]
    pairwise_rows: list[list[Any]] = []

    for report in reports:
        study_label = report.get("study_label", "")
        role = report.get("role", "")
        expected_rows = report.get("expected_rows")
        for model_name in report.get("models", []):
            summary = report.get("summaries", {}).get(model_name, {})
            summary_rows.append(
                [
                    study_label,
                    role,
                    model_name,
                    summary.get("rows"),
                    expected_rows,
                    fmt(summary.get("completion_rate")),
                    fmt(summary.get("overall_score_mean")),
                    fmt(summary.get("strict_pass_rate")),
                    fmt(summary.get("source_specificity_score_mean")),
                    fmt(summary.get("caution_score_mean")),
                    fmt(summary.get("actionability_score_mean")),
                    fmt(summary.get("overclaim_clean_rate")),
                    fmt(summary.get("avg_input_words")),
                    fmt(summary.get("avg_output_words")),
                    fmt(max_opener_share(summary)),
                ]
            )

        for pair in report.get("pairwise", []):
            model_left, model_right = pair.get("models", ["", ""])
            for metric_name, stats in pair.get("metrics", {}).items():
                pairwise_rows.append(
                    [
                        study_label,
                        role,
                        model_left,
                        model_right,
                        metric_name,
                        stats.get("wins"),
                        stats.get("losses"),
                        stats.get("ties"),
                        fmt(stats.get("mean_diff")),
                        fmt(stats.get("p_value_sign_test")),
                        fmt(stats.get("bootstrap_ci_low")),
                        fmt(stats.get("bootstrap_ci_high")),
                        stats.get("matched_rows"),
                    ]
                )

    output_prefix = args.output_prefix
    output_prefix.parent.mkdir(parents=True, exist_ok=True)

    summary_csv = output_prefix.with_name(output_prefix.name + "_summary_table.csv")
    summary_md = output_prefix.with_name(output_prefix.name + "_summary_table.md")
    pairwise_csv = output_prefix.with_name(output_prefix.name + "_pairwise_table.csv")
    pairwise_md = output_prefix.with_name(output_prefix.name + "_pairwise_table.md")

    write_csv(summary_csv, summary_headers, summary_rows)
    summary_md.write_text(to_markdown(summary_headers, summary_rows), encoding="utf-8")
    write_csv(pairwise_csv, pairwise_headers, pairwise_rows)
    pairwise_md.write_text(to_markdown(pairwise_headers, pairwise_rows), encoding="utf-8")

    print("teacher-text calibration table export")
    print("  reports used:")
    for path in used_files:
        print("   -", path)
    print("  summary csv:", summary_csv)
    print("  summary md :", summary_md)
    print("  pairwise csv:", pairwise_csv)
    print("  pairwise md :", pairwise_md)


if __name__ == "__main__":
    main()
