"""Command-line tasks.

    python -m app.cli init                 # create tables, load tickers if empty
    python -m app.cli tickers              # reload the SEC ticker list
    python -m app.cli refresh AAPL MSFT    # force-refresh statements and prices
"""

import argparse
import logging
import sys

from . import ingest
from . import repository as repo
from .db import apply_schema, engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("cli")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create tables and load tickers if the table is empty")
    sub.add_parser("tickers", help="Reload the SEC ticker list")
    refresh = sub.add_parser("refresh", help="Force-refresh data for tickers")
    refresh.add_argument("tickers", nargs="+")
    refresh.add_argument("--skip-prices", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "init":
        apply_schema()
        log.info("Schema applied")
        with engine.connect() as conn:
            empty = repo.count_companies(conn) == 0
        if empty:
            try:
                log.info("Loaded %d tickers", ingest.load_tickers())
            except Exception:
                log.exception("Couldn't load tickers from SEC. Run `python -m app.cli tickers` later.")
        return 0

    if args.command == "tickers":
        log.info("Loaded %d tickers", ingest.load_tickers())
        return 0

    if args.command == "refresh":
        status = 0
        for raw in args.tickers:
            ticker = raw.upper().replace(".", "-")
            with engine.connect() as conn:
                company = repo.get_company(conn, ticker)
            if not company:
                log.error("Unknown ticker %s (run `tickers` first?)", ticker)
                status = 1
                continue
            log.info("%s: %d facts", ticker, ingest.refresh_fundamentals(company["cik"], company["name"]))
            if not args.skip_prices:
                log.info("%s: %d price bars", ticker, ingest.refresh_prices(ticker))
        return status
    return 1


if __name__ == "__main__":
    sys.exit(main())
