"""Top-level daily sync job. Run as a systemd timer or cron.

Order:
  1. Rabobank (Enable Banking API)
  2. Trade Republic (pytr)
  3. GBI Sparen (CSV watcher)
  4. Rabo Beleggen (CSV watcher)
  5. Update prices for tracked instruments
  6. Categorize new transactions
  7. Check 90-day consent expiry
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

from src.enable_banking import fetch_all as fetch_rabo
from src.trade_republic import fetch_all as fetch_tr
from src.gbi_sparen import import_all as import_gbi
from src.manual_import import import_all as import_rabo_invest
from src.prices import update_all_prices
from src.categorizer import categorize_uncategorized
from src.notifier import notify, notify_error
from src.consent_check import check_consent_expiry


def main() -> int:
    errors: list[tuple[str, Exception]] = []

    # 1) Rabobank
    try:
        fetch_rabo(since=date.today() - timedelta(days=7))
        notify("✓ Rabobank synced")
    except Exception as e:
        errors.append(("rabobank", e))
        notify_error("✗ Rabobank sync failed", e)

    # 2) Trade Republic
    try:
        ins, skip = fetch_tr()
        notify(f"✓ Trade Republic: {ins} new, {skip} skipped")
    except Exception as e:
        errors.append(("trade_republic", e))
        notify_error("✗ Trade Republic sync failed", e)

    # 3) GBI Sparen
    try:
        n = import_gbi()
        if n:
            notify(f"✓ GBI Sparen: {n} new rows from CSV")
    except Exception as e:
        errors.append(("gbi", e))
        notify_error("✗ GBI Sparen import failed", e)

    # 4) Rabo Beleggen
    try:
        n = import_rabo_invest()
        if n:
            notify(f"✓ Rabo Beleggen: {n} new rows from CSV")
    except Exception as e:
        errors.append(("rabo_invest", e))

    # 5) Prices
    try:
        n = update_all_prices()
        if n:
            notify(f"✓ Updated {n} instrument prices")
    except Exception as e:
        errors.append(("prices", e))

    # 6) Categorize
    try:
        n = categorize_uncategorized()
        if n:
            notify(f"✓ Categorized {n} new transactions")
    except Exception as e:
        notify_error("Categorizer failed", e)

    # 7) Consent expiry check
    try:
        check_consent_expiry(warn_days=14)
    except Exception as e:
        notify_error("Consent check failed", e)

    if errors:
        print("Errors:", errors)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
