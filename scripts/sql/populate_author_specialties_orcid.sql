-- ============================================================================
-- Populate specialties for authors with ORCID
-- Using affiliations as source + specialty synonyms
-- ============================================================================

-- Truncate existing table
TRUNCATE sm_result.author_specialties;

-- Insert specialties detected in affiliations of ORCID authors
-- Search by: name_en, name_es AND synonyms
INSERT INTO sm_result.author_specialties (author_name, author_orcid, snomed_code, confidence, article_count)
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
-- Group by author and specialty, counting articles
SELECT
    author_name,
    author_orcid,
    snomed_code,
    1.0 as confidence,
    COUNT(DISTINCT pubmed_id) as article_count
FROM author_specialty_matches
GROUP BY author_name, author_orcid, snomed_code;

-- Statistics
SELECT '=== SUMMARY ===' as info;

SELECT
    COUNT(DISTINCT author_orcid) as authors_with_specialty,
    COUNT(*) as total_assignments,
    COUNT(DISTINCT snomed_code) as distinct_specialties
FROM sm_result.author_specialties;

SELECT
    (SELECT COUNT(*) FROM sm_result.authors_orcid) as total_authors_orcid,
    COUNT(DISTINCT author_orcid) as authors_with_specialty,
    ROUND(100.0 * COUNT(DISTINCT author_orcid) / (SELECT COUNT(*) FROM sm_result.authors_orcid), 1) as percentage
FROM sm_result.author_specialties;

SELECT '=== TOP 10 SPECIALTIES ===' as info;

SELECT
    ss.name_es as specialty,
    COUNT(DISTINCT asp.author_orcid) as authors
FROM sm_result.author_specialties asp
JOIN vocab.snomed_specialties ss ON asp.snomed_code = ss.snomed_code
GROUP BY ss.snomed_code, ss.name_es
ORDER BY authors DESC
LIMIT 10;

SELECT '=== AUTHORS WITH MOST SPECIALTIES ===' as info;

SELECT
    author_name,
    author_orcid,
    COUNT(*) as num_specialties
FROM sm_result.author_specialties
GROUP BY author_name, author_orcid
HAVING COUNT(*) > 1
ORDER BY num_specialties DESC
LIMIT 10;
