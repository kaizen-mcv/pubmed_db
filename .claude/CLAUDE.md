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
│   │   └── specialty_service.py # Inferencia de especialidades (solo afiliaciones)
│   │
│   └── utils/                  # Utilidades
│       └── logger.py           # Sistema de logging centralizado
│
├── scripts/                    # Scripts ejecutables
│   ├── create_tables.sql               # Esquema BD principal (raw.*)
│   ├── create_attr_tables.sql          # Tablas atributos (sm_attr.*)
│   ├── create_specialties_table.sql    # Tabla SNOMED (vocab.snomed_specialties)
│   ├── create_mesh_table.sql           # Tabla términos MeSH (vocab.nlm_mesh_terms)
│   ├── create_mesh_snomed_mapping.sql  # Mapeo MeSH→SNOMED (vocab.mesh_to_snomed)
│   ├── create_specialty_mappings.sql   # Mapeo afiliación→SNOMED (sm_maps.*)
│   ├── create_author_specialties.sql   # Resultado (sm_result.author_specialties)
│   ├── download_pubmed.py              # Descarga de artículos
│   ├── import_mesh_terms.py            # Importar términos MeSH
│   ├── sync_snomed_specialties.py      # Sincronizar con API FHIR
│   ├── populate_specialty_mappings.py  # Poblar mapeo afiliación→SNOMED
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

## Organización por Schemas PostgreSQL

La base de datos está organizada en 5 schemas para separar responsabilidades:

```
raw       → Datos brutos de PubMed (pubmed_articles, pubmed_authors)
sm_attr   → Atributos normalizados (journals, keywords, affiliations, mesh_terms_articles)
vocab     → Vocabulario médico controlado (snomed_specialties, nlm_mesh_terms, mesh_to_snomed)
sm_maps   → Mapeo afiliación→SNOMED (affiliation_to_snomed)
sm_result → Resultados finales (author_specialties)
```

### Resumen de Tablas

| Schema | Tabla | Registros | Descripción |
|--------|-------|-----------|-------------|
| `raw` | pubmed_articles | ~471K | Artículos de PubMed |
| `raw` | pubmed_authors | ~2M | Autores españoles |
| `sm_attr` | journals | ~8K | Revistas únicas |
| `sm_attr` | keywords | ~568K | Keywords de autores |
| `sm_attr` | affiliations | ~932K | Afiliaciones únicas |
| `sm_attr` | mesh_terms_articles | ~25K | MeSH terms únicos |
| `vocab` | snomed_specialties | 117 | Especialidades SNOMED |
| `vocab` | nlm_mesh_terms | ~31K | Vocabulario MeSH |
| `vocab` | mesh_to_snomed | 159 | Mapeo MeSH→SNOMED |
| `sm_maps` | affiliation_to_snomed | - | Afiliación→Especialidad |
| `sm_result` | author_specialties | - | Especialidades por autor |

---

## Esquema de Base de Datos

### Tablas Principales (Schema: `raw`)

#### Tabla: `raw.pubmed_articles`

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

#### Tabla: `raw.pubmed_authors`

Solo se guardan autores con afiliación española.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `sm_author_id` | SERIAL (PK) | ID auto-generado |
| `pubmed_id` | INTEGER (FK) | Referencia al artículo |
| `author_name` | VARCHAR(500) | Nombre: "Apellido, Nombre" |
| `author_position` | INTEGER | Posición (1=primer autor) |
| `author_orcid` | VARCHAR(50) | ORCID del autor |
| `author_email` | VARCHAR(255) | Email del autor (raro) |
| `affiliation` | TEXT | Afiliación española |
| `created_at` | TIMESTAMP | Fecha de inserción |

---

### Tablas SNOMED CT (Schema: `vocab`)

#### Tabla: `vocab.snomed_specialties`

Especialidades médicas según estándar SNOMED CT / HL7 FHIR.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL (PK) | ID auto-generado |
| `snomed_code` | VARCHAR(20) | Código SNOMED CT (UNIQUE) |
| `name_en` | VARCHAR(200) | Nombre simplificado inglés |
| `name_snomed` | VARCHAR(200) | Nombre oficial FHIR (con "qualifier value") |
| `name_es` | VARCHAR(200) | Traducción al español |
| `is_mir_spain` | BOOLEAN | TRUE si es especialidad MIR española |
| `created_at` | TIMESTAMP | Fecha de creación |
| `last_checked` | DATE | Última sincronización con API FHIR |

**Notas:**
- 117 especialidades SNOMED CT totales
- 45 especialidades MIR españolas (con `is_mir_spain = TRUE`)

