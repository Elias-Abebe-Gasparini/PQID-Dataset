# PQID License Governance Report

- input file: `PQID/data/processed/pqid_2026_enriched_github_circuits_plus_metadata_design_v1.jsonl`
- rows: `91,719`

## Release State Overview

| section                           | value                        | count |
| --------------------------------- | ---------------------------- | ----- |
| license_category_counts           | no_license                   | 50567 |
| license_category_counts           | permissive                   | 39806 |
| license_category_counts           | copyleft                     | 1226  |
| license_category_counts           | other                        | 117   |
| license_category_counts           | <missing>                    | 3     |
| distribution_rights_status_counts | unresolved_no_license        | 50570 |
| distribution_rights_status_counts | redistributable_permissive   | 39806 |
| distribution_rights_status_counts | redistributable_copyleft     | 1226  |
| distribution_rights_status_counts | review_required_other        | 117   |
| public_release_bucket_counts      | restricted_internal_only     | 50570 |
| public_release_bucket_counts      | public_open                  | 39806 |
| public_release_bucket_counts      | public_open_with_obligations | 1226  |
| public_release_bucket_counts      | public_review_required       | 117   |
| license_audit_priority_counts     | medium                       | 49042 |
| license_audit_priority_counts     | low                          | 41146 |
| license_audit_priority_counts     | high                         | 1531  |

## Unresolved No-License Breakdown

### `unresolved_no_license_by_validation_status`

| value        | count |
| ------------ | ----- |
| exec_error   | 22247 |
| no_circuit   | 21093 |
| name_error   | 5506  |
| validated    | 1531  |
| syntax_error | 182   |
| timeout      | 10    |
| import_error | 1     |

### `unresolved_no_license_by_expected_model_stance`

| value    | count |
| -------- | ----- |
| diagnose | 49039 |
| repair   | 1034  |
| generate | 497   |

### `unresolved_no_license_by_retrieval_strategy`

| value                   | count |
| ----------------------- | ----- |
| empirical_promoted_repo | 31062 |
| search                  | 9990  |
| expanded_search         | 5372  |
| expanded_search_v2      | 2382  |
| topic                   | 902   |
| org                     | 811   |
| curated                 | 48    |
| gist                    | 3     |

### `unresolved_no_license_by_source`

| value                      | count |
| -------------------------- | ----- |
| empirical_promoted_repo_v2 | 31062 |
| search                     | 9990  |
| search_v2                  | 5372  |
| search_v3                  | 2382  |
| topic                      | 902   |
| org_v2                     | 692   |
| org                        | 119   |
| curated                    | 48    |
| gist_v3                    | 3     |

## Top Unresolved Repositories

| repo                                                  | rows  | validated_rows | generate_rows | repair_rows | robustness_compare_rows | priority_score |
| ----------------------------------------------------- | ----- | -------------- | ------------- | ----------- | ----------------------- | -------------- |
| backordinary/QDP-FSL                                  | 8959  | 838            | 300           | 538         | 0                       | 15125          |
| runtsang/Q-Bridge                                     | 12148 | 0              | 0             | 0           | 0                       | 12148          |
| wjy99-c/QDiff                                         | 8174  | 0              | 0             | 0           | 0                       | 8174           |
| lockephi/Allentown-L104-Node                          | 4979  | 2              | 1             | 1           | 0                       | 4994           |
| dereklin1205/COMM_LAB_Final                           | 702   | 8              | 0             | 8           | 0                       | 758            |
| qiskit-community/qiskit-presentations                 | 97    | 45             | 8             | 37          | 0                       | 420            |
| Xzore19/QEMI                                          | 232   | 14             | 5             | 9           | 0                       | 335            |
| peiyi1/nassc_code                                     | 284   | 2              | 1             | 1           | 0                       | 299            |
| Simula-COMPLEX/MutTG-paper                            | 237   | 0              | 0             | 0           | 0                       | 237            |
| AIComputing101/quantum-computing-101                  | 226   | 0              | 0             | 0           | 0                       | 226            |
| PennyLaneAI/llvm-project                              | 226   | 0              | 0             | 0           | 0                       | 226            |
| kanishkmittal/qbronze                                 | 46    | 21             | 3             | 18          | 0                       | 196            |
| ibarra18/QAST                                         | 57    | 18             | 10            | 8           | 0                       | 193            |
| NiloGregginz33/QMGRExperiments                        | 174   | 1              | 0             | 1           | 0                       | 181            |
| qiskit-community/qgss-2023                            | 26    | 15             | 0             | 15          | 0                       | 131            |
| QuantumAmplification/ampamp                           | 113   | 0              | 0             | 0           | 0                       | 113            |
| balewski/quantumMind                                  | 80    | 2              | 0             | 2           | 0                       | 94             |
| 023b/quantum_learning                                 | 26    | 9              | 3             | 6           | 0                       | 92             |
| qiskit-community/Qiskit-Hackathon-at-World-of-QUANTUM | 11    | 10             | 1             | 9           | 0                       | 82             |
| NickQrumpton/quantum-mcmc                             | 78    | 0              | 0             | 0           | 0                       | 78             |
| lanl/quantum_algorithms                               | 9     | 9              | 1             | 8           | 0                       | 73             |
| kazuki-matsumoto/Entangle_QNN                         | 71    | 0              | 0             | 0           | 0                       | 71             |
| joshuarg007/quanta                                    | 10    | 8              | 5             | 3           | 0                       | 71             |
| LBNL-HEP-QIS/QCLatticeJLabTutorial                    | 70    | 0              | 0             | 0           | 0                       | 70             |
| Quantinuum/circuit-benchmarks-guppy                   | 69    | 0              | 0             | 0           | 0                       | 69             |
