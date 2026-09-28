"""All SQL lives here. Functions take an open SQLAlchemy connection."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import Any, Iterable

from sqlalchemy import Connection, text

from .prices import PriceBar
from .sec.normalize import NormalizedFact

# --------------------------------------------------------------------------- #
# Companies & search
# --------------------------------------------------------------------------- #


def count_companies(conn: Connection) -> int:
    return conn.execute(text("SELECT count(*) FROM companies")).scalar_one()


def upsert_companies(conn: Connection, rows: Iterable[dict[str, Any]]) -> int:
    payload = [
        {"ticker": r["ticker"].upper(), "cik": int(r["cik"]), "name": r["name"], "exchange": r.get("exchange")}
        for r in rows
        if r.get("ticker") and r.get("cik")
    ]
    if payload:
        conn.execute(
            text(
                """
                INSERT INTO companies (ticker, cik, name, exchange)
                VALUES (:ticker, :cik, :name, :exchange)
                ON CONFLICT (ticker) DO UPDATE
                SET cik = EXCLUDED.cik, name = EXCLUDED.name, exchange = EXCLUDED.exchange
                """
            ),
            payload,
        )
    return len(payload)


def get_company(conn: Connection, ticker: str) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            """
            SELECT c.ticker, c.cik, c.name, c.exchange, c.prices_updated_at,
                   f.entity_name, f.sic_description, f.fiscal_year_end,
                   f.shares_outstanding, f.shares_outstanding_date, f.fundamentals_updated_at
            FROM companies c
            LEFT JOIN filers f ON f.cik = c.cik
            WHERE c.ticker = :ticker
            """
        ),
        {"ticker": ticker},
    ).mappings().first()
    return dict(row) if row else None


def search_companies(conn: Connection, query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Exact ticker first, then ticker prefix, then fuzzy name matches."""
    q = query.strip()
    rows = conn.execute(
        text(
            """
            SELECT ticker, name, exchange
            FROM companies
            WHERE ticker ILIKE :prefix
               OR name ILIKE :contains
               OR :q <% name
            ORDER BY (upper(ticker) = upper(:q)) DESC,
                     (ticker ILIKE :prefix) DESC,
                     word_similarity(:q, name) DESC,
                     length(ticker),
                     ticker
            LIMIT :limit
            """
        ),
        {"q": q, "prefix": f"{_escape_like(q)}%", "contains": f"%{_escape_like(q)}%", "limit": limit},
    ).mappings()
    return [dict(r) for r in rows]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


# --------------------------------------------------------------------------- #
# Fundamentals
# --------------------------------------------------------------------------- #


def upsert_filer(
    conn: Connection,
    *,
    cik: int,
    entity_name: str,
    sic_description: str | None,
    fiscal_year_end: str | None,
    shares_outstanding: float | None,
    shares_outstanding_date: date | None,
) -> None:
    conn.execute(
        text(
            """
            INSERT INTO filers (cik, entity_name, sic_description, fiscal_year_end,
                                shares_outstanding, shares_outstanding_date, fundamentals_updated_at)
            VALUES (:cik, :entity_name, :sic, :fye, :shares, :shares_date, :now)
            ON CONFLICT (cik) DO UPDATE SET
                entity_name = EXCLUDED.entity_name,
                sic_description = EXCLUDED.sic_description,
                fiscal_year_end = EXCLUDED.fiscal_year_end,
                shares_outstanding = EXCLUDED.shares_outstanding,
                shares_outstanding_date = EXCLUDED.shares_outstanding_date,
                fundamentals_updated_at = EXCLUDED.fundamentals_updated_at
            """
        ),
        {
            "cik": cik,
            "entity_name": entity_name,
            "sic": sic_description,
            "fye": fiscal_year_end,
            "shares": shares_outstanding,
            "shares_date": shares_outstanding_date,
            "now": datetime.now(timezone.utc),
        },
    )


def replace_facts(conn: Connection, cik: int, facts: list[NormalizedFact]) -> None:
    """Replace a filer's facts wholesale so restatements and mapping changes apply cleanly."""
    conn.execute(text("DELETE FROM financial_facts WHERE cik = :cik"), {"cik": cik})
    if not facts:
        return
    conn.execute(
        text(
            """
            INSERT INTO financial_facts (cik, period_type, line_item, statement, period_start, period_end,
                                         fiscal_year, fiscal_quarter, value, unit, source_concept, filed)
            VALUES (:cik, :period_type, :line_item, :statement, :period_start, :period_end,
                    :fiscal_year, :fiscal_quarter, :value, :unit, :source_concept, :filed)
            """
        ),
        [{"cik": cik, **asdict(f)} for f in facts],
    )


