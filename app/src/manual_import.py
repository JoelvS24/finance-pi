"""Rabo Beleggen (investment account) CSV import.

Rabobank does not expose investment accounts through PSD2. Workflow:
    1. Log into Rabobank online → Beleggen → Transactieoverzicht → Download CSV
    2. Drop the CSV into /data/imports/rabo_invest/
    3. The orchestrator picks it up on the next run
"""
from __future__ import annotations

import csv
import shutil
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from src.db import db_session
from src.models import Account, Transaction, SyncRun


IMPORTS_DIR = Path("/data/imports/rabo_invest")
PROCESSED_DIR = Path("/data/imports/processed/rabo_invest")
RABO_INVEST_EXTERNAL_ID = "rabo_invest"


def _ensure_account() -> int:
    with db_session() as s:
        a = s.query(Account).filter_by(external_id=RABO_INVEST_EXTERNAL_ID).first()
        if not a:
            a = Account(
                external_id=RABO_INVEST_EXTERNAL_ID,
                provider="rabobank",
                type="investment",
                name="Rabo Beleggen",
                currency="EUR",
                active=True,
                created_at=datetime.now(timezone.utc),
            )
            s.add(a)
            s.flush()
        return a.id


def import_all() -> int:
    if not IMPORTS_DIR.exists():
        return 0
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    run_id = _start_run()
    inserted = 0
    try:
        for csv_file in sorted(IMPORTS_DIR.glob("*.csv")):
            inserted += _process_csv(csv_file)
            shutil.move(str(csv_file), PROCESSED_DIR / csv_file.name)
        _finish_run(run_id, "ok", inserted, 0)
    except Exception as e:
        _finish_run(run_id, "error", inserted, 0, str(e))
        raise
    return inserted


def _process_csv(path: Path) -> int:
    """Rabo Beleggen CSV typically: Datum;Omschrijving;ISIN;Aantal;Koers;Bedrag.
    Adjust column names after inspecting your actual export.
    """
    account_id = _ensure_account()
    inserted = 0
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        with db_session() as s:
            for row in reader:
                date_str = row.get("Datum") or row.get("Boekdatum") or ""
                if not date_str:
                    continue
                booked = datetime.strptime(date_str.strip(), "%d-%m-%Y").date()
                amount_str = row.get("Bedrag") or row.get("Mutatie") or "0"
                amount = Decimal(amount_str.replace(".", "").replace(",", "."))
                isin = row.get("ISIN", "")
                desc = row.get("Omschrijving", "")
                ext_id = f"rabo-inv-{booked.isoformat()}-{isin}-{amount}"
                if s.query(Transaction).filter_by(account_id=account_id, external_id=ext_id).first():
                    continue
                s.add(Transaction(
                    account_id=account_id,
                    external_id=ext_id,
                    booked_at=booked,
                    amount=amount,
                    currency="EUR",
                    description=desc,
                    counterparty_name="Rabo Beleggen",
                    raw=dict(row),
                    created_at=datetime.now(timezone.utc),
                ))
                inserted += 1
    return inserted


def _start_run() -> int:
    with db_session() as s:
        r = SyncRun(started_at=datetime.now(timezone.utc), provider="rabo_invest_csv", status="running")
        s.add(r); s.flush()
        return r.id


def _finish_run(run_id, status, ins, upd, err=None):
    with db_session() as s:
        r = s.get(SyncRun, run_id)
        r.status = status
        r.finished_at = datetime.now(timezone.utc)
        r.rows_inserted = ins
        r.rows_updated = upd
        r.error_message = err
