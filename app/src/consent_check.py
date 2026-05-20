"""Warn when the 90-day Enable Banking consent is nearly expired."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from src.db import db_session
from src.models import Consent
from src.notifier import notify


def check_consent_expiry(warn_days: int = 14) -> None:
    cutoff = datetime.now(timezone.utc) + timedelta(days=warn_days)
    with db_session() as s:
        soon = (
            s.query(Consent)
            .filter(Consent.active == True, Consent.expires_at < cutoff)
            .all()
        )
    for c in soon:
        days = (c.expires_at - datetime.now(timezone.utc)).days
        notify(
            f"⚠️ Enable Banking consent for *{c.provider}* expires in *{days} days*.\n"
            f"SSH into the Pi and run `python -m src.bootstrap_eb` to renew."
        )
