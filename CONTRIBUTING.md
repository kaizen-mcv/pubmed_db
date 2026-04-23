# Contributing

Contributions are welcome. Please open an issue first to discuss anything
larger than a typo or a minor fix.

## Development setup

```bash
git clone git@github.com:kaizen-mcv/pubmed_db.git
cd pubmed_db
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"          # ruff + pytest
cp .env.example .env             # fill in your values
```

A local PostgreSQL instance is required to run the end-to-end flow but
**not** to run the unit test suite.

## Running the checks

```bash
pytest tests/ -v                 # unit tests
ruff check .                     # lint
ruff format --check .            # style
```

The same checks run on every pull request via GitHub Actions.

## Pull requests

- Branch off `main`.
- Keep commits focused; write messages in English (`<type>: <subject>`).
- Update documentation (`README.md`, `docs/`) when behaviour changes.
- Make sure the CI suite is green before requesting review.

## Code style

- Python 3.10+. Type hints are encouraged, especially at module
  boundaries.
- Formatting is enforced by `ruff format` (line length 100).
- Logging instead of `print` for anything that is not CLI output.
- Secrets go through environment variables or `.env` — never commit them.