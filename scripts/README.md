# PQID Data Engineering Pipeline

This directory contains the modular Python codebase used to generate the Polyglot Quantum Instruction Dataset (PQID). To ensure reproducibility, memory efficiency, and crash-resilient processing, the architecture is divided into four distinct execution phases. 

The pipeline is designed to be executed sequentially, with high-compute loops abstracted into standalone `.py` scripts to prevent memory leaks in standard Jupyter environments.

---

### 📁 01_acquisition
Scripts responsible for scraping, standardizing, and extracting base `QuantumCircuit` objects from open-source repositories and benchmark datasets.
* **GitHub Sources:** A complete list of the open-source repositories utilized is documented in `source_repositories.txt`.
* **RevLib Benchmark:** Due to GitHub's strict file size limits, the raw RevLib `.tgz` archive (2.1+ GB) is not hosted in this repository. To reproduce this pipeline, download the archive directly from the RevLib database and place it in the `data/raw/` directory before executing `revlib_tgz_dataset_extraction.py`.

### 📁 02_translation_and_validation
The core quantum logic engine. These scripts ingest the raw extracted circuits, standardize them into the IBM Qiskit framework, and perform strict, error-handled compilations. This iterative loop filters out unsupported operations and translates the logic into validated OPENQASM 3.0 hardware representations.

### 📁 03_instruction_generation
The semantic expansion module. This phase utilizes asynchronous API calls to generate a 1:5 ratio of natural language instructions for each validated circuit. It handles rate-limiting and dynamically constructs the final `instruction`, `qiskit_code`, and `qasm_code` JSONL structures required for supervised fine-tuning.

### 📁 04_metadata_analysis
The statistical validation suite. These scripts parse the finalized dataset to extract structural metrics, including average circuit depths, quantum gate distributions, and token length boundaries. These metrics verify the dataset's complexity and inform the formal dataset characteristics reported in the accompanying arXiv publication.

---

### Execution Note
While the scripts can be run individually via the command line, the entire pipeline is orchestrated via the master execution dashboard (`MS_Thesis_Notebook.ipynb` located in the root directory). Reviewers are encouraged to examine the notebook to view the chronological execution logs and validation outputs.