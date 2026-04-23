# Configuration Reference

Runtime behaviour is controlled by:

1. **Environment variables** — always win.
2. **YAML files in [`config/`](../config/)** — provide defaults.
3. Command-line flags on the entry-point scripts.

See [`config/settings.py`](../config/settings.py) for the exact
precedence logic.

---

## Environment variables

Set them in a shell or via a local `.env` file (copy `.env.example` as a
starting point — `.env` is gitignored).

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `PUBMED_DB_HOST` | no | `localhost` | PostgreSQL host |
| `PUBMED_DB_PORT` | no | `5432` | PostgreSQL port |
| `PUBMED_DB_NAME` | no | `pubmed_db` | Database name |
| `PUBMED_DB_USER` | no | `pubmed_user` | Database user |
| `PUBMED_DB_PASSWORD` | **yes** | *(empty)* | Database password |
| `PUBMED_API_KEY` | no | *(unset)* | Raises the NCBI rate limit to 10 req/s |

If `PUBMED_API_KEY` is set it is forwarded to BioPython's `Entrez.email`
mechanism; otherwise the project stays within the unauthenticated
3 req/s quota.

---

## `config/pubmed_config.yaml`

Controls how the download client talks to NCBI.

| Key | Default | Notes |
|---|---|---|
| `rate_limiting.requests_per_second` | `3` | With no API key |
| `rate_limiting.requests_per_second_off_peak` | `10` | Off-peak: weekends + 9pm–5am EST |
| `batch.ids_per_batch` | `200` | `efetch` accepts up to 500 |
| `batch.search_batch_size` | `10000` | `esearch` `retmax` |
| `batch.max_retries` | `3` | Per-request retries (exponential backoff) |
| `batch.retry_delay` | `5` | Seconds between retries |
| `batch.batch_delay` | `30` | Safety pause between batches |
| `download.email` | *(placeholder)* | **Use a real one** — required by NCBI |
| `download.api_key` | `null` | Same as `PUBMED_API_KEY` env var |
| `download.database` | `"pubmed"` | Entrez database |
| `download.rettype` / `retmode` | `"xml"` / `"xml"` | |
| `search.query` | `"Spain[Affiliation]"` | NCBI search expression |
| `search.date_from` / `date_to` | `2015/01/01` / `2025/12/31` | Inclusive |
| `search.max_articles` | `null` | `null` = unlimited |
| `state.state_file` | `data/download_state.json` | Resume file |
| `state.save_frequency` | `100` | Save state every N articles |
| `state.log_dir` | `data/logs` | |
| `state.log_level` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `database_config.commit_frequency` | `50` | `COMMIT` every N articles |
| `database_config.use_transactions` | `true` | |
| `fault_tolerance.skip_malformed_records` | `true` | |
| `fault_tolerance.skip_db_errors` | `true` | |
| `fault_tolerance.save_error_records` | `true` | |
| `fault_tolerance.error_file` | `data/error_records.json` | |

---

## `config/db_config.yaml`

Provides PostgreSQL connection defaults. All values can be overridden by
the `PUBMED_DB_*` environment variables. Typical production setup leaves
the YAML with safe defaults and puts real credentials in `.env`.

```yaml
database:
  host: localhost
  port: 5432
  name: pubmed_db
  user: pubmed_user
  password: ""        # keep empty; use PUBMED_DB_PASSWORD env var

pool:
  min_connections: 1
  max_connections: 10
```

---

## `config/spanish_filters.yaml`

Defines what counts as a "Spanish affiliation" for
[`src/filters/spanish_filter.py`](../src/filters/spanish_filter.py).

- `spanish_markers` — required substrings to accept an affiliation
  (`spain`, `españa`, `spanish`, `español`, `espana`).
- `spanish_cities` — ~94 Spanish cities used as supporting evidence.
- `foreign_countries` — ~130 countries that **must not** appear in the
  affiliation text (used as a denylist to reject dual-affiliation
  records).

An affiliation is accepted iff it contains at least one Spanish marker
or Spanish city **and** none of the foreign-country names.

---

## Command-line flags

### `scripts/download_pubmed.py`

| Flag | Effect |
|---|---|
| *(none)* | Fresh download using `config/pubmed_config.yaml` |
| `--resume` | Resume from the state file |
| `--incremental` | Only new articles since last run (for cron) |
| `--config PATH` | Use an alternative YAML config |

### `scripts/cron_update.py`

| Flag | Effect |
|---|---|
| *(none)* | Full nightly update (download + specialty inference) |
| `--download-only` | Run only the download step |
| `--specialties-only` | Run only the specialty inference |
| `--dry-run` | Print what would run, do nothing |

### `scripts/populate_author_specialties.py`

| Flag | Effect |
|---|---|
| *(none)* | Recompute specialties for all authors |
| `--incremental` | Only authors that appeared since the last run |
