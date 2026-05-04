# Benchmark Tiering Report

This report documents the split from the enriched broad raw pool into:
- a strict core benchmark candidate set
- a broad Tier 2 repair / fixing set

## Core Rule

- `validation_status == "validated"`
- `extraction_confidence == "high"`
- `contains_demo_scaffolding == False`
- `cleanup_candidate == False`
- `code_lines >= 5`
- `gate_count >= 2`
- `retrieval_strategy != "empirical_promoted_repo"`: `True`

## Counts

- Total enriched entries: `91,719`
- `validated` entries: `14,267` (15.6%)
- `materialized_circuit=True`: `14,267` (15.6%)
- `validated` and `materialized_circuit=True`: `14,267`
- `validated` and `gate_count > 0`: `13,530`
- `validated` and `gate_count == 0`: `737`
- Core benchmark candidates: `803` (0.9%)
- Tier 2 entries: `90,916` (99.1%)

## Benchmark Suitability Checks

- `validated_execution`: `validation_status == "validated"`
- `high_extraction_confidence`: `extraction_confidence == "high"`
- `no_demo_scaffolding`: `contains_demo_scaffolding != True`
- `no_cleanup_candidate`: `cleanup_candidate != True`
- `minimum_code_lines`: `code_lines >= min_code_lines`
- `minimum_gate_count`: `gate_count >= min_gate_count`
- `trusted_retrieval_strategy`: `retrieval_strategy != "empirical_promoted_repo"`

## Benchmark Suitability Tier Distribution

- `tier2_unvalidated`: `77,452` (84.4%)
- `extended_core_candidate`: `11,196` (12.2%)
- `validated_broad_candidate`: `2,268` (2.5%)
- `strict_core_candidate`: `803` (0.9%)

## Benchmark Suitability Score Distribution

- `0/7`: `73` (0.1%)
- `1/7`: `2,980` (3.2%)
- `2/7`: `9,153` (10.0%)
- `3/7`: `39,219` (42.8%)
- `4/7`: `26,942` (29.4%)
- `5/7`: `973` (1.1%)
- `6/7`: `11,576` (12.6%)
- `7/7`: `803` (0.9%)

## Core Strategy Distribution

- `search`: `627`
- `topic`: `68`
- `curated`: `53`
- `org`: `38`
- `expanded_search`: `11`
- `expanded_search_v2`: `6`

## Tier 2 Strategy Distribution

- `empirical_promoted_repo`: `53,026`
- `search`: `16,745`
- `expanded_search`: `8,805`
- `expanded_search_v2`: `4,398`
- `org`: `4,297`
- `topic`: `2,120`
- `curated`: `1,395`
- `promoted_repo`: `127`
- `gist`: `3`

## Top Core Rejection Reasons

- `not_validated`: `77,452`
- `empirical_strategy_excluded`: `11,196`
- `too_few_code_lines`: `1,568`
- `not_high_confidence`: `644`
- `too_few_gates`: `56`

