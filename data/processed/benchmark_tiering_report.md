# Benchmark Tiering Report

> Historical snapshot. This report predates the final Phase 3 `materialized_circuit` correction and should not be used as the current public dataset headline. Use `benchmark_tiering_report_phase3.md` and `benchmark_tiering_report_phase3_extended.md` for the corrected final counts.

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

- Total enriched entries: `87,312`
- Core benchmark candidates: `779` (0.9%)
- Tier 2 entries: `86,533` (99.1%)

## Benchmark Suitability Checks

- `validated_execution`: `validation_status == "validated"`
- `high_extraction_confidence`: `extraction_confidence == "high"`
- `no_demo_scaffolding`: `contains_demo_scaffolding != True`
- `no_cleanup_candidate`: `cleanup_candidate != True`
- `minimum_code_lines`: `code_lines >= min_code_lines`
- `minimum_gate_count`: `gate_count >= min_gate_count`
- `trusted_retrieval_strategy`: `retrieval_strategy != "empirical_promoted_repo"`

## Benchmark Suitability Tier Distribution

- `tier2_unvalidated`: `41,836` (47.9%)
- `validated_broad_candidate`: `33,517` (38.4%)
- `extended_core_candidate`: `11,180` (12.8%)
- `strict_core_candidate`: `779` (0.9%)

## Benchmark Suitability Score Distribution

- `0/7`: `96` (0.1%)
- `1/7`: `1,625` (1.9%)
- `2/7`: `6,087` (7.0%)
- `3/7`: `26,778` (30.7%)
- `4/7`: `13,649` (15.6%)
- `5/7`: `16,001` (18.3%)
- `6/7`: `22,297` (25.5%)
- `7/7`: `779` (0.9%)

## Core Strategy Distribution

- `search`: `617`
- `topic`: `62`
- `curated`: `52`
- `org`: `37`
- `expanded_search`: `11`

## Tier 2 Strategy Distribution

- `empirical_promoted_repo`: `53,026`
- `search`: `16,755`
- `expanded_search`: `8,805`
- `org`: `4,298`
- `topic`: `2,126`
- `curated`: `1,396`
- `promoted_repo`: `127`

## Top Core Rejection Reasons

- `not_validated`: `41,836`
- `too_few_gates`: `25,619`
- `empirical_strategy_excluded`: `11,180`
- `not_high_confidence`: `5,989`
- `too_few_code_lines`: `1,909`

