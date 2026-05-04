# Benchmark Tiering Report (Cleaned)

This report documents the cleaned split from the enriched broad raw pool into:
- a cleaned core benchmark candidate set
- a cleaned Tier 2 repair / fixing set

## Core Rule

- `validation_status == "validated"`
- `extraction_confidence == "high"`
- `contains_demo_scaffolding == False`
- `cleanup_candidate == False`
- `code_lines >= 5`
- `gate_count >= 2`
- `retrieval_strategy != "empirical_promoted_repo"`: `True`
- `exclude mutation-suite paths`: `True`

## Counts

- Total enriched entries: `91,719`
- `validated` entries: `14,267` (15.6%)
- `materialized_circuit=True`: `14,267` (15.6%)
- `validated` and `materialized_circuit=True`: `14,267`
- `validated` and `gate_count > 0`: `13,530`
- `validated` and `gate_count == 0`: `737`
- Cleaned core benchmark candidates: `415` (0.5%)
- Cleaned Tier 2 entries: `91,304` (99.5%)
- Tier 2 entries excluded by mutation-path cleaning: `11,586`

## Benchmark Suitability Checks (`n/7`)

- `validated_execution`: `validation_status == "validated"`
- `high_extraction_confidence`: `extraction_confidence == "high"`
- `no_demo_scaffolding`: `contains_demo_scaffolding != True`
- `no_cleanup_candidate`: `cleanup_candidate != True`
- `minimum_code_lines`: `code_lines >= min_code_lines`
- `minimum_gate_count`: `gate_count >= min_gate_count`
- `trusted_retrieval_strategy`: `retrieval_strategy != "empirical_promoted_repo"`

## Benchmark Suitability Tier Distribution (`n/7`)

- `tier2_unvalidated`: `77,452` (84.4%)
- `extended_core_candidate`: `11,196` (12.2%)
- `validated_broad_candidate`: `2,268` (2.5%)
- `strict_core_candidate`: `803` (0.9%)

## Benchmark Suitability Score Distribution (`n/7`)

- `0/7`: `73` (0.1%)
- `1/7`: `2,980` (3.2%)
- `2/7`: `9,153` (10.0%)
- `3/7`: `39,219` (42.8%)
- `4/7`: `26,942` (29.4%)
- `5/7`: `973` (1.1%)
- `6/7`: `11,576` (12.6%)
- `7/7`: `803` (0.9%)

## Cleanliness-Aware Benchmark Checks (`n/8`)

- `validated_execution`: `validation_status == "validated"`
- `high_extraction_confidence`: `extraction_confidence == "high"`
- `no_demo_scaffolding`: `contains_demo_scaffolding != True`
- `no_cleanup_candidate`: `cleanup_candidate != True`
- `minimum_code_lines`: `code_lines >= min_code_lines`
- `minimum_gate_count`: `gate_count >= min_gate_count`
- `trusted_retrieval_strategy`: `retrieval_strategy != "empirical_promoted_repo"`
- `non_mutation_suite_path`: `mutation_suite_candidate != True`

## Cleanliness-Aware Tier Distribution (`n/8`)

- `tier2_unvalidated`: `77,452` (84.4%)
- `mutation_stress_candidate`: `11,265` (12.3%)
- `validated_broad_candidate`: `2,268` (2.5%)
- `strict_core_candidate`: `415` (0.5%)
- `extended_core_candidate`: `319` (0.3%)

## Cleanliness-Aware Score Distribution (`n/8`)

- `1/8`: `73` (0.1%)
- `2/8`: `2,988` (3.3%)
- `3/8`: `9,197` (10.0%)
- `4/8`: `39,253` (42.8%)
- `5/8`: `27,030` (29.5%)
- `6/8`: `11,677` (12.7%)
- `7/8`: `1,086` (1.2%)
- `8/8`: `415` (0.5%)

## Cleaned Core Strategy Distribution

- `search`: `239`
- `topic`: `68`
- `curated`: `53`
- `org`: `38`
- `expanded_search`: `11`
- `expanded_search_v2`: `6`

## Cleaned Tier 2 Strategy Distribution

- `empirical_promoted_repo`: `53,026`
- `search`: `17,133`
- `expanded_search`: `8,805`
- `expanded_search_v2`: `4,398`
- `org`: `4,297`
- `topic`: `2,120`
- `curated`: `1,395`
- `promoted_repo`: `127`
- `gist`: `3`

## Top Cleaned Core Rejection Reasons

- `not_validated`: `77,306`
- `mutation_suite_excluded`: `11,586`
- `too_few_code_lines`: `1,393`
- `not_high_confidence`: `644`
- `empirical_strategy_excluded`: `319`
- `too_few_gates`: `56`

## Top Mutation-Path Exclusions

- `Ahmik-Virani/Differentiating-Quantum-Bug-From-Noise-Statistical-Approach`: `11,498`
- `GabrielPontolillo/qucheck`: `56`
- `Simula-COMPLEX/muskit`: `21`
- `GabrielPontolillo/QuCheck_with_QOIN`: `11`

