# Finance Pi

A self-hosted personal finance system for the Raspberry Pi 5.

Tracks Rabobank, Trade Republic, GBI Sparen, manual investments (stocks/gold/crypto),
car expenses, and any other valuables — all in one PostgreSQL database, with a
Streamlit dashboard and Grafana time-series view.

**Stack:** Pi 5 · Docker · PostgreSQL · Python 3.12 · Streamlit · Grafana · Tailscale

---

## Quick start

On a Raspberry Pi 5 with Docker installed:

```bash
git clone https://github.com/<your-username>/finance-pi.git
cd finance-pi

# Copy and fill in secrets
cp secrets/.env.example secrets/.env
$EDITOR secrets/.env

# Generate the Enable Banking key pair
openssl genrsa -out secrets/enable_banking.pem 2048
openssl rsa -in secrets/enable_banking.pem -pubout -out secrets/enable_banking_public.pem

# Start the stack
docker compose -f compose/docker-compose.yml up -d

# Apply the database schema
docker compose -f compose/docker-compose.yml exec -T postgres \
    psql -U finance -d finance < app/sql/001_init.sql
docker compose -f compose/docker-compose.yml exec -T postgres \
    psql -U finance -d finance < app/sql/002_seed_rules.sql

# Bootstrap Enable Banking (first-time 90-day consent)
docker compose -f compose/docker-compose.yml run --rm app python -m src.bootstrap_eb

# Bootstrap Trade Republic
docker compose -f compose/docker-compose.yml run --rm -it app pytr login

# Visit the dashboard at http://<pi-ip>:8501
# Visit Grafana at http://<pi-ip>:3000
```

See [docs/setup.md](docs/setup.md) for the full step-by-step.

## Features

| Feature | Source | Status |
|---|---|---|
| Rabobank payment account | Enable Banking API | Auto |
| Rabobank savings account | Enable Banking API | Auto |
| Rabobank credit card | Enable Banking API | Auto |
| Rabobank investment (Beleggen) | CSV upload | Manual |
| Trade Republic cash + investments | pytr (private API) | Auto |
| GBI Sparen (Garanti BBVA) | CSV/PDF upload | Manual |
| Stocks (outside TR) | manual entry + yfinance prices | Manual + auto prices |
| Gold / silver / precious metals | manual entry + LBMA/spot price | Manual + auto prices |
| Crypto | manual entry + CoinGecko free API | Manual + auto prices |
| Cash, valuables, other | manual entry | Manual |
| Car expenses (fuel) | Auto-categorized bank transactions | Auto |
| Car expenses (insurance/APK/tires) | Manual entry | Manual |
| Cost per kilometer | Computed from total spent + odometer | Auto-derived |
| Total wealth widget | Aggregates everything above | Auto |
| Daily sync | systemd timer at 06:00 | Auto |
| Telegram notifications | Bot for sync results + reauth reminders | Auto |
| Backups | Encrypted nightly Postgres dump | Auto |

## Repo layout

```
finance-pi/
├── README.md                ← you are here
├── CLAUDE.md                ← guidance for Claude Code
├── .gitignore
├── compose/
│   └── docker-compose.yml
├── app/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── sql/                 ← versioned schema
│   │   ├── 001_init.sql
│   │   └── 002_seed_rules.sql
│   └── src/                 ← Python modules
│       ├── db.py
│       ├── models.py
│       ├── enable_banking.py    ← Rabobank PSD2
│       ├── trade_republic.py    ← pytr wrapper
│       ├── gbi_sparen.py        ← GBI CSV importer
│       ├── manual_import.py     ← Rabo Beleggen CSV
│       ├── manual_assets.py     ← cash / valuables / non-tracked assets
│       ├── car_tracker.py       ← fuel + manual costs + cost/km
│       ├── prices.py            ← stocks (yfinance) + crypto (CoinGecko) + gold (spot)
│       ├── categorizer.py
│       ├── notifier.py          ← Telegram
│       ├── consent_check.py     ← 90-day reauth warning
│       ├── orchestrator.py      ← daily sync entry point
│       ├── bootstrap_eb.py      ← first-time EB consent
│       └── dashboard.py         ← Streamlit UI
├── design/                  ← Claude Design inputs
│   ├── README.md            ← design system overview
│   ├── mockups.md           ← widget specs and layout
│   └── tokens.css           ← color / typography tokens
├── scripts/
│   ├── backup.sh
│   └── setup-pi.sh          ← idempotent bootstrap
├── secrets/                 ← gitignored, you populate these
│   └── .env.example
├── data/                    ← gitignored, persisted state
│   ├── imports/             ← drop CSVs here for ingestion
│   ├── postgres/            ← postgres data volume
│   └── grafana/             ← grafana data volume
└── docs/
    ├── setup.md             ← the master walkthrough
    ├── adding-a-bank.md
    └── troubleshooting.md
```

## License

Personal use only. No warranty — this code is automating access to your real money,
review every line before you run it.
