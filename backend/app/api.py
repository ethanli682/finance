from typing import Literal

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from . import ingest
from . import repository as repo
from .db import engine
from .metrics import build_statement, key_metrics
from .schemas import CompanyOverview, PriceBar, PriceSummary, SearchResult, Statement

router = APIRouter(prefix="/api")

RANGES: dict[str, pd.DateOffset | None] = {
    "1m": pd.DateOffset(months=1),
    "3m": pd.DateOffset(months=3),
    "6m": pd.DateOffset(months=6),
    "1y": pd.DateOffset(years=1),
    "5y": pd.DateOffset(years=5),
    "max": None,
}


def _normalize_ticker(raw: str) -> str:
    # EDGAR uses dashes for share classes (BRK-B); people often type BRK.B.
    return raw.strip().upper().replace(".", "-").replace("/", "-")


def _company_or_404(ticker: str) -> dict:
    with engine.connect() as conn:
        company = repo.get_company(conn, _normalize_ticker(ticker))
    if company is None:
        raise HTTPException(404, f"No company found with ticker {ticker.upper()}.")
    return company


def _ensure_fundamentals(company: dict) -> None:
    try:
        ingest.ensure_fundamentals(company)
    except ingest.DataUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/health")
def health() -> dict:
    with engine.connect() as conn:
        companies = repo.count_companies(conn)
    return {"status": "ok", "companies": companies}


@router.get("/search", response_model=list[SearchResult])
def search(q: str = Query("", max_length=100), limit: int = Query(8, ge=1, le=25)):
    if not q.strip():
        return []
    with engine.connect() as conn:
        return repo.search_companies(conn, q, limit)


@router.get("/companies/{ticker}", response_model=CompanyOverview)
def company_overview(ticker: str):
    company = _company_or_404(ticker)
    _ensure_fundamentals(company)
    ingest.ensure_prices(company)

    with engine.connect() as conn:
        company = repo.get_company(conn, company["ticker"])
        facts = repo.get_facts(conn, company["cik"])
        summary = repo.price_summary(conn, company["ticker"])
        siblings = repo.sibling_tickers(conn, company["cik"], company["ticker"])

    price = None
    if summary:
        previous = summary["previous"]
        change = summary["last"] - previous if previous else None
        price = PriceSummary(
            last=summary["last"],
            previous=previous,
            change=change,
            change_percent=change / previous if change is not None else None,
            as_of=summary["as_of"],
            year_high=summary["year_high"],
            year_low=summary["year_low"],
        )

    return CompanyOverview(
        ticker=company["ticker"],
        name=company["entity_name"] or company["name"],
        exchange=company["exchange"],
        cik=company["cik"],
        industry=company["sic_description"],
        other_tickers=siblings,
        price=price,
        metrics=key_metrics(facts, summary, company["shares_outstanding"]),
        has_financials=bool(facts),
        fundamentals_updated_at=company["fundamentals_updated_at"],
    )


@router.get("/companies/{ticker}/financials", response_model=Statement)
def financials(
    ticker: str,
    statement: Literal["income", "balance", "cashflow"] = "income",
    period: Literal["annual", "quarterly"] = "annual",
    limit: int | None = Query(None, ge=1, le=40),
):
    company = _company_or_404(ticker)
    _ensure_fundamentals(company)
    with engine.connect() as conn:
        facts = repo.get_facts(conn, company["cik"], statement=statement, period_type=period)
    table = build_statement(facts, statement, period, limit or (10 if period == "annual" else 12))
    return Statement(ticker=company["ticker"], statement=statement, period=period, **table)


@router.get("/companies/{ticker}/prices", response_model=list[PriceBar])
def prices(ticker: str, range: Literal["1m", "3m", "6m", "1y", "5y", "max"] = "1y"):
    company = _company_or_404(ticker)
    ingest.ensure_prices(company)
    with engine.connect() as conn:
        last = repo.last_price_date(conn, company["ticker"])
        if last is None:
            return []
        offset = RANGES[range]
        start = (pd.Timestamp(last) - offset).date() if offset is not None else None
        return repo.get_prices(conn, company["ticker"], start)
