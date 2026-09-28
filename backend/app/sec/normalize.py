"""Turn an SEC `companyfacts` payload into clean, period-aligned statement rows.

The raw XBRL data has three quirks this module deals with:

1. The same value appears in many filings (a 10-K repeats the prior year as a
   comparative). We keep the most recently filed value, which picks up
   restatements.
2. 10-Qs report cash flows year-to-date (6 and 9 months), and nobody files a
   Q4 report. Discrete quarters are derived by subtracting consecutive
   year-to-date figures that share a start date (Q4 = FY - 9M, etc.).
3. Different concepts are used for the same line item across companies and
   across years. See `concepts.py`.
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

from .concepts import ALL_ITEMS, ANNUAL_FORMS, ITEMS_BY_KEY, QUARTERLY_FORMS, SPINE_ITEMS, LineItem

ANNUAL_DAYS = range(340, 381)  # 52/53-week fiscal years are 364 or 371 days
QUARTER_DAYS = range(80, 101)
SNAP_TOLERANCE_DAYS = 3  # instants a few days off the spine are snapped onto it


@dataclass(frozen=True)
class RawFact:
    start: date | None
    end: date
    value: float
    filed: date
    form: str
    accn: str


@dataclass(frozen=True)
class Cell:
    start: date | None
    value: float
    filed: date | None
    concept: str


@dataclass(frozen=True)
class NormalizedFact:
    period_type: str  # "annual" | "quarterly"
    line_item: str
    statement: str
    period_start: date | None
    period_end: date
    fiscal_year: int
    fiscal_quarter: int | None
    value: float
    unit: str
    source_concept: str
    filed: date | None


# --------------------------------------------------------------------------- #
# Raw fact loading
# --------------------------------------------------------------------------- #


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def load_concept(facts_json: dict[str, Any], concept: str, unit: str, taxonomy: str = "us-gaap") -> list[RawFact]:
    node = facts_json.get("facts", {}).get(taxonomy, {}).get(concept)
    if not node:
        return []
    out: list[RawFact] = []
    for entry in node.get("units", {}).get(unit, []):
        form = entry.get("form", "")
        if form not in ANNUAL_FORMS and form not in QUARTERLY_FORMS:
            continue
        end = _parse_date(entry.get("end"))
        filed = _parse_date(entry.get("filed"))
        val = entry.get("val")
        if end is None or filed is None or val is None:
            continue
        out.append(
            RawFact(
                start=_parse_date(entry.get("start")),
                end=end,
                value=float(val),
                filed=filed,
                form=form,
                accn=entry.get("accn", ""),
            )
        )
    return out


def _latest_by(facts: Iterable[RawFact], key) -> dict:
    latest: dict = {}
    for f in facts:
        k = key(f)
        if k not in latest or f.filed > latest[k].filed:
            latest[k] = f
    return latest


# --------------------------------------------------------------------------- #
# Period extraction
# --------------------------------------------------------------------------- #


def duration_periods(facts: list[RawFact], additive: bool) -> tuple[dict[date, RawFact], dict[date, RawFact]]:
    """Return (annual, quarterly) values keyed by period end."""
    by_span: dict[tuple[date, date], RawFact] = _latest_by(
        (f for f in facts if f.start is not None), key=lambda f: (f.start, f.end)
    )

    annual: dict[date, RawFact] = {}
    quarterly: dict[date, RawFact] = {}
    for (start, end), fact in by_span.items():
        days = (end - start).days
        target = annual if days in ANNUAL_DAYS else quarterly if days in QUARTER_DAYS else None
        if target is not None and (end not in target or fact.filed > target[end].filed):
            target[end] = fact

    if additive:
        # Derive missing quarters from year-to-date chains sharing a start date.
        chains: dict[date, list[RawFact]] = defaultdict(list)
        for (start, _), fact in by_span.items():
            chains[start].append(fact)
        for chain in chains.values():
            chain.sort(key=lambda f: f.end)
            for earlier, later in zip(chain, chain[1:]):
                q_start = earlier.end + timedelta(days=1)
                if (later.end - q_start).days not in QUARTER_DAYS or later.end in quarterly:
                    continue
                quarterly[later.end] = RawFact(
                    start=q_start,
                    end=later.end,
                    value=later.value - earlier.value,
                    filed=max(earlier.filed, later.filed),
                    form=later.form,
                    accn=later.accn,
                )
    return annual, quarterly


def instant_periods(facts: list[RawFact]) -> tuple[dict[date, RawFact], dict[date, RawFact]]:
    instants = [f for f in facts if f.start is None]
    quarterly = _latest_by(instants, key=lambda f: f.end)
    annual = _latest_by((f for f in instants if f.form in ANNUAL_FORMS), key=lambda f: f.end)
    return annual, quarterly


def _snap(end: date, spine: list[date]) -> date | None:
    """Map a date onto the closest spine date within tolerance (None if no match)."""
    if not spine:
        return end
    best = min(spine, key=lambda s: abs((s - end).days))
    return best if abs((best - end).days) <= SNAP_TOLERANCE_DAYS else None


# --------------------------------------------------------------------------- #
# Fiscal calendar
# --------------------------------------------------------------------------- #


def parse_fiscal_year_end(value: str | None) -> tuple[int, int] | None:
    """SEC submissions report fiscal year end as 'MMDD'."""
    if not value or len(value) != 4 or not value.isdigit():
        return None
    month, day = int(value[:2]), int(value[2:])
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None
    return month, day


def fiscal_period(end: date, fye: tuple[int, int]) -> tuple[int, int]:
    """Return (fiscal_year, fiscal_quarter) for a period ending on `end`.

    Works with 52/53-week years whose end drifts a few days around `fye`.
    Fiscal years are named for the calendar year they end in, except years
    ending in the first days of January, which companies name for the prior year.
    """
    month, day = fye

    def fye_in(year: int) -> date:
        return date(year, month, min(day, calendar.monthrange(year, month)[1]))

    target = fye_in(end.year)
    if end > target + timedelta(days=7):
        target = fye_in(end.year + 1)
    quarter = 4 - round((target - end).days / 91.31)
    quarter = min(4, max(1, quarter))
    fiscal_year = target.year - 1 if (month == 1 and day <= 10) else target.year
    return fiscal_year, quarter


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #

Table = dict[str, dict[str, dict[date, Cell]]]  # period_type -> item -> end -> cell


def _collect_item(facts_json: dict[str, Any], item: LineItem) -> dict[str, dict[date, Cell]]:
    merged: dict[str, dict[date, Cell]] = {"annual": {}, "quarterly": {}}
    for concept in item.concepts:
        raw = load_concept(facts_json, concept, item.unit)
        if not raw:
            continue
        if item.is_instant:
            annual, quarterly = instant_periods(raw)
        else:
            annual, quarterly = duration_periods(raw, additive=item.additive)
        for period_type, values in (("annual", annual), ("quarterly", quarterly)):
            bucket = merged[period_type]
            for end, fact in values.items():
                cell = Cell(fact.start, fact.value * item.sign, fact.filed, concept)
                if end not in bucket:
                    bucket[end] = cell
                elif item.merge == "max" and abs(cell.value) > abs(bucket[end].value):
                    # e.g. Revenues (total) vs RevenueFromContract... (a subset) in the same period
                    bucket[end] = cell
    return merged


def _derive(table: Table) -> None:
    """Fill in line items that can be computed from others when not reported."""
    for period_type, items in table.items():

        def get(key: str, end: date) -> float | None:
            cell = items.get(key, {}).get(end)
            return cell.value if cell else None

        def put(key: str, end: date, value: float, start: date | None) -> None:
            items.setdefault(key, {})
            if end not in items[key]:
                items[key][end] = Cell(start, value, None, "derived")

        for end, rev in list(items.get("revenue", {}).items()):
            cost = get("cost_of_revenue", end)
            if cost is not None:
                put("gross_profit", end, rev.value - cost, rev.start)

        for end, total in list(items.get("total_liabilities_and_equity", {}).items()):
            equity = get("shareholders_equity", end)
            if equity is not None:
                nci = get("noncontrolling_interest", end) or 0.0
                put("total_liabilities", end, total.value - equity - nci, None)

        for end, ocf in list(items.get("operating_cash_flow", {}).items()):
            capex = get("capex", end)
            if capex is not None:
                put("free_cash_flow", end, ocf.value + capex, ocf.start)


def normalize_company_facts(facts_json: dict[str, Any], fiscal_year_end: str | None = None) -> list[NormalizedFact]:
    table: Table = {"annual": {}, "quarterly": {}}
    for item in ALL_ITEMS:
        if not item.concepts:
            continue
        collected = _collect_item(facts_json, item)
        for period_type in table:
            if collected[period_type]:
                table[period_type][item.key] = collected[period_type]

    # The spine: period ends where the company reported revenue or net income.
    spines: dict[str, list[date]] = {}
    for period_type, items in table.items():
        ends: set[date] = set()
        for key in SPINE_ITEMS:
            ends.update(items.get(key, {}).keys())
        spines[period_type] = sorted(ends)
    # A fiscal year end is also a quarter end (Q4), so quarterly balance sheets
    # can align to annual ends too.
    spines["quarterly"] = sorted(set(spines["quarterly"]) | set(spines["annual"]))

    # Align every item to the spine so statement columns line up.
    for period_type, items in table.items():
        spine = spines[period_type]
        for key, cells in list(items.items()):
            aligned: dict[date, Cell] = {}
            for end, cell in cells.items():
                snapped = _snap(end, spine)
                if snapped is not None and snapped not in aligned:
                    aligned[snapped] = cell
            items[key] = aligned

    _derive(table)

    fye = parse_fiscal_year_end(fiscal_year_end)
    if fye is None:
        annual_ends = spines["annual"]
        fye = (annual_ends[-1].month, annual_ends[-1].day) if annual_ends else (12, 31)

    rows: list[NormalizedFact] = []
    for period_type, items in table.items():
        for key, cells in items.items():
            item = ITEMS_BY_KEY[key]
            for end, cell in cells.items():
                fy, fq = fiscal_period(end, fye)
                rows.append(
                    NormalizedFact(
                        period_type=period_type,
                        line_item=key,
                        statement=item.statement,
                        period_start=cell.start,
                        period_end=end,
                        fiscal_year=fy,
                        fiscal_quarter=fq if period_type == "quarterly" else None,
                        value=cell.value,
                        unit=item.unit,
                        source_concept=cell.concept,
                        filed=cell.filed,
                    )
                )
    return rows


def latest_shares_outstanding(facts_json: dict[str, Any]) -> tuple[float, date] | None:
    """Most recent cover-page share count (summed across classes in one filing)."""
    entries = (
        facts_json.get("facts", {})
        .get("dei", {})
        .get("EntityCommonStockSharesOutstanding", {})
        .get("units", {})
        .get("shares", [])
    )
    parsed = [(e, _parse_date(e.get("end")), _parse_date(e.get("filed"))) for e in entries]
    parsed = [(e, end, filed) for e, end, filed in parsed if end and filed and e.get("val") is not None]
    if not parsed:
        return None
    _, end, filed = max(parsed, key=lambda p: (p[2], p[1]))
    accn = next(e.get("accn") for e, en, fi in parsed if en == end and fi == filed)
    total = sum(float(e["val"]) for e, en, _ in parsed if en == end and e.get("accn") == accn)
    return total, end
