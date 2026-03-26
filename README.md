# PQID: Polyglot Quantum Instruction Dataset ⚛️

[![Hugging Face Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dataset-blue)](https://huggingface.co/datasets/Elias-Abebe-Gasparini/PQID)
[![Kaggle: Upcoming](https://img.shields.io/badge/Kaggle-Upcoming-lightgrey?logo=kaggle)](https://www.kaggle.com/abebegasparini)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![arXiv Placeholder](https://img.shields.io/badge/arXiv-Pending-B31B1B.svg)](https://arxiv.org/)

The **Polyglot Quantum Instruction Dataset (PQID)** is a rigorously validated, parallel corpus designed for the supervised fine-tuning (SFT) of Large Language Models in quantum computing domains.

It bridges the semantic gap between human-readable intent and hardware-executable logic by providing a 1:5 ratio of natural language instructions mapped to standard **IBM Qiskit** implementations and validated **OPENQASM 3.0** hardware representations.

## 📑 Table of Contents

---

- [📌 Project Overview](#-project-overview)
- [🔄 Replication Research Ecosystem](#-replication-research-ecosystem)
- [🏗️ Repository Architecture](#%EF%B8%8F-repository-architecture)
  - [📂 File Hierarchy](#-file-hierarchy)
- [🧠 The 1.3B Quantum-Instruct Model](#-the-13b-quantum-instruct-model)
- [🕹️ Interactive Inference (Upcoming)](#%EF%B8%8F-interactive-inference-upcoming)
- [🛠️ Data Transformation Pipeline](#%EF%B8%8F-data-transformation-pipeline)
- [📊 Dataset Overview](#-dataset-overview)
- [🚀 Quickstart: Loading the Dataset](#-quickstart-loading-the-dataset)
- [📜 Citation & Academic Context](#-citation--academic-context)
  - [⏳ Research Roadmap](#-research-roadmap)
- [📧 Contact](#-contact)

---

## 📌 Project Overview

Extracting and standardizing quantum circuits from the wild presents significant memory and compilation challenges. PQID solves this by ingesting unstandardized base circuits from open-source GitHub repositories and the massive RevLib benchmark dataset, pushing them through a strict, error-handled compilation pipeline.

The resulting dataset provides high-quality, instruction-tuned data pairs that teach LLMs how to construct, optimize, and translate complex quantum logic.

## 🔄 Replication Research Ecosystem

```mermaid
graph LR
    %% Class Definitions
    classDef github fill:#76ddff,stroke:#01579b,stroke-width:2px;
    classDef hf fill:#92d097,stroke:#2e7d32,stroke-width:2px;
    classDef kaggle fill:#c1adea,stroke:#7b1fa2,stroke-width:2px;

    subgraph "GitHub (The Logic)"
        A[00_DB_Infra] --> B[01_Acquisition]
        B --> C[02_Validation]
        C --> D[03_Gen]
        D --> E[04_Analysis]
        E --> F[05_Training]
    end

    subgraph "Hugging Face (The Storage)"
        G[(PQID Dataset)]
        H[(1.3B Model Weights)]
    end

    subgraph "Kaggle (The Execution)"
        I[Inference Demo]
    end

    %% Applying Classes
    class A,B,C,D,E,F github;
    class G,H hf;
    class I kaggle;

    %% Connections
    F -.-> G
    F -.-> H
    G --> I
    H --> I
    I -- Feedback --> A
```

> 🔗 **Architectural Blueprint:** [View Raw Mermaid Syntax](./ARCHITECTURE.mmd)

## 🏗️ Repository Architecture

This repository contains the complete, end-to-end MLOps and Data Engineering pipeline used to construct PQID and fine-tune its accompanying models. The codebase is modularized chronologically:

- **`00_database_infrastructure/`**: SQL schemas and ETL initialization for robust data storage.
- **`01_acquisition/`**: Memory-efficient scrapers and extraction logic for GitHub and RevLib archives.
- **`02_translation_and_validation/`**: The core Qiskit standardization and OPENQASM 3.0 compilation engine.
- **`03_instruction_generation/`**: Asynchronous LLM pipelines for generating semantic natural language pairs.
- **`04_metadata_analysis/`**: Statistical validation suites (token lengths, quantum gate distributions, circuit depths).
- **`05_model_training/`**: PyTorch and Hugging Face SFT scripts used to fine-tune a 1.3B parameter model on the finalized corpus.

*(For detailed execution instructions and phase-specific documentation, please see the `scripts/README.md` file).*

### 📂 File Hierarchy

```text
PQID/
├── .gitignore
├── README.md
├── .github/
│   └── FUNDING.yml
├── 00_database_infrastructure/
│   ├── DATABASE.md
│   ├── etl_and_cleaning.sql
│   ├── schema.sql
│   └── validation.sql
├── data/
│   └── processed/
│       ├── train.jsonl
│       └── validation.jsonl
└── scripts/
    ├── README.md
    ├── 01_acquisition/
    ├── 02_translation_and_validation/
    ├── 03_instruction_generation/
    ├── 04_metadata_analysis/
    └── 05_model_training/

```

## 🧠 The 1.3B Quantum-Instruct Model

To validate the semantic density and training efficacy of the PQID dataset, a 1.3-Billion parameter language model was fine-tuned exclusively on this corpus. The training architecture utilized QLoRA and PyTorch FSDP, resulting in a specialized model highly capable of zero-shot Qiskit code generation and OPENQASM translation. The training scripts are available in the `05_model_training` directory.

## 🕹️ Interactive Inference (Upcoming)

To ensure zero-install reproducibility, an interactive **Inference Notebook** is currently being prepared for Kaggle.

- **Status:** 🏗️ *Work in Progress (Optimization for T4/P100 GPUs)*
- **Purpose:** This notebook will provide a pre-configured environment to load the **PQID-1.3B model** and generate valid Qiskit/OpenQASM 3.0 code from natural language prompts in real-time.
- **Why Kaggle?** By leveraging Kaggle's free GPU compute, researchers can validate the model's performance without local hardware constraints or additional cloud computing costs.

## 🛠️ Data Transformation Pipeline

```mermaid
sequenceDiagram
    autonumber
    participant H as Human Seed
    participant LLM as LLM Paraphraser
    participant QK as Qiskit (Python)
    participant VAL as Compilation Engine
    participant Q3 as OpenQASM 3.0

    rect rgb(121, 170, 208)
    Note over H,LLM: Phase 1: Semantic Expansion (1:5 Ratio)
    H->>LLM: 2,118 "Natural" Prompts
    LLM-->>LLM: Paraphrasing & Rewriting
    LLM->>QK: 10,718 Instruction-Code Pairs
    end

    rect rgb(44, 189, 146)
    Note over QK,VAL: Phase 2: Logic Validation
    QK->>VAL: Execute Python Logic
    VAL-->>VAL: Syntax Check & Error Handling
    end
    
    rect rgb(183, 142, 203)
    Note over VAL,Q3: Phase 3: Hardware Mapping
    VAL->>Q3: Transpile to Hardware Representation
    Q3-->>QK: Final Validated Pair
    end
```

## 📊 Dataset Overview

### 📐 Mathematical Formalization

The semantic expansion of the PQID corpus is formally defined by the **Instruction Density Ratio** ($\rho$), which measures the linguistic variety mapped to each hardware-validated circuit:

$$\rho = \frac{|P|}{|C_{base}|}$$

Where $|P|$ represents the total volume of instruction-tuned prompts (10,718), and $|C_{base}|$ represents the set of unique, validated quantum circuits (2,118).

For PQID v1.0, the density is strictly maintained at $\rho \approx 5.06$. This high ratio ensures that the fine-tuned model generalizes across a diverse linguistic distribution for any single quantum logical operation, mitigating the risk of structural overfitting and encouraging true semantic understanding.

- **Total Prompts:** 10,718
- **Base Circuits:** 2,118 (1,869 GitHub / 249 RevLib)
- **Languages:** Qiskit, OPENQASM 3.0

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'pie1': '#6eb2d1', 'pie2': '#519f58'}}}%%
pie title PQID Base Circuit Provenance
    "GitHub Scraped (1,869)" : 1869
    "RevLib Benchmark (249)" : 249
```

### 🛡️ Data Quality & Deduplication

Unlike standard instruction datasets, PQID underwent a multi-stage validation process:

- **Relational Integrity:** Using a PostgreSQL backend to manage the 1:5 mapping of natural instructions to paraphrased variants.
- **Deep Deduplication:** A SQL-based `ctid` analysis was used to identify and remove **29 semantic duplicates** that bypassed initial Python-based string-matching filters.
- **Hardware Validation:** Every circuit in this dataset has been compiled and validated through the IBM Qiskit backend to ensure syntax and logical validity.

### 📈 Dataset Splits & Generalization

To prevent model memorization and encourage true linguistic generalization:

- **Training/Validation (10,718 entries):** Consists of 100% paraphrased instructions.
- **Test Set (2,118 entries):** Consists exclusively of the original "Natural" human-authored seed prompts.
This "Zero-Shot" evaluation strategy ensures the model is tested on real human input it has never seen in its original form during training.

## 🚀 Quickstart: Loading the Dataset

The finalized dataset is hosted on Hugging Face and can be instantly loaded into any PyTorch/TensorFlow environment:

```python

# Load the dataset directly from the Hugging Face Hub
from datasets import load_dataset
dataset = load_dataset("Elias-Abebe-Gasparini/PQID")

print(dataset[0]["instruction"])
print(dataset[0]["qiskit_code"])

```

## 📜 Citation & Academic Context

### 📝 How to Cite

If you use the PQID dataset or this pipeline in your research, please cite it as follows:

```bibtex
@misc{gasparini2026pqid,
  author = {Gasparini, Elias A.},
  title = {PQID: Polyglot Quantum Instruction Dataset for Large Language Model Tuning},
  year = {2026},
  publisher = {GitHub},
  journal = {GitHub Repository},
  howpublished = {\url{https://github.com/Elias-Abebe-Gasparini/PQID-Dataset}}
}

```

### 🔬 Research Context

This project is an **independent research initiative** conducted by Elias Abebe Gasparini.

- **Independence:** All data engineering, SQL architecture, and model training logic were developed and funded solely by the author.
- **Affiliation:** While the author was affiliated with Yonsei University at the time of the thesis writing, this specific body of work was produced independently of laboratory funding or institutional resources.
- **Academic Contribution:** This dataset and its accompanying pipeline were developed as part of a Master's Thesis for the **MS in Innovation** at the **Department of Innovation, Yonsei University**. A formal breakdown of the dataset characteristics, validation methodology, and training results is currently pending publication. Once available on arXiv, the formal BibTeX citation will be updated above.

### ⏳ Research Roadmap

```mermaid
gantt
    title PQID Development & High-Impact Academic Roadmap
    dateFormat  YYYY-MM
    axisFormat  %b %Y

    section 🏗️ Completed Data Engineering
    01-02 - Acquisition & Harmonisation     :done, a1, 2025-01, 5M
    03-04 - Validation & LLM Generation     :done, b1, 2025-03, 7M
    05 - SFT 1.3B Model Training            :done, c1, 2025-06, 3M
    00-06 - DB Infrastructure & ETL         :done, d1, 2025-09, 6M
    07-08 - PostgreSQL & Deduplication      :done, d2, 2026-01, 2M

    section 🎓 Graduation Milestones
    Thesis Compilation                      :done, m1, 2025-04, 3M
    Thesis Defense                          :done, m2, 2025-06, 1M
    Thesis Submission                       :done, m3, 2025-07, 1M

    section 🌐 Platform Sync
    GitHub & Hugging Face Release           :active, p1, 2026-03, 1M
    Kaggle Interactive Demo                 :active, p2, 2026-03, 2M

    section 📚 Publication Targets
    arXiv Preprint Submission               :crit, milestone, t1, 2026-04, 1d
    Nature Portfolio (Scientific Data) Sub  :crit, milestone, t2, 2026-04, 1d
    ACM TQC Journal Submission              :crit, milestone, t3, 2026-04, 1d
    NeurIPS Workshop Submission             :crit, milestone, t4, 2026-05, 1d
```

## 📧 Contact

For technical inquiries, dataset access, or collaboration opportunities:

- **GitHub:** [Open an Issue](https://github.com/Elias-Abebe-Gasparini/PQID-Dataset/issues)
- **LinkedIn:** [Elias A. Gasparini](https://www.linkedin.com/in/elias-abebe-gasparini/)
