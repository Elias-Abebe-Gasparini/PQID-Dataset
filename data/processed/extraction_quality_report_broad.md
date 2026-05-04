# Extraction Quality Audit Report

> Historical snapshot. This report belongs to the pre-Phase-3 broad checkpoint and is retained for audit history only. Use `extraction_quality_report_phase3.md` for the corrected final rebuild counts.

This report is generated from the enriched raw circuit pool.
It is an inspection layer only: it does not rewrite or filter the raw dataset.

## Summary

- Total entries: `87,312`
- `contains_demo_scaffolding=True`: `11,255` (12.9%)
- `cleanup_candidate=True`: `9,002` (10.3%)
- `cleanup_candidate=True` and `validated`: `5,086`
- `extraction_confidence='low'` and `validated`: `0`

## Extraction Confidence

- `high`: `39,487` (45.2%)
- `medium`: `31,737` (36.3%)
- `low`: `16,088` (18.4%)

## Validation Status

- `validated`: `45,476` (52.1%)
- `exec_error`: `38,182` (43.7%)
- `name_error`: `3,300` (3.8%)
- `syntax_error`: `353` (0.4%)
- `timeout`: `1` (0.0%)

## Top Cleanup Rules Triggered

- `print_call`: `5,031`
- `result_inspection`: `4,533`
- `job_result`: `2,857`
- `draw_call`: `2,538`
- `backend_run`: `844`
- `matplotlib_plot`: `719`
- `primitive_run`: `678`
- `display_call`: `169`
- `matplotlib_magic`: `14`

## Top Repositories By Low-Confidence Entries

- `runtsang/Q-Bridge`: `3,889`
- `lockephi/Allentown-L104-Node`: `2,716`
- `backordinary/QDP-FSL`: `1,798`
- `AayushSarkar/Qiskit-Experiment-Hub`: `1,717`
- `sethuquantum/LearnQuantum`: `433`
- `Ali-hey-0/Qiskit`: `324`
- `Qiskit/documentation`: `251`
- `PennyLaneAI/pennylane`: `186`
- `Arka221B/Qiskit_terra`: `137`
- `PennyLaneAI/llvm-project`: `125`

## Top Repositories By Cleanup Candidates

- `backordinary/QDP-FSL`: `2,269`
- `runtsang/Q-Bridge`: `319`
- `lockephi/Allentown-L104-Node`: `264`
- `Qiskit/platypus`: `229`
- `Simula-COMPLEX/MutTG-paper`: `228`
- `Qiskit/documentation`: `136`
- `sethuquantum/LearnQuantum`: `121`
- `AIComputing101/quantum-computing-101`: `97`
- `dereklin1205/COMM_LAB_Final`: `72`
- `NiloGregginz33/QMGRExperiments`: `66`

## Deterministic Review Samples

- Samples written to `extraction_quality_samples_broad.jsonl` with `10` entries per group.
- `low_confidence`: `10` sampled entries
- `cleanup_candidates`: `10` sampled entries
- `cleanup_candidates_validated`: `10` sampled entries

Sample groups included:
- `low_confidence`
- `cleanup_candidates`
- `cleanup_candidates_validated`

