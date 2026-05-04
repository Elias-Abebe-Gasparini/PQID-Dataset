# Temperature Annotation Rubric

Last updated: 2026-04-12

This rubric is used for the high-rigor temperature-selection stage in the PQID seed-generation pipeline.

The annotation pack is **temperature-blinded**. Reviewers should score each prompt candidate against the provided source code and metadata context without trying to infer or guess the underlying temperature.

## Rating dimensions

Use a `1` to `5` scale unless noted otherwise.

### `semantic_fidelity_1to5`

- `5`: preserves the task implied by the source circuit very accurately
- `4`: minor wording looseness, but no meaningful semantic distortion
- `3`: partially faithful, with noticeable omissions or mild drift
- `2`: significant mismatch with source semantics
- `1`: seriously misleading or contradictory

### `role_fidelity_1to5`

- `5`: perfectly matches the intended role (`gold_generation`, `broad_generation`, or `repair_or_explanation`)
- `4`: mostly consistent, with small framing noise
- `3`: mixed role framing
- `2`: role framing is substantially off
- `1`: role is clearly wrong

### `clarity_1to5`

- `5`: concise, natural, and easy to act on
- `4`: clear with minor awkwardness
- `3`: understandable but somewhat clumsy
- `2`: noticeably awkward or ambiguous
- `1`: hard to understand or poorly formed

### `unnecessary_drift_1to5`

Interpret this as **how well the prompt avoids unnecessary drift**.

- `5`: no unnecessary elaboration or unsupported constraints
- `4`: very slight extra wording, but still disciplined
- `3`: moderate drift or over-specification
- `2`: substantial unsupported detail
- `1`: strong drift or hallucinated requirements

### `benchmark_appropriateness_1to5`

- `5`: excellent fit for PQID’s benchmark-aware seed bank
- `4`: good fit with small caveats
- `3`: usable but weaker than desirable
- `2`: questionable fit
- `1`: not suitable

### `overall_preference_1to5`

This is a holistic judgment of whether the prompt should be preferred as a seed-bank candidate for this source item.

### `accept_for_seed_bank`

Binary field:

- `yes`
- `no`

### `reviewer_notes`

Free-text note for:

- semantic concerns
- role mismatch
- awkward phrasing
- unsupported additions
- anything unusually strong or weak

## Review guidance

- Judge the prompt against the supplied source circuit, not against your own preferred implementation.
- Avoid over-penalizing light paraphrastic differences when semantics are preserved.
- Penalize unsupported extra constraints, task reshaping, or loss of required elements more heavily than small stylistic differences.
- Do not use temperature guesses during annotation.

## Suggested decision use

For a high-rigor final choice:

1. eliminate temperatures that are clearly weaker on semantic fidelity or benchmark appropriateness
2. among the remaining candidates, prefer the temperature with better wording diversity and lower lexical concentration
3. keep the decision rule fixed before looking at aggregated scores
