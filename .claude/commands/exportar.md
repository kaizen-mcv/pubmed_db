# Exportar datos a CSV

Exporta los datos de la base de datos a archivos CSV.

## Opciones de exportación

1. **Artículos completos**
2. **Autores españoles**
3. **Resumen por autor**

## Ejecución

```bash
cd /home/marc/db-projects/pubmed

# Exportar artículos
PGPASSWORD='REDACTED_PWD' psql -h localhost -U pubmed_user -d pubmed_db -c "\copy (SELECT * FROM articles) TO 'data/articles.csv' WITH CSV HEADER"

# Exportar autores españoles
PGPASSWORD='REDACTED_PWD' psql -h localhost -U pubmed_user -d pubmed_db -c "\copy (SELECT * FROM article_authors) TO 'data/spanish_authors.csv' WITH CSV HEADER"

# Exportar resumen por autor (con conteo de artículos)
PGPASSWORD='REDACTED_PWD' psql -h localhost -U pubmed_user -d pubmed_db -c "\copy (SELECT author_name, author_orcid, COUNT(*) as total_articulos FROM article_authors GROUP BY author_name, author_orcid ORDER BY total_articulos DESC) TO 'data/author_summary.csv' WITH CSV HEADER"
```

Crea la carpeta `data/` si no existe antes de exportar.
