# Guidance for Claude Code

You're working in a self-hosted finance application that runs on a Raspberry Pi 5.
Read this first before making changes.

## Project shape

- Single-user, runs on local network only (plus Tailscale for remote)
- Python 3.12, SQLAlchemy 2.0, FastAPI/Streamlit stack
- PostgreSQL 16 as primary store
- Docker Compose for orchestration
- All modules live under `app/src/`
- All SQL migrations under `app/sql/` (numbered, applied in order)

## Conventions

- **Imports**: absolute (`from src.db import ...`), never relative
- **Type hints**: required on every public function (`from __future__ import annotations`)
- **Database access**: always via `db_session()` context manager from `src.db`
- **External IDs**: every transaction/holding/asset must have a stable, idempotent `external_id` so re-runs don't duplicate rows
- **Money**: use `Decimal`, never `float`. Store as `NUMERIC(12, 2)` in Postgres
- **Dates**: store dates as `DATE`, timestamps as `TIMESTAMPTZ`, always UTC at storage layer
- **Secrets**: read from environment, never hardcoded. `.env` is gitignored

## Where to add things

| You want to... | Edit |
|---|---|
| Add a new bank importer | New file under `app/src/`, wire into `orchestrator.py` |
| Add a new transaction category | `app/sql/002_seed_rules.sql` + Streamlit UI for editing |
| Add a categorization rule | UI (preferred) or `002_seed_rules.sql` for defaults |
| Add a new dashboard widget | Edit `app/src/dashboard.py`, then update `design/mockups.md` |
| Change the schema | New migration file `app/sql/NNN_what_changed.sql`, never edit existing migrations |
| Add a price source | Extend `app/src/prices.py` |
| Add a manual asset type | Update the `manual_assets` table check constraint + UI |

## Running tests

There aren't any yet. If you add a feature, add a test in `app/tests/` using pytest.

## Running the app locally

```bash
docker compose -f compose/docker-compose.yml up -d postgres
docker compose -f compose/docker-compose.yml run --rm app python -m src.orchestrator
docker compose -f compose/docker-compose.yml up -d app grafana
```

## Things to never do

- Never store bank passwords, PINs, or API keys in code or git
- Never write directly to production data without going through `db_session()` (no raw `psql` updates)
- Never `pip install` outside the container — modify `pyproject.toml` and rebuild
- Never use `latest` Docker image tags — pin versions
- Never commit anything from `secrets/`, `data/`, or `backups/`

## Design changes

When changing the dashboard UI:
1. Update `design/mockups.md` first to describe the new widget
2. Then implement in `app/src/dashboard.py`
3. The design tokens in `design/tokens.css` are the source of truth for colors and spacing

## Deployment

The Pi runs `git pull && docker compose up -d --build` to deploy. There's no CI yet.
A `scripts/setup-pi.sh` script handles first-time provisioning.
