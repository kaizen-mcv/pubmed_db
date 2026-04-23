-- ============================================================================
-- Tabla de términos MeSH (Medical Subject Headings)
-- Fuente: NLM (National Library of Medicine)
-- URL: https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/asciimesh/
-- Actualización: Anual (enero)
-- Schema: vocab (vocabulario médico controlado)
-- ============================================================================

-- Crear schema si no existe
CREATE SCHEMA IF NOT EXISTS vocab;

-- Eliminar tabla existente
DROP TABLE IF EXISTS vocab.nlm_mesh_terms CASCADE;

-- Crear tabla nlm_mesh_terms
CREATE TABLE vocab.nlm_mesh_terms (
    sm_mesh_term_id SERIAL PRIMARY KEY,
    mesh_ui VARCHAR(20) UNIQUE NOT NULL,      -- Unique Identifier (ej: D002318)
    mesh_name VARCHAR(500) NOT NULL,          -- Nombre principal (ej: "Cardiovascular Diseases")
    tree_numbers TEXT,                        -- Códigos jerárquicos separados por ; (ej: "C14;C14.280")
    parent_category CHAR(1),                  -- Categoría raíz: A,B,C,D,E,F,G,H,I,J,K,L,M,N,V,Z
    year_introduced INTEGER,                  -- Año de introducción del término
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para búsquedas eficientes
CREATE INDEX idx_nlm_mesh_ui ON vocab.nlm_mesh_terms(mesh_ui);
CREATE INDEX idx_nlm_mesh_name ON vocab.nlm_mesh_terms(mesh_name);
CREATE INDEX idx_nlm_mesh_category ON vocab.nlm_mesh_terms(parent_category);

-- Comentarios de documentación
COMMENT ON TABLE vocab.nlm_mesh_terms IS 'Términos MeSH (Medical Subject Headings) de la National Library of Medicine (NLM)';
COMMENT ON COLUMN vocab.nlm_mesh_terms.mesh_ui IS 'Identificador único MeSH (ej: D002318)';
COMMENT ON COLUMN vocab.nlm_mesh_terms.mesh_name IS 'Nombre principal del término MeSH';
COMMENT ON COLUMN vocab.nlm_mesh_terms.tree_numbers IS 'Códigos jerárquicos separados por ; (ej: C14;C14.280.647)';
COMMENT ON COLUMN vocab.nlm_mesh_terms.parent_category IS 'Categoría raíz: C=Diseases, F=Psychiatry, etc.';
COMMENT ON COLUMN vocab.nlm_mesh_terms.year_introduced IS 'Año en que se introdujo el término en MeSH';

-- ============================================================================
-- Categorías MeSH principales:
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
