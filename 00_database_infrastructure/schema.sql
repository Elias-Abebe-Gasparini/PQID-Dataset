-- =====================================================================
-- PQID Database Architecture
-- Engine: PostgreSQL
-- Description: Table definitions for the Polyglot Quantum Instruction Dataset
-- =====================================================================

CREATE TABLE harmonized_circuits (
    circuit_hash VARCHAR(64) PRIMARY KEY,
    source_dataset VARCHAR(50),      -- 'github' or 'revlib'
    original_url TEXT,
    circuit_name VARCHAR(255),
    circuit_code TEXT NOT NULL,      -- The valid, executable target code
    metadata JSONB                   -- Store qubits, depth, etc., without needing strict columns
);

CREATE TABLE quantum_prompts (
    prompt_id SERIAL PRIMARY KEY,
    circuit_hash VARCHAR(64) REFERENCES harmonized_circuits(circuit_hash) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,       -- The actual instruction
    prompt_type VARCHAR(20),         -- 'natural' or 'paraphrased'
    paraphrase_index INT,            -- 0 to 4 (NULL if it's the 'natural' prompt)
    split_type VARCHAR(20)           -- 'train', 'validation', 'test' (or NULL if unassigned)
);
