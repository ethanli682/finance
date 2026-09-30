// Mirrors backend/app/schemas.py

export type SearchResult = {
  ticker: string;
  name: string;
  exchange: string | null;
};

export type PriceSummary = {
  last: number;
  previous: number | null;
  change: number | null;
  change_percent: number | null;
  as_of: string;
  year_high: number | null;
  year_low: number | null;
};

export type MetricFormat = "currency" | "percent" | "ratio" | "multiple";

export type Metric = {
  key: string;
  label: string;
  value: number | null;
  format: MetricFormat;
  basis: string | null;
};

export type CompanyOverview = {
  ticker: string;
  name: string;
  exchange: string | null;
  cik: number;
  industry: string | null;
  other_tickers: string[];
  price: PriceSummary | null;
  metrics: Metric[];
  has_financials: boolean;
  fundamentals_updated_at: string | null;
};

export type StatementKind = "income" | "balance" | "cashflow";
export type PeriodKind = "annual" | "quarterly";

export type Period = {
  end: string;
  fiscal_year: number;
  fiscal_quarter: number | null;
  label: string;
};

export type StatementRow = {
  key: string;
  label: string;
  unit: string; // "USD" | "USD/shares" | "shares"
  level: "item" | "subtotal" | "total";
  indent: number;
  values: (number | null)[];
};

export type Statement = {
  ticker: string;
  statement: StatementKind;
  period: PeriodKind;
  currency: string;
  periods: Period[];
  rows: StatementRow[];
};

export type PriceBar = {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
};

export type PriceRange = "1m" | "3m" | "6m" | "1y" | "5y" | "max";

export type FcfYear = {
  label: string;
  value: number;
};

export type ValuationInputs = {
  ticker: string;
  name: string;
  price: number | null;
  price_as_of: string | null;
  shares: number | null;
  free_cash_flow: number | null;
  free_cash_flow_basis: string | null;
  fcf_history: FcfYear[];
  fcf_cagr: number | null;
  cash: number | null;
  cash_basis: string | null;
  debt: number | null;
  debt_basis: string | null;
};
