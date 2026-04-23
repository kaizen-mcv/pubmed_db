-- ============================================================================
-- Tablas de Autores Únicos
-- Schema: sm_result (resultados finales)
--
-- Este script crea dos tablas para autores únicos:
-- 1. authors_orcid: Solo autores con ORCID (100% fiable)
-- 2. authors_norm: Todos los autores por nombre normalizado
--
-- Documentación: docs/deduplicacion_autores.md
-- ============================================================================

-- ============================================================================
-- TABLA 1: sm_result.authors_orcid
-- Autores identificados únicamente por ORCID (máxima fiabilidad)
-- Registros esperados: ~105,616
-- ============================================================================

DROP TABLE IF EXISTS sm_result.authors_orcid CASCADE;

CREATE TABLE sm_result.authors_orcid (
    sm_author_id SERIAL PRIMARY KEY,

    -- Identificación (ORCID es la clave única)
    author_orcid VARCHAR(50) NOT NULL UNIQUE,  -- ORCID (identificador único y fiable)
    display_name VARCHAR(500) NOT NULL,        -- Nombre preferido para mostrar
    canonical_name VARCHAR(500) NOT NULL,      -- Nombre normalizado (lowercase, sin acentos)

    -- Variantes de nombre detectadas
    name_variants TEXT[],                      -- Array con todas las variantes del nombre

    -- Estadísticas agregadas
    article_count INTEGER DEFAULT 0,           -- Número de artículos del autor
    first_publication DATE,                    -- Fecha de primera publicación
    last_publication DATE,                     -- Fecha de última publicación

    -- Metadatos
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para búsquedas
CREATE INDEX idx_authors_orcid_canonical ON sm_result.authors_orcid(canonical_name);
CREATE INDEX idx_authors_orcid_display ON sm_result.authors_orcid(display_name);
CREATE INDEX idx_authors_orcid_canonical_pattern ON sm_result.authors_orcid(canonical_name varchar_pattern_ops);
CREATE INDEX idx_authors_orcid_articles ON sm_result.authors_orcid(article_count DESC);

-- Comentarios
COMMENT ON TABLE sm_result.authors_orcid IS 'Autores únicos identificados por ORCID (100% fiabilidad)';
COMMENT ON COLUMN sm_result.authors_orcid.author_orcid IS 'ORCID del autor - identificador único universal';
COMMENT ON COLUMN sm_result.authors_orcid.display_name IS 'Nombre preferido para mostrar (el más completo con acentos)';
COMMENT ON COLUMN sm_result.authors_orcid.canonical_name IS 'Nombre normalizado para búsquedas (lowercase, sin acentos, sin guiones)';
COMMENT ON COLUMN sm_result.authors_orcid.name_variants IS 'Array con todas las variantes del nombre detectadas en PubMed';


-- ============================================================================
-- TABLA 2: sm_result.authors_norm
-- Todos los autores identificados por nombre normalizado
-- Incluye tanto los que tienen ORCID como los que no
-- Registros esperados: ~500,000-525,000
-- ============================================================================

DROP TABLE IF EXISTS sm_result.authors_norm CASCADE;

CREATE TABLE sm_result.authors_norm (
    sm_author_id SERIAL PRIMARY KEY,

    -- Identificación (nombre normalizado es la clave)
    canonical_name VARCHAR(500) NOT NULL UNIQUE, -- Nombre normalizado (clave única)
    display_name VARCHAR(500) NOT NULL,          -- Nombre preferido para mostrar

    -- Referencia a ORCID si existe
    author_orcid VARCHAR(50),                    -- ORCID si se conoce (puede ser NULL)
    orcid_author_id INTEGER REFERENCES sm_result.authors_orcid(sm_author_id),

    -- Variantes de nombre
    name_variants TEXT[],                        -- Array con todas las variantes

    -- Confianza de identificación
    confidence DECIMAL(3,2) DEFAULT 0.7,         -- 1.0=tiene ORCID, 0.7=solo normalizado

    -- Estadísticas agregadas
    article_count INTEGER DEFAULT 0,             -- Número de artículos del autor
    first_publication DATE,                      -- Fecha de primera publicación
    last_publication DATE,                       -- Fecha de última publicación

    -- Metadatos
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para búsquedas
CREATE INDEX idx_authors_norm_display ON sm_result.authors_norm(display_name);
CREATE INDEX idx_authors_norm_display_pattern ON sm_result.authors_norm(display_name varchar_pattern_ops);
CREATE INDEX idx_authors_norm_orcid ON sm_result.authors_norm(author_orcid) WHERE author_orcid IS NOT NULL;
CREATE INDEX idx_authors_norm_confidence ON sm_result.authors_norm(confidence DESC);
CREATE INDEX idx_authors_norm_articles ON sm_result.authors_norm(article_count DESC);
CREATE INDEX idx_authors_norm_orcid_ref ON sm_result.authors_norm(orcid_author_id) WHERE orcid_author_id IS NOT NULL;

-- Comentarios
COMMENT ON TABLE sm_result.authors_norm IS 'Todos los autores únicos identificados por nombre normalizado';
COMMENT ON COLUMN sm_result.authors_norm.canonical_name IS 'Nombre normalizado - clave única (lowercase, sin acentos)';
COMMENT ON COLUMN sm_result.authors_norm.display_name IS 'Nombre preferido para mostrar';
COMMENT ON COLUMN sm_result.authors_norm.author_orcid IS 'ORCID del autor si se conoce';
COMMENT ON COLUMN sm_result.authors_norm.orcid_author_id IS 'FK a authors_orcid para autores con ORCID';
COMMENT ON COLUMN sm_result.authors_norm.confidence IS 'Confianza de identificación: 1.0=ORCID, 0.7=solo nombre';


-- ============================================================================
-- VISTAS ÚTILES
-- ============================================================================

-- Vista: Autores con sus publicaciones (simplificada)
CREATE OR REPLACE VIEW sm_result.v_authors_summary AS
SELECT
    an.sm_author_id,
    an.display_name,
    an.canonical_name,
    an.author_orcid,
    an.confidence,
    an.article_count,
    an.first_publication,
    an.last_publication,
    array_length(an.name_variants, 1) as variant_count,
    CASE
        WHEN an.author_orcid IS NOT NULL THEN 'ORCID identificado'
        ELSE 'Solo nombre normalizado'
    END as identification_method
FROM sm_result.authors_norm an
ORDER BY an.article_count DESC;

COMMENT ON VIEW sm_result.v_authors_summary IS 'Resumen de autores con método de identificación';


-- ============================================================================
-- FUNCIONES ÚTILES
-- ============================================================================

-- Función: Buscar autor por nombre (aproximado)
CREATE OR REPLACE FUNCTION sm_result.search_author(p_name VARCHAR)
RETURNS TABLE (
    sm_author_id INTEGER,
    display_name VARCHAR,
    canonical_name VARCHAR,
    author_orcid VARCHAR,
    article_count INTEGER,
    confidence DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        an.sm_author_id,
        an.display_name,
        an.canonical_name,
        an.author_orcid,
        an.article_count,
        an.confidence
    FROM sm_result.authors_norm an
    WHERE an.canonical_name ILIKE '%' || lower(p_name) || '%'
       OR an.display_name ILIKE '%' || p_name || '%'
    ORDER BY an.article_count DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sm_result.search_author IS 'Busca autores por nombre (aproximado)';


-- Función: Obtener variantes de un autor
CREATE OR REPLACE FUNCTION sm_result.get_author_variants(p_author_id INTEGER)
RETURNS TABLE (
    variant VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT unnest(an.name_variants)::VARCHAR
    FROM sm_result.authors_norm an
    WHERE an.sm_author_id = p_author_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sm_result.get_author_variants IS 'Obtiene todas las variantes de nombre de un autor';


-- ============================================================================
-- CONSULTAS DE EJEMPLO
-- ============================================================================

-- Buscar autor por nombre
-- SELECT * FROM sm_result.search_author('García');

-- Ver autores más prolíficos con ORCID
-- SELECT display_name, author_orcid, article_count
-- FROM sm_result.authors_orcid
-- ORDER BY article_count DESC
-- LIMIT 20;

-- Ver autores con más variantes de nombre
-- SELECT display_name, author_orcid, array_length(name_variants, 1) as variants
-- FROM sm_result.authors_norm
-- ORDER BY array_length(name_variants, 1) DESC
-- LIMIT 20;

-- Comparar estadísticas de las dos tablas
-- SELECT
--     'authors_orcid' as tabla,
--     COUNT(*) as registros,
--     AVG(article_count)::numeric(10,2) as avg_articles
-- FROM sm_result.authors_orcid
-- UNION ALL
-- SELECT
--     'authors_norm' as tabla,
--     COUNT(*) as registros,
--     AVG(article_count)::numeric(10,2) as avg_articles
-- FROM sm_result.authors_norm;