def get_facts(
    conn: Connection, cik: int, statement: str | None = None, period_type: str | None = None
) -> list[dict[str, Any]]:
    clauses = ["cik = :cik"]
    params: dict[str, Any] = {"cik": cik}
    if statement:
        clauses.append("statement = :statement")
        params["statement"] = statement
    if period_type:
        clauses.append("period_type = :period_type")
        params["period_type"] = period_type
    rows = conn.execute(
        text(
            f"""
            SELECT period_type, line_item, statement, period_start, period_end,
                   fiscal_year, fiscal_quarter, value, unit, source_concept
            FROM financial_facts
            WHERE {" AND ".join(clauses)}
            ORDER BY period_end DESC
            """
        ),
        params,
    ).mappings()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Prices
# --------------------------------------------------------------------------- #


def last_price_date(conn: Connection, ticker: str) -> date | None:
    return conn.execute(text("SELECT max(date) FROM daily_prices WHERE ticker = :t"), {"t": ticker}).scalar_one()


def closes_since(conn: Connection, ticker: str, start: date) -> dict[date, float]:
    rows = conn.execute(
        text("SELECT date, close FROM daily_prices WHERE ticker = :t AND date >= :start"),
        {"t": ticker, "start": start},
    )
    return {r.date: r.close for r in rows}


def upsert_prices(conn: Connection, ticker: str, bars: list[PriceBar], replace: bool = False) -> None:
    if replace:
        conn.execute(text("DELETE FROM daily_prices WHERE ticker = :t"), {"t": ticker})
    if bars:
        conn.execute(
            text(
                """
                INSERT INTO daily_prices (ticker, date, open, high, low, close, adj_close, volume)
                VALUES (:ticker, :date, :open, :high, :low, :close, :adj_close, :volume)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                    close = EXCLUDED.close, adj_close = EXCLUDED.adj_close, volume = EXCLUDED.volume
                """
            ),
            [{"ticker": ticker, **asdict(b)} for b in bars],
        )


def mark_prices_updated(conn: Connection, ticker: str) -> None:
    conn.execute(
        text("UPDATE companies SET prices_updated_at = :now WHERE ticker = :t"),
        {"now": datetime.now(timezone.utc), "t": ticker},
    )


def get_prices(conn: Connection, ticker: str, start: date | None = None) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT date, open, high, low, close, volume
            FROM daily_prices
            WHERE ticker = :t AND (CAST(:start AS DATE) IS NULL OR date >= :start)
            ORDER BY date
            """
        ),
        {"t": ticker, "start": start},
    ).mappings()
    return [dict(r) for r in rows]


def price_summary(conn: Connection, ticker: str) -> dict[str, Any] | None:
    row = conn.execute(
        text(
            """
            WITH recent AS (
                SELECT date, close FROM daily_prices WHERE ticker = :t ORDER BY date DESC LIMIT 2
            ), year AS (
                SELECT max(high) AS high, min(low) AS low FROM daily_prices
                WHERE ticker = :t AND date >= (SELECT max(date) FROM daily_prices WHERE ticker = :t) - 365
            )
            SELECT
                (SELECT date FROM recent ORDER BY date DESC LIMIT 1) AS as_of,
                (SELECT close FROM recent ORDER BY date DESC LIMIT 1) AS last,
                (SELECT close FROM recent ORDER BY date DESC LIMIT 1 OFFSET 1) AS previous,
                (SELECT high FROM year) AS year_high,
                (SELECT low FROM year) AS year_low
            """
        ),
        {"t": ticker},
    ).mappings().first()
    if not row or row["last"] is None:
        return None
    return dict(row)


def sibling_tickers(conn: Connection, cik: int, ticker: str) -> list[str]:
    """Other share classes filed under the same CIK (e.g. GOOG for GOOGL)."""
    rows = conn.execute(
        text("SELECT ticker FROM companies WHERE cik = :cik AND ticker <> :t ORDER BY ticker"),
        {"cik": cik, "t": ticker},
    )
    return [r.ticker for r in rows]
