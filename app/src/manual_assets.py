"""Manual asset tracking.

For anything not connected via a bank API: cash in your wallet, jewelry, watches,
art, collectibles. These are static value entries that you update periodically.

For tradeable holdings (stocks, gold, crypto) that you want auto-priced, use
the `holdings` + `instruments` + `prices` flow instead — see prices.py.
"""
from __future__ import annotations

from datetime import datetime, date, timezone
from decimal import Decimal

from src.db import db_session
from src.models import ManualAsset


VALID_TYPES = {"cash", "jewelry", "watch", "art", "vehicle", "collectible", "other"}


def add_asset(
    name: str,
    asset_type: str,
    value_eur: Decimal | float,
    quantity: Decimal | float = 1,
    unit: str | None = None,
    notes: str | None = None,
) -> int:
    """Create a new manual asset entry. Returns the new asset's id."""
    if asset_type not in VALID_TYPES:
        raise ValueError(f"asset_type must be one of {VALID_TYPES}, got {asset_type!r}")
    with db_session() as s:
        a = ManualAsset(
            name=name,
            type=asset_type,
            quantity=Decimal(str(quantity)),
            unit=unit,
            value_eur=Decimal(str(value_eur)),
            last_updated=date.today(),
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        s.add(a)
        s.flush()
        return a.id


def update_value(asset_id: int, new_value_eur: Decimal | float, notes: str | None = None) -> None:
    """Update the current valuation of an asset (e.g. revalue jewelry yearly)."""
    with db_session() as s:
        a = s.get(ManualAsset, asset_id)
        if not a:
            raise ValueError(f"No manual asset with id {asset_id}")
        a.value_eur = Decimal(str(new_value_eur))
        a.last_updated = date.today()
        if notes is not None:
            a.notes = notes


def delete_asset(asset_id: int) -> None:
    with db_session() as s:
        a = s.get(ManualAsset, asset_id)
        if a:
            s.delete(a)


def total_value() -> Decimal:
    """Return the total EUR value of all manual assets."""
    with db_session() as s:
        rows = s.query(ManualAsset).all()
        return sum((a.value_eur for a in rows), Decimal("0"))


def list_assets() -> list[dict]:
    """Return all assets as plain dicts (UI-friendly)."""
    with db_session() as s:
        return [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type,
                "quantity": float(a.quantity),
                "unit": a.unit,
                "value_eur": float(a.value_eur),
                "last_updated": a.last_updated.isoformat(),
                "notes": a.notes,
            }
            for a in s.query(ManualAsset).order_by(ManualAsset.value_eur.desc()).all()
        ]
