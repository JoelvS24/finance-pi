# Widget mockups

ASCII mockups for every widget in the dashboard. Update this file *before*
changing `dashboard.py` so the design intent stays documented.

---

## Tab 1 — Overview

The "am I OK?" tab. Total wealth at the very top, then current balances, then
this month's flow.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 💰 Total wealth                                                             │
│                                                                             │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│   │   Total     │ │ Bank & sav. │ │ Investments │ │ Manual      │           │
│   │             │ │             │ │             │ │ assets      │           │
│   │ € 47.392,18 │ │ € 18.420,55 │ │ € 24.871,63 │ │ € 4.100,00  │           │
│   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
│                                                                             │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│ Accounts                                                                    │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│   │ Rabo Betaal  │ │ Rabo Spaar   │ │ Rabo CC      │ │ TR Cash      │       │
│   │ payment      │ │ savings      │ │ credit_card  │ │ savings      │       │
│   │ € 2.184,33   │ │ € 12.000,00  │ │ -€ 234,11    │ │ € 4.470,33   │       │
│   └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│   ┌──────────────┐ ┌──────────────┐                                         │
│   │ GBI Sparen   │ │ Rabo Beleggen│                                         │
│   │ savings      │ │ investment   │                                         │
│   │ € 8.500,00   │ │ € 12.471,63  │                                         │
│   └──────────────┘ └──────────────┘                                         │
│                                                                             │
│ Monthly cashflow                                                            │
│  [grouped bar chart: income vs expense vs car, last 3-6 months]             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Key behavior:
- Total wealth = sum(latest balance per account) + value_of_holdings + total_manual_assets
- Account cards sorted by type then balance descending
- Negative balances (credit card debt) shown in red

---

## Tab 2 — Transactions

Browse, filter, and manually categorize transactions.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 247 transactions                                                            │
│ ⚠ 12 uncategorized — fix these to improve future auto-categorization        │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Date       │ Account     │ Amount      │ Description    │ Category      │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │ 2026-05-19 │ Rabo Betaal │ -€  42,18   │ AH To Go ...   │ Groceries     │ │
│ │ 2026-05-19 │ Rabo Betaal │ -€  68,42   │ Shell Almelo   │ Car: Fuel     │ │
│ │ 2026-05-18 │ Rabo Betaal │ +€2.450,00  │ SALARY ACME    │ Salary        │ │
│ │ 2026-05-18 │ Rabo CC     │ -€  18,99   │ Netflix.com    │ Subscriptions │ │
│ │ ...                                                                     │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

Future enhancement (not yet built): clicking a row opens a side panel to
re-categorize and create a new rule from the pattern.

---

## Tab 3 — Categories

Where the money goes. Donut chart on top, table below.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Spending by category (last 90 days)                                         │
│                                                                             │
│        ╭───────────╮                                                        │
│        │  Donut    │   Groceries        € 1.234,18                         │
│        │  chart    │   Car: Fuel        €   542,30                         │
│        │           │   Rent             €   850,00                         │
│        ╰───────────╯   Subscriptions    €   124,42                         │
│                        Eating Out       €   213,75                         │
│                        ...                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tab 4 — Investments

Unified view of all tradeable holdings: TR positions, Rabo Beleggen (from CSV),
and manually-added stocks/gold/crypto.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Holdings                                                                    │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Account │ Symbol │ Instrument          │ Qty    │ Cost   │ Price │ Value │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │ TR Inv  │ VWCE.DE│ Vanguard FTSE...    │  35.00 │ 92.40  │104.21 │3.647  │ │
│ │ TR Inv  │ BTC    │ Bitcoin             │   0.05 │ ...    │58.700 │2.935  │ │
│ │ Manual  │ XAU    │ Gold (per oz)       │   0.10 │ 1.870  │1.910  │  191  │ │
│ │ ...                                                                     │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐                                │
│ │ Market val │ │ Cost basis │ │ Unrealized │                                │
│ │ € 24.871   │ │ € 19.420   │ │ +€ 5.451   │                                │
│ │            │ │            │ │   +28.1%   │                                │
│ └────────────┘ └────────────┘ └────────────┘                                │
│                                                                             │
│ ───────────────────────────────────────────────────────────────────────     │
│                                                                             │
│ [+ Add a holding (stocks, gold, crypto)] form                               │
│ [Seed common instruments] button                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tab 5 — 🚗 Car

The dedicated car cost tracker.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🚗 Vehicles                                                                 │
│                                                                             │
│ Select vehicle: [ Swift Sport ▾ ]                                           │
│                                                                             │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐                 │
│ │ Total spent│ │ Km driven  │ │ Cost / km  │ │ Latest odo │                 │
│ │ (paid)     │ │            │ │            │ │            │                 │
│ │ € 3.847    │ │ 18.420 km  │ │ € 0,209/km │ │ 48.420 km  │                 │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘                 │
│                                                                             │
│ Cost-per-km is computed from money actually spent so far                    │
│ (bank-extracted fuel + manual entries) divided by km driven                 │
│ since purchase. No future projections.                                      │
│                                                                             │
│ Car expenses by category                                                    │
│  [bar chart: Fuel | Insurance | MRB | Maintenance | Tires | Parking ...]    │
│                                                                             │
│ #### Add odometer reading                                                   │
│   [number]  [date]                          [ Save reading ]                │
│                                                                             │
│ #### Add manual car expense                                                 │
│   Use this for cash payments or things not on the bank statement.           │
│   [Category ▾] [Date] [Amount €] [Odometer] [Description] [ Save ]          │
└─────────────────────────────────────────────────────────────────────────────┘
```

Key design decisions:
- The four metric cards are the at-a-glance summary
- `total spent` includes ONLY paid expenses (bank txs + manual entries past dates)
- `cost / km` = total_spent / (latest_odometer - purchase_odometer)
- Fuel costs are extracted automatically from bank transactions categorized "Car: Fuel"
- Manual expenses are for things NOT on bank statements (cash payments, receipts you photograph)

---

## Tab 6 — Manual assets

Cash, valuables, jewelry — anything without a bank API and without a market price.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Other assets (cash, valuables, untracked)                                   │
│                                                                             │
│ ┌──────────────────────────────────────────────────────────────────────┐    │
│ │ Name           │ Type    │ Qty  │ Unit │ Value EUR │ Last updated    │    │
│ ├──────────────────────────────────────────────────────────────────────┤    │
│ │ Cash in wallet │ cash    │ 1    │ EUR  │   180,00  │ 2026-05-19      │    │
│ │ Wedding ring   │ jewelry │ 1    │ pcs  │ 2.500,00  │ 2025-12-01      │    │
│ │ Bike           │ vehicle │ 1    │ pcs  │ 1.200,00  │ 2026-01-15      │    │
│ │ Watch          │ watch   │ 1    │ pcs  │   220,00  │ 2025-06-04      │    │
│ └──────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│ Total manual assets: € 4.100,00                                             │
│                                                                             │
│ #### Add an asset                                                           │
│   [Name] [Type ▾] [Value EUR] [Quantity] [Unit] [Notes]   [ Add ]           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Future widgets (not yet built)

- **Subscription detector** — flag recurring charges; alert on price increases
- **Budget envelope tracker** — set monthly limits per category
- **Net worth over time** — line chart of total wealth, sampled daily
- **Forecast** — projection of next 30 days based on recurring transactions
- **Tax helper** — Box 3 calculation for NL (peildatum 1 januari)
