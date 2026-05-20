"""Trade Republic ingestion via pytr (unofficial private API).

We shell out to `pytr export_transactions` to produce a CSV, then parse it.
This is more robust than reimplementing the timeline traversal ourselves.
"""
from __future__ import annotations

import csv
import subprocess
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from src.db import db_session
from src.models import Account, Transaction, SyncRun


TR_CASH_ID = "trade_republic_cash"
TR_INV_ID = "trade_republic_inv"

INVESTMENT_TYPES = {"TRADE_BUY", "TRADE_SELL", "DIVIDEND", "SAVINGS_PLAN", "TRADE_INVOICE"}


def _ensure_accounts() -> tuple[int, int]:
    with db_session() as s:
        cash = s.query(Account).filter_by(external_id=TR_CASH_ID).first()
        if not cash:
            cash = Account(
                external_id=TR_CASH_ID,
                provider="trade_republic",
                type="savings",
                name="Trade Republic Cash",
                currency="EUR",
                active=True,
                created_at=datetime.now(timezone.utc),
            )
            s.add(cash)
            s.flush()
        inv = s.query(Account).filter_by(external_id=TR_INV_ID).first()
        if not inv:
            inv = Account(
                external_id=TR_INV_ID,
                provider="trade_republic",
                type="investment",
                name="Trade Republic Investments",
                currency="EUR",
                active=True,
                created_at=datetime.now(timezone.utc),
            )
            s.add(inv)
            s.flush()
        return cash.id, inv.id


def fetch_all() -> tuple[int, int]:
    """Run pytr, parse CSV, upsert. Returns (inserted, skipped)."""
    cash_id, inv_id = _ensure_accounts()
    run_id = _start_run()
    inserted = skipped = 0

    try:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                ["pytr", "export_transactions"],
                cwd=tmp, check=True, capture_output=True, text=True,
            )

            csv_path = Path(tmp) / "account_transactions.csv"
            if not csv_path.exists():
                raise RuntimeError(f"pytr did not produce {csv_path}")

            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                with db_session() as s:
                    for row in reader:
                        ext_id = row.get("ID") or row.get("id") or _synth_id(row)
                        booked_str = row.get("Datum") or row.get("date")
                        if not booked_str:
                            continue
                        booked = datetime.fromisoformat(booked_str.split("T")[0]).date()
                        amount = Decimal(
                            (row.get("Wert") or row.get("value") or "0").replace(",", ".")
                        )
                        desc = row.get("Notiz") or row.get("note") or row.get("Typ") or ""

                        tx_type = (row.get("Typ") or row.get("type") or "").upper()
                        account_id = inv_id if tx_type in INVESTMENT_TYPES else cash_id

                        existing = (
                            s.query(Transaction)
                            .filter_by(account_id=account_id, external_id=ext_id)
                            .first()
                        )
                        if existing:
                            skipped += 1
                            continue
                        s.add(Transaction(
                            account_id=account_id,
                            external_id=ext_id,
                            booked_at=booked,
                            amount=amount,
                            currency="EUR",
                            description=desc,
                            counterparty_name="Trade Republic",
                            raw=dict(row),
                            created_at=datetime.now(timezone.utc),
                        ))
                        inserted += 1

        _finish_run(run_id, "ok", inserted, skipped)
    except Exception as e:
        _finish_run(run_id, "error", inserted, skipped, str(e))
        raise

    return inserted, skipped


def _synth_id(row: dict) -> str:
    return f"tr-{row.get('Datum','')}-{row.get('Wert','0')}-{hash(str(row))}"


def _start_run() -> int:
    with db_session() as s:
        r = SyncRun(started_at=datetime.now(timezone.utc), provider="trade_republic", status="running")
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
