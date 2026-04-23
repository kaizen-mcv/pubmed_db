-- ============================================================================
-- Specialties table for normalized authors (ORCID not required)
-- Stores medical specialties detected in affiliations
-- Schema: sm_result (final results)
-- ============================================================================

-- Drop existing table if it exists
DROP TABLE IF EXISTS sm_result.authors_norm_specialties CASCADE;

-- Create authors_norm_specialties table
CREATE TABLE sm_result.authors_norm_specialties (
    id SERIAL PRIMARY KEY,
    sm_author_id INTEGER NOT NULL REFERENCES sm_result.authors_norm(sm_author_id),
    canonical_name VARCHAR(500) NOT NULL,       -- Normalized author name
    display_name VARCHAR(500) NOT NULL,         -- Display name
    snomed_code VARCHAR(20) NOT NULL REFERENCES vocab.snomed_specialties(snomed_code),
    confidence DECIMAL(4,3) DEFAULT 1.0,        -- Mapping confidence (0.000-1.000)
    article_count INTEGER DEFAULT 1,            -- Number of contributing articles
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- An author can have multiple specialties, but each combination is unique
    UNIQUE(sm_author_id, snomed_code)
);

-- Indexes for efficient lookups
CREATE INDEX idx_authors_norm_spec_author ON sm_result.authors_norm_specialties(sm_author_id);
CREATE INDEX idx_authors_norm_spec_canonical ON sm_result.authors_norm_specialties(canonical_name);
CREATE INDEX idx_authors_norm_spec_snomed ON sm_result.authors_norm_specialties(snomed_code);
CREATE INDEX idx_authors_norm_spec_confidence ON sm_result.authors_norm_specialties(confidence DESC);

-- Index for name search (LIKE)
CREATE INDEX idx_authors_norm_spec_canonical_pattern ON sm_result.authors_norm_specialties(canonical_name varchar_pattern_ops);

-- ============================================================================
-- Documentation comments
-- ============================================================================

COMMENT ON TABLE sm_result.authors_norm_specialties IS 'Medical specialties inferred for normalized authors (all authors, with or without ORCID)';
COMMENT ON COLUMN sm_result.authors_norm_specialties.sm_author_id IS 'Reference to the author in authors_norm';
COMMENT ON COLUMN sm_result.authors_norm_specialties.canonical_name IS 'Normalized name (lowercase, no accents)';
COMMENT ON COLUMN sm_result.authors_norm_specialties.display_name IS 'Preferred display name';
COMMENT ON COLUMN sm_result.authors_norm_specialties.snomed_code IS 'SNOMED CT code of the inferred specialty';
COMMENT ON COLUMN sm_result.authors_norm_specialties.confidence IS 'Mapping confidence (1.0=direct match in affiliation)';
COMMENT ON COLUMN sm_result.authors_norm_specialties.article_count IS 'Number of author articles contributing to this specialty';

-- ============================================================================
-- View for queries with specialty details
-- ============================================================================

CREATE OR REPLACE VIEW sm_result.v_authors_norm_specialties_detail AS
SELECT
    ans.sm_author_id,
    ans.canonical_name,
    ans.display_name,
    ans.snomed_code,
    ss.name_en AS specialty_en,
    ss.name_es AS specialty_es,
    ans.confidence,
    ans.article_count,
    an.author_orcid,
    ans.last_updated
FROM sm_result.authors_norm_specialties ans
JOIN vocab.snomed_specialties ss ON ans.snomed_code = ss.snomed_code
JOIN sm_result.authors_norm an ON ans.sm_author_id = an.sm_author_id
ORDER BY ans.display_name, ans.confidence DESC;

COMMENT ON VIEW sm_result.v_authors_norm_specialties_detail IS 'View with full specialty details per normalized author';
