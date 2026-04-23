# Database Schema

The project persists data into a PostgreSQL database organised into
several logical schemas. Each schema has its own DDL script under
[`scripts/sql/`](../scripts/sql/).

```
┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
│    raw    │    │   vocab   │    │  sm_maps  │    │  sm_attr  │    │ sm_result │
│           │    │           │    │           │    │           │    │           │
│ PubMed    │    │ MeSH,     │    │ Affiliation│   │ Auxiliary │    │ Author-   │
│ articles, │───►│ SNOMED-CT │───►│ → SNOMED  │───►│ attribute │───►│ level     │
│ authors   │    │ specialty │    │ mapping   │    │ tables    │    │ results   │
└───────────┘    └───────────┘    └───────────┘    └───────────┘    └───────────┘
```

## Schema `raw` — ingested PubMed data

Source: PubMed E-utilities (`efetch` with `rettype=xml`). Populated by
`scripts/download_pubmed.py`.

### `raw.pubmed_articles`

One row per PubMed article kept after the Spanish-affiliation filter.

| Column | Type | Description |
|---|---|---|
| `pubmed_id` | INTEGER PK | PubMed unique identifier |
| `article_title` | TEXT | Full title |
| `article_abstract` | TEXT | Abstract text |
| `journal_name` | VARCHAR(500) | Journal name |
| `journal_issn` | VARCHAR(50) | ISSN |
| `publication_date` | DATE | Publication date |
| `article_doi` | VARCHAR(255) | DOI |
| `publication_types` | TEXT | Publication types, `;`-separated |
| `mesh_terms` | TEXT | MeSH terms, `;`-separated |
| `author_keywords` | TEXT | Author keywords, `;`-separated |
| `created_at` | TIMESTAMP | Ingestion timestamp |

Indexes on `publication_date`, `article_doi`, `journal_issn`.

### `raw.pubmed_authors`

One row per **author × article**, filtered to keep only authors with a
Spanish affiliation.

| Column | Type | Description |
|---|---|---|
| `sm_author_id` | SERIAL PK | Surrogate id |
| `pubmed_id` | INTEGER FK → `raw.pubmed_articles` | |
| `author_name` | VARCHAR(500) | `"Lastname, Firstname"` form |
| `author_position` | INTEGER | 1 = first author |
| `author_orcid` | VARCHAR(50) | ORCID when declared |
| `author_email` | VARCHAR(255) | Email when declared (rare) |
| `affiliation` | TEXT | Full Spanish affiliation text |
| `created_at` | TIMESTAMP | Ingestion timestamp |

Indexes on `pubmed_id`, `author_name`, `author_orcid`.

DDL: [`scripts/sql/create_tables.sql`](../scripts/sql/create_tables.sql)

---

## Schema `vocab` — controlled vocabularies

### `vocab.nlm_mesh_terms`

Medical Subject Headings from NLM (annual ASCII release).

| Column | Type | Description |
|---|---|---|
| `mesh_ui` | VARCHAR(20) UNIQUE | MeSH unique id (e.g. `D002318`) |
| `mesh_name` | VARCHAR(500) | Main heading |
| `tree_numbers` | TEXT | Hierarchical codes, `;`-separated |
| `parent_category` | CHAR(1) | Root category (A–N, V, Z) |
| `year_introduced` | INTEGER | Year the term was introduced |

Top-level categories: A Anatomy · B Organisms · C Diseases · D Chemicals
and Drugs · E Techniques · F Psychiatry · G Phenomena · H Sciences ·
I Anthropology · J Technology · K Humanities · L Information · M Named
Groups · N Healthcare · V Publication Types · Z Geography.

DDL: [`scripts/sql/create_mesh_table.sql`](../scripts/sql/create_mesh_table.sql)

### `vocab.snomed_specialties`

SNOMED-CT practitioner specialties (117 total, 45 are Spanish MIR
specialties).

| Column | Type | Description |
|---|---|---|
| `snomed_code` | VARCHAR(20) UNIQUE | SNOMED-CT code |
| `name_en` | VARCHAR(200) | Simplified English name |
| `name_snomed` | VARCHAR(200) | Official FHIR name |
| `name_es` | VARCHAR(200) | Spanish translation |
| `synonyms` | TEXT | Matching synonyms, `;`-separated |
| `is_mir_spain` | BOOLEAN | Part of the Spanish MIR catalogue |
| `last_checked` | DATE | Last FHIR sync |

DDL: [`scripts/sql/create_specialties_table.sql`](../scripts/sql/create_specialties_table.sql)

---

## Schema `sm_maps` — affiliation mapping

### `sm_maps.affiliation_to_snomed`

Rules that map affiliation patterns to SNOMED-CT specialty codes. This
is the **only** mapping source: affiliation is the single field deemed
reliable enough to assign a specialty to an individual author (articles
can have authors from multiple specialties).

| Column | Type | Description |
|---|---|---|
| `affiliation_pattern` | TEXT | Literal or pattern to match |
| `pattern_type` | VARCHAR(20) | `exact` \| `contains` \| `prefix` \| `suffix` |
| `snomed_code` | VARCHAR(20) | Target SNOMED-CT code |
| `fidelity` | VARCHAR(20) | `snomed` \| `simplified` |

DDL: [`scripts/sql/create_specialty_mappings.sql`](../scripts/sql/create_specialty_mappings.sql)

---

## Schema `sm_attr` — auxiliary attribute tables

Supplementary attribute tables used during specialty inference (e.g.
journal specialties, keyword specialties). See
[`scripts/sql/create_attr_tables.sql`](../scripts/sql/create_attr_tables.sql).

---

## Schema `sm_result` — computed results

### `sm_result.author_specialties`

One row per `(author, specialty)` combination detected. An author can
have multiple specialties.

| Column | Type | Description |
|---|---|---|
| `author_name` | VARCHAR(500) | `"Lastname, Firstname"` form |
| `author_orcid` | VARCHAR(50) | ORCID if declared |
| `snomed_code` | VARCHAR(20) FK → `vocab.snomed_specialties` | |
| `confidence` | DECIMAL(4,3) | 0.000–1.000 |
| `article_count` | INTEGER | Supporting article count |

DDL: [`scripts/sql/create_author_specialties.sql`](../scripts/sql/create_author_specialties.sql)

### `sm_result.authors_orcid`, `sm_result.authors_norm`

Deduplicated author tables produced by the name-normalization and ORCID
pipelines. See
[`docs/author_deduplication.md`](author_deduplication.md) for the full
methodology and
[`scripts/sql/create_authors_table.sql`](../scripts/sql/create_authors_table.sql)
for the DDL.

---

## Bootstrapping the schema

Run the scripts in order from a freshly-created database:

```bash
psql … -f scripts/sql/create_tables.sql              # raw
psql … -f scripts/sql/create_mesh_table.sql          # vocab.mesh
psql … -f scripts/sql/create_specialties_table.sql   # vocab.snomed
psql … -f scripts/sql/create_specialty_mappings.sql  # sm_maps
psql … -f scripts/sql/create_attr_tables.sql         # sm_attr
psql … -f scripts/sql/create_author_specialties.sql  # sm_result
psql … -f scripts/sql/create_authors_table.sql       # sm_result (dedup)
```

Each script starts with `CREATE SCHEMA IF NOT EXISTS …` and is idempotent
(but drops its own tables at the top — beware of re-running once data
has landed).
