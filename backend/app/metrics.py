"""Statement tables and ratios, computed with pandas from long-format facts."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from .sec.concepts import ITEMS_BY_STATEMENT

TTM_SPAN_DAYS = range(250, 300)  # first to last of four consecutive quarter ends (~273 days)


def _period_label(period_type: str, fiscal_year: int, fiscal_quarter: int | None) -> str:
    if period_type == "quarterly" and fiscal_quarter:
        return f"Q{fiscal_quarter} FY{fiscal_year}"
    return f"FY{fiscal_year}"


def build_statement(facts: list[dict[str, Any]], statement: str, period_type: str, limit: int) -> dict[str, Any]:
    """Pivot long facts into columns (newest first) and ordered rows."""
    if not facts:
        return {"periods": [], "rows": []}

    df = pd.DataFrame(facts)
    periods = (
        df[["period_end", "fiscal_year", "fiscal_quarter"]]
        .drop_duplicates("period_end")
        .sort_values("period_end", ascending=False)
        .head(limit)
    )
    ends = list(periods["period_end"])
    wide = df[df["period_end"].isin(ends)].pivot_table(
        index="line_item", columns="period_end", values="value", aggfunc="first"
    )

    rows = []
    for item in ITEMS_BY_STATEMENT[statement]:
        if item.key not in wide.index:
            continue
        series = wide.loc[item.key].reindex(ends)
        values = [None if pd.isna(v) else float(v) for v in series]
        if all(v is None for v in values):
            continue
        rows.append(
            {
                "key": item.key,
                "label": item.label,
                "unit": item.unit,
                "level": item.level,
                "indent": item.indent,
                "values": values,
            }
        )

    return {
        "periods": [
            {
                "end": p.period_end,
                "fiscal_year": int(p.fiscal_year),
                "fiscal_quarter": None if pd.isna(p.fiscal_quarter) else int(p.fiscal_quarter),
                "label": _period_label(
                    period_type, int(p.fiscal_year), None if pd.isna(p.fiscal_quarter) else int(p.fiscal_quarter)
                ),
            }
            for p in periods.itertuples()
        ],
        "rows": rows,
    }


class _Frames:
    """Wide annual/quarterly frames (index: period_end, columns: line items)."""

    def __init__(self, facts: list[dict[str, Any]]):
        df = pd.DataFrame(facts) if facts else pd.DataFrame(columns=["period_type", "period_end", "line_item", "value"])
        self.fiscal_year = {r.period_end: int(r.fiscal_year) for r in df.itertuples()} if facts else {}
        self.annual = self._wide(df, "annual")
        self.quarterly = self._wide(df, "quarterly")

    @staticmethod
    def _wide(df: pd.DataFrame, period_type: str) -> pd.DataFrame:
        sub = df[df["period_type"] == period_type]
        if sub.empty:
            return pd.DataFrame()
        return sub.pivot_table(index="period_end", columns="line_item", values="value", aggfunc="first").sort_index()

    def ttm(self, item: str) -> float | None:
        q = self.quarterly
        if q.empty or item not in q:
            return None
        series = q[item].dropna()
        last4 = series.iloc[-4:]
        if len(last4) < 4 or last4.index[-1] != q.index[-1]:
            return None  # need the four most recent quarters, consecutive
        if (last4.index[-1] - last4.index[0]).days not in TTM_SPAN_DAYS:
            return None
        return float(last4.sum())

    def latest_annual(self, *items: str) -> tuple[list[float], date] | None:
        a = self.annual
        if a.empty or any(i not in a for i in items):
            return None
        complete = a[list(items)].dropna()
        if complete.empty:
            return None
        end = complete.index[-1]
        return [float(v) for v in complete.iloc[-1]], end

    def flows(self, *items: str) -> tuple[list[float], str] | None:
        """Values for flow items on a common basis: TTM if possible, else latest fiscal year."""
        ttm = [self.ttm(i) for i in items]
        if all(v is not None for v in ttm):
            return ttm, "TTM"  # type: ignore[return-value]
        annual = self.latest_annual(*items)
        if annual:
            values, end = annual
            return values, f"FY{self.fiscal_year.get(end, end.year)}"
        return None

    def latest_balance(self, *items: str) -> tuple[list[float], str] | None:
        frame = self.quarterly if not self.quarterly.empty else self.annual
        if frame.empty or any(i not in frame for i in items):
            return None
        complete = frame[list(items)].dropna()
        if complete.empty:
            return None
        end = complete.index[-1]
        return [float(v) for v in complete.iloc[-1]], f"{end:%b} {end.day}, {end.year}"


def _metric(key: str, label: str, value: float | None, fmt: str, basis: str | None) -> dict[str, Any]:
    return {"key": key, "label": label, "value": value, "format": fmt, "basis": basis}


def key_metrics(
    facts: list[dict[str, Any]], price: dict[str, Any] | None, shares_outstanding: float | None
) -> list[dict[str, Any]]:
    f = _Frames(facts)
    out: list[dict[str, Any]] = []
    last_price = price["last"] if price else None

    shares = shares_outstanding
    if not shares and not f.quarterly.empty and "shares_diluted" in f.quarterly:
        diluted = f.quarterly["shares_diluted"].dropna()
        shares = float(diluted.iloc[-1]) if not diluted.empty else None
    market_cap = last_price * shares if last_price and shares else None
    out.append(_metric("market_cap", "Market cap", market_cap, "currency", "Latest close" if market_cap else None))

    eps = f.flows("eps_diluted")
    pe = last_price / eps[0][0] if last_price and eps and eps[0][0] > 0 else None
    out.append(_metric("pe", "P/E ratio", pe, "multiple", eps[1] if pe else None))

    for key, label in (("revenue", "Revenue"), ("net_income", "Net income"), ("free_cash_flow", "Free cash flow")):
        flow = f.flows(key)
        out.append(_metric(key, label, flow[0][0] if flow else None, "currency", flow[1] if flow else None))

    for key, label, num in (
        ("gross_margin", "Gross margin", "gross_profit"),
        ("operating_margin", "Operating margin", "operating_income"),
        ("net_margin", "Net margin", "net_income"),
    ):
        pair = f.flows(num, "revenue")
        value = pair[0][0] / pair[0][1] if pair and pair[0][1] else None
        out.append(_metric(key, label, value, "percent", pair[1] if value is not None else None))

    growth = None
    growth_basis = None
    if not f.annual.empty and "revenue" in f.annual:
        revenue = f.annual["revenue"].dropna()
        if len(revenue) >= 2 and revenue.iloc[-2]:
            growth = float(revenue.iloc[-1] / revenue.iloc[-2] - 1)
            growth_basis = f"FY{f.fiscal_year.get(revenue.index[-1], revenue.index[-1].year)}"
    out.append(_metric("revenue_growth", "Revenue growth", growth, "percent", growth_basis))

    ni = f.flows("net_income")
    equity = f.latest_balance("shareholders_equity")
    roe = ni[0][0] / equity[0][0] if ni and equity and equity[0][0] > 0 else None
    out.append(_metric("roe", "Return on equity", roe, "percent", ni[1] if roe is not None else None))

    current = f.latest_balance("current_assets", "current_liabilities")
    ratio = current[0][0] / current[0][1] if current and current[0][1] else None
    out.append(_metric("current_ratio", "Current ratio", ratio, "ratio", current[1] if ratio is not None else None))

    leverage = f.latest_balance("long_term_debt", "shareholders_equity")
    de = leverage[0][0] / leverage[0][1] if leverage and leverage[0][1] > 0 else None
    out.append(_metric("debt_to_equity", "Debt to equity", de, "ratio", leverage[1] if de is not None else None))

    return out
