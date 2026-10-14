"""Settings read from environment variables (optionally loaded from a .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_SYMBOLS = (
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "MATICUSDT",
    "DOGEUSDT",
    "SOLUSDT",
    "DOTUSDT",
    "LTCUSDT",
    "AVAXUSDT",
    "TRXUSDT",
    "UNIUSDT",
    "ALGOUSDT",
)


def _csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    user: str
    password: str
    name: str


@dataclass(frozen=True)
class Settings:
    binance_url: str
    database: DatabaseSettings
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    intervals: tuple[str, ...] = field(default_factory=tuple)
    symbol_pause_seconds: float = 60.0


def load_settings(env: dict[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    return Settings(
        binance_url=env.get("BINANCE_URL", "https://fapi.binance.com"),
        database=DatabaseSettings(
            host=env.get("HOST_DATABASE", "localhost"),
            port=int(env.get("PORT_DATABASE", "5432")),
            user=env.get("USER_DATABASE", "postgres"),
            password=env.get("PASS_DATABASE", ""),
            name=env.get("NAME_DATABASE", "bot-trading"),
        ),
        symbols=_csv(env.get("SYMBOLS"), DEFAULT_SYMBOLS),
        intervals=_csv(env.get("INTERVALS"), ()),
        symbol_pause_seconds=float(env.get("SYMBOL_PAUSE_SECONDS", "60")),
    )
