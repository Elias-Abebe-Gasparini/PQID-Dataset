param(
    [int]$Port = 7860,
    [switch]$InstallRequirements
)

$ErrorActionPreference = "Stop"
$SpaceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SpaceDir

Write-Host "PQID Gradio Space folder: $SpaceDir"

$PythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$PythonVersion -ge [version]"3.14") {
    Write-Error "Local preview should use Python 3.11 or 3.12. Python $PythonVersion may still have wheel gaps on Windows. Create a Python 3.11/3.12 environment, then rerun this script."
}

if ($InstallRequirements) {
    Write-Host "Installing Space requirements..."
    python -m pip install -r requirements.txt
}

Write-Host "Running local package checks..."
python check_gradio_space.py

$env:GRADIO_ANALYTICS_ENABLED = "False"
$env:GRADIO_SERVER_PORT = "$Port"

Write-Host "Launching PQID Dataset Gateway on http://127.0.0.1:$Port"
python app.py
