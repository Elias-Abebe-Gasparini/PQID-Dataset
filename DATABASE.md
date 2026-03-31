# 🗄️ PQID Database Documentation

This document details the PostgreSQL infrastructure used to harmonize, store, and validate the **Polyglot Quantum Instruction Dataset (PQID)**.

While initial acquisition was handled via Python, the PostgreSQL layer served as the "Source of Truth" for relational integrity and final semantic cleaning.

---

## 🏗️ Architecture Overview

The database utilizes two primary relational tables to map natural language instructions to optimized quantum circuits.

- **Engine:** PostgreSQL 15+
- **Database Name:** `quantum_nlp`
- **Key Feature:** Extensive use of `JSONB` for flexible quantum metadata storage (gate depth, qubit counts, etc.) without requiring rigid schema migrations.

---

## 📂 File Manifest

The following scripts are located at the root of the repository and should be executed in order:

1. **`schema.sql`**:
   - Defines the table structures for `harmonized_circuits` and `quantum_prompts`.
   - Establishes `ON DELETE CASCADE` relationships to ensure data consistency during experimentation.

2. **`etl_and_cleaning.sql`**:
   - Documents the transformation pipeline from raw `.jsonl` staging to relational tables.
   - **Critical Win:** Contains the Deep Deduplication Protocol using `ctid` logic which identified and removed **29 semantic duplicates** that successfully bypassed upstream Python-based cleaning.

3. **`validation.sql`**:
   - A suite of diagnostic queries used to verify the dataset before training.
   - Generates the split statistics (Train/Val/Test) used in Table 1 of the manuscript.

---

## 🧪 Data Validation Results

The final database state was verified using `validation.sql` to confirm the following distribution:

| Source | Type | Split | Count |
| :--- | :--- | :--- | :--- |
| GitHub | Natural | Test | 1,869 |
| GitHub | Paraphrased | Train | 8,546 |
| GitHub | Paraphrased | Validation | 927 |
| RevLib | Natural | Test | 249 |
| RevLib | Paraphrased | Train | 1,099 |
| RevLib | Paraphrased | Validation | 146 |
| **Total** | | | **12,836** |

---

## 🚀 Usage & Replication

To replicate this database locally:

1. Run `schema.sql` to build the structure.
2. Ingest your processed `.jsonl` files (located in `/data/processed/`).
3. Run `etl_and_cleaning.sql` to finalize the deduplication.
4. Execute `validation.sql` to ensure your local row counts match the published results.
