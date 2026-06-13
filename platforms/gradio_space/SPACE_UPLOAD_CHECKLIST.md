# PQID Gradio Space Upload Checklist

Use this checklist when publishing the dashboard on Hugging Face Spaces.

## 1. Create the Space

On Hugging Face:

- Space name: `PQID-Dataset-Gateway` or `PQID-Explorer`
- SDK: `Gradio`
- Visibility: public

Alternatively, use the local uploader script after setting your token:

```powershell
$env:HF_TOKEN="hf_your_token_here"
python "PQID\platforms\gradio_space\upload_space.py" --repo-id "YOUR_HF_USERNAME/PQID-Dataset-Gateway"
```

This creates the Space if needed and uploads the runtime files plus the packaged
figure assets:

- `app.py`
- `README.md`
- `requirements.txt`
- `assets/figures/*.png`

## 2. Upload Runtime Files

Upload these runtime files first:

- `app.py`
- `README.md`
- `requirements.txt`
- `assets/figures/*.png`

Optional audit/helper files may be uploaded later, but they are not required for
the Space to run.

## 3. Wait for Build

Hugging Face should read the YAML metadata in `README.md`, including:

```yaml
sdk: gradio
sdk_version: 6.11.0
python_version: "3.11"
app_file: app.py
```

The build should install:

- `gradio==6.11.0`
- `datasets>=2.21.0,<5.0.0`
- `huggingface_hub>=1.0.0,<2.0.0`
- `pandas>=2.2.0,<3.0.0`

## 4. Smoke Test Online

Once the Space opens, check:

- the top buttons open Hugging Face, GitHub, Zenodo, and the issue tracker
- the Pipeline Map tab renders the D3 interactive explorer
- clicking pipeline stages changes the detail panel
- Dataset Rows can load a small sample from `train`
- Attribution can load or filter the manifest
- Release Integrity displays static checks and can run the live summary check
- Figures selector changes the large preview image
- Citation tab displays the Zenodo BibTeX text

## 5. If the Space Build Fails

Open the Hugging Face build logs and check:

- whether it is using Python 3.11
- whether `requirements.txt` was installed
- whether a dependency version conflict appears

Do not treat local environment failures as definitive Space failures; Hugging
Face builds in its own containerized environment.
