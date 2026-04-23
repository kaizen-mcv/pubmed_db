# Author Deduplication — Strategy and Methodology

This document describes how unique authors are identified across the raw
PubMed data, handling name variants and the absence of a universal
identifier.

---

## The Problem

Author records in PubMed are noisy. For the dataset at the time of
writing:

| Metric | Value |
|---|---|
| Total author records | 2,086,595 |
| Distinct name strings | 540,354 |
| Distinct name + affiliation combinations | 1,819,834 |
| Records with ORCID | 423,806 (20.31%) |
| Distinct ORCIDs | 105,616 |
| Distinct affiliations | 931,660 |

### Types of variation

| Type | Example | Frequency |
|---|---|---|
| Accents | García vs Garcia | Very high |
| Hyphens / spaces | García-Pavia vs García Pavia | High |
| Initials vs full name | J A vs José Alfredo | High |
| "María" abbreviations | Mª, Ma, M, María | Medium |
| Surname order | de Luis-Román vs Luis, Daniel de | Medium |
| Particles | de la Torre vs De La Torre | Medium |

### Real example

A single author (ORCID `0000-0002-1745-9315`) appears under **19**
different name strings:

```
de Luis, D
de Luis, Daniel
De Luis, Daniel
de Luis, Daniel A
de Luis, Daniel Antonio
de Luis Roman, Daniel
de Luis Román, Daniel
De Luis Román, Daniel
de Luis-Román, Daniel Antonio
Luis, Daniel A De
Luis, Daniel de
...
```

---

## Strategy

### Two result tables

Two tables are produced under the `sm_result` schema, for different
confidence levels:

1. `sm_result.authors_orcid` — ORCID-based identity (100% reliable).
2. `sm_result.authors_norm` — all authors keyed by normalized name.

### Three-phase pipeline

```
PHASE 1 — Direct ORCID
├── 423,806 records with ORCID
├── Grouped by unique ORCID
└── Output: ~105,616 authors (confidence 1.0)

PHASE 2 — ORCID propagation
├── Records without ORCID whose (name, affiliation) matches a record
│   that has an ORCID
└── Output: ~58,028 additional records recovered

PHASE 3 — Name normalization
├── Remaining records without ORCID
├── Grouped by canonical (normalized) name
└── Output: ~420,000 authors (confidence 0.7)
```

---

## Normalization algorithm

```python
def normalize_name(name: str) -> str:
    """Canonical form used for matching."""
    # Lowercase
    name = name.lower()
    # Strip accents (unidecode): garcía → garcia
    name = unidecode(name)
    # Normalize "María" variants
    for variant in ['mª', 'ma', 'm.ª', 'm.a', 'mᵃ']:
        name = name.replace(variant, 'maria')
    # Unify hyphens and spaces
    name = name.replace('-', ' ')
    # Drop punctuation
    name = re.sub(r'[.]', '', name)
    # Collapse whitespace
    return ' '.join(name.split())
```

### Examples

| Original | Normalized |
|---|---|
| García-Pavia, Pablo | garcia pavia, pablo |
| García Pavía, Pablo | garcia pavia, pablo |
| Garcia-Pavia, P | garcia pavia, p |
| Martínez, José Mª | martinez, jose maria |
| de Luis-Román, Daniel | de luis roman, daniel |

---

## Choosing the display name

### Ranking criteria

1. **With ORCID** — prefer the most complete form:
   - Full forenames over initials (`José` > `J`).
   - Accented forms over stripped (`García` > `Garcia`).
2. **Without ORCID** — prefer the most frequently seen form.

### Implementation

```python
def select_display_name(name_variants, counts):
    def score_name(name):
        has_full_name = not re.search(r', [A-Z](\s|$)', name)
        has_accents = bool(re.search(r'[áéíóúñüÁÉÍÓÚÑÜ]', name))
        frequency = counts.get(name, 0)
        length = len(name)
        return (has_full_name, has_accents, frequency, length)
    return max(name_variants, key=score_name)
```

