# PQID Metadata-Design Evaluation Report

- input file: `PQID/data/processed/pqid_2026_enriched_github_circuits_plus_metadata_design_v3.jsonl`
- rows: `91,719`

## Field Coverage

| field                        | present_rows | missing_rows |
| ---------------------------- | ------------ | ------------ |
| metadata_design_version      | 91719        | 0            |
| source_snapshot_timestamp    | 91719        | 0            |
| source_snapshot_granularity  | 91719        | 0            |
| source_revision_id           | 91719        | 0            |
| license_evidence_source      | 91719        | 0            |
| license_detection_method     | 91719        | 0            |
| release_view_membership      | 91719        | 0            |
| lineage_parent_id            | 91719        | 0            |
| benchmark_view_membership    | 91719        | 0            |
| expected_model_stance        | 91719        | 0            |
| context_sufficiency_class    | 91719        | 0            |
| repairability_score          | 91719        | 0            |
| repairability_band           | 91719        | 0            |
| evidence_regime              | 91719        | 0            |
| split_group_id               | 91719        | 0            |
| split_group_source           | 91719        | 0            |
| near_duplicate_group_id      | 91719        | 0            |
| domain_slice                 | 91719        | 0            |
| shift_axis                   | 91719        | 0            |
| review_trace_id              | 91719        | 0            |
| distribution_rights_status   | 91719        | 0            |
| license_resolution_status    | 91719        | 0            |
| public_release_bucket        | 91719        | 0            |
| license_audit_priority       | 91719        | 0            |
| contact_outreach_status      | 91719        | 0            |
| permission_response_status   | 91719        | 0            |
| manual_license_review_status | 91719        | 0            |

## Field Value Distributions

### `metadata_design_version`

| value              | count |
| ------------------ | ----- |
| metadata_design_v3 | 91719 |

### `source_snapshot_timestamp`

| value      | count |
| ---------- | ----- |
| 2026-04-02 | 42002 |
| 2026-04-04 | 29317 |
| 2026-03-31 | 14299 |
| 2026-04-01 | 6101  |

### `source_snapshot_granularity`

| value                                   | count |
| --------------------------------------- | ----- |
| day_level_scrape_snapshot_with_blob_sha | 91719 |

### `license_evidence_source`

| value      | count |
| ---------- | ----- |
| missing    | 50570 |
| github_api | 41149 |

### `license_detection_method`

| value        | count |
| ------------ | ----- |
| unresolved   | 50570 |
| api_declared | 41149 |

### `release_view_membership`

| value                  | count |
| ---------------------- | ----- |
| restricted_index       | 50570 |
| public_open            | 39806 |
| public_obligations     | 1226  |
| public_review_required | 117   |

### `benchmark_view_membership`

| value                 | count |
| --------------------- | ----- |
| tier2_unvalidated     | 77452 |
| mutation_stress_n8    | 11265 |
| validated_broad_n8    | 1531  |
| validated_master_only | 737   |
| strict_n8             | 415   |
| extended_n8           | 319   |

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

### `domain_slice`

| value               | count |
| ------------------- | ----- |
| research_proto      | 48523 |
| tutorial            | 13561 |
| test_fixture        | 11584 |
| mutation_suite      | 11440 |
| library_internal    | 5877  |
| benchmark_candidate | 734   |

### `shift_axis`

| value                | count |
| -------------------- | ----- |
| context_completeness | 78096 |
| mutation_status      | 11440 |
| benchmark_tier       | 1495  |
| repo_family          | 580   |
| validation_status    | 108   |

### `review_trace_id`

