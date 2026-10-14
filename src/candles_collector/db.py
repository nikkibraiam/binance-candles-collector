"""PostgreSQL persistence for candles."""

from __future__ import annotations

import logging
from collections.abc import Sequence

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from .config import DatabaseSettings
from .models import INTERVALS, Candle

log = logging.getLogger(__name__)

COLUMNS = (
    "candle_type",
    "crypto",
    "open_time",
    "open_price",
    "max_price",
    "min_price",
    "close_price",
    "close_time",
    "volumen",
)


def table_for(interval: str) -> str:
    """Table name for an interval. Only known intervals are accepted, because the
    name ends up in SQL as an identifier."""
    if interval not in INTERVALS:
        raise ValueError(f"Unsupported interval: {interval!r}")
    return f"candles_{interval}"


def candle_values(candle: Candle) -> tuple:
    return (
        candle.candle_type,
        candle.crypto,
        candle.open_time,
        candle.open_price,
        candle.max_price,
        candle.min_price,
        candle.close_price,
        candle.close_time,
        candle.volume,
    )


class CandleStore:
    def __init__(self, settings: DatabaseSettings):
        self.settings = settings
        self._conn = None

    def _connection(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.host,
                port=self.settings.port,
                user=self.settings.user,
                password=self.settings.password,
                dbname=self.settings.name,
            )
        return self._conn

    def insert_candles(self, interval: str, candles: Sequence[Candle]) -> int:
        """Insert candles that are not stored yet; returns how many were new.

        A candle is identified by (candle_type, crypto, open_time), so re-reading
        the same 1000-candle window on every poll is idempotent.
        """
        if not candles:
            return 0
        query = sql.SQL(
            "INSERT INTO {table} ({columns}) VALUES %s "
            "ON CONFLICT (candle_type, crypto, open_time) DO NOTHING"
        ).format(
            table=sql.Identifier(table_for(interval)),
            columns=sql.SQL(", ").join(map(sql.Identifier, COLUMNS)),
        )
        conn = self._connection()
        try:
            with conn.cursor() as cur:
                # A single page, so rowcount covers every row of the batch.
                execute_values(cur, query, [candle_values(c) for c in candles], page_size=len(candles))
                inserted = cur.rowcount
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return inserted

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
