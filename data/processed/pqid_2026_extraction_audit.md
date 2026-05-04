# Extraction Quality Audit Report

This report is generated from the enriched raw circuit pool.
It is an inspection layer only: it does not rewrite or filter the raw dataset.

## Summary

- Total entries: `91,719`
- `materialized_circuit=True`: `14,267` (15.6%)
- `validated` and `materialized_circuit=True`: `14,267`
- `validated` and `gate_count == 0`: `737`
- `validated` and `gate_count == 0` and `materialized_circuit=True`: `737`
- `contains_demo_scaffolding=True`: `12,435` (13.6%)
- `cleanup_candidate=True`: `9,824` (10.7%)
- `cleanup_candidate=True` and `validated`: `639`
- `extraction_confidence='low'` and `validated`: `0`

## Extraction Confidence

- `high`: `13,623` (14.9%)
- `medium`: `50,648` (55.2%)
- `low`: `27,448` (29.9%)

## Validation Status

- `exec_error`: `40,048` (43.7%)
- `no_circuit`: `28,872` (31.5%)
- `validated`: `14,267` (15.6%)
- `name_error`: `8,142` (8.9%)
- `syntax_error`: `372` (0.4%)
- `timeout`: `17` (0.0%)
- `import_error`: `1` (0.0%)

## Top Cleanup Rules Triggered

- `print_call`: `5,750`
- `result_inspection`: `4,895`
- `job_result`: `3,160`
- `draw_call`: `2,689`
- `backend_run`: `959`
- `matplotlib_plot`: `813`
- `primitive_run`: `812`
- `display_call`: `183`
- `matplotlib_magic`: `14`

## Top Repositories By Low-Confidence Entries

- `runtsang/Q-Bridge`: `4,721`
- `backordinary/QDP-FSL`: `3,843`
- `lockephi/Allentown-L104-Node`: `3,105`
- `AayushSarkar/Qiskit-Experiment-Hub`: `2,741`
- `sethuquantum/LearnQuantum`: `480`
- `Ali-hey-0/Qiskit`: `359`
- `PennyLaneAI/pennylane`: `335`
- `Simula-COMPLEX/MutTG-paper`: `237`
- `Qiskit/documentation`: `229`
- `PennyLaneAI/llvm-project`: `166`

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

## Top Repositories By `validated` + `gate_count == 0`

- `backordinary/QDP-FSL`: `170`
- `Qiskit/platypus`: `103`
- `Ali-hey-0/Qiskit`: `53`
- `qiskit-community/qiskit-community-tutorials`: `31`
- `Qiskit/documentation`: `30`
- `qiskit-community/korean-community`: `18`
- `GT-Quantum-Computing-Association/LogicalQ`: `11`
- `qiskit-community/qiskit-presentations`: `10`
- `kanishkmittal/qbronze`: `10`
- `JooNiv/QCut`: `9`

## Deterministic Review Samples

- Samples written to `extraction_quality_samples_phase3.jsonl` with `10` entries per group.
- `low_confidence`: `10` sampled entries
- `cleanup_candidates`: `10` sampled entries
- `cleanup_candidates_validated`: `10` sampled entries
- `validated_zero_gate`: `10` sampled entries

Sample groups included:
- `low_confidence`
- `cleanup_candidates`
- `cleanup_candidates_validated`
- `validated_zero_gate`

