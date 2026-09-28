-- Idempotent: safe to run on every start.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- One row per SEC filer (a CIK). Fundamentals are stored per filer because
-- several tickers (share classes like GOOG/GOOGL) can share one CIK.
CREATE TABLE IF NOT EXISTS filers (
    cik                      INTEGER PRIMARY KEY,
    entity_name              TEXT NOT NULL,
    sic_description          TEXT,
    fiscal_year_end          TEXT,              -- 'MMDD' as reported by SEC
    shares_outstanding       DOUBLE PRECISION,
    shares_outstanding_date  DATE,
    fundamentals_updated_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS companies (
    ticker             TEXT PRIMARY KEY,
    cik                INTEGER NOT NULL,
    name               TEXT NOT NULL,
    exchange           TEXT,
    prices_updated_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS companies_cik_idx ON companies (cik);
CREATE INDEX IF NOT EXISTS companies_ticker_trgm ON companies USING gin (ticker gin_trgm_ops);
CREATE INDEX IF NOT EXISTS companies_name_trgm ON companies USING gin (name gin_trgm_ops);

-- Normalized statement values in long format: one row per line item per period.
CREATE TABLE IF NOT EXISTS financial_facts (
    cik             INTEGER NOT NULL,
    period_type     TEXT NOT NULL CHECK (period_type IN ('annual', 'quarterly')),
    line_item       TEXT NOT NULL,
    statement       TEXT NOT NULL CHECK (statement IN ('income', 'balance', 'cashflow')),
    period_start    DATE,
    period_end      DATE NOT NULL,
    fiscal_year     INTEGER NOT NULL,
    fiscal_quarter  SMALLINT,
    value           DOUBLE PRECISION NOT NULL,
    unit            TEXT NOT NULL,
    source_concept  TEXT NOT NULL,
    filed           DATE,
    PRIMARY KEY (cik, period_type, line_item, period_end)
);
CREATE INDEX IF NOT EXISTS financial_facts_statement_idx
    ON financial_facts (cik, statement, period_type, period_end DESC);

-- Daily bars. Plain Postgres handles tens of millions of these fine; convert
-- to a TimescaleDB hypertable later if you add intraday data.
CREATE TABLE IF NOT EXISTS daily_prices (
    ticker     TEXT NOT NULL,
    date       DATE NOT NULL,
    open       DOUBLE PRECISION,
    high       DOUBLE PRECISION,
    low        DOUBLE PRECISION,
    close      DOUBLE PRECISION NOT NULL,
    adj_close  DOUBLE PRECISION,
    volume     BIGINT,
    PRIMARY KEY (ticker, date)
);
