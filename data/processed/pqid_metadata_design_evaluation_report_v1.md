# PQID Metadata-Design Evaluation Report

- input file: `PQID/data/processed/pqid_2026_enriched_github_circuits_plus_metadata_design_v1.jsonl`
- rows: `91,719`

## Field Coverage

| field                      | present_rows | missing_rows |
| -------------------------- | ------------ | ------------ |
| metadata_design_version    | 91719        | 0            |
| expected_model_stance      | 91719        | 0            |
| context_sufficiency_class  | 91719        | 0            |
| repairability_score        | 91719        | 0            |
| repairability_band         | 91719        | 0            |
| evidence_regime            | 91719        | 0            |
| split_group_id             | 91719        | 0            |
| split_group_source         | 91719        | 0            |
| distribution_rights_status | 91719        | 0            |
| license_resolution_status  | 91719        | 0            |
| public_release_bucket      | 91719        | 0            |
| license_audit_priority     | 91719        | 0            |
| contact_outreach_status    | 91719        | 0            |

## Field Value Distributions

### `metadata_design_version`

| value              | count |
| ------------------ | ----- |
| metadata_design_v1 | 91719 |

### `expected_model_stance`

| value              | count |
| ------------------ | ----- |
| diagnose           | 77452 |
| robustness_compare | 11265 |
| repair             | 2268  |
| generate           | 734   |

### `context_sufficiency_class`

| value                  | count |
| ---------------------- | ----- |
| method_fragment        | 62356 |
| demo_scaffolded        | 12435 |
| mutation_variant       | 11440 |
| partial_implementation | 3305  |
| complete_executable    | 2183  |

### `repairability_score`

| value | count |
| ----- | ----- |
| 2     | 36200 |
| 3     | 27267 |
| 8     | 13628 |
| 1     | 8695  |
| 0     | 5290  |
| 7     | 639   |

### `repairability_band`

| value  | count |
| ------ | ----- |
| low    | 50185 |
| medium | 27267 |
| high   | 14267 |

### `evidence_regime`

| value                          | count |
| ------------------------------ | ----- |
| partial_context                | 77452 |
| validated_mutation_stress      | 11440 |
| validated_code                 | 2093  |
| clean_validated_code           | 415   |
| benchmark_ready_validated_code | 319   |

### `split_group_source`

| value     | count |
| --------- | ----- |
| repo_file | 91719 |

### `distribution_rights_status`

| value                      | count |
| -------------------------- | ----- |
| unresolved_no_license      | 50570 |
| redistributable_permissive | 39806 |
| redistributable_copyleft   | 1226  |
| review_required_other      | 117   |

### `license_resolution_status`

| value                 | count |
| --------------------- | ----- |
| unresolved_no_license | 50570 |
| resolved              | 41032 |
| review_required_other | 117   |

### `public_release_bucket`

| value                        | count |
| ---------------------------- | ----- |
| restricted_internal_only     | 50570 |
| public_open                  | 39806 |
| public_open_with_obligations | 1226  |
| public_review_required       | 117   |

### `license_audit_priority`

| value  | count |
| ------ | ----- |
| medium | 49042 |
| low    | 41146 |
| high   | 1531  |

### `contact_outreach_status`

| value        | count |
| ------------ | ----- |
| needed       | 50570 |
| not_required | 41032 |
| review_first | 117   |

## Split Group Statistics

| metric               | value  |
| -------------------- | ------ |
| unique_groups        | 46480  |
| singleton_groups     | 33666  |
| non_singleton_groups | 12814  |
| max_group_size       | 194    |
| avg_group_size       | 1.9733 |
| median_group_size    | 1.0    |

### `split_group_source`

| value     | count |
| --------- | ----- |
| repo_file | 91719 |

## Cross-Tabs

### `context_sufficiency_class__by_evidence_regime`

| row_key                | benchmark_ready_validated_code | clean_validated_code | partial_context | validated_code | validated_mutation_stress |
| ---------------------- | ------------------------------ | -------------------- | --------------- | -------------- | ------------------------- |
| complete_executable    | 319                            | 415                  | 0               | 1449           | 0                         |
| demo_scaffolded        | 0                              | 0                    | 11791           | 644            | 0                         |
| method_fragment        | 0                              | 0                    | 62356           | 0              | 0                         |
| mutation_variant       | 0                              | 0                    | 0               | 0              | 11440                     |
| partial_implementation | 0                              | 0                    | 3305            | 0              | 0                         |

