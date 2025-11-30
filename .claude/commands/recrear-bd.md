# Recrear Base de Datos

Elimina todas las tablas y las vuelve a crear vacías.

**ADVERTENCIA**: Esto eliminará TODOS los datos existentes.

## Ejecución

```bash
cd /home/marc/db-projects/pubmed
PGPASSWORD='REDACTED_PWD' psql -h localhost -U pubmed_user -d pubmed_db -f scripts/create_tables.sql
```

## Resultado esperado

```
DROP TABLE
CREATE TABLE (articles)
CREATE TABLE (article_authors)
CREATE INDEX (varios índices)
COMMENT (varios comentarios)
```

Confirma con el usuario antes de ejecutar este comando.
