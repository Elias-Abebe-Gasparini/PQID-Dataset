# Polyglot Quantum Instruction Dataset (PQID)

*Developed as part of a Master's thesis in Innovation, exploring structural dataset optimization and multi-abstraction logic in quantum machine learning.*

A high-fidelity, dual-abstraction dataset for instruction-tuning Large Language Models (LLMs) on quantum circuit generation.

## 📊 Dataset Overview
- **Total Prompts:** 10,718
- **Base Circuits:** 2,118 (1,869 GitHub / 249 RevLib)
- **Languages:** Qiskit, OPENQASM 3.0

## 🚀 Usage
```python
from datasets import load_dataset
dataset = load_dataset('json', data_files={'train': 'hf://datasets/Elias-Abebe-Gasparini/PQID/train.jsonl', 'validation': 'hf://datasets/Elias-Abebe-Gasparini/PQID/validation.jsonl'})
```
