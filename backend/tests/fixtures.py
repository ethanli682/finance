"""A small synthetic `companyfacts` payload with the quirks real filings have.

Acme Corp, fiscal year ends Sep 30.
Filings: 10-K 2023-11-01 (FY23), 10-Qs for FY24 Q1-Q3, 10-K 2024-11-01 (FY24),
10-Q 2025-02-01 (FY25 Q1).
"""

from datetime import date, timedelta

K23, Q1_24, Q2_24, Q3_24, K24, Q1_25 = (
    ("10-K", "2023-11-01"),
    ("10-Q", "2024-02-01"),
    ("10-Q", "2024-05-01"),
    ("10-Q", "2024-08-01"),
    ("10-K", "2024-11-01"),
    ("10-Q", "2025-02-01"),
)

FY22 = ("2021-10-01", "2022-09-30")
FY23 = ("2022-10-01", "2023-09-30")
FY24 = ("2023-10-01", "2024-09-30")
Q1 = ("2023-10-01", "2023-12-31")
Q2 = ("2024-01-01", "2024-03-31")
Q3 = ("2024-04-01", "2024-06-30")
H1 = ("2023-10-01", "2024-03-31")
M9 = ("2023-10-01", "2024-06-30")
Q1_FY25 = ("2024-10-01", "2024-12-31")


def d(span, val, filing):
    form, filed = filing
    return {"start": span[0], "end": span[1], "val": val, "form": form, "filed": filed, "accn": f"acc-{filed}"}


def i(end, val, filing):
    form, filed = filing
    return {"end": end, "val": val, "form": form, "filed": filed, "accn": f"acc-{filed}"}


def concept(entries, unit="USD"):
    return {"label": "", "units": {unit: entries}}


def build_company_facts() -> dict:
    gaap = {
        # Old revenue tag covers FY22-FY23; new tag from FY24 (with FY23 comparative).
        "SalesRevenueNet": concept([d(FY22, 350, K23), d(FY23, 395, K23)]),
        "RevenueFromContractWithCustomerExcludingAssessedTax": concept(
            [
                d(FY23, 400, K24),
                d(Q1, 100, Q1_24),
                d(Q2, 110, Q2_24),
                d(H1, 210, Q2_24),
                d(Q3, 120, Q3_24),
                d(M9, 330, Q3_24),
                d(FY24, 450, K24),
                d(Q1_FY25, 130, Q1_25),
            ]
        ),
        "CostOfRevenue": concept(
            [
                d(FY23, 240, K24),
                d(Q1, 60, Q1_24),
                d(Q2, 66, Q2_24),
                d(Q3, 72, Q3_24),
                d(M9, 198, Q3_24),
                d(FY24, 270, K24),
                d(Q1_FY25, 78, Q1_25),
            ]
        ),
        "NetIncomeLoss": concept(
            [
                d(FY23, 78, K23),  # original
                d(FY23, 80, K24),  # restated in the next 10-K
                d(Q1, 20, Q1_24),
                d(Q2, 22, Q2_24),
                d(Q3, 24, Q3_24),
                d(M9, 66, Q3_24),
                d(FY24, 90, K24),
                d(Q1_FY25, 30, Q1_25),
            ]
        ),
        "EarningsPerShareDiluted": concept(
            [
                d(Q1, 0.20, Q1_24),
                d(Q2, 0.22, Q2_24),
                d(Q3, 0.24, Q3_24),
                d(FY24, 0.90, K24),
                d(Q1_FY25, 0.30, Q1_25),
            ],
            unit="USD/shares",
        ),
        # Cash flows are year-to-date only in 10-Qs.
        "NetCashProvidedByUsedInOperatingActivities": concept(
            [
                d(Q1, 30, Q1_24),
                d(H1, 65, Q2_24),
                d(M9, 100, Q3_24),
                d(FY24, 140, K24),
                d(Q1_FY25, 45, Q1_25),
            ]
        ),
        "PaymentsToAcquirePropertyPlantAndEquipment": concept(
            [d(Q1, 5, Q1_24), d(H1, 10, Q2_24), d(M9, 15, Q3_24), d(FY24, 20, K24), d(Q1_FY25, 6, Q1_25)]
        ),
        "Assets": concept(
            [
                i("2021-06-15", 777, K23),  # stray instant (e.g. acquisition date) - not a period end
                i("2023-09-30", 1000, K23),
                i("2023-09-30", 1000, Q1_24),
                i("2023-12-31", 1010, Q1_24),
                i("2024-09-30", 1100, K24),
                i("2024-12-31", 1120, Q1_25),
            ]
        ),
        "LiabilitiesAndStockholdersEquity": concept(
            [i("2023-09-30", 1000, K23), i("2024-09-30", 1100, K24), i("2024-12-31", 1120, Q1_25)]
        ),
        "StockholdersEquity": concept(
            [i("2023-09-30", 560, K23), i("2024-09-30", 600, K24), i("2024-12-31", 620, Q1_25)]
        ),
        "AssetsCurrent": concept([i("2024-09-30", 290, K24), i("2024-12-31", 300, Q1_25)]),
        "LiabilitiesCurrent": concept([i("2024-09-30", 140, K24), i("2024-12-31", 150, Q1_25)]),
        "LongTermDebtNoncurrent": concept([i("2024-09-30", 200, K24), i("2024-12-31", 186, Q1_25)]),
    }
    dei = {
        "EntityCommonStockSharesOutstanding": {
            "units": {
                "shares": [
                    {"end": "2024-10-20", "val": 100, "form": "10-K", "filed": "2024-11-01", "accn": "a1"},
                    {"end": "2025-01-20", "val": 99, "form": "10-Q", "filed": "2025-02-01", "accn": "a2"},
                ]
            }
        }
    }
    return {"cik": 1234, "entityName": "Acme Corp", "facts": {"us-gaap": gaap, "dei": dei}}


SUBMISSIONS = {"name": "ACME CORP", "sicDescription": "Widgets & Gadgets", "fiscalYearEnd": "0930"}

TICKERS = [
    {"cik": 1234, "name": "Acme Corp", "ticker": "ACME", "exchange": "Nasdaq"},
    {"cik": 1234, "name": "Acme Corp", "ticker": "ACME-B", "exchange": "Nasdaq"},
    {"cik": 5678, "name": "Apex Industrial Holdings", "ticker": "APX", "exchange": "NYSE"},
    {"cik": 9012, "name": "Microsoft Corp", "ticker": "MSFT", "exchange": "Nasdaq"},
]


def business_days(end: date, count: int) -> list[date]:
    days: list[date] = []
    current = end
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current -= timedelta(days=1)
    return sorted(days)
