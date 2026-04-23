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
│   │   └── state_manager.py    # Estado de descargas (soporta --incremental)
│   │
│   ├── database/               # Acceso a BD
│   │   ├── connection.py       # Conexión PostgreSQL
│   │   └── repositories/       # CRUD
│   │       ├── article_repo.py
│   │       └── article_author_repo.py
│   │
│   ├── services/               # Lógica de negocio
│   │   ├── article_service.py  # Orquestación guardado
│   │   └── specialty_service.py # Inferencia de especialidades
│   │
│   └── utils/                  # Utilidades
│       └── logger.py           # Sistema de logging centralizado
│
├── scripts/                    # Scripts ejecutables
│   ├── create_tables.sql               # Esquema BD principal
│   ├── create_specialties_table.sql    # Tabla SNOMED specialties
│   ├── create_mesh_table.sql           # Tabla términos MeSH
│   ├── create_mesh_snomed_mapping.sql  # Mapeo MeSH → SNOMED
│   ├── create_specialty_mappings.sql   # Tablas de mapeo adicionales
│   ├── download_pubmed.py              # Descarga de artículos
│   ├── import_mesh_terms.py            # Importar términos MeSH
│   ├── sync_snomed_specialties.py      # Sincronizar con API FHIR
│   ├── populate_specialty_synonyms.py  # Poblar sinónimos MIR
│   ├── populate_specialty_mappings.py  # Poblar mapeos SNOMED
│   ├── create_author_specialties.sql   # Tabla especialidades por autor
│   ├── populate_author_specialties.py  # Poblar especialidades de autores
│   ├── cron_update.py                  # Script para CRON (actualización diaria)
│   └── statistics.py                   # Estadísticas de la BD
│
├── tests/                      # Tests unitarios
│   └── test_filters/
│
├── data/                       # Datos generados (logs, estado)
│
└── venv/                       # Entorno virtual
```

---

## Esquema de Base de Datos

### Tablas Principales

#### Tabla: `pubmed_articles`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pubmed_id` | INTEGER (PK) | ID único en PubMed |
| `article_title` | TEXT | Título del artículo |
| `article_abstract` | TEXT | Resumen/Abstract |
| `journal_name` | VARCHAR(500) | Nombre de la revista |
| `journal_issn` | VARCHAR(50) | ISSN de la revista |
| `publication_date` | DATE | Fecha de publicación |
| `article_doi` | VARCHAR(255) | Digital Object Identifier |
| `publication_types` | TEXT | Tipos de publicación (ej: "Journal Article; Review") |
| `mesh_terms` | TEXT | Términos MeSH (vocabulario médico) |
| `author_keywords` | TEXT | Palabras clave del autor |
| `created_at` | TIMESTAMP | Fecha de inserción |

#### Tabla: `pubmed_authors`

Solo se guardan autores con afiliación española.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL (PK) | ID auto-generado |
| `pubmed_id` | INTEGER (FK) | Referencia al artículo |
| `author_name` | VARCHAR(500) | Nombre: "Apellido, Nombre" |
| `author_position` | INTEGER | Posición (1=primer autor) |
| `author_orcid` | VARCHAR(50) | ORCID del autor |
| `author_email` | VARCHAR(255) | Email del autor (raro) |
| `affiliation` | TEXT | Afiliación española |
| `created_at` | TIMESTAMP | Fecha de inserción |

---

### Tablas SNOMED CT (Especialidades Médicas)

#### Tabla: `snomed_specialties`

Especialidades médicas según estándar SNOMED CT / HL7 FHIR.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL (PK) | ID auto-generado |
| `snomed_code` | VARCHAR(20) | Código SNOMED CT (UNIQUE) |
| `name_en` | VARCHAR(200) | Nombre simplificado inglés |
| `name_snomed` | VARCHAR(200) | Nombre oficial FHIR (con "qualifier value") |
| `name_es` | VARCHAR(200) | Traducción al español |
| `synonyms` | TEXT | Sinónimos para matching (separados por ;) |
| `is_mir_spain` | BOOLEAN | TRUE si es especialidad MIR española |
| `created_at` | TIMESTAMP | Fecha de creación |
| `last_checked` | DATE | Última sincronización con API FHIR |

