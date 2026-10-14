"""Minimal client for the public Binance USD-M futures kline endpoints."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

log = logging.getLogger(__name__)

KLINE_LIMIT = 1000


@dataclass(frozen=True)
class KlineSource:
    """One kline endpoint and the value stored in ``candle_type`` for it."""

    candle_type: str
    path: str
    symbol_param: str
    extra_params: tuple[tuple[str, str], ...] = ()


# Order matches the original collector. "continuosKlines" keeps the original
# spelling because it is the value already stored in candle_type.
SOURCES = (
    KlineSource("klines", "/fapi/v1/klines", "symbol"),
    KlineSource(
        "continuosKlines",
        "/fapi/v1/continuousKlines",
        "pair",
        (("contractType", "PERPETUAL"),),
    ),
    KlineSource("indexKlines", "/fapi/v1/indexPriceKlines", "pair"),
    KlineSource("markKlines", "/fapi/v1/markPriceKlines", "symbol"),
)


def build_url(base_url: str, source: KlineSource, symbol: str, interval: str) -> str:
    params = [(source.symbol_param, symbol), *source.extra_params]
    params += [("interval", interval), ("limit", str(KLINE_LIMIT))]
    return f"{base_url.rstrip('/')}{source.path}?{urlencode(params)}"


class BinanceClient:
    def __init__(self, base_url: str, session: requests.Session | None = None, timeout: float = 10.0):
        self.base_url = base_url
        self.session = session or requests.Session()
        self.timeout = timeout

    def get_klines(self, source: KlineSource, symbol: str, interval: str) -> list | None:
        """Return the raw kline rows, or None when the request fails."""
        url = build_url(self.base_url, source, symbol, interval)
        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.RequestException:
            log.exception("Request failed: %s", url)
            return None
        if response.status_code != 200:
            log.warning("HTTP %s from %s", response.status_code, url)
            return None
        return response.json()
