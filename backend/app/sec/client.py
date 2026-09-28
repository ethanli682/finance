"""Minimal SEC EDGAR client.

SEC asks for a descriptive User-Agent with contact info and at most 10
requests/second: https://www.sec.gov/os/accessing-edgar-data
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import httpx

from ..config import settings

log = logging.getLogger(__name__)

TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


class SecNotFound(Exception):
    """The company has no data at this endpoint (e.g. it never filed XBRL)."""


class SecClient:
    min_interval = 0.12  # stay safely under 10 req/s

    def __init__(self, user_agent: str | None = None, timeout: float = 30.0):
        self._http = httpx.Client(
            headers={"User-Agent": user_agent or settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"},
            timeout=timeout,
            follow_redirects=True,
        )
        self._lock = threading.Lock()
        self._last_request = 0.0

    def _get_json(self, url: str) -> Any:
        for attempt in range(3):
            with self._lock:
                wait = self.min_interval - (time.monotonic() - self._last_request)
                if wait > 0:
                    time.sleep(wait)
                self._last_request = time.monotonic()
            response = self._http.get(url)
            if response.status_code == 404:
                raise SecNotFound(url)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                log.warning("SEC returned %s for %s, retrying", response.status_code, url)
                time.sleep(1.5 * (attempt + 1))
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError("unreachable")

    def tickers(self) -> list[dict[str, Any]]:
        """All tickers SEC knows about: [{cik, name, ticker, exchange}, ...]."""
        payload = self._get_json(TICKERS_URL)
        fields = payload["fields"]
        return [dict(zip(fields, row)) for row in payload["data"]]

    def company_facts(self, cik: int) -> dict[str, Any]:
        return self._get_json(COMPANY_FACTS_URL.format(cik=cik))

    def submissions(self, cik: int) -> dict[str, Any]:
        return self._get_json(SUBMISSIONS_URL.format(cik=cik))


_client: SecClient | None = None


def get_sec_client() -> SecClient:
    global _client
    if _client is None:
        _client = SecClient()
    return _client
