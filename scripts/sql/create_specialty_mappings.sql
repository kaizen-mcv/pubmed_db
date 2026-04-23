-- ============================================================================
-- Mapping table: Affiliations -> SNOMED Specialties
-- Relates author affiliations to medical specialties
-- Schema: sm_maps (mappings to SNOMED)
-- ============================================================================

-- Create schema if it does not exist
CREATE SCHEMA IF NOT EXISTS sm_maps;

-- Drop existing table
DROP TABLE IF EXISTS sm_maps.affiliation_to_snomed CASCADE;

-- ============================================================================
-- Table: sm_maps.affiliation_to_snomed
-- Maps affiliation patterns to specialties
--
-- This is the ONLY mapping table because the affiliation is the only field
-- that is 100% reliable for determining the specialty of an individual author.
-- (A single article may have authors from multiple specialties)
-- ============================================================================
CREATE TABLE sm_maps.affiliation_to_snomed (
    sm_affiliation_id SERIAL PRIMARY KEY,
    affiliation_pattern VARCHAR(500) NOT NULL,
    pattern_type VARCHAR(20) DEFAULT 'exact',     -- 'exact', 'contains', 'prefix', 'suffix'
    snomed_code VARCHAR(20) NOT NULL REFERENCES vocab.snomed_specialties(snomed_code),
    fidelity VARCHAR(20) DEFAULT 'simplified',    -- 'snomed' or 'simplified'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(affiliation_pattern, snomed_code)
);

-- ============================================================================
-- Indexes
-- ============================================================================
CREATE INDEX idx_affiliation_snomed_pattern ON sm_maps.affiliation_to_snomed(affiliation_pattern);
CREATE INDEX idx_affiliation_snomed_code ON sm_maps.affiliation_to_snomed(snomed_code);
CREATE INDEX idx_affiliation_snomed_fidelity ON sm_maps.affiliation_to_snomed(fidelity);

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON SCHEMA sm_maps IS 'Mapping tables from affiliations to SNOMED specialties';
COMMENT ON TABLE sm_maps.affiliation_to_snomed IS 'Mapping of affiliation patterns to SNOMED specialties';
COMMENT ON COLUMN sm_maps.affiliation_to_snomed.affiliation_pattern IS 'Affiliation text that matches a specialty';
COMMENT ON COLUMN sm_maps.affiliation_to_snomed.pattern_type IS 'Match type: exact, contains, prefix, suffix';
COMMENT ON COLUMN sm_maps.affiliation_to_snomed.fidelity IS 'How it was found: snomed=official name, simplified=simplified name';
