-- ============================================================================
-- Populate specialties of normalized authors
-- Using affiliations as source + specialty synonyms
-- ============================================================================

-- Truncate existing table
TRUNCATE sm_result.authors_norm_specialties;

-- Insert specialties detected in affiliations
-- Search by: name_en, name_es AND synonyms
INSERT INTO sm_result.authors_norm_specialties (sm_author_id, canonical_name, display_name, snomed_code, confidence, article_count)
WITH specialty_search_terms AS (
    -- Generate all search terms per specialty
    -- Includes: name_en, name_es, and each synonym separated by ;
    SELECT snomed_code, name_en as search_term FROM vocab.snomed_specialties WHERE name_en IS NOT NULL
    UNION
    SELECT snomed_code, name_es as search_term FROM vocab.snomed_specialties WHERE name_es IS NOT NULL
    UNION
    SELECT snomed_code, trim(regexp_split_to_table(synonyms, ';')) as search_term
    FROM vocab.snomed_specialties WHERE synonyms IS NOT NULL AND synonyms != ''
),
author_specialty_matches AS (
    -- Find all author-specialty matches
    -- Use unnest to expand the name_variants array
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
-- Group by author and specialty, counting articles
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
-- Statistics
-- ============================================================================

SELECT '=== SUMMARY authors_norm_specialties ===' as info;

SELECT
    COUNT(DISTINCT sm_author_id) as authors_with_specialty,
    COUNT(*) as total_assignments,
    COUNT(DISTINCT snomed_code) as distinct_specialties
FROM sm_result.authors_norm_specialties;

SELECT
    (SELECT COUNT(*) FROM sm_result.authors_norm) as total_authors_norm,
    COUNT(DISTINCT sm_author_id) as authors_with_specialty,
    ROUND(100.0 * COUNT(DISTINCT sm_author_id) / (SELECT COUNT(*) FROM sm_result.authors_norm), 1) as percentage
FROM sm_result.authors_norm_specialties;

SELECT '=== TOP 10 SPECIALTIES ===' as info;

SELECT
    ss.name_es as specialty,
    COUNT(DISTINCT ans.sm_author_id) as authors
FROM sm_result.authors_norm_specialties ans
JOIN vocab.snomed_specialties ss ON ans.snomed_code = ss.snomed_code
GROUP BY ss.snomed_code, ss.name_es
ORDER BY authors DESC
LIMIT 10;

SELECT '=== AUTHORS WITH MOST SPECIALTIES ===' as info;

SELECT
    display_name,
    COUNT(*) as num_specialties
FROM sm_result.authors_norm_specialties
GROUP BY sm_author_id, display_name
HAVING COUNT(*) > 1
ORDER BY num_specialties DESC
LIMIT 10;

-- ============================================================================
-- Comparison with ORCID authors
-- ============================================================================

SELECT '=== COMPARISON ORCID vs NORM ===' as info;

SELECT
    'authors_orcid' as table_name,
    COUNT(DISTINCT author_orcid) as authors_with_specialty,
    (SELECT COUNT(*) FROM sm_result.authors_orcid) as total_authors,
    ROUND(100.0 * COUNT(DISTINCT author_orcid) / (SELECT COUNT(*) FROM sm_result.authors_orcid), 1) as percentage
FROM sm_result.author_specialties

UNION ALL

SELECT
    'authors_norm' as table_name,
    COUNT(DISTINCT sm_author_id) as authors_with_specialty,
    (SELECT COUNT(*) FROM sm_result.authors_norm) as total_authors,
    ROUND(100.0 * COUNT(DISTINCT sm_author_id) / (SELECT COUNT(*) FROM sm_result.authors_norm), 1) as percentage
FROM sm_result.authors_norm_specialties;
