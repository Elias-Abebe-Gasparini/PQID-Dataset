# PQID Platform Harmonization Checklist

Last updated: 2026-05-23

This checklist keeps the public GitHub repository, Hugging Face dataset,
Zenodo record, and Gradio gateway aligned around the same public release
object.

## Current Release Object

- Release refresh: `v1.0.1`
- Full construction instruction rows: `550,314`
- Default hosted public-open rows: `360,768`
- License-valid audit rows: `368,826`
- Restricted/no-license rows: `181,488`
- Missing license-category internal rows: `0`
- QDiff license-evidence update: `49,044` rows reclassified as BSD-3-Clause
  based on `UCLA-SEAL/QDiff`

## 1. GitHub

Commit only the public-facing release updates and avoid staging private drafts,
funding notes, publication-target notes, local caches, or internal/no-license
payloads.

Recommended public-facing files for this refresh:

- `README.md`
- `PUBLIC_RELEASE_PLAN.md`
- `HUGGINGFACE_DATASET_CARD.md`
- `SCHEMA.md`
- `PIPELINE.md`
- `scripts/enrich_semantic_consistency.py`
- `scripts/upload_huggingface_public_open_release.py`
- `platforms/gradio_space/`
- `submissions/scientific_data/figures/`
- `submissions/scientific_data/figures_calibri/`
- `submissions/scientific_data/plot_quantitative_figures.ipynb`
- `submissions/scientific_data/plot_license_behavior_panel.py`

After the GitHub commit is merged/published, create a GitHub release/tag for
the synchronized version. Suggested tag:

```text
v1.0.1-license-evidence-refresh
```

## 2. Hugging Face Dataset

The Hugging Face dataset should expose only the permissive public-open view as
the default payload:

- `train.jsonl` from `pqid_v1_public_open_train.jsonl`
- `validation.jsonl` from `pqid_v1_public_open_validation.jsonl`
- `test.jsonl` from `pqid_v1_public_open_test.jsonl`
- `release/pqid_v1_public_open_summary.json`
- `release/pqid_v1_public_open_summary.md`
- `release/pqid_v1_public_open_attribution_manifest.csv`
- `release/pqid_v1_license_valid_summary.json`
- `release/pqid_v1_license_valid_summary.md`
- `README.md` from `HUGGINGFACE_DATASET_CARD.md`

Upload command:

```powershell
python "PQID\scripts\upload_huggingface_public_open_release.py" --repo-id "Elias-Abebe-Gasparini/PQID"
```

## 3. Zenodo

Zenodo should archive the same public-open hosted release object and the
sanitized public reproducibility package. Do not upload private planning files,
funding paths, publication-target notes, caches, or internal/no-license rows.

Prepared public-open dataset bundle:

```text
C:\Users\Public\Documents\Wondershare\CreatorTemp\PQID-Dataset-v1.0.1-public-open-zenodo.zip
```

Expected archive contents:

- `train.jsonl`
- `validation.jsonl`
- `test.jsonl`
- `README.md`
- `release/pqid_v1_public_open_summary.json`
- `release/pqid_v1_public_open_summary.md`
- `release/pqid_v1_public_open_attribution_manifest.csv`
- `release/pqid_v1_license_valid_summary.json`
- `release/pqid_v1_license_valid_summary.md`

After Zenodo publishes the new version, update the dataset card and Gradio
citation panel if Zenodo issues a new version-specific DOI. The concept DOI can
remain:

```text
10.5281/zenodo.20024477
```

## 4. Gradio Space

The Gradio gateway should point to the same Hugging Face dataset, GitHub
repository/release, and Zenodo DOI. It should package refreshed figure assets
from `submissions/scientific_data/figures/`.

Check locally:

```powershell
python "PQID\platforms\gradio_space\check_gradio_space.py"
```

Upload command:

```powershell
python "PQID\platforms\gradio_space\upload_space.py" --repo-id "Elias-Abebe-Gasparini/PQID-Dataset-Gateway"
```

## Final Consistency Checks

- GitHub README badges resolve to Hugging Face, Gradio, Zenodo, and license.
- Hugging Face dataset card reports `360,768` public-open rows.
- Gradio release-flow explorer reports `360,768` public-open rows,
  `368,826` license-valid rows, and `181,488` restricted rows.
- Zenodo files include train, validation, and test splits for the same release.
- No internal/no-license rows are redistributed in hosted payloads.
