# PQID Database Documentation

This directory documents the PostgreSQL layer used in the original thesis-era PQID workflow.

It is archival. The active 2026 rebuild does not use this database layer as its source of truth.

## Historical Purpose

The SQL assets here were used to:

- define the original relational schema
- ingest thesis-era JSONL staging outputs
- run SQL-side deduplication and validation checks
- support the original small harmonized thesis corpus

## Current Project Reality

The current rebuilt dataset is managed through:

- JSONL artifacts in `PQID/data/processed/`
- the active notebook `PQID/scripts/scrape_github_unified.ipynb`
- the current public benchmark docs in `README.md`, `PIPELINE.md`, and `SCHEMA.md`

## Files

- `schema.sql`
- `etl_and_cleaning.sql`
- `validation.sql`

These files remain useful for provenance and historical reproducibility, but their row counts and assumptions should not be reused as the current public dataset headline.
