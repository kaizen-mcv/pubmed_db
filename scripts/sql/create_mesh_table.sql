-- ============================================================================
-- MeSH terms table (Medical Subject Headings)
-- Source: NLM (National Library of Medicine)
-- URL: https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/asciimesh/
-- Update: Annual (January)
-- Schema: vocab (controlled medical vocabulary)
-- ============================================================================

-- Create schema if it does not exist
CREATE SCHEMA IF NOT EXISTS vocab;

-- Drop existing table
DROP TABLE IF EXISTS vocab.nlm_mesh_terms CASCADE;

-- Create nlm_mesh_terms table
CREATE TABLE vocab.nlm_mesh_terms (
    sm_mesh_term_id SERIAL PRIMARY KEY,
    mesh_ui VARCHAR(20) UNIQUE NOT NULL,      -- Unique Identifier (e.g. D002318)
    mesh_name VARCHAR(500) NOT NULL,          -- Main name (e.g. "Cardiovascular Diseases")
    tree_numbers TEXT,                        -- Hierarchical codes separated by ; (e.g. "C14;C14.280")
    parent_category CHAR(1),                  -- Root category: A,B,C,D,E,F,G,H,I,J,K,L,M,N,V,Z
    year_introduced INTEGER,                  -- Year the term was introduced
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient lookups
CREATE INDEX idx_nlm_mesh_ui ON vocab.nlm_mesh_terms(mesh_ui);
CREATE INDEX idx_nlm_mesh_name ON vocab.nlm_mesh_terms(mesh_name);
CREATE INDEX idx_nlm_mesh_category ON vocab.nlm_mesh_terms(parent_category);

-- Documentation comments
COMMENT ON TABLE vocab.nlm_mesh_terms IS 'MeSH terms (Medical Subject Headings) from the National Library of Medicine (NLM)';
COMMENT ON COLUMN vocab.nlm_mesh_terms.mesh_ui IS 'Unique MeSH Identifier (e.g. D002318)';
COMMENT ON COLUMN vocab.nlm_mesh_terms.mesh_name IS 'Main name of the MeSH term';
COMMENT ON COLUMN vocab.nlm_mesh_terms.tree_numbers IS 'Hierarchical codes separated by ; (e.g. C14;C14.280.647)';
COMMENT ON COLUMN vocab.nlm_mesh_terms.parent_category IS 'Root category: C=Diseases, F=Psychiatry, etc.';
COMMENT ON COLUMN vocab.nlm_mesh_terms.year_introduced IS 'Year the term was introduced in MeSH';

-- ============================================================================
-- Main MeSH categories:
-- A = Anatomy
-- B = Organisms
-- C = Diseases
-- D = Chemicals and Drugs
-- E = Analytical, Diagnostic and Therapeutic Techniques
-- F = Psychiatry and Psychology
-- G = Phenomena and Processes
-- H = Disciplines and Occupations
-- I = Anthropology, Education, Sociology
-- J = Technology, Industry, Agriculture
-- K = Humanities
-- L = Information Science
-- M = Named Groups
-- N = Health Care
-- V = Publication Characteristics
-- Z = Geographicals
-- ============================================================================