**Notas:**
- 117 especialidades SNOMED CT totales
- 45 especialidades MIR españolas (con `is_mir_spain = TRUE`)
- Sinónimos solo para especialidades MIR (exclusivos, sin solapamiento)

#### Tabla: `nlm_mesh_terms`

Vocabulario controlado MeSH de la NLM (National Library of Medicine).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL (PK) | ID auto-generado |
| `mesh_ui` | VARCHAR(20) | Identificador único MeSH (ej: D002309) |
| `mesh_name` | VARCHAR(500) | Nombre del término |
| `tree_numbers` | TEXT | Números de árbol jerárquico |
| `parent_category` | CHAR(1) | Categoría raíz (C=Diseases, etc.) |
| `year_introduced` | INTEGER | Año de introducción |
| `created_at` | TIMESTAMP | Fecha de inserción |

#### Tabla: `mesh_to_snomed`

Mapeo de términos MeSH a especialidades SNOMED.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL (PK) | ID auto-generado |
| `mesh_tree_prefix` | VARCHAR(20) | Prefijo del árbol MeSH |
| `snomed_code` | VARCHAR(20) (FK) | Código SNOMED CT |
| `confidence` | DECIMAL(3,2) | Confianza del mapeo (0.0-1.0) |
| `notes` | TEXT | Notas del mapeo |

---

### Tablas de Mapeo Adicionales

Para inferir especialidades desde diferentes fuentes:

| Tabla | Descripción |
|-------|-------------|
| `journal_to_snomed` | Revistas → Especialidades |
| `affiliation_to_snomed` | Afiliaciones → Especialidades |
| `keyword_to_snomed` | Palabras clave → Especialidades |
| `title_pattern_to_snomed` | Patrones en títulos → Especialidades |
| `abstract_pattern_to_snomed` | Patrones en abstracts → Especialidades |

#### Tabla: `author_specialties`

Especialidades inferidas por autor (tabla derivada).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL (PK) | ID auto-generado |
| `author_name` | VARCHAR(500) | Nombre del autor |
| `author_orcid` | VARCHAR(50) | ORCID si disponible |
| `snomed_code` | VARCHAR(20) (FK) | Código SNOMED CT |
| `confidence` | DECIMAL(4,3) | Confianza agregada (0.000-1.000) |
| `article_count` | INTEGER | Artículos que contribuyen |
| `sources` | TEXT | Fuentes (journal,mesh,affiliation,...) |
| `last_updated` | TIMESTAMP | Última actualización |

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
cd $PROJECT_DIR
source venv/bin/activate
pip install -r config/requirements.txt
```

### 2. Configurar credenciales

**Opción A: Variables de entorno (recomendado)**
```bash
export PUBMED_DB_HOST=localhost
export PUBMED_DB_PORT=5432
export PUBMED_DB_NAME=pubmed_db
export PUBMED_DB_USER=pubmed_user
export PUBMED_DB_PASSWORD=tu_password
```

**Opción B: Archivos YAML (solo desarrollo local)**

Editar `config/pubmed_config.yaml`:
```yaml
email: "tu_email@example.com"
api_key: "tu_api_key_opcional"  # Gratis en ncbi.nlm.nih.gov
```

Editar `config/db_config.yaml`:
```yaml
host: localhost
port: 5432
name: pubmed_db
user: pubmed_user
password: tu_password
```

### 3. Crear tablas

```bash
# Tablas principales
PGPASSWORD='password' psql -h localhost -U pubmed_user -d pubmed_db -f scripts/create_tables.sql

