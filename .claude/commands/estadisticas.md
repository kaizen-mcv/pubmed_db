# Estadísticas de la Base de Datos

Muestra estadísticas de la base de datos PubMed.

## Ejecuta estas consultas SQL

```bash
PGPASSWORD='REDACTED_PWD' psql -h localhost -U pubmed_user -d pubmed_db << 'EOF'

-- Resumen general
SELECT
    (SELECT COUNT(*) FROM articles) as total_articulos,
    (SELECT COUNT(*) FROM article_authors) as total_autores_espanoles,
    (SELECT COUNT(DISTINCT author_orcid) FROM article_authors WHERE author_orcid IS NOT NULL) as autores_con_orcid;

-- Top 10 revistas
SELECT journal_name, COUNT(*) as articulos
FROM articles
WHERE journal_name IS NOT NULL
GROUP BY journal_name
ORDER BY articulos DESC
LIMIT 10;

-- Tipos de publicación
SELECT publication_types, COUNT(*) as total
FROM articles
WHERE publication_types IS NOT NULL
GROUP BY publication_types
ORDER BY total DESC
LIMIT 10;

-- Autores más prolíficos (con ORCID)
SELECT author_name, author_orcid, COUNT(*) as articulos
FROM article_authors
WHERE author_orcid IS NOT NULL
GROUP BY author_name, author_orcid
ORDER BY articulos DESC
LIMIT 10;

EOF
```

Muestra los resultados al usuario de forma clara.
