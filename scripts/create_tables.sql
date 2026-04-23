-- ============================================================================
-- Script de creación de tablas para el sistema PubMed
-- Versión: 6.0 - Organizado por schemas
-- Schema: raw (datos brutos de PubMed)
-- ============================================================================

-- Crear schema si no existe
CREATE SCHEMA IF NOT EXISTS raw;

-- Eliminar tablas existentes (si existen)
DROP TABLE IF EXISTS raw.pubmed_authors CASCADE;
DROP TABLE IF EXISTS raw.pubmed_articles CASCADE;

-- ============================================================================
-- Tabla: raw.pubmed_articles
-- Descripción: Almacena información de artículos científicos de PubMed
-- ============================================================================
CREATE TABLE raw.pubmed_articles (
    pubmed_id INTEGER PRIMARY KEY,                    -- ID único del artículo en PubMed
    article_title TEXT,                               -- Título completo del artículo
    article_abstract TEXT,                            -- Resumen/Abstract del artículo
    journal_name VARCHAR(500),                        -- Nombre de la revista científica
    journal_issn VARCHAR(50),                         -- ISSN de la revista
    publication_date DATE,                            -- Fecha de publicación
    article_doi VARCHAR(255),                         -- Digital Object Identifier
    publication_types TEXT,                           -- Tipos de publicación (separados por ;)
    mesh_terms TEXT,                                  -- Términos MeSH (vocabulario controlado NLM)
    author_keywords TEXT,                             -- Palabras clave definidas por el autor
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Tabla: raw.pubmed_authors
-- Descripción: Autores de cada artículo (1 fila por autor por artículo)
-- ============================================================================
CREATE TABLE raw.pubmed_authors (
    sm_author_id SERIAL PRIMARY KEY,
    pubmed_id INTEGER NOT NULL REFERENCES raw.pubmed_articles(pubmed_id) ON DELETE CASCADE,
    author_name VARCHAR(500) NOT NULL,                -- Nombre completo: "Apellido, Nombre"
    author_position INTEGER,                          -- Posición del autor (1=primer autor)
    author_orcid VARCHAR(50),                         -- ORCID del autor
    author_email VARCHAR(255),                        -- Email del autor (raro en PubMed)
    affiliation TEXT,                                 -- Texto completo de afiliación española
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Índices para optimizar consultas
-- ============================================================================
CREATE INDEX idx_pubmed_authors_pubmed ON raw.pubmed_authors(pubmed_id);
CREATE INDEX idx_pubmed_authors_name ON raw.pubmed_authors(author_name);
CREATE INDEX idx_pubmed_authors_orcid ON raw.pubmed_authors(author_orcid);
CREATE INDEX idx_pubmed_articles_date ON raw.pubmed_articles(publication_date);
CREATE INDEX idx_pubmed_articles_doi ON raw.pubmed_articles(article_doi);
CREATE INDEX idx_pubmed_articles_issn ON raw.pubmed_articles(journal_issn);

-- ============================================================================
-- Comentarios
-- ============================================================================
COMMENT ON SCHEMA raw IS 'Datos brutos importados de PubMed';
COMMENT ON TABLE raw.pubmed_articles IS 'Artículos científicos de PubMed';
COMMENT ON TABLE raw.pubmed_authors IS 'Autores de cada artículo';

COMMENT ON COLUMN raw.pubmed_articles.pubmed_id IS 'ID único del artículo en PubMed';
COMMENT ON COLUMN raw.pubmed_articles.article_title IS 'Título completo del artículo';
COMMENT ON COLUMN raw.pubmed_articles.article_abstract IS 'Resumen/Abstract del artículo';
COMMENT ON COLUMN raw.pubmed_articles.journal_name IS 'Nombre de la revista científica';
COMMENT ON COLUMN raw.pubmed_articles.journal_issn IS 'ISSN de la revista';
COMMENT ON COLUMN raw.pubmed_articles.publication_date IS 'Fecha de publicación';
COMMENT ON COLUMN raw.pubmed_articles.article_doi IS 'Digital Object Identifier';
COMMENT ON COLUMN raw.pubmed_articles.publication_types IS 'Tipos de publicación (ej: Journal Article; Review)';
COMMENT ON COLUMN raw.pubmed_articles.mesh_terms IS 'Términos MeSH (vocabulario controlado NLM)';
COMMENT ON COLUMN raw.pubmed_articles.author_keywords IS 'Palabras clave definidas por el autor';

COMMENT ON COLUMN raw.pubmed_authors.author_name IS 'Nombre completo: "Apellido, Nombre"';
COMMENT ON COLUMN raw.pubmed_authors.author_position IS 'Posición del autor (1=primer autor)';
COMMENT ON COLUMN raw.pubmed_authors.author_orcid IS 'ORCID del autor (ej: 0000-0001-2345-6789)';
COMMENT ON COLUMN raw.pubmed_authors.author_email IS 'Email del autor (raro en PubMed)';
COMMENT ON COLUMN raw.pubmed_authors.affiliation IS 'Texto completo de afiliación española';

-- ============================================================================
-- Fin del script
-- ============================================================================
