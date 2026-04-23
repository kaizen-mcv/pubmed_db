-- ============================================================================
-- Poblar especialidades de autores normalizados
-- Usando afiliaciones como fuente + sinónimos de especialidades
-- ============================================================================

-- Vaciar tabla existente
TRUNCATE sm_result.authors_norm_specialties;

-- Insertar especialidades detectadas en afiliaciones
-- Buscamos por: name_en, name_es Y sinónimos
INSERT INTO sm_result.authors_norm_specialties (sm_author_id, canonical_name, display_name, snomed_code, confidence, article_count)
WITH specialty_search_terms AS (
    -- Generar todos los términos de búsqueda por especialidad
    -- Incluye: name_en, name_es, y cada sinónimo separado por ;
    SELECT snomed_code, name_en as search_term FROM vocab.snomed_specialties WHERE name_en IS NOT NULL
    UNION
    SELECT snomed_code, name_es as search_term FROM vocab.snomed_specialties WHERE name_es IS NOT NULL
    UNION
    SELECT snomed_code, trim(regexp_split_to_table(synonyms, ';')) as search_term
    FROM vocab.snomed_specialties WHERE synonyms IS NOT NULL AND synonyms != ''
),
author_specialty_matches AS (
    -- Encontrar todas las coincidencias autor-especialidad
    -- Usamos unnest para expandir el array de variantes de nombre
    SELECT DISTINCT
        an.sm_author_id,
        an.canonical_name,
        an.display_name,
        st.snomed_code,
        pa.pubmed_id
    FROM sm_result.authors_norm an
    CROSS JOIN LATERAL unnest(an.name_variants) as variant(name)
    JOIN raw.pubmed_authors pa ON pa.author_name = variant.name
    CROSS JOIN specialty_search_terms st
    WHERE pa.affiliation IS NOT NULL
      AND st.search_term IS NOT NULL
      AND st.search_term != ''
      AND pa.affiliation ILIKE '%' || st.search_term || '%'
)
-- Agrupar por autor y especialidad, contando artículos
SELECT
    sm_author_id,
    canonical_name,
    display_name,
    snomed_code,
    1.0 as confidence,
    COUNT(DISTINCT pubmed_id) as article_count
FROM author_specialty_matches
GROUP BY sm_author_id, canonical_name, display_name, snomed_code;

-- ============================================================================
-- Estadísticas
-- ============================================================================

SELECT '=== RESUMEN authors_norm_specialties ===' as info;

SELECT
    COUNT(DISTINCT sm_author_id) as autores_con_especialidad,
    COUNT(*) as total_asignaciones,
    COUNT(DISTINCT snomed_code) as especialidades_distintas
FROM sm_result.authors_norm_specialties;

SELECT
    (SELECT COUNT(*) FROM sm_result.authors_norm) as total_autores_norm,
    COUNT(DISTINCT sm_author_id) as autores_con_especialidad,
    ROUND(100.0 * COUNT(DISTINCT sm_author_id) / (SELECT COUNT(*) FROM sm_result.authors_norm), 1) as porcentaje
FROM sm_result.authors_norm_specialties;

SELECT '=== TOP 10 ESPECIALIDADES ===' as info;

SELECT
    ss.name_es as especialidad,
    COUNT(DISTINCT ans.sm_author_id) as autores
FROM sm_result.authors_norm_specialties ans
JOIN vocab.snomed_specialties ss ON ans.snomed_code = ss.snomed_code
GROUP BY ss.snomed_code, ss.name_es
ORDER BY autores DESC
LIMIT 10;

SELECT '=== AUTORES CON MÁS ESPECIALIDADES ===' as info;

SELECT
    display_name,
    COUNT(*) as num_especialidades
FROM sm_result.authors_norm_specialties
GROUP BY sm_author_id, display_name
HAVING COUNT(*) > 1
ORDER BY num_especialidades DESC
LIMIT 10;

-- ============================================================================
-- Comparación con autores ORCID
-- ============================================================================

SELECT '=== COMPARACIÓN ORCID vs NORM ===' as info;

SELECT
    'authors_orcid' as tabla,
    COUNT(DISTINCT author_orcid) as autores_con_especialidad,
    (SELECT COUNT(*) FROM sm_result.authors_orcid) as total_autores,
    ROUND(100.0 * COUNT(DISTINCT author_orcid) / (SELECT COUNT(*) FROM sm_result.authors_orcid), 1) as porcentaje
FROM sm_result.author_specialties

UNION ALL

SELECT
    'authors_norm' as tabla,
    COUNT(DISTINCT sm_author_id) as autores_con_especialidad,
    (SELECT COUNT(*) FROM sm_result.authors_norm) as total_autores,
    ROUND(100.0 * COUNT(DISTINCT sm_author_id) / (SELECT COUNT(*) FROM sm_result.authors_norm), 1) as porcentaje
FROM sm_result.authors_norm_specialties;