| value                                                                                                       | count |
| ----------------------------------------------------------------------------------------------------------- | ----- |
| review::aggressive_v1_2026-04-02::no_benchmark_profile::2026-04-02::unresolved                              | 31284 |
| review::aggressive_v1_2026-04-04::benchmark_suitability_v2_code5_gate2::2026-04-04::api_declared            | 11132 |
| review::aggressive_v1_2026-04-02::no_benchmark_profile::2026-04-02::api_declared                            | 8772  |
| review::aggressive_v1_2026-04-04::no_benchmark_profile::2026-04-04::api_declared                            | 8553  |
| review::baseline_legacy::no_benchmark_profile::2026-03-31::api_declared                                     | 6684  |
| review::baseline_legacy::no_benchmark_profile::2026-03-31::unresolved                                       | 6536  |
| review::aggressive_v1_2026-04-04::no_benchmark_profile::2026-04-04::unresolved                              | 5217  |
| review::baseline_legacy::no_benchmark_profile::2026-04-01::unresolved                                       | 3605  |
| review::aggressive_v2_high_yield_2026-04-04::no_benchmark_profile::2026-04-04::unresolved                   | 2364  |
| review::aggressive_v2_high_yield_2026-04-04::no_benchmark_profile::2026-04-04::api_declared                 | 2016  |
| review::baseline_legacy::no_benchmark_profile::2026-04-01::api_declared                                     | 1996  |
| review::baseline_legacy::no_benchmark_profile::2026-04-02::api_declared                                     | 772   |
| review::baseline_legacy::benchmark_suitability_v2_code5_gate2::2026-03-31::api_declared                     | 736   |
| review::aggressive_v1_2026-04-02::benchmark_suitability_v2_code5_gate2::2026-04-02::unresolved              | 617   |
| review::baseline_legacy::no_benchmark_profile::2026-04-02::unresolved                                       | 390   |
| review::baseline_legacy::benchmark_suitability_v2_code5_gate2::2026-04-01::api_declared                     | 356   |
| review::baseline_legacy::benchmark_suitability_v2_code5_gate2::2026-03-31::unresolved                       | 343   |
| review::baseline_legacy::benchmark_suitability_v2_code5_gate2::2026-04-01::unresolved                       | 144   |
| review::aggressive_v1_2026-04-02::benchmark_suitability_v2_code5_gate2::2026-04-02::api_declared            | 97    |
| review::baseline_legacy::benchmark_suitability_v2_code5_gate2::2026-04-02::unresolved                       | 41    |
| review::baseline_legacy::benchmark_suitability_v2_code5_gate2::2026-04-02::api_declared                     | 29    |
| review::aggressive_v2_high_yield_2026-04-04::benchmark_suitability_v2_code5_gate2::2026-04-04::unresolved   | 21    |
| review::aggressive_v1_2026-04-04::benchmark_suitability_v2_code5_gate2::2026-04-04::unresolved              | 8     |
| review::aggressive_v2_high_yield_2026-04-04::benchmark_suitability_v2_code5_gate2::2026-04-04::api_declared | 6     |

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

### `permission_response_status`

| value                 | count |
| --------------------- | ----- |
| not_contacted         | 50570 |
| not_applicable        | 41032 |
| review_before_contact | 117   |

### `manual_license_review_status`

| value          | count |
| -------------- | ----- |
| not_started    | 50570 |
| not_required   | 41032 |
| pending_review | 117   |

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

## Near-Duplicate Group Statistics

| metric               | value  |
| -------------------- | ------ |
| unique_groups        | 88665  |
| singleton_groups     | 87158  |
| non_singleton_groups | 1507   |
| max_group_size       | 167    |
| avg_group_size       | 1.0344 |
| median_group_size    | 1      |

## Cross-Tabs

### `benchmark_view_membership__by_expected_model_stance`

| row_key               | diagnose | generate | repair | robustness_compare |
| --------------------- | -------- | -------- | ------ | ------------------ |
| extended_n8           | 0        | 319      | 0      | 0                  |
| mutation_stress_n8    | 0        | 0        | 0      | 11265              |
| strict_n8             | 0        | 415      | 0      | 0                  |
| tier2_unvalidated     | 77452    | 0        | 0      | 0                  |
| validated_broad_n8    | 0        | 0        | 1531   | 0                  |
| validated_master_only | 0        | 0        | 737    | 0                  |

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

### `domain_slice__by_expected_model_stance`

