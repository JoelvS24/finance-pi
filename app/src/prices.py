"""Price fetching for tracked instruments.

Sources:
- yfinance: stocks, ETFs (free, no auth, sometimes rate-limited)
- CoinGecko: crypto (free tier, 10-30 calls/min, no auth needed for basic price)
- Metal spot (via yfinance proxies for XAU/USD, XAG/USD)

Holdings × latest price = current market value, used by the total-wealth widget.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

import httpx
import yfinance as yf

from src.db import db_session, engine
from src.models import Instrument, Price, Holding


# ---------------------------------------------------------------------------
# Instrument management
# ---------------------------------------------------------------------------

def add_instrument(
    symbol: str,
    name: str,
    instrument_type: str,
    price_source: str,
    source_id: str | None = None,
    isin: str | None = None,
    currency: str = "EUR",
) -> int:
    """Register a new tradeable instrument. After this, prices can be fetched."""
    if price_source not in {"yfinance", "coingecko", "metal_spot", "manual"}:
        raise ValueError(f"Unknown price_source: {price_source}")
    with db_session() as s:
        existing = s.query(Instrument).filter_by(symbol=symbol, type=instrument_type).first()
        if existing:
            return existing.id
        i = Instrument(
            symbol=symbol,
            isin=isin,
            name=name,
            type=instrument_type,
            currency=currency,
            price_source=price_source,
            source_id=source_id or symbol,
        )
        s.add(i)
        s.flush()
        return i.id


# ---------------------------------------------------------------------------
# Holdings
# ---------------------------------------------------------------------------

def set_holding(account_id: int, instrument_id: int, quantity: Decimal | float,
                avg_cost: Decimal | float | None = None, as_of: date | None = None) -> None:
    """Upsert a holding for an account on a given date.

    Use this for manual entries: 'I own 0.5 BTC in my Ledger', '12.3g of gold at Holland Gold'.
    """
    with db_session() as s:
        as_of = as_of or date.today()
        existing = (
            s.query(Holding)
            .filter_by(account_id=account_id, instrument_id=instrument_id, as_of=as_of)
            .first()
        )
        if existing:
            existing.quantity = Decimal(str(quantity))
            if avg_cost is not None:
                existing.avg_cost = Decimal(str(avg_cost))
        else:
            h = Holding(
                account_id=account_id,
                instrument_id=instrument_id,
                as_of=as_of,
                quantity=Decimal(str(quantity)),
                avg_cost=Decimal(str(avg_cost)) if avg_cost is not None else None,
            )
            s.add(h)


# ---------------------------------------------------------------------------
# Price fetching
# ---------------------------------------------------------------------------

def fetch_yfinance(symbol: str) -> Decimal | None:
    """Latest close price via yfinance. Returns None on failure."""
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if hist.empty:
            return None
        return Decimal(str(round(float(hist["Close"].iloc[-1]), 4)))
    except Exception as e:
        print(f"[prices] yfinance {symbol}: {e}")
        return None


def fetch_coingecko(coin_id: str, vs_currency: str = "eur") -> Decimal | None:
    """Latest price via CoinGecko free API. coin_id is the gecko id, e.g. 'bitcoin'."""
    try:
        r = httpx.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": vs_currency},
            timeout=10,
        )
        r.raise_for_status()
        return Decimal(str(r.json()[coin_id][vs_currency]))
    except Exception as e:
        print(f"[prices] coingecko {coin_id}: {e}")
        return None


def fetch_metal_spot(symbol: str) -> Decimal | None:
    """Metal spot prices. symbol = 'XAU' (gold), 'XAG' (silver), 'XPT' (platinum).
    Uses yfinance futures contracts (GC=F for gold, SI=F for silver) as a proxy.
    Returns price per troy ounce in USD; convert to EUR/gram in the caller if needed.
    """
    proxy = {"XAU": "GC=F", "XAG": "SI=F", "XPT": "PL=F", "XPD": "PA=F"}.get(symbol.upper())
    if not proxy:
        return None
    return fetch_yfinance(proxy)


def update_all_prices() -> int:
    """Fetch latest price for every instrument and write to `prices` table.
    Returns count of prices updated."""
    today = date.today()
    updated = 0
    with db_session() as s:
        instruments = s.query(Instrument).all()
        for i in instruments:
            price: Decimal | None = None
            if i.price_source == "yfinance":
                price = fetch_yfinance(i.source_id or i.symbol)
            elif i.price_source == "coingecko":
                price = fetch_coingecko(i.source_id or i.symbol.lower())
            elif i.price_source == "metal_spot":
                price = fetch_metal_spot(i.source_id or i.symbol)
            elif i.price_source == "manual":
                continue  # Set manually via UI

            if price is not None:
                existing = (
                    s.query(Price)
                    .filter_by(instrument_id=i.id, as_of=today)
                    .first()
                )
                if existing:
                    existing.close = price
                else:
                    s.add(Price(
                        instrument_id=i.id,
                        as_of=today,
                        close=price,
                        currency=i.currency,
                    ))
                updated += 1
    return updated


# ---------------------------------------------------------------------------
# Holding valuation
# ---------------------------------------------------------------------------

def value_of_holdings() -> Decimal:
    """Current market value of all holdings using latest known prices."""
    from sqlalchemy import text
    with engine.connect() as conn:
        # Take the most recent holding row per (account, instrument), multiply by
        # the most recent price.
        rows = conn.execute(text("""
            WITH latest_holdings AS (
                SELECT DISTINCT ON (account_id, instrument_id)
                       account_id, instrument_id, quantity
                FROM holdings
                ORDER BY account_id, instrument_id, as_of DESC
            ),
            latest_prices AS (
                SELECT DISTINCT ON (instrument_id)
                       instrument_id, close
                FROM prices
                ORDER BY instrument_id, as_of DESC
            )
            SELECT COALESCE(SUM(h.quantity * p.close), 0)
            FROM latest_holdings h
            JOIN latest_prices  p ON p.instrument_id = h.instrument_id
        """)).scalar_one()
    return Decimal(str(rows or 0))


# ---------------------------------------------------------------------------
# Convenience: bootstrap common instruments
# ---------------------------------------------------------------------------

def seed_common_instruments() -> None:
    """Register popular EU ETFs, BTC/ETH, gold/silver. Idempotent."""
    common = [
        # ETFs
        ("VWCE.DE",  "Vanguard FTSE All-World",        "etf",            "yfinance",   "VWCE.DE"),
        ("IWDA.AS",  "iShares Core MSCI World",        "etf",            "yfinance",   "IWDA.AS"),
        ("VWRL.AS",  "Vanguard FTSE All-World",        "etf",            "yfinance",   "VWRL.AS"),
        ("EUNL.DE",  "iShares Core MSCI World UCITS",  "etf",            "yfinance",   "EUNL.DE"),
        # Crypto
        ("BTC",      "Bitcoin",                        "crypto",         "coingecko",  "bitcoin"),
        ("ETH",      "Ethereum",                       "crypto",         "coingecko",  "ethereum"),
        # Precious metals
        ("XAU",      "Gold (spot, per oz USD)",        "precious_metal", "metal_spot", "XAU"),
        ("XAG",      "Silver (spot, per oz USD)",      "precious_metal", "metal_spot", "XAG"),
    ]
    for sym, name, t, ps, sid in common:
        add_instrument(symbol=sym, name=name, instrument_type=t, price_source=ps, source_id=sid)


if __name__ == "__main__":
    # Run as a script to refresh prices once.
    n = update_all_prices()
    print(f"Updated {n} prices")
