# pubmed_db

Batch downloader for PubMed articles authored by researchers with Spanish
affiliations, with PostgreSQL persistence, MeSH enrichment and SNOMED-CT
specialty inference.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/kaizen-mcv/pubmed_db/actions/workflows/ci.yml/badge.svg)](https://github.com/kaizen-mcv/pubmed_db/actions/workflows/ci.yml)

## Features

- Incremental, resumable bulk download from PubMed via BioPython / E-utilities.
- Strict compliance with NCBI rate limits (3 req/s, 10 req/s with API key).
- Affiliation-based filtering to keep only Spanish-authored papers.
- Persistence into PostgreSQL with idempotent UPSERTs.
- MeSH thesaurus ingest and SNOMED-CT specialty mapping per author.
- Author name normalization and ORCID-aware deduplication.
- Ready-to-use `cron` workflow for nightly incremental updates.

## Requirements

- Python 3.10+
- PostgreSQL 14+
- A valid email address (required by NCBI E-utilities)
- Optional: an [NCBI API key](https://www.ncbi.nlm.nih.gov/account/settings/)
  to raise the rate limit from 3 to 10 req/s

## Quickstart

```bash
git clone git@github.com:kaizen-mcv/pubmed_db.git
cd pubmed_db

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # edit DB credentials
$EDITOR config/pubmed_config.yaml   # set your email and search window

# Create the PostgreSQL schema
psql -h "$PUBMED_DB_HOST" -U "$PUBMED_DB_USER" -d "$PUBMED_DB_NAME" \
  -f scripts/sql/create_tables.sql

# Run the first download
python scripts/download_pubmed.py
```

## Configuration

Runtime configuration comes from three YAML files and a handful of
environment variables. Environment variables always take precedence over
YAML values.

| Variable | Purpose | Default |
|---|---|---|
| `PUBMED_DB_HOST` | PostgreSQL host | `localhost` |
| `PUBMED_DB_PORT` | PostgreSQL port | `5432` |
| `PUBMED_DB_NAME` | Database name | `pubmed_db` |
| `PUBMED_DB_USER` | Database user | `pubmed_user` |
| `PUBMED_DB_PASSWORD` | Database password | *(required)* |
| `PUBMED_API_KEY` | NCBI API key (optional) | *(unset)* |

Config files:

- [`config/pubmed_config.yaml`](config/pubmed_config.yaml) — download policy,
  rate limits, search query, date range, state/log paths.
- [`config/db_config.yaml`](config/db_config.yaml) — database connection
  defaults (typically overridden by env vars).
- [`config/spanish_filters.yaml`](config/spanish_filters.yaml) — Spanish
  affiliation markers, cities and a blacklist of foreign countries.

See [`docs/configuration.md`](docs/configuration.md) for the full reference.

## Usage

```bash
# Initial download (uses config/pubmed_config.yaml)
python scripts/download_pubmed.py

# Resume an interrupted run from state file
python scripts/download_pubmed.py --resume

# Incremental update (new articles only — for cron)
python scripts/download_pubmed.py --incremental

# Point to an alternative config
python scripts/download_pubmed.py --config path/to/my_config.yaml
```

Auxiliary scripts:

```bash
# Import the current year's MeSH thesaurus
python scripts/import_mesh_terms.py

# Sync SNOMED-CT specialty catalogue
python scripts/sync_snomed_specialties.py

# Assign specialties to authors based on their affiliations
python scripts/populate_author_specialties.py [--incremental]

# Generate JSON statistics snapshots under .stats/
python scripts/statistics.py
```

### Scheduled updates (cron)

Use [`config/cron.example`](config/cron.example) as a template. A typical
nightly job:

```cron
PUBMED_DB_PASSWORD=your_password
0 3 * * * cd $PROJECT_DIR && ./venv/bin/python scripts/cron_update.py >> data/logs/cron.log 2>&1
```

## Project layout

```
pubmed_db/
├── config/               # YAML configs + settings loader
├── data/                 # Runtime artefacts (logs, state) — gitignored
├── docs/                 # Additional documentation
├── scripts/              # Entry points (download, cron, import…)
│   └── sql/              # DDL for each logical schema
├── src/                  # Library code
│   ├── database/         # Connection singleton + repositories
│   ├── download/         # PubMed client, rate limiter, state manager
│   ├── extractors/       # XML parsing (article, author, affiliation)
│   ├── filters/          # Spanish affiliation filter
│   ├── models/           # Dataclasses (Article, Author)
│   ├── services/         # High-level orchestration (article, specialty)
│   └── utils/            # Logger, name normalizer
└── tests/                # Unit tests (pytest)
```

## Database overview

The project targets a multi-schema PostgreSQL database:

| Schema | Content |
|---|---|
| `raw` | `pubmed_articles`, `pubmed_authors` — raw ingested data |
| `vocab` | `nlm_mesh_terms`, SNOMED specialty catalogue |
| `sm_maps` | Affiliation → specialty mapping tables |
| `sm_attr` | Auxiliary attribute tables (journals, keywords…) |
| `sm_result` | Computed results (`author_specialties`, `authors_norm`, `authors_orcid`) |

DDL lives under [`scripts/sql/`](scripts/sql/) (`create_*.sql`). For the full
schema reference see [`docs/schema.md`](docs/schema.md). For the author
deduplication strategy see
[`docs/author_deduplication.md`](docs/author_deduplication.md).

## Testing

```bash
pytest                    # runs tests/ with the config in pyproject.toml
ruff check .              # lint
ruff format --check .     # style
```

CI runs the same commands on Python 3.10, 3.11 and 3.12 for every push
and pull request.

## Contributing

Issues and pull requests are welcome. Please read
[`CONTRIBUTING.md`](CONTRIBUTING.md) first.

## License

Released under the [MIT License](LICENSE).

## Acknowledgements

- [BioPython](https://biopython.org/) — NCBI E-utilities client.
- [NCBI / NLM](https://www.ncbi.nlm.nih.gov/) — PubMed data (public domain)
  and MeSH thesaurus.
- [SNOMED International](https://www.snomed.org/) — medical specialty
  terminology.