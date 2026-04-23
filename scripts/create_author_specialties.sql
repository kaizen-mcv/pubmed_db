-- ============================================================================
-- Tabla de especialidades inferidas por autor
-- Almacena las especialidades médicas detectadas para cada autor único
-- Schema: sm_result (resultados finales)
--
-- NOTA: Las especialidades se infieren únicamente desde las afiliaciones
-- de los autores, que es el único campo 100% fiable para determinar
-- la especialidad de cada autor individual.
-- ============================================================================

-- Crear schema si no existe
CREATE SCHEMA IF NOT EXISTS sm_result;

-- Eliminar tabla existente
DROP TABLE IF EXISTS sm_result.author_specialties CASCADE;

-- Crear tabla author_specialties
CREATE TABLE sm_result.author_specialties (
    sm_author_specialty_id SERIAL PRIMARY KEY,
    author_name VARCHAR(500) NOT NULL,          -- Nombre del autor (formato "Apellido, Nombre")
    author_orcid VARCHAR(50),                   -- ORCID si está disponible
    snomed_code VARCHAR(20) NOT NULL REFERENCES vocab.snomed_specialties(snomed_code),
    confidence DECIMAL(4,3),                    -- Confianza del mapeo (0.000-1.000)
    article_count INTEGER DEFAULT 1,            -- Número de artículos que contribuyen a esta especialidad
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Un autor puede tener múltiples especialidades, pero cada combinación es única
    UNIQUE(author_name, snomed_code)
);

-- Índices para búsquedas eficientes
CREATE INDEX idx_author_specialties_name ON sm_result.author_specialties(author_name);
CREATE INDEX idx_author_specialties_orcid ON sm_result.author_specialties(author_orcid) WHERE author_orcid IS NOT NULL;
CREATE INDEX idx_author_specialties_snomed ON sm_result.author_specialties(snomed_code);
CREATE INDEX idx_author_specialties_confidence ON sm_result.author_specialties(confidence DESC);

-- Índice para búsquedas por nombre (LIKE)
CREATE INDEX idx_author_specialties_name_pattern ON sm_result.author_specialties(author_name varchar_pattern_ops);

-- ============================================================================
-- Comentarios de documentación
-- ============================================================================

COMMENT ON SCHEMA sm_result IS 'Resultados finales de inferencia de especialidades';
COMMENT ON TABLE sm_result.author_specialties IS 'Especialidades médicas inferidas para cada autor único basándose en sus afiliaciones';
COMMENT ON COLUMN sm_result.author_specialties.author_name IS 'Nombre del autor en formato "Apellido, Nombre"';
COMMENT ON COLUMN sm_result.author_specialties.author_orcid IS 'ORCID del autor si está disponible (permite desambiguación)';
COMMENT ON COLUMN sm_result.author_specialties.snomed_code IS 'Código SNOMED CT de la especialidad inferida';
COMMENT ON COLUMN sm_result.author_specialties.confidence IS 'Confianza del mapeo (1.0=nombre SNOMED oficial, 0.9=nombre simplificado)';
COMMENT ON COLUMN sm_result.author_specialties.article_count IS 'Número de artículos del autor que contribuyen a esta especialidad';
COMMENT ON COLUMN sm_result.author_specialties.last_updated IS 'Última actualización de esta inferencia';

-- ============================================================================
-- Vista para consultas rápidas
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

COMMENT ON VIEW sm_result.v_author_specialties_detail IS 'Vista con detalles completos de especialidades por autor';

-- ============================================================================
-- Función para obtener especialidades de un autor
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

COMMENT ON FUNCTION get_author_specialties IS 'Obtiene las especialidades de un autor por su nombre';

-- ============================================================================
-- Consultas SQL útiles
-- ============================================================================

-- Top autores por especialidad
-- SELECT author_name, confidence, article_count
-- FROM sm_result.author_specialties
-- WHERE snomed_code = '394579002'  -- Cardiología
-- ORDER BY confidence DESC, article_count DESC
-- LIMIT 20;

-- Distribución de especialidades
-- SELECT s.name_en, COUNT(*) as autores, AVG(a.confidence) as confianza_media
-- FROM sm_result.author_specialties a
-- JOIN vocab.snomed_specialties s ON a.snomed_code = s.snomed_code
-- GROUP BY s.snomed_code, s.name_en
-- ORDER BY autores DESC;

-- Autores con múltiples especialidades
-- SELECT author_name, COUNT(*) as num_especialidades
-- FROM sm_result.author_specialties
-- GROUP BY author_name
-- HAVING COUNT(*) > 1
-- ORDER BY num_especialidades DESC;
