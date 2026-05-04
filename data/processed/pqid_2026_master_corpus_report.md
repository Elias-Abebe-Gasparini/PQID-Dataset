# Master Processable Corpus Report

This report documents the corpus that proceeds to seed generation, paraphrasing, and later semantic analyses before any final public-release filtering is applied.

## Processability Rule

- `validation_status == "validated"`
- `materialized_circuit == True`
- `gate_count > 0`: `True`

## Counts

- Total enriched entries examined: `91,719`
- Master processable entries kept: `13,530` (14.8%)
- Rejected `not_validated`: `77,452`
- Rejected `zero_gate_count`: `737`

## Benchmark Suitability Tier Distribution Within Master Corpus (`n/7`)

- `extended_core_candidate`: `11,196`
- `validated_broad_candidate`: `1,531`
- `strict_core_candidate`: `803`

## Benchmark Suitability Score Distribution Within Master Corpus (`n/7`)

- `1/7`: `19`
- `2/7`: `97`
- `3/7`: `240`
- `4/7`: `332`
- `5/7`: `487`
- `6/7`: `11,552`
- `7/7`: `803`

## Cleanliness-Aware Benchmark Tier Distribution Within Master Corpus (`n/8`)

- `mutation_stress_candidate`: `11,265`
- `validated_broad_candidate`: `1,531`
- `strict_core_candidate`: `415`
- `extended_core_candidate`: `319`

## Cleanliness-Aware Benchmark Score Distribution Within Master Corpus (`n/8`)

- `2/8`: `19`
- `3/8`: `97`
- `4/8`: `240`
- `5/8`: `506`
- `6/8`: `11,191`
- `7/8`: `1,062`
- `8/8`: `415`

## License Distribution Within Master Corpus

- `no_license`: `12,642`
- `permissive`: `869`
- `copyleft`: `14`
- `<missing>`: `3`
- `other`: `2`

## Mutation-Suite Flag Distribution Within Master Corpus

- `True`: `11,440`
- `False`: `2,090`

