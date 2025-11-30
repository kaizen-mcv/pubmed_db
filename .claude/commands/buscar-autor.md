# Buscar artículos de un autor

Busca artículos de un autor específico en la base de datos.

## Parámetros

El usuario debe proporcionar el nombre o parte del nombre del autor.

## Consulta SQL

```bash
PGPASSWORD='REDACTED_PWD' psql -h localhost -U pubmed_user -d pubmed_db << EOF

-- Buscar autor
SELECT
    aa.author_name,
    aa.author_orcid,
    aa.author_position,
    aa.affiliation,
    a.article_title,
    a.journal_name,
    a.publication_date
FROM article_authors aa
JOIN articles a ON aa.pubmed_id = a.pubmed_id
WHERE aa.author_name ILIKE '%$ARGUMENTS%'
ORDER BY a.publication_date DESC
LIMIT 20;

EOF
```

Muestra los resultados al usuario de forma clara, incluyendo:
- Nombre del autor
- ORCID (si existe)
- Títulos de artículos
- Revistas
- Fechas de publicación
