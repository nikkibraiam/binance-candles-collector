"""Candle model and parsing of Binance kline rows."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

# Intervals that have a candles_<interval> table in sql/schema.sql.
INTERVALS = ("1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w")


@dataclass(frozen=True)
class Candle:
    candle_type: str
    crypto: str
    open_time: int
    open_price: Decimal
    max_price: Decimal
    min_price: Decimal
    close_price: Decimal
    close_time: int
    volume: Decimal


def parse_kline(row: Sequence, candle_type: str, crypto: str) -> Candle:
    """Map one Binance kline array to a Candle.

    Binance returns ``[open_time, open, high, low, close, volume, close_time, ...]``
    with prices and volume as strings; Decimal keeps them exact.
    """
    return Candle(
        candle_type=candle_type,
        crypto=crypto,
        open_time=int(row[0]),
        open_price=Decimal(row[1]),
        max_price=Decimal(row[2]),
        min_price=Decimal(row[3]),
        close_price=Decimal(row[4]),
        close_time=int(row[6]),
        volume=Decimal(row[5]),
    )


def closed_candles(rows: Iterable[Sequence], candle_type: str, crypto: str) -> list[Candle]:
    """Parse every row except the last one, which is the candle still in progress."""
    rows = list(rows or [])
    return [parse_kline(row, candle_type, crypto) for row in rows[:-1]]
