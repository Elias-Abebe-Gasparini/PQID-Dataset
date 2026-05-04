# Extraction Quality Audit Report

> Historical snapshot. This report belongs to an earlier thesis-era / baseline checkpoint and is not the current public dataset summary. Use `extraction_quality_report_phase3.md` for the corrected final rebuild counts.

This report is generated from the enriched raw circuit pool.
It is an inspection layer only: it does not rewrite or filter the raw dataset.

## Summary

- Total entries: `21,632`
- `contains_demo_scaffolding=True`: `4,308` (19.9%)
- `cleanup_candidate=True`: `4,308` (19.9%)
- `cleanup_candidate=True` and `validated`: `2,600`
- `extraction_confidence='low'` and `validated`: `0`

## Extraction Confidence

- `high`: `7,992` (36.9%)
- `medium`: `11,888` (55.0%)
- `low`: `1,752` (8.1%)

## Validation Status

- `validated`: `10,592` (49.0%)
- `exec_error`: `8,805` (40.7%)
- `name_error`: `2,174` (10.0%)
- `syntax_error`: `50` (0.2%)
- `timeout`: `11` (0.1%)

## Top Cleanup Rules Triggered

- `result_inspection`: `1,923`
- `print_call`: `1,656`
- `draw_call`: `1,417`
- `job_result`: `1,188`
- `backend_run`: `382`
- `primitive_run`: `267`
- `matplotlib_plot`: `255`
- `display_call`: `74`
- `matplotlib_magic`: `6`

## Top Repositories By Low-Confidence Entries

- `backordinary/QDP-FSL`: `92`
- `Qiskit/platypus`: `77`
- `Qiskit/documentation`: `48`
- `dereklin1205/COMM_LAB_Final`: `37`
- `qiskit-community/qiskit-presentations`: `35`
- `qiskit-community/korean-community`: `30`
- `runtsang/Q-Bridge`: `27`
- `1chooo/quantum-oracle`: `27`
- `AIComputing101/quantum-computing-101`: `27`
- `Qiskit/qiskit-aer`: `25`

## Top Repositories By Cleanup Candidates

- `backordinary/QDP-FSL`: `241`
- `Qiskit/platypus`: `229`
- `Simula-COMPLEX/MutTG-paper`: `145`
- `Qiskit/documentation`: `87`
- `AIComputing101/quantum-computing-101`: `71`
- `qiskit-community/qiskit-presentations`: `57`
- `pathuang1112/QDT_IL`: `53`
- `qiskit-community/korean-community`: `51`
- `1chooo/quantum-oracle`: `45`
- `Qiskit/qiskit-tutorials`: `44`

## Deterministic Review Samples

- Samples written to `extraction_quality_samples.jsonl` with `10` entries per group.
- `low_confidence`: `10` sampled entries
- `cleanup_candidates`: `10` sampled entries
- `cleanup_candidates_validated`: `10` sampled entries

Sample groups included:
- `low_confidence`
- `cleanup_candidates`
- `cleanup_candidates_validated`

