"""End-to-end API tests against a real Postgres, with SEC and price fetches faked."""

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import prices as price_source
from app.prices import PriceBar
from app.sec import client as sec_client

from .fixtures import SUBMISSIONS, TICKERS, build_company_facts, business_days

LAST_DAY = date(2025, 2, 14)
DAYS = business_days(LAST_DAY, 400)


class FakeSec:
    def __init__(self):
        self.calls = 0

    def tickers(self):
        return TICKERS

    def submissions(self, cik):
        if cik != 1234:
            raise sec_client.SecNotFound(cik)
        return SUBMISSIONS

    def company_facts(self, cik):
        self.calls += 1
        if cik != 1234:
            raise sec_client.SecNotFound(cik)
        return build_company_facts()


class FakePrices:
    def __init__(self):
        self.scale = 1.0
        self.calls = []

    def __call__(self, ticker, start=None):
        self.calls.append(start)
        return [
            PriceBar(d, None, (50 + n * 0.1) * self.scale, (48 + n * 0.1) * self.scale,
                     (49 + n * 0.1) * self.scale, None, 1000)
            for n, d in enumerate(DAYS)
            if start is None or d >= start
        ]


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.db import apply_schema, engine

    try:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS financial_facts, daily_prices, companies, filers"))
    except OperationalError:
        pytest.skip("Postgres not available")
    apply_schema()

    fake_sec, fake_prices = FakeSec(), FakePrices()
    mp = pytest.MonkeyPatch()
    mp.setattr(sec_client, "_client", fake_sec)
    mp.setattr(price_source, "fetch_price_history", fake_prices)

    from app import ingest
    from app.main import app

    ingest.load_tickers()
    with TestClient(app) as c:
        c.fake_sec, c.fake_prices = fake_sec, fake_prices
        yield c
    mp.undo()


def test_search_ranks_exact_ticker_first(client):
    results = client.get("/api/search", params={"q": "acme"}).json()
    assert [r["ticker"] for r in results][:2] == ["ACME", "ACME-B"]


def test_search_by_partial_name(client):
    assert client.get("/api/search", params={"q": "micro"}).json()[0]["ticker"] == "MSFT"
    assert client.get("/api/search", params={"q": "industrial"}).json()[0]["ticker"] == "APX"
    assert client.get("/api/search", params={"q": "%"}).json() == []


def test_overview_loads_lazily_and_computes_metrics(client):
    body = client.get("/api/companies/acme").json()
    assert body["name"] == "Acme Corp"
    assert body["industry"] == "Widgets & Gadgets"
    assert body["other_tickers"] == ["ACME-B"]
    assert body["has_financials"] is True

    price = body["price"]
    assert price["as_of"] == LAST_DAY.isoformat()
    assert price["change"] == pytest.approx(0.1)

    metrics = {m["key"]: m for m in body["metrics"]}
    # TTM = Q2..Q4 FY24 + Q1 FY25
    assert metrics["revenue"]["value"] == 110 + 120 + 120 + 130
    assert metrics["revenue"]["basis"] == "TTM"
    assert metrics["gross_margin"]["value"] == pytest.approx(1 - (66 + 72 + 72 + 78) / 480)
    assert metrics["current_ratio"]["value"] == 2.0
    assert metrics["current_ratio"]["basis"] == "Dec 31, 2024"
    assert metrics["revenue_growth"]["value"] == pytest.approx(450 / 400 - 1)
    assert metrics["market_cap"]["value"] == pytest.approx(99 * price["last"])
    # Q4 EPS isn't reported, so P/E falls back to the fiscal year.
    assert metrics["pe"]["basis"] == "FY2024"
    assert metrics["pe"]["value"] == pytest.approx(price["last"] / 0.90)


def test_second_request_is_served_from_cache(client):
    before = client.fake_sec.calls
    client.get("/api/companies/ACME")
    client.get("/api/companies/ACME/financials")
    assert client.fake_sec.calls == before


def test_income_statement_annual(client):
    body = client.get("/api/companies/ACME/financials", params={"statement": "income"}).json()
    assert [p["label"] for p in body["periods"]] == ["FY2024", "FY2023", "FY2022"]
    rows = {r["key"]: r for r in body["rows"]}
    assert rows["revenue"]["values"] == [450, 400, 350]
    assert rows["gross_profit"]["values"] == [180, 160, None]
    assert rows["net_income"]["level"] == "total"
    assert list(rows)[:3] == ["revenue", "cost_of_revenue", "gross_profit"]  # display order


def test_cash_flow_quarterly(client):
    body = client.get(
        "/api/companies/ACME/financials", params={"statement": "cashflow", "period": "quarterly"}
    ).json()
    assert body["periods"][0]["label"] == "Q1 FY2025"
    rows = {r["key"]: r for r in body["rows"]}
    assert rows["operating_cash_flow"]["values"] == [45, 40, 35, 35, 30]
    assert rows["capex"]["values"][0] == -6


def test_balance_sheet(client):
    body = client.get("/api/companies/ACME/financials", params={"statement": "balance"}).json()
    rows = {r["key"]: r for r in body["rows"]}
    assert rows["total_liabilities"]["values"] == [500, 440]


def test_prices_range(client):
    bars = client.get("/api/companies/ACME/prices", params={"range": "1m"}).json()
    assert bars[-1]["date"] == LAST_DAY.isoformat()
    assert date.fromisoformat(bars[0]["date"]) >= date(2025, 1, 14)
    assert len(client.get("/api/companies/ACME/prices", params={"range": "max"}).json()) == 400


def test_unknown_ticker_404(client):
    response = client.get("/api/companies/NOPE")
    assert response.status_code == 404
    assert "NOPE" in response.json()["detail"]


def test_company_without_xbrl_has_no_financials(client):
    body = client.get("/api/companies/APX").json()
    assert body["has_financials"] is False
    assert client.get("/api/companies/APX/financials").json()["rows"] == []


def test_price_refresh_detects_split(client):
    from app import ingest

    client.fake_prices.calls.clear()
    client.fake_prices.scale = 0.5  # history re-based, as after a 2:1 split
    ingest.refresh_prices("ACME")
    assert client.fake_prices.calls[0] is not None  # incremental attempt first
    assert client.fake_prices.calls[-1] is None  # then a full reload
    bars = client.get("/api/companies/ACME/prices", params={"range": "max"}).json()
    assert bars[0]["close"] == pytest.approx(49 * 0.5)
