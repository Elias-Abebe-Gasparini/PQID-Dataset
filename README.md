# PQID: Polyglot Quantum Instruction Dataset ⚛️

[![Hugging Face Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dataset-blue)](https://huggingface.co/datasets/Elias-Abebe-Gasparini/PQID)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![arXiv Placeholder](https://img.shields.io/badge/arXiv-Pending-B31B1B.svg)](https://arxiv.org/)

The **Polyglot Quantum Instruction Dataset (PQID)** is a rigorously validated, parallel corpus designed for the supervised fine-tuning (SFT) of Large Language Models in quantum computing domains. 

It bridges the semantic gap between human-readable intent and hardware-executable logic by providing a 1:5 ratio of natural language instructions mapped to standard **IBM Qiskit** implementations and validated **OPENQASM 3.0** hardware representations.

## 📌 Project Overview

Extracting and standardizing quantum circuits from the wild presents significant memory and compilation challenges. PQID solves this by ingesting unstandardized base circuits from open-source GitHub repositories and the massive RevLib benchmark dataset, pushing them through a strict, error-handled compilation pipeline.

The resulting dataset provides high-quality, instruction-tuned data pairs that teach LLMs how to construct, optimize, and translate complex quantum logic.

## 🏗️ Repository Architecture

This repository contains the complete, end-to-end MLOps and Data Engineering pipeline used to construct PQID and fine-tune its accompanying models. The codebase is modularized chronologically:

* **`00_database_infrastructure/`**: SQL schemas and ETL initialization for robust data storage.
* **`01_acquisition/`**: Memory-efficient scrapers and extraction logic for GitHub and RevLib archives.
* **`02_translation_and_validation/`**: The core Qiskit standardization and OPENQASM 3.0 compilation engine.
* **`03_instruction_generation/`**: Asynchronous LLM pipelines for generating semantic natural language pairs.
* **`04_metadata_analysis/`**: Statistical validation suites (token lengths, quantum gate distributions, circuit depths).
* **`05_model_training/`**: PyTorch and Hugging Face SFT scripts used to fine-tune a 1.3B parameter model on the finalized corpus.

*(For detailed execution instructions and phase-specific documentation, please see the `scripts/README.md` file).*

## 🧠 The 1.3B Quantum-Instruct Model

To validate the semantic density and training efficacy of the PQID dataset, a 1.3-Billion parameter language model was fine-tuned exclusively on this corpus. The training architecture utilized QLoRA and PyTorch FSDP, resulting in a specialized model highly capable of zero-shot Qiskit code generation and OPENQASM translation. The training scripts are available in the `05_model_training` directory.

## 📊 Dataset Overview
- **Total Prompts:** 10,718
- **Base Circuits:** 2,118 (1,869 GitHub / 249 RevLib)
- **Languages:** Qiskit, OPENQASM 3.0

## 🚀 Quickstart: Loading the Dataset

The finalized dataset is hosted on Hugging Face and can be instantly loaded into any PyTorch/TensorFlow environment:

```python
from datasets import load_dataset

# Load the dataset directly from the Hugging Face Hub
from datasets import load_dataset
dataset = load_dataset("Elias-Abebe-Gasparini/PQID")

print(dataset[0]["instruction"])
print(dataset[0]["qiskit_code"])