---

## Table structure

### `sm_result.authors_orcid` — ~105,616 rows

ORCID-identified authors.

| Column | Type | Description |
|---|---|---|
| `sm_author_id` | SERIAL PK | Surrogate id |
| `author_orcid` | VARCHAR(50) UNIQUE | ORCID identifier |
| `display_name` | VARCHAR(500) | Preferred human-readable form |
| `canonical_name` | VARCHAR(500) | Normalized form |
| `name_variants` | TEXT[] | All observed spellings |
| `article_count` | INTEGER | Number of articles |
| `first_publication` | DATE | First seen publication date |
| `last_publication` | DATE | Latest publication date |

### `sm_result.authors_norm` — ~500,000–525,000 rows

All authors keyed by canonical name.

| Column | Type | Description |
|---|---|---|
| `sm_author_id` | SERIAL PK | Surrogate id |
| `canonical_name` | VARCHAR(500) UNIQUE | Normalized key |
| `display_name` | VARCHAR(500) | Preferred form |
| `author_orcid` | VARCHAR(50) | ORCID if any |
| `orcid_author_id` | INTEGER FK | Link to `authors_orcid` |
| `name_variants` | TEXT[] | All observed spellings |
| `confidence` | DECIMAL(3,2) | `1.0` (ORCID) or `0.7` (normalized) |
| `article_count` | INTEGER | Number of articles |
| `first_publication` | DATE | First publication |
| `last_publication` | DATE | Latest publication |

---

## Flow

```
raw.pubmed_authors (2,086,595 rows)
        │
        ▼
┌───────────────────────────────────────┐
│        DEDUPLICATION PIPELINE         │
│  (scripts/deduplicacion_autores.py)   │
└───────────────────────────────────────┘
        │
        ├──► sm_result.authors_orcid (105,616) — confidence 1.0
        │
        └──► sm_result.authors_norm (500,000–525,000)
             ├── with ORCID → confidence 1.0
             └── without ORCID → confidence 0.7
```

---

## Which table to use

| Use case | Table | Why |
|---|---|---|
| High-precision analysis | `authors_orcid` | 100% reliable |
| Name-based lookup | `authors_norm` | Covers every author |
| External ORCID linking | `authors_orcid` | ORCID is the key |
| General statistics | `authors_norm` | Full coverage |
| ML training data | `authors_orcid` | Low noise |

---

## Specialty coverage

### Authors with a detected SNOMED-CT specialty

| Metric | Value | % |
|---|---|---|
| With SNOMED specialty | 144,080 | 26.7% |
| Without detected specialty | 396,274 | 73.3% |
| Total | 540,354 | 100% |

### Top 10 specialties

| Specialty | Authors |
|---|---|
| Urology | 19,071 |
| Neurology | 14,292 |
| Cardiology | 13,262 |
| Internal Medicine | 11,066 |
| Medical Oncology | 8,409 |
| Radiology | 8,204 |
| Gastroenterology | 7,734 |
| Dermatology | 7,488 |
| Infectious Diseases | 6,604 |
| Psychiatry | 6,582 |

---

## Known limitations

1. **Homonymy.** Two different people with the same canonical name are
   merged in `authors_norm` when neither has an ORCID — nothing in the
   data allows us to tell them apart.
2. **ORCID propagation.** Only works with exact `(name, affiliation)`
   matches. Typos in affiliation defeat it.
3. **Initials.** `García, J` and `García, Juan` are *not* merged — they
   may or may not be the same person.
4. **ORCID coverage.** Only 20.31% of raw records carry an ORCID.

---

## Related files

| File | Purpose |
|---|---|
| `scripts/sql/create_authors_table.sql` | DDL for both result tables |
| `scripts/deduplicacion_autores.py` | Pipeline entry point |
| `src/utils/name_normalizer.py` | `normalize_name` implementation |

---

*Last updated: December 2024.*
