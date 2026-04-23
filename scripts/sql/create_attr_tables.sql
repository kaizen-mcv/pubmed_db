-- ============================================================================
-- Normalized attribute tables
-- Extract unique values from raw tables to avoid duplicates
-- Schema: sm_attr (normalized attributes)
-- ============================================================================

-- Create schema if it does not exist
CREATE SCHEMA IF NOT EXISTS sm_attr;

-- ============================================================================
-- Table: sm_attr.journals
-- Unique journals from the articles
-- ============================================================================
DROP TABLE IF EXISTS sm_attr.journals CASCADE;

CREATE TABLE sm_attr.journals (
    sm_journal_id SERIAL PRIMARY KEY,
    journal_issn VARCHAR(50),
    journal_name VARCHAR(500) NOT NULL,
    article_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(journal_issn, journal_name)
);

CREATE INDEX idx_journals_issn ON sm_attr.journals(journal_issn);
CREATE INDEX idx_journals_name ON sm_attr.journals(journal_name);
CREATE INDEX idx_journals_name_pattern ON sm_attr.journals(journal_name varchar_pattern_ops);

COMMENT ON TABLE sm_attr.journals IS 'Unique journals extracted from pubmed_articles';
COMMENT ON COLUMN sm_attr.journals.journal_issn IS 'Journal ISSN';
COMMENT ON COLUMN sm_attr.journals.journal_name IS 'Journal name';
COMMENT ON COLUMN sm_attr.journals.article_count IS 'Number of articles in this journal';

-- Populate journals
INSERT INTO sm_attr.journals (journal_issn, journal_name, article_count)
SELECT
    journal_issn,
    journal_name,
    COUNT(*) as article_count
FROM raw.pubmed_articles
WHERE journal_name IS NOT NULL AND journal_name <> ''
GROUP BY journal_issn, journal_name
ORDER BY article_count DESC;

-- ============================================================================
-- Table: sm_attr.keywords
-- Unique author keywords
-- ============================================================================
DROP TABLE IF EXISTS sm_attr.keywords CASCADE;

CREATE TABLE sm_attr.keywords (
    sm_keyword_id SERIAL PRIMARY KEY,
    keyword_text VARCHAR(500) NOT NULL UNIQUE,
    article_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_keywords_text ON sm_attr.keywords(keyword_text);
CREATE INDEX idx_keywords_text_pattern ON sm_attr.keywords(keyword_text varchar_pattern_ops);

COMMENT ON TABLE sm_attr.keywords IS 'Unique author keywords extracted from pubmed_articles.author_keywords';
COMMENT ON COLUMN sm_attr.keywords.keyword_text IS 'Keyword text (normalized)';
COMMENT ON COLUMN sm_attr.keywords.article_count IS 'Number of articles using this keyword';

-- Populate keywords (filter malformed data)
INSERT INTO sm_attr.keywords (keyword_text, article_count)
SELECT
    TRIM(keyword) as keyword_text,
    COUNT(DISTINCT pubmed_id) as article_count
FROM raw.pubmed_articles,
     LATERAL unnest(string_to_array(author_keywords, ',')) AS keyword
WHERE author_keywords IS NOT NULL
  AND author_keywords <> ''
  AND TRIM(keyword) <> ''
  AND LENGTH(TRIM(keyword)) <= 300
  AND TRIM(keyword) NOT LIKE '%<math%'
  AND TRIM(keyword) NOT LIKE '%xmlns%'
  AND TRIM(keyword) NOT LIKE '%</%'
GROUP BY TRIM(keyword)
ORDER BY article_count DESC;

-- ============================================================================
-- Table: sm_attr.affiliations
-- Unique author affiliations
-- ============================================================================
DROP TABLE IF EXISTS sm_attr.affiliations CASCADE;

CREATE TABLE sm_attr.affiliations (
    sm_affiliation_id SERIAL PRIMARY KEY,
    affiliation_text TEXT NOT NULL UNIQUE,
    author_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_affiliations_text ON sm_attr.affiliations USING gin(to_tsvector('english', affiliation_text));
CREATE INDEX idx_affiliations_author_count ON sm_attr.affiliations(author_count DESC);

COMMENT ON TABLE sm_attr.affiliations IS 'Unique affiliations extracted from pubmed_authors.affiliation';
COMMENT ON COLUMN sm_attr.affiliations.affiliation_text IS 'Full affiliation text';
COMMENT ON COLUMN sm_attr.affiliations.author_count IS 'Number of authors with this affiliation';

-- Populate affiliations
INSERT INTO sm_attr.affiliations (affiliation_text, author_count)
SELECT
    affiliation as affiliation_text,
    COUNT(*) as author_count
FROM raw.pubmed_authors
WHERE affiliation IS NOT NULL
  AND affiliation <> ''
GROUP BY affiliation
ORDER BY author_count DESC;

-- ============================================================================
-- Table: sm_attr.mesh_terms_articles
-- Unique MeSH terms from articles
-- ============================================================================
DROP TABLE IF EXISTS sm_attr.mesh_terms_articles CASCADE;

CREATE TABLE sm_attr.mesh_terms_articles (
    sm_mesh_term_article_id SERIAL PRIMARY KEY,
    mesh_term_text VARCHAR(500) NOT NULL UNIQUE,
    article_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mesh_terms_articles_text ON sm_attr.mesh_terms_articles(mesh_term_text);
CREATE INDEX idx_mesh_terms_articles_pattern ON sm_attr.mesh_terms_articles(mesh_term_text varchar_pattern_ops);
CREATE INDEX idx_mesh_terms_articles_count ON sm_attr.mesh_terms_articles(article_count DESC);

COMMENT ON TABLE sm_attr.mesh_terms_articles IS 'Unique MeSH terms extracted from pubmed_articles.mesh_terms';
COMMENT ON COLUMN sm_attr.mesh_terms_articles.mesh_term_text IS 'MeSH term name';
COMMENT ON COLUMN sm_attr.mesh_terms_articles.article_count IS 'Number of articles that have this MeSH term';

-- Populate mesh_terms_articles
INSERT INTO sm_attr.mesh_terms_articles (mesh_term_text, article_count)
SELECT
    TRIM(mesh_term) as mesh_term_text,
    COUNT(DISTINCT pubmed_id) as article_count
FROM raw.pubmed_articles,
     LATERAL unnest(string_to_array(mesh_terms, ',')) AS mesh_term
WHERE mesh_terms IS NOT NULL
  AND mesh_terms <> ''
  AND TRIM(mesh_term) <> ''
GROUP BY TRIM(mesh_term)
ORDER BY article_count DESC;

-- ============================================================================
-- Final summary
-- ============================================================================
SELECT 'sm_attr.journals' as table_name, COUNT(*) as row_count FROM sm_attr.journals
UNION ALL
SELECT 'sm_attr.keywords', COUNT(*) FROM sm_attr.keywords
UNION ALL
SELECT 'sm_attr.affiliations', COUNT(*) FROM sm_attr.affiliations
UNION ALL
SELECT 'sm_attr.mesh_terms_articles', COUNT(*) FROM sm_attr.mesh_terms_articles
ORDER BY table_name;