### `context_sufficiency_class__by_validation_status`

| row_key                | exec_error | import_error | name_error | no_circuit | syntax_error | timeout | validated |
| ---------------------- | ---------- | ------------ | ---------- | ---------- | ------------ | ------- | --------- |
| complete_executable    | 0          | 0            | 0          | 0          | 0            | 0       | 2183      |
| demo_scaffolded        | 4607       | 0            | 1303       | 5828       | 42           | 11      | 644       |
| method_fragment        | 34989      | 1            | 4278       | 23037      | 45           | 6       | 0         |
| mutation_variant       | 0          | 0            | 0          | 0          | 0            | 0       | 11440     |
| partial_implementation | 452        | 0            | 2561       | 7          | 285          | 0       | 0         |

### `distribution_rights_status__by_license_category`

| row_key                    | <missing> | copyleft | no_license | other | permissive |
| -------------------------- | --------- | -------- | ---------- | ----- | ---------- |
| redistributable_copyleft   | 0         | 1226     | 0          | 0     | 0          |
| redistributable_permissive | 0         | 0        | 0          | 0     | 39806      |
| review_required_other      | 0         | 0        | 0          | 117   | 0          |
| unresolved_no_license      | 3         | 0        | 50567      | 0     | 0          |

### `evidence_regime__by_expected_model_stance`

| row_key                        | diagnose | generate | repair | robustness_compare |
| ------------------------------ | -------- | -------- | ------ | ------------------ |
| benchmark_ready_validated_code | 0        | 319      | 0      | 0                  |
| clean_validated_code           | 0        | 415      | 0      | 0                  |
| partial_context                | 77452    | 0        | 0      | 0                  |
| validated_code                 | 0        | 0        | 2093   | 0                  |
| validated_mutation_stress      | 0        | 0        | 175    | 11265              |

### `expected_model_stance__by_benchmark_suitability_tier_v2`

| row_key            | <missing> | extended_core_candidate | mutation_stress_candidate | strict_core_candidate | validated_broad_candidate |
| ------------------ | --------- | ----------------------- | ------------------------- | --------------------- | ------------------------- |
| diagnose           | 77452     | 0                       | 0                         | 0                     | 0                         |
| generate           | 0         | 319                     | 0                         | 415                   | 0                         |
| repair             | 737       | 0                       | 0                         | 0                     | 1531                      |
| robustness_compare | 0         | 0                       | 11265                     | 0                     | 0                         |

### `expected_model_stance__by_validation_status`

| row_key            | exec_error | import_error | name_error | no_circuit | syntax_error | timeout | validated |
| ------------------ | ---------- | ------------ | ---------- | ---------- | ------------ | ------- | --------- |
| diagnose           | 40048      | 1            | 8142       | 28872      | 372          | 17      | 0         |
| generate           | 0          | 0            | 0          | 0          | 0            | 0       | 734       |
| repair             | 0          | 0            | 0          | 0          | 0            | 0       | 2268      |
| robustness_compare | 0          | 0            | 0          | 0          | 0            | 0       | 11265     |

### `license_audit_priority__by_expected_model_stance`

| row_key | diagnose | generate | repair | robustness_compare |
| ------- | -------- | -------- | ------ | ------------------ |
| high    | 0        | 497      | 1034   | 0                  |
| low     | 28413    | 237      | 1231   | 11265              |
| medium  | 49039    | 0        | 3      | 0                  |

### `public_release_bucket__by_expected_model_stance`

| row_key                      | diagnose | generate | repair | robustness_compare |
| ---------------------------- | -------- | -------- | ------ | ------------------ |
| public_open                  | 27092    | 228      | 1221   | 11265              |
| public_open_with_obligations | 1207     | 9        | 10     | 0                  |
| public_review_required       | 114      | 0        | 3      | 0                  |
| restricted_internal_only     | 49039    | 497      | 1034   | 0                  |

### `repairability_band__by_expected_model_stance`

| row_key | diagnose | generate | repair | robustness_compare |
| ------- | -------- | -------- | ------ | ------------------ |
| high    | 0        | 734      | 2268   | 11265              |
| low     | 50185    | 0        | 0      | 0                  |
| medium  | 27267    | 0        | 0      | 0                  |
