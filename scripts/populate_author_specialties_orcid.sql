-- ============================================================================
-- Poblar especialidades de autores con ORCID
-- Usando afiliaciones como fuente + sinónimos de especialidades
-- ============================================================================

-- Vaciar tabla existente
TRUNCATE sm_result.author_specialties;

-- Insertar especialidades detectadas en afiliaciones de autores con ORCID
-- Buscamos por: name_en, name_es Y sinónimos
INSERT INTO sm_result.author_specialties (author_name, author_orcid, snomed_code, confidence, article_count)
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
    SELECT DISTINCT
        ao.display_name as author_name,
        ao.author_orcid,
        st.snomed_code,
        pa.pubmed_id
    FROM sm_result.authors_orcid ao
    JOIN raw.pubmed_authors pa ON ao.author_orcid = pa.author_orcid
    CROSS JOIN specialty_search_terms st
    WHERE pa.affiliation IS NOT NULL
      AND st.search_term IS NOT NULL
      AND st.search_term != ''
      AND pa.affiliation ILIKE '%' || st.search_term || '%'
)
-- Agrupar por autor y especialidad, contando artículos
SELECT
    author_name,
    author_orcid,
    snomed_code,
    1.0 as confidence,
    COUNT(DISTINCT pubmed_id) as article_count
FROM author_specialty_matches
GROUP BY author_name, author_orcid, snomed_code;

-- Estadísticas
SELECT '=== RESUMEN ===' as info;

SELECT
    COUNT(DISTINCT author_orcid) as autores_con_especialidad,
    COUNT(*) as total_asignaciones,
    COUNT(DISTINCT snomed_code) as especialidades_distintas
FROM sm_result.author_specialties;

SELECT
    (SELECT COUNT(*) FROM sm_result.authors_orcid) as total_autores_orcid,
    COUNT(DISTINCT author_orcid) as autores_con_especialidad,
    ROUND(100.0 * COUNT(DISTINCT author_orcid) / (SELECT COUNT(*) FROM sm_result.authors_orcid), 1) as porcentaje
FROM sm_result.author_specialties;

SELECT '=== TOP 10 ESPECIALIDADES ===' as info;

SELECT
    ss.name_es as especialidad,
    COUNT(DISTINCT asp.author_orcid) as autores
FROM sm_result.author_specialties asp
JOIN vocab.snomed_specialties ss ON asp.snomed_code = ss.snomed_code
GROUP BY ss.snomed_code, ss.name_es
ORDER BY autores DESC
LIMIT 10;

SELECT '=== AUTORES CON MÁS ESPECIALIDADES ===' as info;

SELECT
    author_name,
    author_orcid,
    COUNT(*) as num_especialidades
FROM sm_result.author_specialties
GROUP BY author_name, author_orcid
HAVING COUNT(*) > 1
ORDER BY num_especialidades DESC
LIMIT 10;
