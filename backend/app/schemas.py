from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class SearchResult(BaseModel):
    ticker: str
    name: str
    exchange: str | None


class PriceSummary(BaseModel):
    last: float
    previous: float | None
    change: float | None
    change_percent: float | None
    as_of: date
    year_high: float | None
    year_low: float | None


class Metric(BaseModel):
    key: str
    label: str
    value: float | None
    format: Literal["currency", "percent", "ratio", "multiple"]
    basis: str | None


class CompanyOverview(BaseModel):
    ticker: str
    name: str
    exchange: str | None
    cik: int
    industry: str | None
    other_tickers: list[str]
    price: PriceSummary | None
    metrics: list[Metric]
    has_financials: bool
    fundamentals_updated_at: datetime | None


class Period(BaseModel):
    end: date
    fiscal_year: int
    fiscal_quarter: int | None
    label: str


class StatementRow(BaseModel):
    key: str
    label: str
    unit: str
    level: Literal["item", "subtotal", "total"]
    indent: int
    values: list[float | None]


class Statement(BaseModel):
    ticker: str
    statement: Literal["income", "balance", "cashflow"]
    period: Literal["annual", "quarterly"]
    currency: str = "USD"
    periods: list[Period]
    rows: list[StatementRow]


class PriceBar(BaseModel):
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None
