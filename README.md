# Axon

A barebones stock research site: search any SEC-registered company and read its share price, income statement, balance sheet, and cash flows.

- **Backend:** Python, FastAPI, pandas, PostgreSQL (with `pg_trgm` for fuzzy search)
- **Frontend:** Next.js 16 (App Router), TypeScript, Tailwind CSS v4, TradingView Lightweight Charts
- **Data:** fundamentals from [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) (free, official); daily prices from Yahoo Finance via `yfinance` (prototype only, see [Before you launch](#before-you-launch))

## Quick start (Docker)

```bash
cp .env.example .env         # then set SEC_USER_AGENT to your app name + email
docker compose up --build
```

Open http://localhost:3000. On first boot the backend creates its tables and loads about 10,000 tickers from SEC, which takes a few seconds. A company's filings and price history are downloaded the first time someone opens its page; later visits read from Postgres.

## Local development

You need Python 3.12+, Node 22+, and Postgres 16 (or just `docker compose up db`).

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.cli init                  # tables + ticker list
uvicorn app.main:app --reload           # http://localhost:8000/docs

# Frontend (second terminal)
cd frontend
npm install
npm run dev                             # http://localhost:3000
```

The frontend reads `API_URL` (default `http://localhost:8000`) at runtime.

## How it fits together

```
Browser ──► Next.js ──► /api/* proxy ──► FastAPI ──► Postgres
                                            │
                                            └─► SEC EDGAR / yfinance  (only when data is missing or stale)
```

- **Pages render on the server.** The company page fetches the overview, the annual income statement, and one year of prices before sending HTML. Switching statements or chart ranges happens in the browser through a same-origin proxy (`frontend/app/api/[...path]/route.ts`), so there's no CORS setup and the backend URL stays a runtime setting.
- **The API never proxies data providers.** Every request reads from Postgres. If a company's data is missing or older than its TTL (24h for statements, 6h for prices), it's fetched first. Per-company locks stop simultaneous visitors from triggering duplicate downloads, and if a refresh fails the stale copy is served.
- **Prices update incrementally.** Only recent days are re-downloaded. If those overlap stored closes that no longer match (a stock split re-bases history), the full history is reloaded.

### Turning SEC data into statements

`backend/app/sec/` does the real work. Raw XBRL "company facts" have three problems, handled in `normalize.py`:

1. **Duplicates and restatements.** A 10-K repeats last year's figures as a comparative. The most recently filed value wins, which picks up restatements.
2. **Year-to-date cash flows.** 10-Qs report cash flows for 3, 6, and 9 months, and there's no Q4 filing. Discrete quarters, including Q4, are derived by subtracting consecutive year-to-date values with the same start date. Per-share values and share counts are never derived this way.
3. **Inconsistent tags.** Companies use different concepts for the same line item and switch over time (for example, `SalesRevenueNet` before 2018 and `RevenueFromContractWithCustomerExcludingAssessedTax` after). `concepts.py` lists candidate tags per line item in priority order and stitches them into one history.

Every line item is then aligned to the periods where the company reported revenue or net income, so statement columns line up. Gross profit, total liabilities, and free cash flow are calculated when a company doesn't report them. Fiscal quarters are labeled correctly for 52/53-week years (Apple) and January year-ends (Walmart).

To add or fix a line item, edit `concepts.py`; the API and frontend pick it up automatically.

## API

| Endpoint | Returns |
| --- | --- |
| `GET /api/search?q=appl` | Up to 8 matches: exact ticker first, then ticker prefix, then fuzzy name matches |
| `GET /api/companies/{ticker}` | Name, industry, latest price, and key figures (TTM revenue, margins, P/E, ROE, and more) |
| `GET /api/companies/{ticker}/financials?statement=income\|balance\|cashflow&period=annual\|quarterly` | A statement table, newest period first |
| `GET /api/companies/{ticker}/prices?range=1m\|3m\|6m\|1y\|5y\|max` | Daily bars |
| `GET /api/companies/{ticker}/valuation-inputs` | Starting figures for the DCF calculator: free cash flow (TTM or latest year), its annual history and trend, cash, debt, shares, and price |

Interactive docs are at http://localhost:8000/docs.

## Commands

```bash
python -m app.cli init                 # create tables; load tickers if the table is empty
python -m app.cli tickers              # reload the SEC ticker list (new listings)
python -m app.cli refresh AAPL MSFT    # force-refresh statements and prices now
python -m pytest                       # backend tests (needs Postgres; see below)
```

The API tests run against a real database named `finance_test`, with SEC and price downloads faked. Create it once with `createdb -U finance finance_test`, or point `TEST_DATABASE_URL` elsewhere. The unit tests for statement normalization need no database.

## Project layout

```
backend/
  app/
    main.py          FastAPI app
    api.py           routes
    ingest.py        loading data, lazy refresh, locks
    metrics.py       statement pivots and ratios (pandas)
    repository.py    all SQL
    schema.sql       tables and indexes
    prices.py        price provider (swap this out)
    sec/
      client.py      rate-limited EDGAR client
      concepts.py    XBRL tag → line item mapping
      normalize.py   periods, quarters, restatements
  tests/
frontend/
  app/
    page.tsx                  home and search
    stock/[ticker]/page.tsx   company page
    valuation/page.tsx        DCF and reverse DCF calculator (?ticker= prefills it)
    api/[...path]/route.ts    proxy to the backend
  components/                 SearchBox, PriceChart, Statements, LedgerTable, KeyFigures, DcfCalculator
  lib/                        types, formatting, API helpers, dcf.ts (valuation math)
```

## Before you launch

- **Replace yfinance.** It scrapes Yahoo, can break without notice, and Yahoo's terms don't permit it as the data source for a public site. Replace `fetch_price_history` in `backend/app/prices.py` with a licensed provider; nothing else needs to change.
- **Coverage.** Statements come from US-GAAP XBRL filings (10-K and 10-Q). Foreign companies filing 20-F under IFRS, and most funds and trusts, will show prices but no statements.
- **Banks and insurers** use different statement structures, so some standard line items (like gross profit) won't appear for them.
- **Market cap** uses the latest cover-page share count, which can be incomplete for companies with several share classes.
- **Time-series scale.** Plain Postgres handles daily bars for every US ticker comfortably. If you add intraday data, convert `daily_prices` (or a new table) to a TimescaleDB hypertable; the schema doesn't need to change.
