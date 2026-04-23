-- ============================================================================
-- Inferred specialties table per author
-- Stores the medical specialties detected for each unique author
-- Schema: sm_result (final results)
--
-- NOTE: Specialties are inferred only from author affiliations, which
-- is the only 100% reliable field for determining the specialty of each
-- individual author.
-- ============================================================================

-- Create schema if it does not exist
CREATE SCHEMA IF NOT EXISTS sm_result;

-- Drop existing table
DROP TABLE IF EXISTS sm_result.author_specialties CASCADE;

-- Create author_specialties table
CREATE TABLE sm_result.author_specialties (
    sm_author_specialty_id SERIAL PRIMARY KEY,
    author_name VARCHAR(500) NOT NULL,          -- Author name (format "Lastname, Firstname")
    author_orcid VARCHAR(50),                   -- ORCID if available
    snomed_code VARCHAR(20) NOT NULL REFERENCES vocab.snomed_specialties(snomed_code),
    confidence DECIMAL(4,3),                    -- Mapping confidence (0.000-1.000)
    article_count INTEGER DEFAULT 1,            -- Number of articles contributing to this specialty
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- An author can have multiple specialties, but each combination is unique
    UNIQUE(author_name, snomed_code)
);

-- Indexes for efficient lookups
CREATE INDEX idx_author_specialties_name ON sm_result.author_specialties(author_name);
CREATE INDEX idx_author_specialties_orcid ON sm_result.author_specialties(author_orcid) WHERE author_orcid IS NOT NULL;
CREATE INDEX idx_author_specialties_snomed ON sm_result.author_specialties(snomed_code);
CREATE INDEX idx_author_specialties_confidence ON sm_result.author_specialties(confidence DESC);

-- Index for name search (LIKE)
CREATE INDEX idx_author_specialties_name_pattern ON sm_result.author_specialties(author_name varchar_pattern_ops);

-- ============================================================================
-- Documentation comments
-- ============================================================================

COMMENT ON SCHEMA sm_result IS 'Final results of specialty inference';
COMMENT ON TABLE sm_result.author_specialties IS 'Medical specialties inferred for each unique author based on their affiliations';
COMMENT ON COLUMN sm_result.author_specialties.author_name IS 'Author name in "Lastname, Firstname" format';
COMMENT ON COLUMN sm_result.author_specialties.author_orcid IS 'Author ORCID if available (enables disambiguation)';
COMMENT ON COLUMN sm_result.author_specialties.snomed_code IS 'SNOMED CT code of the inferred specialty';
COMMENT ON COLUMN sm_result.author_specialties.confidence IS 'Mapping confidence (1.0=official SNOMED name, 0.9=simplified name)';
COMMENT ON COLUMN sm_result.author_specialties.article_count IS 'Number of author articles contributing to this specialty';
COMMENT ON COLUMN sm_result.author_specialties.last_updated IS 'Last update of this inference';

-- ============================================================================
-- View for quick queries
-- ============================================================================

CREATE OR REPLACE VIEW sm_result.v_author_specialties_detail AS
SELECT
    asp.author_name,
    asp.author_orcid,
    asp.snomed_code,
    ss.name_en AS specialty_en,
    ss.name_es AS specialty_es,
    asp.confidence,
    asp.article_count,
    asp.last_updated
FROM sm_result.author_specialties asp
JOIN vocab.snomed_specialties ss ON asp.snomed_code = ss.snomed_code
ORDER BY asp.author_name, asp.confidence DESC;

COMMENT ON VIEW sm_result.v_author_specialties_detail IS 'View with full specialty details per author';

-- ============================================================================
-- Function to get specialties for an author
-- ============================================================================

DROP FUNCTION IF EXISTS get_author_specialties(VARCHAR);

CREATE OR REPLACE FUNCTION get_author_specialties(p_author_name VARCHAR)
RETURNS TABLE (
    snomed_code VARCHAR,
    specialty_en VARCHAR,
    specialty_es VARCHAR,
    confidence DECIMAL,
    article_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        asp.snomed_code,
        ss.name_en::VARCHAR,
        ss.name_es::VARCHAR,
        asp.confidence,
        asp.article_count
    FROM sm_result.author_specialties asp
    JOIN vocab.snomed_specialties ss ON asp.snomed_code = ss.snomed_code
    WHERE asp.author_name ILIKE p_author_name
    ORDER BY asp.confidence DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_author_specialties IS 'Returns the specialties of an author by name';

-- ============================================================================
-- Useful SQL queries
-- ============================================================================

-- Top authors by specialty
-- SELECT author_name, confidence, article_count
-- FROM sm_result.author_specialties
-- WHERE snomed_code = '394579002'  -- Cardiology
-- ORDER BY confidence DESC, article_count DESC
-- LIMIT 20;

-- Specialty distribution
-- SELECT s.name_en, COUNT(*) as authors, AVG(a.confidence) as avg_confidence
-- FROM sm_result.author_specialties a
-- JOIN vocab.snomed_specialties s ON a.snomed_code = s.snomed_code
-- GROUP BY s.snomed_code, s.name_en
-- ORDER BY authors DESC;

-- Authors with multiple specialties
-- SELECT author_name, COUNT(*) as num_specialties
-- FROM sm_result.author_specialties
-- GROUP BY author_name
-- HAVING COUNT(*) > 1
-- ORDER BY num_specialties DESC;
