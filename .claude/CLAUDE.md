# PubMed Downloader - Investigadores Españoles

## Propósito

Descargar y almacenar artículos científicos de PubMed que tengan **autores con afiliación española**, para analizar qué están investigando los doctores de España y en qué se especializan.

---

## Estructura del Proyecto

```
pubmed/
├── config/                     # Configuración
│   ├── settings.py             # Carga de configuración
│   ├── pubmed_config.yaml      # Credenciales PubMed (email, api_key)
│   ├── db_config.yaml          # Credenciales PostgreSQL
│   ├── spanish_filters.yaml    # Lista de marcadores españoles
│   └── requirements.txt        # Dependencias Python
│
├── src/                        # Código fuente
│   ├── models/                 # Modelos de datos (dataclasses)
│   │   ├── article.py          # Modelo Article
│   │   └── author.py           # Modelo Author
│   │
│   ├── extractors/             # Extracción de XML de PubMed
│   │   ├── article_extractor.py    # Campos del artículo
│   │   ├── author_extractor.py     # Datos de autores (ORCID, email)
│   │   └── affiliation_extractor.py # Texto de afiliación
│   │
│   ├── filters/                # Filtros locales
│   │   └── spanish_filter.py   # Identifica afiliaciones españolas
│   │
│   ├── download/               # Descarga de PubMed
│   │   ├── pubmed_client.py    # Cliente Entrez API
│   │   ├── batch_downloader.py # Descarga en lotes
│   │   ├── rate_limiter.py     # Control de rate (NCBI)
│   │   └── state_manager.py    # Estado de descargas
│   │
│   ├── database/               # Acceso a BD
│   │   ├── connection.py       # Conexión PostgreSQL
│   │   └── repositories/       # CRUD
│   │       ├── article_repo.py
│   │       └── article_author_repo.py
│   │
│   └── services/               # Lógica de negocio
│       └── article_service.py  # Orquestación
│
├── scripts/                    # Scripts
│   ├── create_tables.sql       # Esquema BD (2 tablas)
│   └── download_pubmed.py      # Script principal de descarga
│
├── tests/                      # Tests unitarios
│   └── test_filters/
│
├── data/                       # Datos generados (logs, estado)
│
└── venv/                       # Entorno virtual
```

---

## Esquema de Base de Datos (2 tablas)

### Tabla: `articles`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pubmed_id` | INTEGER (PK) | ID único en PubMed |
| `article_title` | TEXT | Título del artículo |
| `article_abstract` | TEXT | Resumen/Abstract |
| `journal_name` | VARCHAR(500) | Nombre de la revista |
| `journal_issn` | VARCHAR(20) | ISSN de la revista |
| `publication_date` | DATE | Fecha de publicación |
| `article_doi` | VARCHAR(255) | Digital Object Identifier |
| `publication_types` | TEXT | Tipos de publicación (ej: "Journal Article; Review") |
| `mesh_terms` | TEXT | Términos MeSH (vocabulario médico) |
| `author_keywords` | TEXT | Palabras clave del autor |
| `created_at` | TIMESTAMP | Fecha de inserción |

### Tabla: `article_authors`

Solo se guardan autores con afiliación española.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL (PK) | ID auto-generado |
| `pubmed_id` | INTEGER (FK) | Referencia al artículo |
| `author_name` | VARCHAR(500) | Nombre: "Apellido, Nombre" |
| `author_position` | INTEGER | Posición (1=primer autor) |
| `author_orcid` | VARCHAR(20) | ORCID del autor |
| `author_email` | VARCHAR(255) | Email del autor (raro) |
| `affiliation` | TEXT | Afiliación española |
| `created_at` | TIMESTAMP | Fecha de inserción |

---

## Convenciones de Código

### Nombres de Atributos

- Usar nombres descriptivos y completos
- Prefijo según origen: `article_`, `author_`, `journal_`
- Ejemplo: `article_title`, `author_orcid`, `journal_issn`

---

## Cómo Ejecutar

### 1. Preparar entorno

```bash
cd /home/marc/db-projects/pubmed
source venv/bin/activate
pip install -r config/requirements.txt
```

### 2. Configurar credenciales

Editar `config/pubmed_config.yaml`:
```yaml
email: "tu_email@example.com"
api_key: "tu_api_key_opcional"
```

Editar `config/db_config.yaml`:
```yaml
host: localhost
port: 5432
database: pubmed_db
user: pubmed_user
password: tu_password
```

### 3. Crear tablas

```bash
PGPASSWORD='password' psql -h localhost -U pubmed_user -d pubmed_db -f scripts/create_tables.sql
```

### 4. Configurar y ejecutar descarga

Editar `config/pubmed_config.yaml` para configurar:
- `search.date_from` / `search.date_to`: Rango de fechas
- `search.max_articles`: Número máximo (null = sin límite)

```bash
python scripts/download_pubmed.py          # Descarga nueva
python scripts/download_pubmed.py --resume # Reanudar descarga
```

---

## Flujo de Datos

```
PubMed API (Entrez)
       │
       ▼
┌─────────────────┐
│ batch_downloader │ ← rate_limiter (3 req/s sin API key)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   extractors    │ ← article, author, affiliation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ spanish_filter  │ ← Filtra solo afiliaciones españolas
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  article_service│ ← Orquesta guardado
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │ ← 2 tablas: articles + article_authors
└─────────────────┘
```

---

## Rate Limits de NCBI

- **Sin API Key**: 3 requests/segundo
- **Con API Key**: 10 requests/segundo
- **Horas off-peak** (fines de semana, 9pm-5am EST): Límites más flexibles

El módulo `rate_limiter.py` gestiona esto automáticamente.

---

## Consultas SQL Útiles

```sql
-- Todos los autores españoles únicos
SELECT DISTINCT author_name, author_orcid
FROM article_authors;

-- Artículos por tipo de publicación
SELECT publication_types, COUNT(*)
FROM articles
GROUP BY publication_types;

-- Autores con ORCID
SELECT author_name, author_orcid, COUNT(*) as articulos
FROM article_authors
WHERE author_orcid IS NOT NULL
GROUP BY author_name, author_orcid
ORDER BY articulos DESC;

-- Artículos de un autor específico
SELECT a.*
FROM articles a
JOIN article_authors aa ON a.pubmed_id = aa.pubmed_id
WHERE aa.author_name LIKE 'García%';
```