#### Tabla: `vocab.nlm_mesh_terms`

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

#### Tabla: `vocab.mesh_to_snomed`

Mapeo de términos MeSH a especialidades SNOMED.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL (PK) | ID auto-generado |
| `mesh_tree_prefix` | VARCHAR(20) | Prefijo del árbol MeSH |
| `snomed_code` | VARCHAR(20) (FK) | Código SNOMED CT |
| `confidence` | DECIMAL(3,2) | Confianza del mapeo (0.0-1.0) |
| `notes` | TEXT | Notas del mapeo |

---

### Tabla de Mapeo (Schema: `sm_maps`)

#### Tabla: `sm_maps.affiliation_to_snomed`

Mapea afiliaciones de autores a especialidades SNOMED.

**Esta es la única tabla de mapeo** porque la afiliación es el único campo 100% fiable para determinar la especialidad de un autor individual. Un artículo puede tener autores de múltiples especialidades, pero la afiliación indica directamente dónde trabaja cada autor.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `sm_affiliation_id` | SERIAL (PK) | ID auto-generado |
| `affiliation_pattern` | VARCHAR(500) | Patrón de afiliación |
| `pattern_type` | VARCHAR(20) | Tipo: exact, contains, prefix, suffix |
| `snomed_code` | VARCHAR(20) (FK) | Código SNOMED CT |
| `fidelity` | VARCHAR(20) | snomed=nombre oficial, simplified=nombre simplificado |
| `created_at` | TIMESTAMP | Fecha de creación |

---

### Tablas de Resultados (Schema: `sm_result`)

#### Tabla: `sm_result.author_specialties`

Especialidades inferidas por autor basándose en sus afiliaciones.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `sm_author_specialty_id` | SERIAL (PK) | ID auto-generado |
| `author_name` | VARCHAR(500) | Nombre del autor |
| `author_orcid` | VARCHAR(50) | ORCID si disponible |
| `snomed_code` | VARCHAR(20) (FK) | Código SNOMED CT |
| `confidence` | DECIMAL(4,3) | Confianza (1.0=SNOMED, 0.9=simplificado) |
| `article_count` | INTEGER | Artículos que contribuyen |
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

# Poblar mapeo afiliación→SNOMED
python scripts/populate_specialty_mappings.py --apply

# Poblar especialidades de autores
python scripts/populate_author_specialties.py

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
raw.*      vocab.*
sm_attr.*  sm_maps.*
           sm_result.*
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
FROM raw.pubmed_authors;

-- Artículos por tipo de publicación
SELECT publication_types, COUNT(*)
FROM raw.pubmed_articles
GROUP BY publication_types;

-- Autores con ORCID
SELECT author_name, author_orcid, COUNT(*) as articulos
FROM raw.pubmed_authors
WHERE author_orcid IS NOT NULL
GROUP BY author_name, author_orcid
ORDER BY articulos DESC;

-- Especialidades MIR españolas
SELECT snomed_code, name_en, name_es
FROM vocab.snomed_specialties
WHERE is_mir_spain = TRUE
ORDER BY name_es;

-- Top keywords más usados
SELECT keyword_text, article_count
FROM sm_attr.keywords
ORDER BY article_count DESC
LIMIT 20;

-- Top revistas por número de artículos
SELECT journal_name, article_count
FROM sm_attr.journals
ORDER BY article_count DESC
LIMIT 20;

-- Especialidades más comunes entre autores
SELECT s.name_en, COUNT(*) as autores
FROM sm_result.author_specialties a
JOIN vocab.snomed_specialties s ON a.snomed_code = s.snomed_code
GROUP BY s.name_en
ORDER BY autores DESC;
```

---

## Inferencia de Especialidades

El servicio `SpecialtyService` infiere especialidades **únicamente desde las afiliaciones de los autores**, ya que es el único campo 100% fiable para determinar la especialidad de cada autor individual.

```python
from src.services.specialty_service import SpecialtyService
from src.database.connection import db

with db.cursor_context() as cur:
    # Infiere especialidades de los autores de un artículo
    specialties = SpecialtyService.infer_author_specialties(
        cur,
        pubmed_id=12345678,
        min_confidence=0.5
    )

    for spec in specialties:
        print(f"{spec['name_en']}: {spec['confidence']:.2f}")
        print(f"  Afiliaciones: {spec['affiliations']}")
```

### Niveles de Confianza

| Nivel | Valor | Descripción |
|-------|-------|-------------|
| SNOMED | 1.0 | Nombre oficial SNOMED encontrado en afiliación |
| Simplificado | 0.9 | Nombre simplificado (en/es) encontrado |

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
