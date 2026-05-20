"""Car expense tracking and cost-per-kilometer calculation.

Two sources of car expenses:
1. Bank transactions categorized under a 'car' category (auto, via categorizer)
2. Manual entries in `car_expenses` table (APK, tires, maintenance receipts not
   on bank statements, e.g. paid in cash)

The `v_car_spend` SQL view unifies both. Cost-per-km is computed from total
spend to date divided by km driven since purchase (or since the first odometer
reading we have, whichever is later).

ONLY paid expenses count — there are no scheduled/future projections in this
calculation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, timezone
from decimal import Decimal

from sqlalchemy import text

from src.db import db_session, engine
from src.models import Vehicle, OdometerReading, CarExpense, Category


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

def add_vehicle(
    name: str,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    license_plate: str | None = None,
    purchase_date: date | None = None,
    purchase_price: Decimal | float | None = None,
    purchase_odometer: int = 0,
) -> int:
    with db_session() as s:
        v = Vehicle(
            name=name,
            make=make,
            model=model,
            year=year,
            license_plate=license_plate,
            purchase_date=purchase_date,
            purchase_price=Decimal(str(purchase_price)) if purchase_price is not None else None,
            purchase_odometer=purchase_odometer,
            active=True,
            created_at=datetime.now(timezone.utc),
        )
        s.add(v)
        s.flush()
        return v.id


def list_vehicles() -> list[dict]:
    with db_session() as s:
        return [
            {
                "id": v.id, "name": v.name, "make": v.make, "model": v.model,
                "year": v.year, "license_plate": v.license_plate,
                "purchase_date": v.purchase_date.isoformat() if v.purchase_date else None,
                "purchase_odometer": v.purchase_odometer,
                "active": v.active,
            }
            for v in s.query(Vehicle).filter_by(active=True).all()
        ]


# ---------------------------------------------------------------------------
# Odometer
# ---------------------------------------------------------------------------

def add_odometer_reading(vehicle_id: int, odometer_km: int, as_of: date | None = None,
                         notes: str | None = None) -> int:
    with db_session() as s:
        r = OdometerReading(
            vehicle_id=vehicle_id,
            as_of=as_of or date.today(),
            odometer_km=odometer_km,
            notes=notes,
        )
        s.add(r)
        s.flush()
        return r.id


def latest_odometer(vehicle_id: int) -> tuple[date, int] | None:
    with db_session() as s:
        r = (
            s.query(OdometerReading)
            .filter_by(vehicle_id=vehicle_id)
            .order_by(OdometerReading.as_of.desc())
            .first()
        )
        return (r.as_of, r.odometer_km) if r else None


# ---------------------------------------------------------------------------
# Manual car expenses
# ---------------------------------------------------------------------------

def add_expense(
    vehicle_id: int,
    category_name: str,
    amount: Decimal | float,
    incurred_at: date | None = None,
    odometer_km: int | None = None,
    description: str | None = None,
    transaction_id: int | None = None,
) -> int:
    """Record a car expense. category_name must be one of the 'Car: ...' categories."""
    with db_session() as s:
        cat = s.query(Category).filter_by(name=category_name).first()
        if not cat:
            raise ValueError(f"Unknown category: {category_name}")
        if cat.kind != "car":
            raise ValueError(f"Category {category_name!r} is not a car category")
        e = CarExpense(
            vehicle_id=vehicle_id,
            incurred_at=incurred_at or date.today(),
            category_id=cat.id,
            amount=Decimal(str(amount)),
            odometer_km=odometer_km,
            description=description,
            transaction_id=transaction_id,
            created_at=datetime.now(timezone.utc),
        )
        s.add(e)
        s.flush()
        return e.id


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------

@dataclass
class CarStats:
    vehicle_id: int
    vehicle_name: str
    total_spent_eur: Decimal
    km_driven: int
    cost_per_km: Decimal | None
    purchase_price: Decimal | None
    purchase_odometer: int
    latest_odometer: int | None
    by_category: dict[str, Decimal]


def stats(vehicle_id: int) -> CarStats:
    """Compute total spent + cost-per-km for a vehicle. ONLY paid expenses count."""
    with db_session() as s:
        v = s.get(Vehicle, vehicle_id)
        if not v:
            raise ValueError(f"No vehicle with id {vehicle_id}")
        vehicle_name = v.name
        purchase_price = v.purchase_price
        purchase_odometer = v.purchase_odometer

    # Manual + bank expenses via the v_car_spend view
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT category, SUM(amount) AS total
                FROM v_car_spend
                WHERE vehicle_id = :vid OR vehicle_id IS NULL
                GROUP BY category
            """),
            {"vid": vehicle_id},
        ).fetchall()

    by_category: dict[str, Decimal] = {r[0]: Decimal(str(r[1])) for r in rows}
    total_spent = sum(by_category.values(), Decimal("0"))

    latest = latest_odometer(vehicle_id)
    latest_km = latest[1] if latest else None
    km_driven = (latest_km - purchase_odometer) if latest_km is not None else 0
    cost_per_km = (total_spent / km_driven) if km_driven > 0 else None

    return CarStats(
        vehicle_id=vehicle_id,
        vehicle_name=vehicle_name,
        total_spent_eur=total_spent,
        km_driven=km_driven,
        cost_per_km=cost_per_km,
        purchase_price=purchase_price,
        purchase_odometer=purchase_odometer,
        latest_odometer=latest_km,
        by_category=by_category,
    )
