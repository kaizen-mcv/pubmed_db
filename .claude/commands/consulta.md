# Consulta la Base de Datos PubMed

Ejecuta consultas SQL sobre la base de datos de artículos PubMed con autores españoles.

## Argumentos

El usuario proporciona: **$ARGUMENTS**

## Instrucciones

Interpreta la solicitud del usuario y ejecuta la consulta SQL apropiada. Puedes combinar múltiples consultas según sea necesario.

## Conexión a la Base de Datos

```bash
PGPASSWORD='REDACTED_PWD' psql -h localhost -U pubmed_user -d pubmed_db
```

## Esquema de Tablas

### articles
- `pubmed_id` (PK): ID único en PubMed
- `article_title`: Título del artículo
- `article_abstract`: Resumen/Abstract
- `journal_name`: Nombre de la revista
- `journal_issn`: ISSN de la revista
- `publication_date`: Fecha de publicación
- `article_doi`: DOI
- `publication_types`: Tipos de publicación (ej: "Journal Article; Review")
- `mesh_terms`: Términos MeSH (vocabulario médico)
- `author_keywords`: Palabras clave del autor
- `created_at`: Fecha de inserción

### article_authors (solo autores con afiliación española)
- `id` (PK): ID auto-generado
- `pubmed_id` (FK): Referencia al artículo
- `author_name`: Nombre formato "Apellido, Nombre"
- `author_position`: Posición (1=primer autor)
- `author_orcid`: ORCID del autor
- `author_email`: Email del autor
- `affiliation`: Texto de afiliación española
- `created_at`: Fecha de inserción

## Tipos de Consulta Disponibles

### 1. Estadísticas generales
```sql
SELECT
    (SELECT COUNT(*) FROM articles) as total_articulos,
    (SELECT COUNT(*) FROM article_authors) as total_registros_autores,
    (SELECT COUNT(DISTINCT author_name) FROM article_authors) as autores_unicos,
    (SELECT COUNT(DISTINCT author_orcid) FROM article_authors WHERE author_orcid IS NOT NULL) as autores_con_orcid;
```

### 2. Buscar autor (por nombre)
```sql
SELECT aa.author_name, aa.author_orcid, aa.author_position, aa.affiliation,
       a.article_title, a.journal_name, a.publication_date
FROM article_authors aa
JOIN articles a ON aa.pubmed_id = a.pubmed_id
WHERE aa.author_name ILIKE '%nombre%'
ORDER BY a.publication_date DESC;
```

### 3. Buscar por ORCID
```sql
SELECT aa.author_name, aa.author_orcid, a.article_title, a.journal_name, a.publication_date
FROM article_authors aa
JOIN articles a ON aa.pubmed_id = a.pubmed_id
WHERE aa.author_orcid = '0000-0000-0000-0000';
```

### 4. Autores más prolíficos
```sql
SELECT author_name, author_orcid, COUNT(*) as articulos
FROM article_authors
GROUP BY author_name, author_orcid
ORDER BY articulos DESC
LIMIT 20;
```

### 5. Top revistas
```sql
SELECT journal_name, COUNT(*) as articulos
FROM articles
WHERE journal_name IS NOT NULL
GROUP BY journal_name
ORDER BY articulos DESC
LIMIT 20;
```

### 6. Tipos de publicación
```sql
SELECT publication_types, COUNT(*) as total
FROM articles
WHERE publication_types IS NOT NULL
GROUP BY publication_types
ORDER BY total DESC;
```

### 7. Buscar por palabra clave (título o abstract)
```sql
SELECT pubmed_id, article_title, journal_name, publication_date
FROM articles
WHERE article_title ILIKE '%keyword%' OR article_abstract ILIKE '%keyword%'
ORDER BY publication_date DESC
LIMIT 20;
```

### 8. Buscar por términos MeSH
```sql
SELECT pubmed_id, article_title, mesh_terms, journal_name
FROM articles
WHERE mesh_terms ILIKE '%term%'
ORDER BY publication_date DESC
LIMIT 20;
```

### 9. Artículos por rango de fechas
```sql
SELECT pubmed_id, article_title, journal_name, publication_date
FROM articles
WHERE publication_date BETWEEN '2023-01-01' AND '2023-12-31'
ORDER BY publication_date DESC;
```

### 10. Buscar por afiliación (hospital, universidad, etc.)
```sql
SELECT DISTINCT aa.author_name, aa.affiliation, a.article_title
FROM article_authors aa
JOIN articles a ON aa.pubmed_id = a.pubmed_id
WHERE aa.affiliation ILIKE '%hospital%' OR aa.affiliation ILIKE '%universidad%'
LIMIT 30;
```

### 11. Coautorías (autores que publican juntos)
```sql
SELECT a1.author_name as autor1, a2.author_name as autor2, COUNT(*) as publicaciones_juntos
FROM article_authors a1
JOIN article_authors a2 ON a1.pubmed_id = a2.pubmed_id AND a1.author_name < a2.author_name
GROUP BY a1.author_name, a2.author_name
HAVING COUNT(*) > 1
ORDER BY publicaciones_juntos DESC
LIMIT 20;
```

### 12. Primeros autores (posición 1)
```sql
SELECT author_name, author_orcid, COUNT(*) as veces_primer_autor
FROM article_authors
WHERE author_position = 1
GROUP BY author_name, author_orcid
ORDER BY veces_primer_autor DESC
LIMIT 20;
```

### 13. Artículos recientes
```sql
SELECT pubmed_id, article_title, journal_name, publication_date, created_at
FROM articles
ORDER BY created_at DESC
LIMIT 20;
```

### 14. Conteo por año
```sql
SELECT EXTRACT(YEAR FROM publication_date) as anio, COUNT(*) as articulos
FROM articles
WHERE publication_date IS NOT NULL
GROUP BY anio
ORDER BY anio DESC;
```

### 15. Detalle de un artículo específico (por PubMed ID)
```sql
SELECT * FROM articles WHERE pubmed_id = 12345678;
SELECT * FROM article_authors WHERE pubmed_id = 12345678;
```

## Comportamiento

1. Interpreta qué quiere el usuario basándote en $ARGUMENTS
2. Construye y ejecuta la consulta SQL apropiada
3. Muestra los resultados de forma clara y legible
4. Si la consulta es ambigua, pregunta al usuario qué prefiere
5. Puedes combinar múltiples consultas si es necesario
6. Limita resultados grandes con LIMIT para evitar output excesivo

## Ejemplos de uso

- `/consulta estadísticas` → Estadísticas generales
- `/consulta autor García López` → Buscar artículos de ese autor
- `/consulta orcid 0000-0002-1234-5678` → Buscar por ORCID
- `/consulta revistas top` → Top revistas
- `/consulta keyword diabetes` → Artículos sobre diabetes
- `/consulta mesh oncology` → Artículos con término MeSH
- `/consulta hospital La Paz` → Autores afiliados a ese hospital
- `/consulta año 2023` → Artículos de 2023
- `/consulta pubmed 38123456` → Detalle de artículo específico
- `/consulta primeros autores` → Ranking de primeros autores
- `/consulta coautorias` → Parejas de autores que publican juntos
