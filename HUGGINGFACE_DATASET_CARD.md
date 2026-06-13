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

PQID is a license-aware, quality-audited instruction dataset for quantum programming. Each row pairs a natural-language instruction with a Qiskit implementation and row-level metadata used for provenance, validation, release governance, and downstream audit.

This Hugging Face release exposes the **public-open PQID v1 view**. It contains only rows whose repository-level license metadata was classified as permissive at release time.

## Dataset Files

| Split | Rows | File |
| --- | ---: | --- |
| train | 331,908 | `train.jsonl` |
| validation | 41,520 | `validation.jsonl` |
| test | 41,094 | `test.jsonl` |
| total | 414,522 |  |

## Release Files

Additional release and audit files are included under `release/`:

- `release/pqid_v1_public_open_summary.json`
- `release/pqid_v1_public_open_summary.md`
- `release/pqid_v1_public_open_attribution_manifest.csv`
- `release/pqid_v1_license_valid_summary.json`
- `release/pqid_v1_license_valid_summary.md`

## Licensing

The dataset-level license is marked as `other` because PQID is composed of source-derived rows with row-level and repository-level license metadata. The default Hugging Face payload includes permissive-license rows only. Individual rows retain upstream license evidence in `metadata.repo_license`, `metadata.license_category`, and related governance fields. Users should consult row metadata and the attribution manifest for downstream reuse obligations. The v1.0.1 license-evidence pass adds the BSD-3-Clause `UCLA-SEAL/QDiff` rows to the public-open view; the v1.0.2 pass adds the MIT `backordinary/QDP-FSL` rows after upstream license clearance.

Rows classified as `no_license` are excluded from public release views and retained only for internal audit. Copyleft and manually reviewed `other` rows are not included in the default Hugging Face payload.

## Loading

```python
from datasets import load_dataset

dataset = load_dataset("Elias-Abebe-Gasparini/PQID")
print(dataset)
```

## Reproducibility

The corresponding sanitized public code and documentation are maintained on GitHub and archived on Zenodo:

- GitHub: `https://github.com/Elias-Abebe-Gasparini/PQID-Dataset`
- Zenodo DOI: `10.5281/zenodo.20024477`
- Release refresh: `v1.0.2`, incorporating the QDiff BSD-3-Clause and QDP-FSL MIT evidence updates

Key public reproducibility files include:

- `PQID/scripts/export_license_valid_release_views.py`
- `PQID/scripts/03_instruction_generation/seed_generation_quality_aware_pipeline.ipynb`
- `PQID/scripts/04_metadata_analysis/pqid_metadata_design_and_evaluation.ipynb`

## Citation

Please cite the archived Zenodo version for the public reproducibility package:

```bibtex
@dataset{gasparini_2026_pqid,
  author    = {Gasparini, Elias Abebe},
  title     = {PQID v1.0.2: Parallel Quantum Instruction Dataset},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20024477},
  url       = {https://doi.org/10.5281/zenodo.20024477}
}
```
