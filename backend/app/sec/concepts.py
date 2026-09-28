"""Mapping from US-GAAP XBRL concepts to normalized statement line items.

Companies tag the same economic idea with different concepts (and switch tags
over time, e.g. SalesRevenueNet -> RevenueFromContractWithCustomer... after
ASC 606). Each line item lists candidate concepts in priority order; for every
period, the first concept that has a value wins. That lets old and new tags
stitch together into one continuous history.

Row order here is the display order in the API.
"""

from dataclasses import dataclass, field
from typing import Literal

Statement = Literal["income", "balance", "cashflow"]
Level = Literal["item", "subtotal", "total"]


@dataclass(frozen=True)
class LineItem:
    key: str
    label: str
    statement: Statement
    concepts: tuple[str, ...] = field(default_factory=tuple)
    unit: str = "USD"  # key into the XBRL "units" dict
    level: Level = "item"
    indent: int = 0
    # Flip the sign when storing (e.g. capex is reported as a positive payment;
    # we store it as a negative cash flow so statements add up visually).
    sign: int = 1
    # Whether values can be derived by subtracting year-to-date figures
    # (true for flows like revenue; false for per-share values and share counts).
    additive: bool = True
    # How to combine concepts reported for the same period: "first" takes the
    # highest-priority concept; "max" takes the largest (used where one concept
    # can be a subset of another, like contract revenue vs total revenue).
    merge: Literal["first", "max"] = "first"

    @property
    def is_instant(self) -> bool:
        return self.statement == "balance"


INCOME: tuple[LineItem, ...] = (
    LineItem(
        "revenue",
        "Revenue",
        "income",
        (
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "SalesRevenueGoodsNet",
            "SalesRevenueServicesNet",
            "RevenuesNetOfInterestExpense",
        ),
        level="subtotal",
        merge="max",
    ),
    LineItem(
        "cost_of_revenue",
        "Cost of revenue",
        "income",
        ("CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold", "CostOfServices"),
        indent=1,
        merge="max",
    ),
    LineItem("gross_profit", "Gross profit", "income", ("GrossProfit",), level="subtotal"),
    LineItem(
        "research_and_development",
        "Research and development",
        "income",
        ("ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"),
        indent=1,
    ),
    LineItem(
        "selling_general_admin",
        "Selling, general and administrative",
        "income",
        ("SellingGeneralAndAdministrativeExpense",),
        indent=1,
    ),
    LineItem("operating_expenses", "Total operating expenses", "income", ("OperatingExpenses",), indent=1),
    LineItem("operating_income", "Operating income", "income", ("OperatingIncomeLoss",), level="subtotal"),
    LineItem(
        "interest_expense",
        "Interest expense",
        "income",
        ("InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"),
        indent=1,
    ),
    LineItem(
        "pretax_income",
        "Income before taxes",
        "income",
        (
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
        ),
        level="subtotal",
    ),
    LineItem("income_tax", "Income tax expense", "income", ("IncomeTaxExpenseBenefit",), indent=1),
    LineItem(
        "net_income",
        "Net income",
        "income",
        ("NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"),
        level="total",
    ),
    LineItem("eps_basic", "EPS, basic", "income", ("EarningsPerShareBasic",), unit="USD/shares", additive=False),
    LineItem(
        "eps_diluted",
        "EPS, diluted",
        "income",
        ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"),
        unit="USD/shares",
        additive=False,
    ),
    LineItem(
        "shares_basic",
        "Weighted avg. shares, basic",
        "income",
        ("WeightedAverageNumberOfSharesOutstandingBasic",),
        unit="shares",
        additive=False,
    ),
    LineItem(
        "shares_diluted",
        "Weighted avg. shares, diluted",
        "income",
        ("WeightedAverageNumberOfDilutedSharesOutstanding",),
        unit="shares",
        additive=False,
    ),
)

