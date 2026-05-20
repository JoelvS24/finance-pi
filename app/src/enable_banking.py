"""Enable Banking client for Rabobank PSD2 access.

Handles JWT auth, the 90-day consent flow, account discovery, and transaction
fetching. Personal-tier free usage covers payment + savings + credit card.
Investment accounts (Rabo Beleggen) are NOT covered by PSD2 — see manual_import.py.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, date, timedelta, timezone

import httpx
import jwt
from cryptography.hazmat.primitives import serialization

from src.db import db_session
from src.models import Account, Balance, Consent, Transaction, SyncRun


API_BASE = "https://api.enablebanking.com"
APP_ID = os.environ.get("EB_APP_ID", "")
KEY_PATH = os.environ.get("EB_KEY_PATH", "/secrets/enable_banking.pem")


def _load_private_key():
    with open(KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _make_jwt() -> str:
    now = int(time.time())
    payload = {
        "iss": "enablebanking.com",
        "aud": "api.enablebanking.com",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(
        payload,
        _load_private_key(),
        algorithm="RS256",
        headers={"kid": APP_ID, "typ": "JWT"},
    )


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=API_BASE,
        headers={"Authorization": f"Bearer {_make_jwt()}"},
        timeout=30.0,
    )


def start_auth(redirect_url: str, valid_days: int = 90) -> dict:
    """Step 1 of the consent dance: get a URL to open in the bank's app."""
    valid_until = (datetime.now(timezone.utc) + timedelta(days=valid_days)).isoformat()
    body = {
        "access": {"valid_until": valid_until},
        "aspsp": {"name": "Rabobank", "country": "NL"},
        "state": str(uuid.uuid4()),
        "redirect_url": redirect_url,
        "psu_type": "personal",
    }
    with _client() as c:
        r = c.post("/auth", json=body)
        r.raise_for_status()
        return r.json()


def finish_auth(code: str) -> str:
    """Step 2: exchange the redirect code for a long-lived (90-day) session_id."""
    with _client() as c:
        r = c.post("/sessions", json={"code": code})
        r.raise_for_status()
        data = r.json()

    session_id = data["session_id"]
    accounts_payload = data.get("accounts", [])

    with db_session() as s:
        s.add(Consent(
            provider="enable_banking_rabobank",
            session_id=session_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            accounts=[a["uid"] for a in accounts_payload],
            active=True,
        ))
        for a in accounts_payload:
            existing = s.query(Account).filter_by(external_id=a["uid"]).first()
            if existing:
                continue
            s.add(Account(
                external_id=a["uid"],
                provider="rabobank",
                type=_map_account_type(a),
                name=a.get("name") or a.get("account_id", {}).get("iban", "Rabobank account"),
                currency=a.get("currency", "EUR"),
                active=True,
                created_at=datetime.now(timezone.utc),
            ))
    return session_id


def _map_account_type(account: dict) -> str:
    raw_type = (account.get("cash_account_type") or "").upper()
    product = (account.get("product") or "").lower()
    if raw_type == "CARD" or "credit" in product:
        return "credit_card"
    if "savings" in product or "spaar" in product:
        return "savings"
    return "payment"


def get_active_session() -> str | None:
    with db_session() as s:
        c = (
            s.query(Consent)
            .filter(Consent.active == True,
                    Consent.expires_at > datetime.now(timezone.utc),
                    Consent.provider == "enable_banking_rabobank")
            .order_by(Consent.created_at.desc())
            .first()
        )
        return c.session_id if c else None


