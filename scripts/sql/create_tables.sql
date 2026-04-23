-- ============================================================================
-- Table creation script for the PubMed system
-- Version: 6.0 - Organized by schemas
-- Schema: raw (raw PubMed data)
-- ============================================================================

-- Create schema if it does not exist
CREATE SCHEMA IF NOT EXISTS raw;

-- Drop existing tables (if they exist)
DROP TABLE IF EXISTS raw.pubmed_authors CASCADE;
DROP TABLE IF EXISTS raw.pubmed_articles CASCADE;

-- ============================================================================
-- Table: raw.pubmed_articles
-- Description: Stores PubMed scientific article information
-- ============================================================================
CREATE TABLE raw.pubmed_articles (
    pubmed_id INTEGER PRIMARY KEY,                    -- Unique article ID in PubMed
    article_title TEXT,                               -- Full article title
    article_abstract TEXT,                            -- Article abstract/summary
    journal_name VARCHAR(500),                        -- Scientific journal name
    journal_issn VARCHAR(50),                         -- Journal ISSN
    publication_date DATE,                            -- Publication date
    article_doi VARCHAR(255),                         -- Digital Object Identifier
    publication_types TEXT,                           -- Publication types (separated by ;)
    mesh_terms TEXT,                                  -- MeSH terms (NLM controlled vocabulary)
    author_keywords TEXT,                             -- Author-defined keywords
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Table: raw.pubmed_authors
-- Description: Authors of each article (1 row per author per article)
-- ============================================================================
CREATE TABLE raw.pubmed_authors (
    sm_author_id SERIAL PRIMARY KEY,
    pubmed_id INTEGER NOT NULL REFERENCES raw.pubmed_articles(pubmed_id) ON DELETE CASCADE,
    author_name VARCHAR(500) NOT NULL,                -- Full name: "Lastname, Firstname"
    author_position INTEGER,                          -- Author position (1=first author)
    author_orcid VARCHAR(50),                         -- Author ORCID
    author_email VARCHAR(255),                        -- Author email (rare in PubMed)
    affiliation TEXT,                                 -- Full Spanish affiliation text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Indexes to optimize queries
-- ============================================================================
CREATE INDEX idx_pubmed_authors_pubmed ON raw.pubmed_authors(pubmed_id);
CREATE INDEX idx_pubmed_authors_name ON raw.pubmed_authors(author_name);
CREATE INDEX idx_pubmed_authors_orcid ON raw.pubmed_authors(author_orcid);
CREATE INDEX idx_pubmed_articles_date ON raw.pubmed_articles(publication_date);
CREATE INDEX idx_pubmed_articles_doi ON raw.pubmed_articles(article_doi);
CREATE INDEX idx_pubmed_articles_issn ON raw.pubmed_articles(journal_issn);

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON SCHEMA raw IS 'Raw data imported from PubMed';
COMMENT ON TABLE raw.pubmed_articles IS 'PubMed scientific articles';
COMMENT ON TABLE raw.pubmed_authors IS 'Authors of each article';

COMMENT ON COLUMN raw.pubmed_articles.pubmed_id IS 'Unique article ID in PubMed';
COMMENT ON COLUMN raw.pubmed_articles.article_title IS 'Full article title';
COMMENT ON COLUMN raw.pubmed_articles.article_abstract IS 'Article abstract/summary';
COMMENT ON COLUMN raw.pubmed_articles.journal_name IS 'Scientific journal name';
COMMENT ON COLUMN raw.pubmed_articles.journal_issn IS 'Journal ISSN';
COMMENT ON COLUMN raw.pubmed_articles.publication_date IS 'Publication date';
COMMENT ON COLUMN raw.pubmed_articles.article_doi IS 'Digital Object Identifier';
COMMENT ON COLUMN raw.pubmed_articles.publication_types IS 'Publication types (e.g. Journal Article; Review)';
COMMENT ON COLUMN raw.pubmed_articles.mesh_terms IS 'MeSH terms (NLM controlled vocabulary)';
COMMENT ON COLUMN raw.pubmed_articles.author_keywords IS 'Author-defined keywords';

COMMENT ON COLUMN raw.pubmed_authors.author_name IS 'Full name: "Lastname, Firstname"';
COMMENT ON COLUMN raw.pubmed_authors.author_position IS 'Author position (1=first author)';
COMMENT ON COLUMN raw.pubmed_authors.author_orcid IS 'Author ORCID (e.g. 0000-0001-2345-6789)';
COMMENT ON COLUMN raw.pubmed_authors.author_email IS 'Author email (rare in PubMed)';
COMMENT ON COLUMN raw.pubmed_authors.affiliation IS 'Full Spanish affiliation text';

-- ============================================================================
-- End of script
-- ============================================================================
