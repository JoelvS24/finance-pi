"""Streamlit dashboard for Finance Pi.

Pages:
  • Overview          — total wealth, key balances, monthly cashflow
  • Transactions      — browse, categorize manually, add rules
  • Categories        — spending breakdown
  • Investments       — TR + Rabo Beleggen + manual stocks/gold/crypto
  • Car               — fuel costs + manual costs + cost-per-km
  • Manual Assets     — cash, valuables, untracked stuff
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text

from src.db import engine, db_session
from src.models import (
    Account, Category, Transaction, Vehicle, ManualAsset, Instrument, Holding
)
from src import car_tracker, manual_assets, prices

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Finance Pi", layout="wide", page_icon="💰")

# Inject design tokens (loaded from design/tokens.css if present)
try:
    with open("/app/design/tokens.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_transactions(start: date, end: date) -> pd.DataFrame:
    q = text("""
        SELECT t.id, t.booked_at, t.amount, t.description, t.counterparty_name,
               a.name AS account, a.type AS account_type,
               c.name AS category, c.kind AS category_kind
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.booked_at BETWEEN :start AND :end
        ORDER BY t.booked_at DESC, t.id DESC
    """)
    return pd.read_sql(q, engine, params={"start": start, "end": end})


@st.cache_data(ttl=60)
def load_balances() -> pd.DataFrame:
    q = text("""
        SELECT DISTINCT ON (a.id)
               a.id, a.name, a.type, a.provider,
               b.amount, b.currency, b.as_of
        FROM accounts a
        LEFT JOIN balances b ON b.account_id = a.id
        WHERE a.active = TRUE
        ORDER BY a.id, b.as_of DESC NULLS LAST
    """)
    return pd.read_sql(q, engine)


@st.cache_data(ttl=60)
def load_total_wealth() -> dict:
    """Aggregate everything: bank balances + holdings × prices + manual assets."""
    # Latest balance per account
    with engine.connect() as conn:
        bank_total = conn.execute(text("""
            SELECT COALESCE(SUM(b.amount), 0) FROM (
                SELECT DISTINCT ON (account_id) account_id, amount
                FROM balances
                ORDER BY account_id, as_of DESC
            ) b
            JOIN accounts a ON a.id = b.account_id
            WHERE a.active = TRUE
        """)).scalar_one()

    holdings_value = prices.value_of_holdings()
    manual_total = manual_assets.total_value()

    bank_d = Decimal(str(bank_total))
    holdings_d = Decimal(str(holdings_value))
    manual_d = Decimal(str(manual_total))
    total = bank_d + holdings_d + manual_d
    return {
        "bank": float(bank_d),
        "holdings": float(holdings_d),
        "manual": float(manual_d),
        "total": float(total),
    }


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("Finance Pi")
today = date.today()
default_start = today - timedelta(days=90)
date_range = st.sidebar.date_input("Date range", value=(default_start, today))
start, end = date_range if isinstance(date_range, tuple) else (default_start, today)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh prices now"):
    n = prices.update_all_prices()
    st.sidebar.success(f"Updated {n} prices")
    st.cache_data.clear()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
tab_overview, tab_tx, tab_cat, tab_inv, tab_car, tab_manual = st.tabs(
    ["Overview", "Transactions", "Categories", "Investments", "🚗 Car", "Manual assets"]
)


# ---------- Overview ----------
with tab_overview:
    wealth = load_total_wealth()
    st.markdown("### 💰 Total wealth")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", f"€ {wealth['total']:,.2f}")
    c2.metric("Bank & savings", f"€ {wealth['bank']:,.2f}")
    c3.metric("Investments", f"€ {wealth['holdings']:,.2f}")
    c4.metric("Manual assets", f"€ {wealth['manual']:,.2f}")

    st.markdown("---")
    st.markdown("### Accounts")
    balances = load_balances()
    if not balances.empty:
        cols = st.columns(min(4, len(balances)))
        for i, row in balances.iterrows():
            with cols[i % len(cols)]:
                st.metric(
                    f"{row['name']} ({row['type']})",
                    f"€ {row['amount']:,.2f}" if pd.notna(row["amount"]) else "—",
                    help=f"As of {row['as_of']}" if pd.notna(row["as_of"]) else "No data yet",
                )

    tx = load_transactions(start, end)
    if not tx.empty:
        st.markdown("### Monthly cashflow")
        tx_mon = tx.copy()
        tx_mon["month"] = pd.to_datetime(tx_mon["booked_at"]).dt.to_period("M").astype(str)
        cf = (
            tx_mon[tx_mon["category_kind"].isin(["expense", "income", "car"])]
            .groupby(["month", "category_kind"])["amount"]
            .sum()
            .reset_index()
        )
        fig = px.bar(cf, x="month", y="amount", color="category_kind", barmode="group")
        st.plotly_chart(fig, use_container_width=True)


# ---------- Transactions ----------
with tab_tx:
    tx = load_transactions(start, end)
    st.markdown(f"### {len(tx)} transactions")
    uncategorized = tx[tx["category"].isna()]
    if not uncategorized.empty:
        st.warning(f"{len(uncategorized)} uncategorized")
    st.dataframe(
        tx[["booked_at", "account", "amount", "description", "counterparty_name", "category"]],
        use_container_width=True, hide_index=True,
    )


# ---------- Categories ----------
with tab_cat:
    tx = load_transactions(start, end)
    if not tx.empty:
        exp = tx[tx["category_kind"].isin(["expense", "car"])].copy()
        if not exp.empty:
            exp["abs"] = exp["amount"].abs()
            by_cat = (
                exp.groupby("category")["abs"]
                .sum()
                .reset_index()
                .sort_values("abs", ascending=False)
            )
            st.markdown("### Spending by category")
            fig = px.pie(by_cat, values="abs", names="category", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(by_cat, use_container_width=True, hide_index=True)


# ---------- Investments ----------
with tab_inv:
    st.markdown("### Holdings")
    with engine.connect() as conn:
        df = pd.read_sql(text("""
            WITH lh AS (
                SELECT DISTINCT ON (account_id, instrument_id)
                       account_id, instrument_id, quantity, avg_cost
                FROM holdings
                ORDER BY account_id, instrument_id, as_of DESC
            ),
            lp AS (
                SELECT DISTINCT ON (instrument_id) instrument_id, close, as_of
                FROM prices
                ORDER BY instrument_id, as_of DESC
            )
            SELECT a.name AS account, i.symbol, i.name AS instrument, i.type,
                   lh.quantity, lh.avg_cost, lp.close AS latest_price,
                   (lh.quantity * lp.close) AS market_value,
                   lp.as_of AS price_date
            FROM lh
            JOIN accounts a    ON a.id = lh.account_id
            JOIN instruments i ON i.id = lh.instrument_id
            LEFT JOIN lp       ON lp.instrument_id = lh.instrument_id
            ORDER BY market_value DESC NULLS LAST
        """), conn)
    if df.empty:
        st.info(
            "No holdings yet. Add some via the form below, or set up Trade Republic / Rabo Beleggen ingestion."
        )
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        total = df["market_value"].sum()
        cost = (df["quantity"] * df["avg_cost"]).sum() if "avg_cost" in df else None
        c1, c2, c3 = st.columns(3)
        c1.metric("Market value", f"€ {total:,.2f}")
        if cost is not None and cost > 0:
            c2.metric("Cost basis", f"€ {cost:,.2f}")
            c3.metric("Unrealized P&L", f"€ {(total - cost):,.2f}",
                      delta=f"{((total - cost) / cost * 100):,.1f}%" if cost else None)

    st.markdown("---")
    st.markdown("### Add a holding (stocks, gold, crypto)")
    with st.form("add_holding"):
        c1, c2 = st.columns(2)
        with c1:
            with db_session() as s:
                acc_options = {
                    f"{a.name} ({a.provider})": a.id
                    for a in s.query(Account).filter(Account.type.in_(["investment", "manual_asset"])).all()
                }
            if not acc_options:
                st.info("Create an investment account first via SQL (or the Manual Assets tab).")
                acc_label = None
            else:
                acc_label = st.selectbox("Account", list(acc_options.keys()))
            with db_session() as s:
                inst_options = {
                    f"{i.symbol} — {i.name}": i.id
                    for i in s.query(Instrument).order_by(Instrument.symbol).all()
                }
            inst_label = st.selectbox("Instrument", list(inst_options.keys())) if inst_options else None
        with c2:
            quantity = st.number_input("Quantity", min_value=0.0, step=0.0001, format="%.8f")
            avg_cost = st.number_input("Avg cost per unit (EUR, optional)", min_value=0.0, step=0.01)
        submitted = st.form_submit_button("Save holding")
        if submitted and acc_label and inst_label:
            prices.set_holding(
                account_id=acc_options[acc_label],
                instrument_id=inst_options[inst_label],
                quantity=quantity,
                avg_cost=avg_cost if avg_cost > 0 else None,
            )
            st.success("Holding saved.")
            st.cache_data.clear()

    st.markdown("### Seed common instruments")
    if st.button("Add VWCE, IWDA, BTC, ETH, gold, silver"):
        prices.seed_common_instruments()
        st.success("Common instruments registered.")


# ---------- Car ----------
with tab_car:
    st.markdown("### 🚗 Vehicles")
    vehicles = car_tracker.list_vehicles()

    if not vehicles:
        st.info("No vehicle registered yet. Add one below.")
        with st.form("add_vehicle"):
            c1, c2, c3 = st.columns(3)
            with c1:
                v_name = st.text_input("Name", "Swift Sport")
                v_make = st.text_input("Make", "Suzuki")
                v_model = st.text_input("Model", "Swift Sport 1.4 Hybrid Boosterjet")
            with c2:
                v_year = st.number_input("Year", min_value=1990, max_value=2030, value=2021)
                v_plate = st.text_input("License plate", "")
                v_pdate = st.date_input("Purchase date", value=date(2021, 1, 1))
            with c3:
                v_price = st.number_input("Purchase price (€)", min_value=0.0, step=100.0)
                v_odo = st.number_input("Odometer at purchase (km)", min_value=0, step=1000)
            if st.form_submit_button("Add vehicle"):
                car_tracker.add_vehicle(
                    name=v_name, make=v_make, model=v_model, year=int(v_year),
                    license_plate=v_plate, purchase_date=v_pdate,
                    purchase_price=v_price, purchase_odometer=int(v_odo),
                )
                st.success(f"Added {v_name}.")
                st.rerun()
    else:
        v_options = {v["name"]: v["id"] for v in vehicles}
        selected = st.selectbox("Select vehicle", list(v_options.keys()))
        vid = v_options[selected]

        stats = car_tracker.stats(vid)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total spent (paid)", f"€ {stats.total_spent_eur:,.2f}")
        c2.metric("Km driven", f"{stats.km_driven:,}")
        if stats.cost_per_km is not None:
            c3.metric("Cost per km", f"€ {stats.cost_per_km:.3f}/km")
        else:
            c3.metric("Cost per km", "Need odometer reading")
        if stats.latest_odometer:
            c4.metric("Latest odometer", f"{stats.latest_odometer:,} km")
        else:
            c4.metric("Latest odometer", "—")

        st.caption(
            "Cost-per-km is computed from money actually spent so far (bank-extracted fuel + "
            "manual entries) divided by km driven since purchase. No future projections."
        )

        # Spending breakdown
        if stats.by_category:
            df = pd.DataFrame(
                [{"category": k, "amount": float(v)} for k, v in stats.by_category.items()]
            ).sort_values("amount", ascending=False)
            fig = px.bar(df, x="category", y="amount", title="Car expenses by category")
            st.plotly_chart(fig, use_container_width=True)

        # Add odometer reading
        st.markdown("#### Add odometer reading")
        with st.form("add_odometer"):
            c1, c2 = st.columns(2)
            with c1:
                odo_km = st.number_input("Odometer (km)", min_value=0, step=100)
                odo_date = st.date_input("As of", value=date.today())
            if st.form_submit_button("Save reading"):
                car_tracker.add_odometer_reading(
                    vehicle_id=vid, odometer_km=int(odo_km), as_of=odo_date
                )
                st.success("Reading saved.")
                st.rerun()

        # Add manual car expense
        st.markdown("#### Add manual car expense")
        st.caption("Use this for costs paid in cash, or that aren't auto-categorized from bank: tires, APK, garage repairs.")
        with st.form("add_car_expense"):
            with db_session() as s:
                cat_options = {
                    c.name: c.name for c in s.query(Category).filter_by(kind="car").all()
                }
            c1, c2 = st.columns(2)
            with c1:
                e_cat = st.selectbox("Category", list(cat_options.keys()))
                e_date = st.date_input("Date", value=date.today())
                e_amount = st.number_input("Amount (€)", min_value=0.0, step=1.0)
            with c2:
                e_odo = st.number_input("Odometer at time (km, optional)", min_value=0, step=100)
                e_desc = st.text_input("Description", "")
            if st.form_submit_button("Save expense"):
                car_tracker.add_expense(
                    vehicle_id=vid, category_name=e_cat, amount=e_amount,
                    incurred_at=e_date, odometer_km=int(e_odo) if e_odo > 0 else None,
                    description=e_desc,
                )
                st.success("Expense saved.")
                st.rerun()


# ---------- Manual assets ----------
with tab_manual:
    st.markdown("### Other assets (cash, valuables, untracked)")
    st.caption(
        "Use this for things that don't live in a bank API and don't have a market price: "
        "cash in your wallet, jewelry, watches, collectibles, etc. For tradeable assets like gold "
        "or crypto with live prices, use the Investments tab instead."
    )

    assets = manual_assets.list_assets()
    if assets:
        df = pd.DataFrame(assets)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("Total manual assets", f"€ {sum(a['value_eur'] for a in assets):,.2f}")

    st.markdown("#### Add an asset")
    with st.form("add_manual_asset"):
        c1, c2 = st.columns(2)
        with c1:
            m_name = st.text_input("Name", "")
            m_type = st.selectbox(
                "Type", ["cash", "jewelry", "watch", "art", "vehicle", "collectible", "other"]
            )
        with c2:
            m_value = st.number_input("Value in EUR", min_value=0.0, step=10.0)
            m_qty = st.number_input("Quantity", min_value=0.0, value=1.0, step=1.0)
            m_unit = st.text_input("Unit (optional)", "")
        m_notes = st.text_area("Notes", "")
        if st.form_submit_button("Add"):
            manual_assets.add_asset(
                name=m_name, asset_type=m_type, value_eur=m_value,
                quantity=m_qty, unit=m_unit or None, notes=m_notes or None,
            )
            st.success(f"Added {m_name}.")
            st.cache_data.clear()
            st.rerun()