def fetch_account(account_uid: str, since: date | None = None) -> tuple[int, int]:
    """Fetch transactions + balance for one account."""
    session_id = get_active_session()
    if not session_id:
        raise RuntimeError("No active Enable Banking session. Run bootstrap_eb.")

    since = since or (date.today() - timedelta(days=14))
    inserted = updated = 0

    with _client() as c:
        # Transactions (paginated)
        params: dict = {"date_from": since.isoformat()}
        while True:
            r = c.get(
                f"/accounts/{account_uid}/transactions",
                params=params,
                headers={"X-Session-Id": session_id},
            )
            r.raise_for_status()
            data = r.json()

            with db_session() as s:
                acct = s.query(Account).filter_by(external_id=account_uid).one()
                for t in data.get("transactions", []):
                    ext_id = t.get("entry_reference") or t.get("transaction_id") or _synth_id(t)
                    if s.query(Transaction).filter_by(account_id=acct.id, external_id=ext_id).first():
                        continue
                    amt = _signed_amount(t)
                    s.add(Transaction(
                        account_id=acct.id,
                        external_id=ext_id,
                        booked_at=date.fromisoformat(t["booking_date"]),
                        value_at=date.fromisoformat(t["value_date"]) if t.get("value_date") else None,
                        amount=amt,
                        currency=t["transaction_amount"]["currency"],
                        description=_compose_description(t),
                        counterparty_name=_counterparty_name(t, amt),
                        counterparty_iban=_counterparty_iban(t, amt),
                        raw=t,
                        created_at=datetime.now(timezone.utc),
                    ))
                    inserted += 1

            cursor = data.get("continuation_key")
            if not cursor:
                break
            params["continuation_key"] = cursor

        # Balance snapshot
        r = c.get(f"/accounts/{account_uid}/balances", headers={"X-Session-Id": session_id})
        r.raise_for_status()
        balances = r.json().get("balances", [])
        if balances:
            current = next((b for b in balances if b.get("balance_type") == "CLBD"), balances[0])
            amt = current["balance_amount"]
            with db_session() as s:
                acct = s.query(Account).filter_by(external_id=account_uid).one()
                s.add(Balance(
                    account_id=acct.id,
                    as_of=datetime.now(timezone.utc),
                    amount=amt["amount"],
                    currency=amt["currency"],
                    source="api",
                ))

    return inserted, updated


def fetch_all(since: date | None = None) -> None:
    """Fetch all Rabobank accounts under the active consent."""
    with db_session() as s:
        consent = (
            s.query(Consent)
            .filter_by(provider="enable_banking_rabobank", active=True)
            .order_by(Consent.created_at.desc())
            .first()
        )
        if not consent:
            raise RuntimeError("No active Rabobank consent.")
        account_uids = consent.accounts

    for uid in account_uids:
        run_id = _start_run("enable_banking")
        try:
            ins, upd = fetch_account(uid, since=since)
            _finish_run(run_id, "ok", ins, upd)
        except Exception as e:
            _finish_run(run_id, "error", 0, 0, str(e))
            raise


def _signed_amount(t: dict) -> float:
    amt = float(t["transaction_amount"]["amount"])
    return -amt if t.get("credit_debit_indicator") == "DBIT" else amt


def _compose_description(t: dict) -> str:
    parts: list[str] = []
    info = t.get("remittance_information")
    if isinstance(info, list):
        parts.extend([str(x) for x in info if x])
    elif info:
        parts.append(str(info))
    for key in ("creditor", "debtor"):
        name = t.get(key, {}).get("name") if isinstance(t.get(key), dict) else None
        if name:
            parts.append(name)
    return " | ".join(parts).strip(" |")


def _counterparty_name(t: dict, amount: float) -> str | None:
    key = "creditor" if amount < 0 else "debtor"
    val = t.get(key, {})
    return val.get("name") if isinstance(val, dict) else None


def _counterparty_iban(t: dict, amount: float) -> str | None:
    key = "creditor_account" if amount < 0 else "debtor_account"
    val = t.get(key, {})
    return val.get("iban") if isinstance(val, dict) else None


def _synth_id(t: dict) -> str:
    return f"{t.get('booking_date','')}-{t.get('transaction_amount',{}).get('amount','0')}-{hash(str(t))}"


def _start_run(provider: str) -> int:
    with db_session() as s:
        r = SyncRun(started_at=datetime.now(timezone.utc), provider=provider, status="running")
        s.add(r)
        s.flush()
        return r.id


def _finish_run(run_id: int, status: str, ins: int, upd: int, err: str | None = None):
    with db_session() as s:
        r = s.get(SyncRun, run_id)
        r.status = status
        r.finished_at = datetime.now(timezone.utc)
        r.rows_inserted = ins
        r.rows_updated = upd
        r.error_message = err