| row_key             | diagnose | generate | repair | robustness_compare |
| ------------------- | -------- | -------- | ------ | ------------------ |
| benchmark_candidate | 0        | 734      | 0      | 0                  |
| library_internal    | 5698     | 0        | 179    | 0                  |
| mutation_suite      | 0        | 0        | 175    | 11265              |
| research_proto      | 47524    | 0        | 999    | 0                  |
| test_fixture        | 11514    | 0        | 70     | 0                  |
| tutorial            | 12716    | 0        | 845    | 0                  |

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

### `license_detection_method__by_license_category`

| row_key      | <missing> | copyleft | no_license | other | permissive |
| ------------ | --------- | -------- | ---------- | ----- | ---------- |
| api_declared | 0         | 1226     | 0          | 117   | 39806      |
| unresolved   | 3         | 0        | 50567      | 0     | 0          |

### `license_evidence_source__by_license_category`

| row_key    | <missing> | copyleft | no_license | other | permissive |
| ---------- | --------- | -------- | ---------- | ----- | ---------- |
| github_api | 0         | 1226     | 0          | 117   | 39806      |
| missing    | 3         | 0        | 50567      | 0     | 0          |

### `manual_license_review_status__by_distribution_rights_status`

| row_key        | redistributable_copyleft | redistributable_permissive | review_required_other | unresolved_no_license |
| -------------- | ------------------------ | -------------------------- | --------------------- | --------------------- |
| not_required   | 1226                     | 39806                      | 0                     | 0                     |
| not_started    | 0                        | 0                          | 0                     | 50570                 |
| pending_review | 0                        | 0                          | 117                   | 0                     |

### `permission_response_status__by_distribution_rights_status`

| row_key               | redistributable_copyleft | redistributable_permissive | review_required_other | unresolved_no_license |
| --------------------- | ------------------------ | -------------------------- | --------------------- | --------------------- |
| not_applicable        | 1226                     | 39806                      | 0                     | 0                     |
| not_contacted         | 0                        | 0                          | 0                     | 50570                 |
| review_before_contact | 0                        | 0                          | 117                   | 0                     |

### `public_release_bucket__by_expected_model_stance`

| row_key                      | diagnose | generate | repair | robustness_compare |
| ---------------------------- | -------- | -------- | ------ | ------------------ |
| public_open                  | 27092    | 228      | 1221   | 11265              |
| public_open_with_obligations | 1207     | 9        | 10     | 0                  |
| public_review_required       | 114      | 0        | 3      | 0                  |
| restricted_internal_only     | 49039    | 497      | 1034   | 0                  |

### `release_view_membership__by_distribution_rights_status`

| row_key                | redistributable_copyleft | redistributable_permissive | review_required_other | unresolved_no_license |
| ---------------------- | ------------------------ | -------------------------- | --------------------- | --------------------- |
| public_obligations     | 1226                     | 0                          | 0                     | 0                     |
| public_open            | 0                        | 39806                      | 0                     | 0                     |
| public_review_required | 0                        | 0                          | 117                   | 0                     |
| restricted_index       | 0                        | 0                          | 0                     | 50570                 |

### `repairability_band__by_expected_model_stance`

| row_key | diagnose | generate | repair | robustness_compare |
| ------- | -------- | -------- | ------ | ------------------ |
| high    | 0        | 734      | 2268   | 11265              |
| low     | 50185    | 0        | 0      | 0                  |
| medium  | 27267    | 0        | 0      | 0                  |

### `shift_axis__by_expected_model_stance`

| row_key              | diagnose | generate | repair | robustness_compare |
| -------------------- | -------- | -------- | ------ | ------------------ |
| benchmark_tier       | 0        | 734      | 761    | 0                  |
| context_completeness | 77452    | 0        | 644    | 0                  |
| mutation_status      | 0        | 0        | 175    | 11265              |
| repo_family          | 0        | 0        | 580    | 0                  |
| validation_status    | 0        | 0        | 108    | 0                  |

### `source_snapshot_granularity__by_license_evidence_source`

| row_key                                 | github_api | missing |
| --------------------------------------- | ---------- | ------- |
| day_level_scrape_snapshot_with_blob_sha | 41149      | 50570   |