# Tablas SNOMED
PGPASSWORD='password' psql -h localhost -U pubmed_user -d pubmed_db -f scripts/create_specialties_table.sql
PGPASSWORD='password' psql -h localhost -U pubmed_user -d pubmed_db -f scripts/create_mesh_table.sql
PGPASSWORD='password' psql -h localhost -U pubmed_user -d pubmed_db -f scripts/create_mesh_snomed_mapping.sql
PGPASSWORD='password' psql -h localhost -U pubmed_user -d pubmed_db -f scripts/create_specialty_mappings.sql
```

### 4. Ejecutar descarga

```bash
python scripts/download_pubmed.py              # Descarga nueva
python scripts/download_pubmed.py --resume     # Reanudar descarga interrumpida
python scripts/download_pubmed.py --incremental # Solo artículos nuevos (para CRON)
```

### 5. Scripts de mantenimiento

```bash
# Sincronizar especialidades con API FHIR
python scripts/sync_snomed_specialties.py --apply

# Poblar sinónimos de especialidades MIR
python scripts/populate_specialty_synonyms.py --apply

# Importar términos MeSH
python scripts/import_mesh_terms.py

# Ver estadísticas
python scripts/statistics.py
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
│   PostgreSQL    │
└─────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
pubmed_    snomed_
articles   specialties
pubmed_    nlm_mesh_terms
authors    mappings...
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
FROM pubmed_authors;

-- Artículos por tipo de publicación
SELECT publication_types, COUNT(*)
FROM pubmed_articles
GROUP BY publication_types;

-- Autores con ORCID
SELECT author_name, author_orcid, COUNT(*) as articulos
FROM pubmed_authors
WHERE author_orcid IS NOT NULL
GROUP BY author_name, author_orcid
ORDER BY articulos DESC;

-- Especialidades MIR españolas
SELECT snomed_code, name_en, name_es
FROM snomed_specialties
WHERE is_mir_spain = TRUE
ORDER BY name_es;

-- Buscar especialidad por sinónimo
SELECT snomed_code, name_en, name_es
FROM snomed_specialties
WHERE synonyms ILIKE '%cardiology%';

-- Inferir especialidades de un artículo (usando función)
SELECT * FROM get_specialties_for_mesh_tree('C14.280.434');
```

---

## Inferencia de Especialidades

El servicio `SpecialtyService` combina múltiples fuentes para inferir especialidades:

```python
from src.services.specialty_service import SpecialtyService
from src.database.connection import db

with db.cursor_context() as cur:
    specialties = SpecialtyService.infer_article_specialties(
        cur,
        pubmed_id=12345678,
        top_n=5,
        min_confidence=0.1
    )

    for spec in specialties:
        print(f"{spec['name_en']}: {spec['score']:.2f}")
        print(f"  Fuentes: {spec['sources']}")
```

### Pesos por fuente

| Fuente | Peso | Confianza típica |
|--------|------|------------------|
| MeSH terms | 0.40 | Alta (vocabulario controlado) |
| Journal | 0.25 | Alta (revistas especializadas) |
| Keywords | 0.15 | Media |
| Title patterns | 0.10 | Media |
| Abstract patterns | 0.05 | Baja |
| Affiliation | 0.05 | Baja |

---

## Tests

```bash
# Ejecutar todos los tests
PUBMED_DB_PASSWORD='xxx' pytest tests/ -v

# Solo tests de filtros
pytest tests/test_filters/ -v

# Solo tests de servicios
pytest tests/test_services/ -v
```

---

## Configuración CRON

Para mantener la base de datos actualizada automáticamente:

```bash
# Copiar ejemplo de configuración
cp config/cron.example /etc/cron.d/pubmed-update

# O añadir a tu crontab personal
crontab -e
```

### Actualización diaria (recomendado)

```cron
# Ejecutar a las 3:00 AM (hora off-peak de NCBI)
0 3 * * * cd $PROJECT_DIR && PUBMED_DB_PASSWORD='xxx' ./venv/bin/python scripts/cron_update.py >> data/logs/cron.log 2>&1
```

### Script CRON

El script `scripts/cron_update.py` realiza:
1. Descarga incremental de artículos nuevos
2. Actualización de especialidades de autores nuevos
3. Genera resumen de cambios

```bash
# Ejecutar manualmente
python scripts/cron_update.py

# Solo descargar artículos
python scripts/cron_update.py --download-only

# Solo actualizar especialidades
python scripts/cron_update.py --specialties-only

# Ver qué se haría sin ejecutar
python scripts/cron_update.py --dry-run
```