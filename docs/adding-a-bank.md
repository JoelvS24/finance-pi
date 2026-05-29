# Adding a new bank

The architecture supports multiple ingestion modes. Pick the one that matches
your bank:

## Mode 1: PSD2-covered (preferred)

If the bank is supported by Enable Banking, add it to the existing flow.

Edit `app/src/enable_banking.py` and add a new function:
```python
def start_auth_<bank>(redirect_url: str, ...):
    body = {
        ...
        "aspsp": {"name": "ING", "country": "NL"},  # or whatever
        ...
    }
```
Then add a new bootstrap script following `bootstrap_eb.py` as a template.

Note: Each PSD2 consent is per-bank and per-90 days. You'll have multiple
consents to renew if you connect multiple banks.

## Mode 2: Bank has a native API (Bunq, some German neobanks)

Create `app/src/<bank>.py` with its own client. Wire it into `orchestrator.py`.

For Bunq specifically, look at the official Python SDK:
`pip install bunq` — note it needs a paid Pro/Elite plan for API access.

## Mode 3: CSV/PDF import only (GBI, niche banks)

Follow the pattern in `app/src/gbi_sparen.py`:

1. Create a new module under `app/src/`
2. Create a watcher that scans `/data/imports/<bank>/`
3. Parse the rows, dedupe on a synthetic external_id
4. Move processed files to `/data/imports/processed/<bank>/`
5. Wire into `orchestrator.py`

## Mode 4: Web scraping

Don't. It violates ToS for every Dutch bank and breaks on every UI update.
If a bank truly can't be reached any other way, use a once-a-month CSV/PDF
export instead.
