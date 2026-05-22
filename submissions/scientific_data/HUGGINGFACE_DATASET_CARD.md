---
license: other
language:
  - en
task_categories:
  - text-generation
tags:
  - quantum-computing
  - qiskit
  - openqasm
  - code-generation
  - instruction-tuning
  - dataset-governance
pretty_name: Parallel Quantum Instruction Dataset
size_categories:
  - 100K<n<1M
---

# PQID: Parallel Quantum Instruction Dataset

PQID is a parallel instruction corpus for quantum circuit generation. Each row pairs a natural-language instruction with a Qiskit implementation and associated metadata used for provenance, validation, release governance, and downstream audit.

This Hugging Face release exposes the **public-open PQID v1 view**. It contains only rows whose repository-level license metadata was classified as permissive at release time.

## Release Contents

Default dataset files:

| Split | Rows | File |
| --- | ---: | --- |
| train | 288,744 | `data/train.jsonl` |
| validation | 36,198 | `data/validation.jsonl` |
| test | 35,826 | `data/test.jsonl` |
| total | 360,768 |  |

Audit and release files:

- `release/pqid_v1_public_open_summary.json`
- `release/pqid_v1_public_open_summary.md`
- `release/pqid_v1_public_open_attribution_manifest.csv`
- `release/LICENSE_DISTRIBUTION_SUMMARY.json`
- `release/LICENSE_DISTRIBUTION_SUMMARY.md`

## Licensing

The dataset-level license is marked as `other` because the public-open corpus is composed of source-derived rows with row-level and repository-level license metadata. The public-open view includes permissive-license rows only, but individual rows retain their upstream license evidence in `metadata.repo_license`, `metadata.license_category`, and related governance fields. Users should consult the attribution manifest and row metadata for downstream reuse obligations. The v1.0.1 license-evidence pass adds the BSD-3-Clause `UCLA-SEAL/QDiff` rows to the public-open view.

Rows classified as `no_license`, copyleft, or reviewed `other` licenses are not included in this default public-open Hugging Face release.

## Loading

```python
from datasets import load_dataset

dataset = load_dataset("Elias-Abebe-Gasparini/PQID")
print(dataset)
```

## Reproducibility

The corresponding code, manuscript, figure, and release-workflow materials are maintained in the GitHub repository at:

`https://github.com/Elias-Abebe-Gasparini/PQID-Dataset`

Release refresh: `v1.0.1`, incorporating the QDiff BSD-3-Clause evidence update.

## Citation

Please cite the accompanying Scientific Data article when available, and cite this dataset record by its Hugging Face revision or DOI if one is minted.
