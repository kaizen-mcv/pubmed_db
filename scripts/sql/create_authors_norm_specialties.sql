-- ============================================================================
-- Tabla de especialidades para autores normalizados (sin ORCID obligatorio)
-- Almacena las especialidades médicas detectadas en afiliaciones
-- Schema: sm_result (resultados finales)
-- ============================================================================

-- Eliminar tabla existente si existe
DROP TABLE IF EXISTS sm_result.authors_norm_specialties CASCADE;

-- Crear tabla authors_norm_specialties
CREATE TABLE sm_result.authors_norm_specialties (
    id SERIAL PRIMARY KEY,
    sm_author_id INTEGER NOT NULL REFERENCES sm_result.authors_norm(sm_author_id),
    canonical_name VARCHAR(500) NOT NULL,       -- Nombre normalizado del autor
    display_name VARCHAR(500) NOT NULL,         -- Nombre para mostrar
    snomed_code VARCHAR(20) NOT NULL REFERENCES vocab.snomed_specialties(snomed_code),
    confidence DECIMAL(4,3) DEFAULT 1.0,        -- Confianza del mapeo (0.000-1.000)
    article_count INTEGER DEFAULT 1,            -- Número de artículos que contribuyen
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Un autor puede tener múltiples especialidades, pero cada combinación es única
    UNIQUE(sm_author_id, snomed_code)
);

-- Índices para búsquedas eficientes
CREATE INDEX idx_authors_norm_spec_author ON sm_result.authors_norm_specialties(sm_author_id);
CREATE INDEX idx_authors_norm_spec_canonical ON sm_result.authors_norm_specialties(canonical_name);
CREATE INDEX idx_authors_norm_spec_snomed ON sm_result.authors_norm_specialties(snomed_code);
CREATE INDEX idx_authors_norm_spec_confidence ON sm_result.authors_norm_specialties(confidence DESC);

-- Índice para búsquedas por nombre (LIKE)
CREATE INDEX idx_authors_norm_spec_canonical_pattern ON sm_result.authors_norm_specialties(canonical_name varchar_pattern_ops);

-- ============================================================================
-- Comentarios de documentación
-- ============================================================================

COMMENT ON TABLE sm_result.authors_norm_specialties IS 'Especialidades médicas inferidas para autores normalizados (todos los autores, con o sin ORCID)';
COMMENT ON COLUMN sm_result.authors_norm_specialties.sm_author_id IS 'Referencia al autor en authors_norm';
COMMENT ON COLUMN sm_result.authors_norm_specialties.canonical_name IS 'Nombre normalizado (lowercase, sin acentos)';
COMMENT ON COLUMN sm_result.authors_norm_specialties.display_name IS 'Nombre preferido para mostrar';
COMMENT ON COLUMN sm_result.authors_norm_specialties.snomed_code IS 'Código SNOMED CT de la especialidad inferida';
COMMENT ON COLUMN sm_result.authors_norm_specialties.confidence IS 'Confianza del mapeo (1.0=match directo en afiliación)';
COMMENT ON COLUMN sm_result.authors_norm_specialties.article_count IS 'Número de artículos del autor que contribuyen a esta especialidad';

-- ============================================================================
-- Vista para consultas con detalles de especialidad
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

COMMENT ON VIEW sm_result.v_authors_norm_specialties_detail IS 'Vista con detalles completos de especialidades por autor normalizado';
