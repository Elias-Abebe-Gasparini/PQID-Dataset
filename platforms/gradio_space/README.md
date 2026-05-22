---
title: PQID Dataset Gateway
emoji: ⚛️
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.11.0
python_version: "3.11"
app_file: app.py
pinned: false
license: other
fullWidth: true
short_description: PQID public dataset gateway and pipeline explorer.
datasets:
  - Elias-Abebe-Gasparini/PQID
---

# PQID Dataset Gateway

Interactive dashboard for the public-open Parallel Quantum Instruction Dataset.

This Space reads the public Hugging Face dataset mirror:

`Elias-Abebe-Gasparini/PQID`

The dashboard includes D3-based explorers for the construction pipeline, release-flow stratification, and license-behaviour clustering, plus reviewer/audit panels for figures, quality evidence, attribution, and citation.

It links the public data payload, the sanitized GitHub repository, and the Zenodo DOI record:

- Hugging Face dataset: `https://huggingface.co/datasets/Elias-Abebe-Gasparini/PQID`
- GitHub repository: `https://github.com/Elias-Abebe-Gasparini/PQID-Dataset`
- Zenodo DOI: `https://doi.org/10.5281/zenodo.20024477`

The Space does not package or redistribute internal/no-license rows. The default Hugging Face dataset payload is the public-open release view.

## Local Checks

Before uploading or replacing files on Hugging Face Spaces, run:

```powershell
python check_gradio_space.py
```

Or open and run the audit notebook cell by cell:

```text
gradio_space_audit.ipynb
```

If dependencies are not installed locally yet, run:

```powershell
.\run_local_space.ps1 -InstallRequirements
```

Use Python 3.11, 3.12, or 3.13 for local preview. Very new Python versions may temporarily lag behind compiled dependency wheels on Windows, so the Hugging Face build environment remains the canonical runtime.

For later local launches:

```powershell
.\run_local_space.ps1
```
