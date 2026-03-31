-- =====================================================================
-- PQID Data Cleaning & Deduplication Protocols
-- Engine: PostgreSQL
-- Description: Scripts used to scrub the dataset after initial ingestion
-- =====================================================================

-- 1. Initial Deduplication
-- Removes exact duplicates based on the serial prompt_id
DELETE FROM quantum_prompts
WHERE prompt_id NOT IN (
    SELECT MIN(prompt_id)
    FROM quantum_prompts
    GROUP BY circuit_hash, prompt_text
);

-- 2. Deep Failsafe Deduplication (CTID method)
-- Used to bypass prompt_id warnings and catch remaining hidden duplicates
DELETE FROM quantum_prompts
WHERE ctid NOT IN (
    SELECT MIN(ctid)
    FROM quantum_prompts
    GROUP BY circuit_hash, prompt_text
);