"""Loading data into Postgres, both in bulk (CLI) and lazily on first request.

The API never proxies providers directly: requests read from Postgres, and a
ticker's data is (re)fetched only when it's missing or older than its TTL.
Per-key locks stop concurrent requests from fetching the same thing twice.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone

from . import prices as price_source
from . import repository as repo
from .config import settings
from .db import engine
from .sec import client as sec_client
from .sec.normalize import latest_shares_outstanding, normalize_company_facts

log = logging.getLogger(__name__)

SPLIT_CHECK_TOLERANCE = 0.005  # re-download full history if overlapping closes differ by >0.5%


class DataUnavailable(Exception):
    """Nothing cached and the upstream fetch failed."""


_locks_guard = threading.Lock()
_locks: dict[str, threading.Lock] = {}


def _lock_for(key: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _is_stale(updated_at: datetime | None, ttl_hours: float) -> bool:
    return updated_at is None or datetime.now(timezone.utc) - updated_at > timedelta(hours=ttl_hours)


# --------------------------------------------------------------------------- #
# Tickers
# --------------------------------------------------------------------------- #


def load_tickers() -> int:
    rows = sec_client.get_sec_client().tickers()
    with engine.begin() as conn:
        return repo.upsert_companies(conn, rows)


# --------------------------------------------------------------------------- #
# Fundamentals
# --------------------------------------------------------------------------- #


def refresh_fundamentals(cik: int, fallback_name: str = "") -> int:
    """Fetch and store a filer's statements. Returns the number of facts stored."""
    sec = sec_client.get_sec_client()
    try:
        submissions = sec.submissions(cik)
    except sec_client.SecNotFound:
        submissions = {}
    try:
        facts_json = sec.company_facts(cik)
    except sec_client.SecNotFound:
        facts_json = None  # e.g. funds and trusts that don't file XBRL financials

    rows = normalize_company_facts(facts_json, submissions.get("fiscalYearEnd")) if facts_json else []
    shares = latest_shares_outstanding(facts_json) if facts_json else None

    with engine.begin() as conn:
        repo.upsert_filer(
            conn,
            cik=cik,
            entity_name=(facts_json or {}).get("entityName") or submissions.get("name") or fallback_name,
            sic_description=submissions.get("sicDescription"),
            fiscal_year_end=submissions.get("fiscalYearEnd"),
            shares_outstanding=shares[0] if shares else None,
            shares_outstanding_date=shares[1] if shares else None,
        )
        repo.replace_facts(conn, cik, rows)
    log.info("Stored %d facts for CIK %s", len(rows), cik)
    return len(rows)


def ensure_fundamentals(company: dict) -> None:
    if not _is_stale(company.get("fundamentals_updated_at"), settings.fundamentals_ttl_hours):
        return
    cik = company["cik"]
    with _lock_for(f"fundamentals:{cik}"):
        with engine.connect() as conn:
            current = repo.get_company(conn, company["ticker"]) or company
        if not _is_stale(current.get("fundamentals_updated_at"), settings.fundamentals_ttl_hours):
            return
        try:
            refresh_fundamentals(cik, fallback_name=company["name"])
        except Exception as exc:
            log.exception("Fundamentals refresh failed for CIK %s", cik)
            if current.get("fundamentals_updated_at") is None:
                raise DataUnavailable("Couldn't load financial statements from SEC EDGAR. Try again shortly.") from exc
            # Otherwise serve the stale copy.


# --------------------------------------------------------------------------- #
# Prices
# --------------------------------------------------------------------------- #


def refresh_prices(ticker: str) -> int:
    """Incrementally update daily bars; re-download everything after a split."""
    with engine.connect() as conn:
        last = repo.last_price_date(conn, ticker)

    replace = False
    if last is None:
        bars = price_source.fetch_price_history(ticker)
        replace = True
    else:
        overlap_start = last - timedelta(days=10)
        bars = price_source.fetch_price_history(ticker, start=overlap_start)
        with engine.connect() as conn:
            stored = repo.closes_since(conn, ticker, overlap_start)
        fetched = {b.date: b.close for b in bars}
        adjusted = any(
            d in fetched and close and abs(fetched[d] - close) / close > SPLIT_CHECK_TOLERANCE
            for d, close in stored.items()
        )
        if adjusted:
            log.info("Historical prices for %s changed (split?); reloading full history", ticker)
            bars = price_source.fetch_price_history(ticker)
            replace = True

    with engine.begin() as conn:
        if bars or replace:
            repo.upsert_prices(conn, ticker, bars, replace=replace and bool(bars))
        repo.mark_prices_updated(conn, ticker)
    return len(bars)


def ensure_prices(company: dict) -> None:
    if not _is_stale(company.get("prices_updated_at"), settings.prices_ttl_hours):
        return
    ticker = company["ticker"]
    with _lock_for(f"prices:{ticker}"):
        with engine.connect() as conn:
            current = repo.get_company(conn, ticker) or company
        if not _is_stale(current.get("prices_updated_at"), settings.prices_ttl_hours):
            return
        try:
            refresh_prices(ticker)
        except Exception:
            # Prices are secondary: the page still works with statements alone.
            log.exception("Price refresh failed for %s", ticker)
