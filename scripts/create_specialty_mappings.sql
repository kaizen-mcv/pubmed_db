-- ============================================================================
-- Tablas de mapeo: Fuentes de datos → Especialidades SNOMED
-- Permite relacionar journals, afiliaciones, keywords, títulos y abstracts
-- con especialidades médicas para clasificar autores
-- ============================================================================

-- Eliminar tablas existentes
DROP TABLE IF EXISTS abstract_pattern_to_snomed CASCADE;
DROP TABLE IF EXISTS title_pattern_to_snomed CASCADE;
DROP TABLE IF EXISTS keyword_to_snomed CASCADE;
DROP TABLE IF EXISTS affiliation_to_snomed CASCADE;
DROP TABLE IF EXISTS journal_to_snomed CASCADE;

-- ============================================================================
-- Tabla: journal_to_snomed
-- Mapea revistas científicas a especialidades
-- ============================================================================
CREATE TABLE journal_to_snomed (
    id SERIAL PRIMARY KEY,
    journal_issn VARCHAR(20),
    journal_name VARCHAR(500),
    snomed_code VARCHAR(20) NOT NULL REFERENCES snomed_specialties(snomed_code),
    fidelity CHAR(1) DEFAULT 'F',                 -- 'V'=nombre exacto encontrado, 'F'=inferido
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(journal_issn, snomed_code),
    UNIQUE(journal_name, snomed_code)
);

-- ============================================================================
-- Tabla: affiliation_to_snomed
-- Mapea patrones de afiliación a especialidades
-- ============================================================================
CREATE TABLE affiliation_to_snomed (
    id SERIAL PRIMARY KEY,
    affiliation_pattern VARCHAR(500) NOT NULL,
    pattern_type VARCHAR(20) DEFAULT 'contains',  -- 'contains', 'prefix', 'suffix', 'exact'
    snomed_code VARCHAR(20) NOT NULL REFERENCES snomed_specialties(snomed_code),
    fidelity CHAR(1) DEFAULT 'F',                 -- 'V'=nombre exacto encontrado, 'F'=inferido
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(affiliation_pattern, snomed_code)
);

-- ============================================================================
-- Tabla: keyword_to_snomed
-- Mapea palabras clave de autor a especialidades
-- ============================================================================
CREATE TABLE keyword_to_snomed (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(500) NOT NULL,
    snomed_code VARCHAR(20) NOT NULL REFERENCES snomed_specialties(snomed_code),
    fidelity CHAR(1) DEFAULT 'F',                 -- 'V'=nombre exacto encontrado, 'F'=inferido
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(keyword, snomed_code)
);

-- ============================================================================
-- Tabla: title_pattern_to_snomed
-- Mapea patrones en títulos de artículos a especialidades
-- ============================================================================
CREATE TABLE title_pattern_to_snomed (
    id SERIAL PRIMARY KEY,
    title_pattern VARCHAR(500) NOT NULL,
    pattern_type VARCHAR(20) DEFAULT 'contains',  -- 'contains', 'regex', 'word'
    snomed_code VARCHAR(20) NOT NULL REFERENCES snomed_specialties(snomed_code),
    fidelity CHAR(1) DEFAULT 'F',                 -- 'V'=nombre exacto encontrado, 'F'=inferido
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title_pattern, snomed_code)
);

-- ============================================================================
-- Tabla: abstract_pattern_to_snomed
-- Mapea patrones en abstracts a especialidades
-- ============================================================================
CREATE TABLE abstract_pattern_to_snomed (
    id SERIAL PRIMARY KEY,
    abstract_pattern VARCHAR(500) NOT NULL,
    pattern_type VARCHAR(20) DEFAULT 'contains',  -- 'contains', 'regex', 'word'
    snomed_code VARCHAR(20) NOT NULL REFERENCES snomed_specialties(snomed_code),
    fidelity CHAR(1) DEFAULT 'F',                 -- 'V'=nombre exacto encontrado, 'F'=inferido
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(abstract_pattern, snomed_code)
);

-- ============================================================================
-- Índices
-- ============================================================================

-- journal_to_snomed
CREATE INDEX idx_journal_snomed_issn ON journal_to_snomed(journal_issn);
CREATE INDEX idx_journal_snomed_name ON journal_to_snomed(journal_name);
CREATE INDEX idx_journal_snomed_code ON journal_to_snomed(snomed_code);

-- affiliation_to_snomed
CREATE INDEX idx_affiliation_snomed_pattern ON affiliation_to_snomed(affiliation_pattern);
CREATE INDEX idx_affiliation_snomed_code ON affiliation_to_snomed(snomed_code);

-- keyword_to_snomed
CREATE INDEX idx_keyword_snomed_keyword ON keyword_to_snomed(keyword);
CREATE INDEX idx_keyword_snomed_code ON keyword_to_snomed(snomed_code);

-- title_pattern_to_snomed
CREATE INDEX idx_title_snomed_pattern ON title_pattern_to_snomed(title_pattern);
CREATE INDEX idx_title_snomed_code ON title_pattern_to_snomed(snomed_code);

-- abstract_pattern_to_snomed
CREATE INDEX idx_abstract_snomed_pattern ON abstract_pattern_to_snomed(abstract_pattern);
CREATE INDEX idx_abstract_snomed_code ON abstract_pattern_to_snomed(snomed_code);

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON TABLE journal_to_snomed IS 'Mapeo de revistas científicas a especialidades SNOMED';
COMMENT ON TABLE affiliation_to_snomed IS 'Mapeo de patrones de afiliación a especialidades SNOMED';
COMMENT ON TABLE keyword_to_snomed IS 'Mapeo de palabras clave de autor a especialidades SNOMED';
COMMENT ON TABLE title_pattern_to_snomed IS 'Mapeo de patrones en títulos a especialidades SNOMED';
COMMENT ON TABLE abstract_pattern_to_snomed IS 'Mapeo de patrones en abstracts a especialidades SNOMED';
