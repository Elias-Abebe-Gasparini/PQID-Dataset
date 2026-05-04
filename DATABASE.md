# PQID Database Documentation

This document describes the PostgreSQL layer used in the original thesis-era PQID workflow.

It is retained for provenance, but it is **not** the source of truth for the active 2026 rebuild.

## Status

Current project state:

- active benchmark workflow: JSONL-first, file-based pipeline
- active source of truth: `PQID/data/processed/`
- active orchestration: `PQID/scripts/scrape_github_unified.ipynb`

The PostgreSQL materials in this repository should therefore be treated as:

- archival documentation for the thesis baseline
- useful for understanding earlier relational cleaning and deduplication logic
- not the canonical release metadata for the rebuilt corpus

## Historical Role

In the thesis-era pipeline, PostgreSQL was used to:

- stage harmonized circuit and prompt records
- enforce relational integrity between circuits and prompts
- support deduplication and validation queries
- produce summary statistics for the original thesis dataset

That historical workflow remains relevant for thesis reproducibility, but not for the corrected Phase 3 rebuild counts now used in public-facing documentation.

## Files

- `schema.sql`
  - thesis-era relational schema
- `etl_and_cleaning.sql`
  - thesis-era ETL and SQL-side deduplication logic
- `validation.sql`
  - thesis-era validation queries

## Use This Document For

- understanding the historical database design
- tracing how the original thesis dataset was organized
- reproducing the earlier relational cleaning layer if needed

## Do Not Use This Document For

- current benchmark counts
- current Hugging Face / GitHub release numbers
- current strict or extended core statistics

For the active rebuild, use:

- `README.md`
- `PIPELINE.md`
- `SCHEMA.md`
