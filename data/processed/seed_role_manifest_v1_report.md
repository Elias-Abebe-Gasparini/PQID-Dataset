# Seed Role Manifest Report

- manifest version: `seed_manifest_v1`
- source corpus: `PQID/data/processed/pqid_2026_enriched_github_circuits.jsonl`
- output manifest: `PQID/data/processed/seed_role_manifest_v1.jsonl`
- total entries: `91,719`

## Seed Role Counts

- `validation_diagnosis`: `77,452`
- `mutation_robustness`: `11,265`
- `repair_or_explanation`: `2,268`
- `gold_generation`: `415`
- `broad_generation`: `319`

## Expected Response Modes

- `diagnosis`: `88,717`
- `repair`: `2,268`
- `generation`: `734`

## Target Supervision Modes

- `teacher_text`: `88,717`
- `source_code`: `3,002`

## Role by n/8 Tier

- `validation_diagnosis` / `<missing>`: `77,452`
- `mutation_robustness` / `mutation_stress_candidate`: `11,265`
- `repair_or_explanation` / `validated_broad_candidate`: `1,531`
- `repair_or_explanation` / `<missing>`: `737`
- `gold_generation` / `strict_core_candidate`: `415`
- `broad_generation` / `extended_core_candidate`: `319`
