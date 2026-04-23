-- ============================================================================
-- Unique Authors Tables
-- Schema: sm_result (final results)
--
-- This script creates two tables for unique authors:
-- 1. authors_orcid: Only authors with ORCID (100% reliable)
-- 2. authors_norm: All authors by normalized name
--
-- Documentation: docs/deduplicacion_autores.md
-- ============================================================================

-- ============================================================================
-- TABLE 1: sm_result.authors_orcid
-- Authors identified only by ORCID (maximum reliability)
-- Expected rows: ~105,616
-- ============================================================================

DROP TABLE IF EXISTS sm_result.authors_orcid CASCADE;

CREATE TABLE sm_result.authors_orcid (
    sm_author_id SERIAL PRIMARY KEY,

    -- Identification (ORCID is the unique key)
    author_orcid VARCHAR(50) NOT NULL UNIQUE,  -- ORCID (unique and reliable identifier)
    display_name VARCHAR(500) NOT NULL,        -- Preferred display name
    canonical_name VARCHAR(500) NOT NULL,      -- Normalized name (lowercase, no accents)

    -- Detected name variants
    name_variants TEXT[],                      -- Array with all name variants

    -- Aggregated statistics
    article_count INTEGER DEFAULT 0,           -- Number of articles by the author
    first_publication DATE,                    -- First publication date
    last_publication DATE,                     -- Last publication date

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for lookups
CREATE INDEX idx_authors_orcid_canonical ON sm_result.authors_orcid(canonical_name);
CREATE INDEX idx_authors_orcid_display ON sm_result.authors_orcid(display_name);
CREATE INDEX idx_authors_orcid_canonical_pattern ON sm_result.authors_orcid(canonical_name varchar_pattern_ops);
CREATE INDEX idx_authors_orcid_articles ON sm_result.authors_orcid(article_count DESC);

-- Comments
COMMENT ON TABLE sm_result.authors_orcid IS 'Unique authors identified by ORCID (100% reliability)';
COMMENT ON COLUMN sm_result.authors_orcid.author_orcid IS 'Author ORCID - universal unique identifier';
COMMENT ON COLUMN sm_result.authors_orcid.display_name IS 'Preferred display name (the most complete one with accents)';
COMMENT ON COLUMN sm_result.authors_orcid.canonical_name IS 'Normalized name for lookups (lowercase, no accents, no hyphens)';
COMMENT ON COLUMN sm_result.authors_orcid.name_variants IS 'Array with all name variants detected in PubMed';


-- ============================================================================
-- TABLE 2: sm_result.authors_norm
-- All authors identified by normalized name
-- Includes both those with ORCID and those without
-- Expected rows: ~500,000-525,000
-- ============================================================================

DROP TABLE IF EXISTS sm_result.authors_norm CASCADE;

CREATE TABLE sm_result.authors_norm (
    sm_author_id SERIAL PRIMARY KEY,

    -- Identification (normalized name is the key)
    canonical_name VARCHAR(500) NOT NULL UNIQUE, -- Normalized name (unique key)
    display_name VARCHAR(500) NOT NULL,          -- Preferred display name

    -- Reference to ORCID if it exists
    author_orcid VARCHAR(50),                    -- ORCID if known (can be NULL)
    orcid_author_id INTEGER REFERENCES sm_result.authors_orcid(sm_author_id),

    -- Name variants
    name_variants TEXT[],                        -- Array with all variants

    -- Identification confidence
    confidence DECIMAL(3,2) DEFAULT 0.7,         -- 1.0=has ORCID, 0.7=normalized only

    -- Aggregated statistics
    article_count INTEGER DEFAULT 0,             -- Number of articles by the author
    first_publication DATE,                      -- First publication date
    last_publication DATE,                       -- Last publication date

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for lookups
CREATE INDEX idx_authors_norm_display ON sm_result.authors_norm(display_name);
CREATE INDEX idx_authors_norm_display_pattern ON sm_result.authors_norm(display_name varchar_pattern_ops);
CREATE INDEX idx_authors_norm_orcid ON sm_result.authors_norm(author_orcid) WHERE author_orcid IS NOT NULL;
CREATE INDEX idx_authors_norm_confidence ON sm_result.authors_norm(confidence DESC);
CREATE INDEX idx_authors_norm_articles ON sm_result.authors_norm(article_count DESC);
CREATE INDEX idx_authors_norm_orcid_ref ON sm_result.authors_norm(orcid_author_id) WHERE orcid_author_id IS NOT NULL;

-- Comments
COMMENT ON TABLE sm_result.authors_norm IS 'All unique authors identified by normalized name';
COMMENT ON COLUMN sm_result.authors_norm.canonical_name IS 'Normalized name - unique key (lowercase, no accents)';
COMMENT ON COLUMN sm_result.authors_norm.display_name IS 'Preferred display name';
COMMENT ON COLUMN sm_result.authors_norm.author_orcid IS 'Author ORCID if known';
COMMENT ON COLUMN sm_result.authors_norm.orcid_author_id IS 'FK to authors_orcid for authors with ORCID';
COMMENT ON COLUMN sm_result.authors_norm.confidence IS 'Identification confidence: 1.0=ORCID, 0.7=name only';


-- ============================================================================
-- USEFUL VIEWS
-- ============================================================================

-- View: Authors with their publications (simplified)
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
        WHEN an.author_orcid IS NOT NULL THEN 'ORCID identified'
        ELSE 'Normalized name only'
    END as identification_method
FROM sm_result.authors_norm an
ORDER BY an.article_count DESC;

COMMENT ON VIEW sm_result.v_authors_summary IS 'Author summary with identification method';


-- ============================================================================
-- USEFUL FUNCTIONS
-- ============================================================================

-- Function: Search author by name (approximate)
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

COMMENT ON FUNCTION sm_result.search_author IS 'Search authors by name (approximate)';


-- Function: Get name variants for an author
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

COMMENT ON FUNCTION sm_result.get_author_variants IS 'Returns all name variants for an author';


-- ============================================================================
-- EXAMPLE QUERIES
-- ============================================================================

-- Search author by name
-- SELECT * FROM sm_result.search_author('García');

-- View most prolific authors with ORCID
-- SELECT display_name, author_orcid, article_count
-- FROM sm_result.authors_orcid
-- ORDER BY article_count DESC
-- LIMIT 20;

-- View authors with most name variants
-- SELECT display_name, author_orcid, array_length(name_variants, 1) as variants
-- FROM sm_result.authors_norm
-- ORDER BY array_length(name_variants, 1) DESC
-- LIMIT 20;

-- Compare statistics of the two tables
-- SELECT
--     'authors_orcid' as table_name,
--     COUNT(*) as row_count,
--     AVG(article_count)::numeric(10,2) as avg_articles
-- FROM sm_result.authors_orcid
-- UNION ALL
-- SELECT
--     'authors_norm' as table_name,
--     COUNT(*) as row_count,
--     AVG(article_count)::numeric(10,2) as avg_articles
-- FROM sm_result.authors_norm;
