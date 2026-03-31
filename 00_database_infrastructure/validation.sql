-- =====================================================================
-- PQID Data Validation Diagnostics
-- Engine: PostgreSQL
-- Description: Generates the ML split distribution for manuscript Table 1
-- =====================================================================

SELECT 
    circuit_hash,
    source_dataset,
    circuit_name 
FROM harmonized_circuits 
LIMIT 5;

SELECT 
    circuit_hash,
    prompt_type,
    split_type,
    prompt_text
FROM quantum_prompts
LIMIT 5;

SELECT 
    hc.source_dataset AS "Dataset",
    qp.prompt_type AS "Prompt Type",
    qp.split_type AS "ML Split",
    COUNT(*) AS "Total Prompts"
FROM quantum_prompts qp
JOIN harmonized_circuits hc ON qp.circuit_hash = hc.circuit_hash
GROUP BY hc.source_dataset, qp.prompt_type, qp.split_type
ORDER BY hc.source_dataset, qp.prompt_type, qp.split_type;
