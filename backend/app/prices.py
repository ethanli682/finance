"""Daily price history.

This uses yfinance, which scrapes Yahoo Finance. It's convenient for
prototyping, but it's unofficial, can break, and Yahoo's terms don't allow
using it to power a public site. Swap `fetch_price_history` for a licensed
provider (Polygon, Tiingo, Alpha Vantage, ...) before launching; nothing else
needs to change.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceBar:
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    adj_close: float | None
    volume: int | None


def _num(value) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def fetch_price_history(ticker: str, start: date | None = None) -> list[PriceBar]:
    """Fetch daily bars from `start` (inclusive) to today, or full history if start is None."""
    import yfinance as yf

    handle = yf.Ticker(ticker)
    options = {"auto_adjust": False, "actions": False}
    df = handle.history(start=start.isoformat(), **options) if start else handle.history(period="max", **options)
    if df is None or df.empty:
        return []

    df = df.rename(columns=lambda c: c.lower().replace(" ", "_"))
    bars: list[PriceBar] = []
    for ts, row in zip(df.index, df.to_dict("records")):
        close = _num(row.get("close"))
        if close is None:
            continue
        volume = _num(row.get("volume"))
        bars.append(
            PriceBar(
                date=ts.date(),
                open=_num(row.get("open")),
                high=_num(row.get("high")),
                low=_num(row.get("low")),
                close=close,
                adj_close=_num(row.get("adj_close")),
                volume=int(volume) if volume is not None else None,
            )
        )
    return bars
