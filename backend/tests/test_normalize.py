from datetime import date

import pytest

from app.sec.normalize import fiscal_period, latest_shares_outstanding, normalize_company_facts

from .fixtures import build_company_facts


@pytest.fixture(scope="module")
def facts():
    rows = normalize_company_facts(build_company_facts(), "0930")
    return {(r.period_type, r.line_item, r.period_end): r for r in rows}


def value(facts, period_type, item, end):
    row = facts.get((period_type, item, date.fromisoformat(end)))
    return row.value if row else None


def test_revenue_stitches_old_and_new_tags(facts):
    assert value(facts, "annual", "revenue", "2022-09-30") == 350  # only in SalesRevenueNet
    assert value(facts, "annual", "revenue", "2024-09-30") == 450
    assert facts[("annual", "revenue", date(2022, 9, 30))].source_concept == "SalesRevenueNet"


def test_revenue_takes_larger_concept_when_both_reported(facts):
    assert value(facts, "annual", "revenue", "2023-09-30") == 400


def test_restated_value_wins(facts):
    assert value(facts, "annual", "net_income", "2023-09-30") == 80


def test_q4_derived_from_full_year_minus_nine_months(facts):
    assert value(facts, "quarterly", "revenue", "2024-09-30") == 120
    assert value(facts, "quarterly", "net_income", "2024-09-30") == 24
    q4 = facts[("quarterly", "revenue", date(2024, 9, 30))]
    assert (q4.fiscal_year, q4.fiscal_quarter) == (2024, 4)


def test_cash_flow_quarters_derived_from_ytd(facts):
    quarters = [value(facts, "quarterly", "operating_cash_flow", e) for e in
                ("2023-12-31", "2024-03-31", "2024-06-30", "2024-09-30")]
    assert quarters == [30, 35, 35, 40]


def test_outflows_are_negative_and_fcf_derived(facts):
    assert value(facts, "annual", "capex", "2024-09-30") == -20
    assert value(facts, "annual", "free_cash_flow", "2024-09-30") == 120
    assert value(facts, "quarterly", "free_cash_flow", "2024-09-30") == 35


def test_gross_profit_and_liabilities_derived(facts):
    assert value(facts, "annual", "gross_profit", "2024-09-30") == 180
    assert value(facts, "annual", "total_liabilities", "2024-09-30") == 500
    assert facts[("annual", "gross_profit", date(2024, 9, 30))].source_concept == "derived"


def test_per_share_values_are_not_derived(facts):
    assert value(facts, "quarterly", "eps_diluted", "2024-06-30") == pytest.approx(0.24)
    assert value(facts, "quarterly", "eps_diluted", "2024-09-30") is None


def test_balance_sheet_aligned_to_period_ends(facts):
    annual_ends = {e for (pt, item, e) in facts if pt == "annual" and item == "total_assets"}
    assert annual_ends == {date(2023, 9, 30), date(2024, 9, 30)}
    assert value(facts, "quarterly", "total_assets", "2023-12-31") == 1010
    assert all(e != date(2021, 6, 15) for (_, _, e) in facts)


def test_new_fiscal_year_quarter_labels(facts):
    q = facts[("quarterly", "revenue", date(2024, 12, 31))]
    assert (q.fiscal_year, q.fiscal_quarter) == (2025, 1)


@pytest.mark.parametrize(
    "end, fye, expected",
    [
        (date(2023, 12, 30), (9, 28), (2024, 1)),  # Apple-style 52/53-week year
        (date(2024, 9, 28), (9, 28), (2024, 4)),
        (date(2023, 9, 30), (9, 28), (2023, 4)),  # 53-week year ends 2 days late
        (date(2024, 4, 30), (1, 31), (2025, 1)),  # Walmart: FY named for the year it ends
        (date(2024, 3, 31), (12, 31), (2024, 1)),
        (date(2024, 12, 29), (1, 3), (2024, 4)),  # early-January year end
    ],
)
def test_fiscal_period(end, fye, expected):
    assert fiscal_period(end, fye) == expected


def test_latest_shares_outstanding():
    assert latest_shares_outstanding(build_company_facts()) == (99.0, date(2025, 1, 20))
