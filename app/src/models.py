"""SQLAlchemy ORM models matching the schema in app/sql/001_init.sql."""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String, unique=True)
    provider: Mapped[str]
    type: Mapped[str]
    name: Mapped[str]
    currency: Mapped[str] = mapped_column(String, default="EUR")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    kind: Mapped[str]
    icon: Mapped[str | None]
    color: Mapped[str | None]


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    external_id: Mapped[str]
    booked_at: Mapped[date]
    value_at: Mapped[date | None]
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(default="EUR")
    description: Mapped[str]
    counterparty_name: Mapped[str | None]
    counterparty_iban: Mapped[str | None]
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    rule_id: Mapped[int | None]
    notes: Mapped[str | None]
    raw: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    priority: Mapped[int] = mapped_column(default=100)
    enabled: Mapped[bool] = mapped_column(default=True)
    description_re: Mapped[str | None]
    counterparty_re: Mapped[str | None]
    iban_eq: Mapped[str | None]
    amount_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    amount_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Balance(Base):
    __tablename__ = "balances"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(default="EUR")
    source: Mapped[str]


class Instrument(Base):
    __tablename__ = "instruments"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str]
    isin: Mapped[str | None]
    name: Mapped[str]
    type: Mapped[str]
    currency: Mapped[str] = mapped_column(default="EUR")
    price_source: Mapped[str]
    source_id: Mapped[str | None]


class Holding(Base):
    __tablename__ = "holdings"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"))
    as_of: Mapped[date]
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    avg_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))


class Price(Base):
    __tablename__ = "prices"
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    as_of: Mapped[date] = mapped_column(primary_key=True)
    close: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    currency: Mapped[str] = mapped_column(default="EUR")


class ManualAsset(Base):
    __tablename__ = "manual_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[str]
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=1)
    unit: Mapped[str | None]
    value_eur: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    last_updated: Mapped[date]
    notes: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    make: Mapped[str | None]
    model: Mapped[str | None]
    year: Mapped[int | None]
    license_plate: Mapped[str | None]
    purchase_date: Mapped[date | None]
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    purchase_odometer: Mapped[int] = mapped_column(default=0)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OdometerReading(Base):
    __tablename__ = "odometer_readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    as_of: Mapped[date]
    odometer_km: Mapped[int]
    notes: Mapped[str | None]


class CarExpense(Base):
    __tablename__ = "car_expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    incurred_at: Mapped[date]
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    odometer_km: Mapped[int | None]
    description: Mapped[str | None]
    receipt_path: Mapped[str | None]
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str]
    session_id: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accounts: Mapped[list] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(default=True)


class SyncRun(Base):
    __tablename__ = "sync_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str]
    account_id: Mapped[int | None]
    status: Mapped[str]
    rows_inserted: Mapped[int] = mapped_column(default=0)
    rows_updated: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None]
