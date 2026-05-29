"""GBI Sparen (Garanti BBVA International) statement import.

GBI Sparen does NOT expose a public API and is not covered by PSD2 in a way
that's accessible to personal aggregators. Workflow:
    1. Open the GBI Sparen app → Statements → Download CSV
    2. Drop the CSV into /data/imports/gbi/
    3. The orchestrator will pick it up on the next run

Tip: GBI also offers PDF statements. If you only have PDFs, the included
`pdf_to_csv` helper uses pdfplumber as a best-effort fallback.
"""
from __future__ import annotations

import csv
import shutil
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from src.db import db_session
from src.models import Account, Balance, Transaction, SyncRun


IMPORTS_DIR = Path("/data/imports/gbi")
PROCESSED_DIR = Path("/data/imports/processed/gbi")
GBI_EXTERNAL_ID = "gbi_sparen"


def _ensure_account() -> int:
    with db_session() as s:
        a = s.query(Account).filter_by(external_id=GBI_EXTERNAL_ID).first()
        if not a:
            a = Account(
                external_id=GBI_EXTERNAL_ID,
                provider="gbi",
                type="savings",
                name="GBI Sparen (Garanti BBVA)",
                currency="EUR",
                active=True,
                created_at=datetime.now(timezone.utc),
            )
            s.add(a)
            s.flush()
        return a.id


def import_all() -> int:
    """Process every CSV in the imports dir. Returns total rows inserted."""
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
    """GBI CSV format (verify against your actual export — may vary):
        Datum;Omschrijving;Tegenrekening;Bedrag;Saldo
    """
    account_id = _ensure_account()
    inserted = 0
    latest_balance: Decimal | None = None

    with open(path, encoding="utf-8") as f:
        # Try comma-delimited first, fall back to semicolon
        sample = f.read(4096)
        f.seek(0)
        delim = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=delim)

        with db_session() as s:
            for row in reader:
                # Normalize column names — GBI has used several formats over the years
                booked_str = (
                    row.get("Datum") or row.get("Date") or row.get("Boekdatum") or ""
                )
                if not booked_str:
                    continue
                booked = _parse_date(booked_str)
                amount_str = (
                    row.get("Bedrag") or row.get("Amount") or row.get("Mutatie") or "0"
                )
                amount = _parse_amount(amount_str)
                desc = row.get("Omschrijving") or row.get("Description") or ""
                counterparty = row.get("Tegenrekening") or row.get("Counterparty") or ""

                ext_id = f"gbi-{booked.isoformat()}-{amount}-{hash(desc)}"
                if s.query(Transaction).filter_by(account_id=account_id, external_id=ext_id).first():
                    continue

                s.add(Transaction(
                    account_id=account_id,
                    external_id=ext_id,
                    booked_at=booked,
                    amount=amount,
                    currency="EUR",
                    description=desc,
                    counterparty_iban=counterparty if "NL" in counterparty.upper() else None,
                    raw=dict(row),
                    created_at=datetime.now(timezone.utc),
                ))
                inserted += 1

                saldo_str = row.get("Saldo") or row.get("Balance")
                if saldo_str:
                    latest_balance = _parse_amount(saldo_str)

            # Persist the last seen balance as a snapshot
            if latest_balance is not None:
                s.add(Balance(
                    account_id=account_id,
                    as_of=datetime.now(timezone.utc),
                    amount=latest_balance,
                    currency="EUR",
                    source="csv",
                ))

    return inserted


def _parse_date(s: str):
    """Try DD-MM-YYYY, YYYY-MM-DD, DD/MM/YYYY."""
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {s!r}")


def _parse_amount(s: str) -> Decimal:
    """Handle '1.234,56' (NL) and '1234.56' (US) and '-1.234,56'."""
    s = s.strip()
    if not s:
        return Decimal("0")
    # NL style: thousands separator '.', decimal ','
    if "," in s and (s.rfind(",") > s.rfind(".")):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    return Decimal(s)


def _start_run() -> int:
    with db_session() as s:
        r = SyncRun(started_at=datetime.now(timezone.utc), provider="gbi_sparen", status="running")
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