BALANCE: tuple[LineItem, ...] = (
    LineItem(
        "cash",
        "Cash and equivalents",
        "balance",
        ("CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash"),
        indent=1,
    ),
    LineItem(
        "short_term_investments",
        "Short-term investments",
        "balance",
        ("ShortTermInvestments", "MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
        indent=1,
    ),
    LineItem("receivables", "Receivables", "balance", ("AccountsReceivableNetCurrent", "ReceivablesNetCurrent"), indent=1),
    LineItem("inventory", "Inventory", "balance", ("InventoryNet",), indent=1),
    LineItem("current_assets", "Total current assets", "balance", ("AssetsCurrent",), level="subtotal"),
    LineItem("ppe", "Property, plant and equipment", "balance", ("PropertyPlantAndEquipmentNet",), indent=1),
    LineItem("goodwill", "Goodwill", "balance", ("Goodwill",), indent=1),
    LineItem("total_assets", "Total assets", "balance", ("Assets",), level="total"),
    LineItem("accounts_payable", "Accounts payable", "balance", ("AccountsPayableCurrent",), indent=1),
    LineItem("current_liabilities", "Total current liabilities", "balance", ("LiabilitiesCurrent",), level="subtotal"),
    LineItem("long_term_debt", "Long-term debt", "balance", ("LongTermDebtNoncurrent", "LongTermDebt"), indent=1),
    LineItem("total_liabilities", "Total liabilities", "balance", ("Liabilities",), level="subtotal"),
    LineItem(
        "shareholders_equity",
        "Shareholders' equity",
        "balance",
        ("StockholdersEquity",),
        level="subtotal",
    ),
    LineItem("noncontrolling_interest", "Noncontrolling interest", "balance", ("MinorityInterest",), indent=1),
    LineItem(
        "total_liabilities_and_equity",
        "Total liabilities and equity",
        "balance",
        ("LiabilitiesAndStockholdersEquity",),
        level="total",
    ),
)

CASHFLOW: tuple[LineItem, ...] = (
    LineItem(
        "depreciation_amortization",
        "Depreciation and amortization",
        "cashflow",
        ("DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet"),
        indent=1,
    ),
    LineItem(
        "stock_compensation",
        "Stock-based compensation",
        "cashflow",
        ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"),
        indent=1,
    ),
    LineItem(
        "operating_cash_flow",
        "Cash from operations",
        "cashflow",
        ("NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
        level="subtotal",
    ),
    LineItem(
        "capex",
        "Capital expenditures",
        "cashflow",
        ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"),
        indent=1,
        sign=-1,
    ),
    LineItem(
        "investing_cash_flow",
        "Cash from investing",
        "cashflow",
        ("NetCashProvidedByUsedInInvestingActivities", "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations"),
        level="subtotal",
    ),
    LineItem(
        "share_repurchases",
        "Share repurchases",
        "cashflow",
        ("PaymentsForRepurchaseOfCommonStock",),
        indent=1,
        sign=-1,
    ),
    LineItem(
        "dividends_paid",
        "Dividends paid",
        "cashflow",
        ("PaymentsOfDividends", "PaymentsOfDividendsCommonStock"),
        indent=1,
        sign=-1,
    ),
    LineItem(
        "financing_cash_flow",
        "Cash from financing",
        "cashflow",
        ("NetCashProvidedByUsedInFinancingActivities", "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations"),
        level="subtotal",
    ),
    LineItem("free_cash_flow", "Free cash flow", "cashflow", (), level="total"),
)

ALL_ITEMS: tuple[LineItem, ...] = INCOME + BALANCE + CASHFLOW
ITEMS_BY_KEY: dict[str, LineItem] = {item.key: item for item in ALL_ITEMS}
ITEMS_BY_STATEMENT: dict[str, tuple[LineItem, ...]] = {
    "income": INCOME,
    "balance": BALANCE,
    "cashflow": CASHFLOW,
}

# Line items whose periods define the column "spine" for a company. Other items
# are aligned to these period ends so statement columns line up.
SPINE_ITEMS = ("revenue", "net_income")

ANNUAL_FORMS = {"10-K", "10-K/A", "10-KT", "10-KT/A"}
QUARTERLY_FORMS = {"10-Q", "10-Q/A"}
