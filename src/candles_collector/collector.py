"""Polling loop: fetch every kline source for every symbol and store closed candles."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from typing import Protocol

from .binance import SOURCES, KlineSource
from .models import Candle, closed_candles

log = logging.getLogger(__name__)


class KlineFetcher(Protocol):
    def get_klines(self, source: KlineSource, symbol: str, interval: str) -> list | None: ...


class CandleSink(Protocol):
    def insert_candles(self, interval: str, candles: Sequence[Candle]) -> int: ...


def collect_symbol(client: KlineFetcher, store: CandleSink, symbol: str, interval: str) -> int:
    """Fetch the four kline sources of one symbol and store them. Returns new rows."""
    inserted = 0
    for source in SOURCES:
        rows = client.get_klines(source, symbol, interval)
        if not rows:
            continue
        candles = closed_candles(rows, source.candle_type, symbol)
        new = store.insert_candles(interval, candles)
        log.info("%s %s %s: %d new of %d", interval, symbol, source.candle_type, new, len(candles))
        inserted += new
    return inserted


def run_cycle(
    client: KlineFetcher,
    store: CandleSink,
    interval: str,
    symbols: Iterable[str],
    pause_seconds: float,
    sleep: Callable[[float], object] = time.sleep,
) -> None:
    """One pass over all symbols, pausing between symbols to stay far below
    Binance's request-weight limits. A truthy return from ``sleep`` (as from
    ``threading.Event.wait``) ends the pass early."""
    for symbol in symbols:
        try:
            collect_symbol(client, store, symbol, interval)
        except Exception:
            # One bad symbol (DB error, malformed row) must not stop the others.
            log.exception("Failed to collect %s %s", interval, symbol)
        if sleep(pause_seconds):
            return


def run_forever(
    client: KlineFetcher,
    store_factory: Callable[[], CandleSink],
    interval: str,
    symbols: Sequence[str],
    pause_seconds: float,
    stop: threading.Event,
) -> None:
    # Each interval worker gets its own store: psycopg2 connections should not be
    # shared across threads.
    store = store_factory()
    log.info("Starting %s collector for %d symbols", interval, len(symbols))
    while not stop.is_set():
        run_cycle(client, store, interval, symbols, pause_seconds, sleep=stop.wait)
