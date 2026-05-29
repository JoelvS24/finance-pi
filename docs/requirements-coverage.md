# Requirements coverage

Maps each user requirement to where it lives in the repo.

## Functional requirements

| # | Requirement | Where it lives | Status |
|---|---|---|---|
| 1 | Document goes into a GitHub repo | This repo's layout, `README.md`, `.gitignore`, `CLAUDE.md` | ✅ |
| 2 | Claude Code can extract everything | `CLAUDE.md` provides guidance; layout is conventional | ✅ |
| 3 | Pi 5 clone-and-run works | `scripts/setup-pi.sh` is idempotent | ✅ |
| 4 | Visual dashboard | `app/src/dashboard.py` (Streamlit) + Grafana | ✅ |
| 5 | Dashboard adaptable via Claude Design | `design/` folder with tokens.css, mockups.md, README.md | ✅ |
| 6 | Import Rabobank transactions | `app/src/enable_banking.py` (PSD2 API) | ✅ |
| 6 | Import Trade Republic transactions | `app/src/trade_republic.py` (pytr) | ✅ |
| 6 | Import GBI Sparen transactions | `app/src/gbi_sparen.py` (CSV watcher) | ✅ |
| 6 | Categorize transactions | `app/src/categorizer.py` + `app/sql/002_seed_rules.sql` | ✅ |
| 6 | Monitor savings account | `balances` table + Overview tab metric cards | ✅ |
| 6 | Track investments (auto where possible) | TR auto, Rabo Beleggen via CSV | ✅ |
| 6 | Manually add investments (stocks/gold/crypto) | Investments tab → "Add a holding" form | ✅ |
| 6 | Price tracking for those manual investments | `app/src/prices.py` (yfinance + CoinGecko + metal spot) | ✅ |
| 6 | Petrol costs extracted from bank | `app/sql/002_seed_rules.sql` rule "Petrol stations" → category "Car: Fuel" | ✅ |
| 6 | Separate car section in dashboard | 🚗 Car tab in `dashboard.py` | ✅ |
| 6 | Input extra car costs manually | Car tab → "Add manual car expense" form | ✅ |
| 6 | Average cost per km, ONLY based on paid | `car_tracker.stats()` uses `v_car_spend` view which includes only realized expenses | ✅ |
| 6 | Total wealth widget | Overview tab → top 4 metric cards (Total/Bank/Investments/Manual) | ✅ |
| 6 | Manual entry for cash/other valuables | Manual assets tab + `app/src/manual_assets.py` | ✅ |

## Where each thing is stored

```
Rabobank current/savings/credit card  →  accounts (provider=rabobank) + transactions
Rabobank Beleggen                     →  accounts (provider=rabobank, type=investment) + transactions
Trade Republic cash                   →  accounts (provider=trade_republic, type=savings) + transactions
Trade Republic investments            →  accounts (provider=trade_republic, type=investment) + transactions
GBI Sparen                            →  accounts (provider=gbi) + transactions
Stocks/gold/crypto (manual)           →  instruments + holdings + prices
Cash / jewelry / valuables            →  manual_assets
Cars                                  →  vehicles + odometer_readings + car_expenses
Categorization rules                  →  rules (priority-ordered)
90-day Enable Banking sessions        →  consents
Audit log of every sync               →  sync_runs
```

## Sources of truth — single-line summary

- "How much money do I have?" → sum(latest balances) + value_of_holdings + total_manual_assets
- "How much does my car cost per km?" → sum(car_expenses + bank txs with car category) / (latest_odometer - purchase_odometer)
- "What did I spend on groceries last month?" → SELECT SUM(amount) FROM transactions WHERE category='Groceries' AND booked_at >= ...
- "How much has my investment portfolio gained?" → SUM(qty * latest_price) - SUM(qty * avg_cost)

## How to extend with Claude Code

1. Open a Claude Code session in the repo root.
2. Claude Code reads `CLAUDE.md` automatically — it knows the conventions.
3. Ask things like:
   - "Add a SNS Bank importer following the gbi_sparen.py pattern"
   - "Add a budget envelope tracker — see design/mockups.md for the layout"
   - "Add a Telegram bot command to log a manual car expense from my phone"
4. Run tests (when they exist) with `pytest app/tests/`.

## Known gaps and trade-offs

| Gap | Why | Workaround |
|---|---|---|
| Rabobank investment account (Rabo Beleggen) | PSD2 doesn't cover investments | Monthly CSV upload via dashboard or `data/imports/rabo_invest/` |
| GBI Sparen | No public API, not on Enable Banking | Monthly CSV upload via dashboard or `data/imports/gbi/` |
| Trade Republic uses private API | TR has no public API | pytr is community-maintained, has held up well |
| 90-day PSD2 reauth | Mandated by EU regulation | Telegram alert 14 days before, then 30-second renewal |
| Cost-per-km bank txs not tied to specific vehicle | We don't know which car a Shell receipt was for if you own multiple | If you own one car, it's correctly attributed. For multiple, future work: tie transactions to vehicles via separate categories. |
