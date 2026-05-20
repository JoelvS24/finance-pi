-- ============================================================================
-- Finance Pi — initial schema (v0.2.0)
-- Apply with: psql -U finance -d finance -f 001_init.sql
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ----------------------------------------------------------------------------
-- accounts: any "container" of money (bank, broker, gold custodian, "cash in wallet")
-- ----------------------------------------------------------------------------
CREATE TABLE accounts (
    id              SERIAL PRIMARY KEY,
    external_id     TEXT NOT NULL UNIQUE,
    provider        TEXT NOT NULL,                   -- 'rabobank' | 'trade_republic' | 'gbi' | 'manual'
    type            TEXT NOT NULL CHECK (type IN
                       ('payment','savings','credit_card','investment','manual_asset','car')),
    name            TEXT NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'EUR',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- categories: hierarchical, tagged by kind
-- ----------------------------------------------------------------------------
CREATE TABLE categories (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    parent_id       INTEGER REFERENCES categories(id),
    kind            TEXT NOT NULL CHECK (kind IN ('expense','income','transfer','investment','car')),
    icon            TEXT,
    color           TEXT
);

INSERT INTO categories (name, kind) VALUES
    ('Groceries',         'expense'),
    ('Eating Out',        'expense'),
    ('Utilities',         'expense'),
    ('Internet & Phone',  'expense'),
    ('Rent/Mortgage',     'expense'),
    ('Insurance',         'expense'),
    ('Subscriptions',     'expense'),
    ('Healthcare',        'expense'),
    ('Clothing',          'expense'),
    ('Travel',            'expense'),
    ('Entertainment',     'expense'),
    ('Gifts',             'expense'),
    ('Other Expense',     'expense'),

    -- Car-specific (kind='car' so the car module can isolate them)
    ('Car: Fuel',         'car'),
    ('Car: Insurance',    'car'),
    ('Car: Road Tax',     'car'),
    ('Car: Maintenance',  'car'),
    ('Car: Parts',        'car'),
    ('Car: APK',          'car'),
    ('Car: Parking',      'car'),
    ('Car: Tolls',        'car'),
    ('Car: Tires',        'car'),
    ('Car: Other',        'car'),

    ('Salary',            'income'),
    ('Toeslagen',         'income'),
    ('Interest',          'income'),
    ('Other Income',      'income'),

    ('Internal Transfer', 'transfer'),

    ('Investment Buy',    'investment'),
    ('Investment Sell',   'investment'),
    ('Dividend',          'investment');

-- ----------------------------------------------------------------------------
-- transactions
-- ----------------------------------------------------------------------------
CREATE TABLE transactions (
    id                SERIAL PRIMARY KEY,
    account_id        INTEGER NOT NULL REFERENCES accounts(id),
    external_id       TEXT NOT NULL,
    booked_at         DATE NOT NULL,
    value_at          DATE,
    amount            NUMERIC(12, 2) NOT NULL,
    currency          TEXT NOT NULL DEFAULT 'EUR',
    description       TEXT NOT NULL,
    counterparty_name TEXT,
    counterparty_iban TEXT,
    category_id       INTEGER REFERENCES categories(id),
    rule_id           INTEGER,
    notes             TEXT,
    raw               JSONB NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (account_id, external_id)
);

CREATE INDEX idx_tx_account_date     ON transactions (account_id, booked_at DESC);
CREATE INDEX idx_tx_category_date    ON transactions (category_id, booked_at DESC);
CREATE INDEX idx_tx_description_trgm ON transactions USING gin (description gin_trgm_ops);

-- ----------------------------------------------------------------------------
-- rules: ordered, regex-based categorization
-- ----------------------------------------------------------------------------
CREATE TABLE rules (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    priority        INTEGER NOT NULL DEFAULT 100,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    description_re  TEXT,
    counterparty_re TEXT,
    iban_eq         TEXT,
    amount_min      NUMERIC(12, 2),
    amount_max      NUMERIC(12, 2),
    account_id      INTEGER REFERENCES accounts(id),
    category_id     INTEGER NOT NULL REFERENCES categories(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rules_active ON rules (priority) WHERE enabled = TRUE;

-- ----------------------------------------------------------------------------
-- balances: timestamped snapshots
-- ----------------------------------------------------------------------------
CREATE TABLE balances (
    id              SERIAL PRIMARY KEY,
    account_id      INTEGER NOT NULL REFERENCES accounts(id),
    as_of           TIMESTAMPTZ NOT NULL,
    amount          NUMERIC(14, 2) NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'EUR',
    source          TEXT NOT NULL,                  -- 'api' | 'csv' | 'manual'
    UNIQUE (account_id, as_of)
);

CREATE INDEX idx_balances_account ON balances (account_id, as_of DESC);

-- ----------------------------------------------------------------------------
-- instruments: ETFs, stocks, crypto, precious metals
-- ----------------------------------------------------------------------------
CREATE TABLE instruments (
    id              SERIAL PRIMARY KEY,
    symbol          TEXT NOT NULL,                  -- 'VWCE.DE', 'BTC', 'XAU', 'AAPL'
    isin            TEXT,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL CHECK (type IN ('etf','stock','bond','crypto','precious_metal','other')),
    currency        TEXT NOT NULL DEFAULT 'EUR',
    price_source    TEXT NOT NULL CHECK (price_source IN ('yfinance','coingecko','metal_spot','manual')),
    source_id       TEXT,                           -- ticker/id used by the price source
    UNIQUE (symbol, type)
);

-- ----------------------------------------------------------------------------
-- holdings: positions per account
-- ----------------------------------------------------------------------------
CREATE TABLE holdings (
    id              SERIAL PRIMARY KEY,
    account_id      INTEGER NOT NULL REFERENCES accounts(id),
    instrument_id   INTEGER NOT NULL REFERENCES instruments(id),
    as_of           DATE NOT NULL,
    quantity        NUMERIC(18, 8) NOT NULL,        -- supports fractional crypto / metal grams
    avg_cost        NUMERIC(14, 4),
    UNIQUE (account_id, instrument_id, as_of)
);

CREATE INDEX idx_holdings_account ON holdings (account_id, as_of DESC);

-- ----------------------------------------------------------------------------
-- prices: daily close prices, populated by prices.py
-- ----------------------------------------------------------------------------
CREATE TABLE prices (
    instrument_id   INTEGER NOT NULL REFERENCES instruments(id),
    as_of           DATE NOT NULL,
    close           NUMERIC(14, 4) NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'EUR',
    PRIMARY KEY (instrument_id, as_of)
);

-- ----------------------------------------------------------------------------
-- manual_assets: anything that doesn't live in a bank API
-- e.g. cash in wallet, jewelry, watches, art, untracked savings
-- ----------------------------------------------------------------------------
CREATE TABLE manual_assets (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL CHECK (type IN
                      ('cash','jewelry','watch','art','vehicle','collectible','other')),
    quantity        NUMERIC(18, 4) NOT NULL DEFAULT 1,
    unit            TEXT,                           -- 'EUR', 'pcs', 'g', etc.
    value_eur       NUMERIC(14, 2) NOT NULL,        -- current estimated value in EUR
    last_updated    DATE NOT NULL DEFAULT CURRENT_DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- vehicles: each car you own (the system supports multiple)
-- ----------------------------------------------------------------------------
CREATE TABLE vehicles (
    id                  SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,              -- 'Swift Sport'
    make                TEXT,
    model               TEXT,
    year                INTEGER,
    license_plate       TEXT,
    purchase_date       DATE,
    purchase_price      NUMERIC(12, 2),
    purchase_odometer   INTEGER NOT NULL DEFAULT 0,
    active              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- odometer_readings: track distance over time
-- ----------------------------------------------------------------------------
CREATE TABLE odometer_readings (
    id              SERIAL PRIMARY KEY,
    vehicle_id      INTEGER NOT NULL REFERENCES vehicles(id),
    as_of           DATE NOT NULL,
    odometer_km     INTEGER NOT NULL,
    notes           TEXT,
    UNIQUE (vehicle_id, as_of)
);

-- ----------------------------------------------------------------------------
-- car_expenses: manual car costs (APK, tires, etc.) NOT from bank statements.
-- Bank-extracted car expenses live in `transactions` with category kind='car'.
-- ----------------------------------------------------------------------------
CREATE TABLE car_expenses (
    id              SERIAL PRIMARY KEY,
    vehicle_id      INTEGER NOT NULL REFERENCES vehicles(id),
    incurred_at     DATE NOT NULL,
    category_id     INTEGER NOT NULL REFERENCES categories(id),
    amount          NUMERIC(12, 2) NOT NULL,        -- positive value (expense in EUR)
    odometer_km     INTEGER,
    description     TEXT,
    receipt_path    TEXT,
    -- If this expense is also visible as a bank transaction, link it
    transaction_id  INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_car_expenses_vehicle ON car_expenses (vehicle_id, incurred_at DESC);

-- ----------------------------------------------------------------------------
-- View: total_car_spent — UNION of bank txs (kind=car) + manual car_expenses
-- Used by the dashboard for cost-per-km calculations.
-- ----------------------------------------------------------------------------
CREATE VIEW v_car_spend AS
SELECT
    'manual'              AS source,
    e.id                  AS source_id,
    e.vehicle_id,
    e.incurred_at         AS date,
    c.name                AS category,
    e.amount              AS amount
FROM car_expenses e
JOIN categories c ON c.id = e.category_id
UNION ALL
SELECT
    'bank'                AS source,
    t.id                  AS source_id,
    NULL::int             AS vehicle_id,  -- bank txs aren't tied to a vehicle yet
    t.booked_at           AS date,
    c.name                AS category,
    -t.amount             AS amount       -- bank amounts are negative for expenses
FROM transactions t
JOIN categories c ON c.id = t.category_id
WHERE c.kind = 'car' AND t.amount < 0;

-- ----------------------------------------------------------------------------
-- sync_runs: audit log
-- ----------------------------------------------------------------------------
CREATE TABLE sync_runs (
    id              SERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    provider        TEXT NOT NULL,
    account_id      INTEGER REFERENCES accounts(id),
    status          TEXT NOT NULL,
    rows_inserted   INTEGER DEFAULT 0,
    rows_updated    INTEGER DEFAULT 0,
    error_message   TEXT
);

-- ----------------------------------------------------------------------------
-- consents: 90-day PSD2 reauth tracking
-- ----------------------------------------------------------------------------
CREATE TABLE consents (
    id              SERIAL PRIMARY KEY,
    provider        TEXT NOT NULL,
    session_id      TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,
    accounts        JSONB NOT NULL,
    active          BOOLEAN NOT NULL DEFAULT TRUE
);
