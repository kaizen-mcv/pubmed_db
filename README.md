# pubmed_db

Base de datos PostgreSQL con artículos de PubMed filtrados por afiliación
española. Incluye descarga incremental, enriquecimiento con términos MeSH y
clasificación por especialidad médica.

**Stack:** Python 3.11+, PostgreSQL, API E-Utilities de NCBI.

## Qué hace

- Descarga incremental de artículos desde PubMed con respeto a rate limits
- Filtra autores con afiliación española (universidades, hospitales, CSIC, etc.)
- Enriquece con términos MeSH y mapea a especialidades médicas
- Genera estadísticas: productividad por autor, revistas, temporalidad

## Estructura del Proyecto

```
pubmed/
├── .claude/                    # Documentación y comandos para Claude
│   ├── commands/               # Comandos slash
│   └── CLAUDE.md               # Documentación detallada
│
├── config/                     # Configuración
│   ├── db_config.yaml          # Credenciales PostgreSQL
│   ├── pubmed_config.yaml      # Configuración PubMed/NCBI
│   ├── spanish_filters.yaml    # Marcadores españoles
│   ├── settings.py             # Carga de configuración
│   └── requirements.txt        # Dependencias Python
│
├── data/                       # Datos generados
│   └── logs/                   # Logs de descarga
│
├── scripts/                    # Ejecutables
│   ├── create_tables.sql       # Esquema de BD
│   └── download_pubmed.py      # Script principal
│
├── src/                        # Código fuente
│   ├── database/               # Conexión y repositorios
│   ├── download/               # Cliente PubMed y rate limiting
│   ├── extractors/             # Extracción de XML
│   ├── filters/                # Filtro español
│   ├── models/                 # Dataclasses
│   └── services/               # Lógica de negocio
│
├── tests/                      # Tests unitarios
│   └── test_filters/
│
└── venv/                       # Entorno virtual
```

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate

# 2. Instalar dependencias
pip install -r config/requirements.txt

# 3. Configurar credenciales
# Editar config/pubmed_config.yaml (email)
# Editar config/db_config.yaml (PostgreSQL)

# 4. Crear tablas
PGPASSWORD='tu_password' psql -h localhost -U pubmed_user -d pubmed_db -f scripts/create_tables.sql
```

## Uso

```bash
# 1. Configurar descarga en config/pubmed_config.yaml:
#    - search.date_from / date_to: rango de fechas
#    - search.max_articles: número máximo (null = sin límite)

# 2. Ejecutar descarga
python scripts/download_pubmed.py

# 3. Reanudar descarga interrumpida
python scripts/download_pubmed.py --resume
```

## Tests

```bash
pytest tests/ -v
```

## Base de Datos

2 tablas:
- `articles` - Artículos científicos
- `article_authors` - Autores con afiliación española

Ver `.claude/CLAUDE.md` para documentación completa del esquema.
