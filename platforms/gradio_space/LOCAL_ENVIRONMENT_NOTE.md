# Local Environment Note

Your current local Python environment is not required for publishing the PQID
Gradio Space.

The older local failure:

```text
ModuleNotFoundError: No module named 'gradio'
```

and the later Pillow build failure were caused by local dependency/version
friction on Windows. The Space itself is configured to use Python 3.11 on
Hugging Face:

```yaml
python_version: "3.11"
```

## Recommended Path

Do not spend more time debugging the local Python environment if the goal is
deployment rather than local preview.

Upload these files to a Hugging Face Gradio Space:

- `app.py`
- `README.md`
- `requirements.txt`
- `assets/figures/*.png`

Hugging Face Spaces will install `requirements.txt` in its own build
environment. The local audit notebook can still verify the file structure,
metadata, public URLs, packaged figure assets, release-integrity checks, and D3
markers without launching the Space.

## Local Notebook Rule

In `gradio_space_audit.ipynb`, run the structural audit cells. If the local
kernel still lacks Gradio or has incompatible packages, skip the cell that
imports `app.py`.

The import cell is useful for local preview and static release-integrity checks.
It is not required for upload if the Hugging Face build succeeds.
