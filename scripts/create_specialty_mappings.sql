-- ============================================================================
-- Tabla de mapeo: Afiliaciones → Especialidades SNOMED
-- Permite relacionar afiliaciones de autores con especialidades médicas
-- Schema: sm_maps (mapeos a SNOMED)
-- ============================================================================

-- Crear schema si no existe
CREATE SCHEMA IF NOT EXISTS sm_maps;

-- Eliminar tabla existente
DROP TABLE IF EXISTS sm_maps.affiliation_to_snomed CASCADE;

-- ============================================================================
-- Tabla: sm_maps.affiliation_to_snomed
-- Mapea patrones de afiliación a especialidades
--
-- Esta es la ÚNICA tabla de mapeo porque la afiliación es el único campo
-- 100% fiable para determinar la especialidad de un autor individual.
-- (Un artículo puede tener autores de múltiples especialidades)
-- ============================================================================
CREATE TABLE sm_maps.affiliation_to_snomed (
    sm_affiliation_id SERIAL PRIMARY KEY,
    affiliation_pattern VARCHAR(500) NOT NULL,
    pattern_type VARCHAR(20) DEFAULT 'exact',     -- 'exact', 'contains', 'prefix', 'suffix'
    snomed_code VARCHAR(20) NOT NULL REFERENCES vocab.snomed_specialties(snomed_code),
    fidelity VARCHAR(20) DEFAULT 'simplified',    -- 'snomed' o 'simplified'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(affiliation_pattern, snomed_code)
);

-- ============================================================================
-- Índices
-- ============================================================================
CREATE INDEX idx_affiliation_snomed_pattern ON sm_maps.affiliation_to_snomed(affiliation_pattern);
CREATE INDEX idx_affiliation_snomed_code ON sm_maps.affiliation_to_snomed(snomed_code);
CREATE INDEX idx_affiliation_snomed_fidelity ON sm_maps.affiliation_to_snomed(fidelity);

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON SCHEMA sm_maps IS 'Tablas de mapeo de afiliaciones a especialidades SNOMED';
COMMENT ON TABLE sm_maps.affiliation_to_snomed IS 'Mapeo de patrones de afiliación a especialidades SNOMED';
COMMENT ON COLUMN sm_maps.affiliation_to_snomed.affiliation_pattern IS 'Texto de afiliación que coincide con una especialidad';
COMMENT ON COLUMN sm_maps.affiliation_to_snomed.pattern_type IS 'Tipo de coincidencia: exact, contains, prefix, suffix';
COMMENT ON COLUMN sm_maps.affiliation_to_snomed.fidelity IS 'Cómo se encontró: snomed=nombre oficial, simplified=nombre simplificado';
