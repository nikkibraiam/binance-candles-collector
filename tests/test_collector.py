import pytest

from candles_collector.__main__ import resolve_intervals
from candles_collector.binance import SOURCES
from candles_collector.collector import collect_symbol, run_cycle
from candles_collector.config import DEFAULT_SYMBOLS, load_settings
from candles_collector.db import table_for
from candles_collector.models import INTERVALS


def _rows(n):
    return [[1000 + i, "1", "2", "0.5", "1.5", "10", 1999 + i] for i in range(n)]


class FakeClient:
    def __init__(self, rows_by_type=None):
        self.rows_by_type = rows_by_type or {}
        self.calls = []

    def get_klines(self, source, symbol, interval):
        self.calls.append((source.candle_type, symbol, interval))
        return self.rows_by_type.get(source.candle_type)


class FakeStore:
    def __init__(self, fail_for=None):
        self.batches = []
        self.fail_for = fail_for

    def insert_candles(self, interval, candles):
        if candles and candles[0].crypto == self.fail_for:
            raise RuntimeError("db down")
        self.batches.append((interval, list(candles)))
        return len(candles)


def test_collect_symbol_fetches_every_source_in_order():
    client = FakeClient({s.candle_type: _rows(3) for s in SOURCES})
    store = FakeStore()

    inserted = collect_symbol(client, store, "BTCUSDT", "1h")

    assert [c[0] for c in client.calls] == [s.candle_type for s in SOURCES]
    assert inserted == 4 * 2  # last candle of each source is still open
    assert {b[1][0].candle_type for b in store.batches} == {s.candle_type for s in SOURCES}


def test_collect_symbol_skips_failed_sources():
    client = FakeClient({"klines": _rows(2)})
    store = FakeStore()

    assert collect_symbol(client, store, "BTCUSDT", "1d") == 1
    assert len(store.batches) == 1


def test_run_cycle_continues_after_a_symbol_fails_and_pauses_between_symbols():
    client = FakeClient({"klines": _rows(2)})
    store = FakeStore(fail_for="ETHUSDT")
    pauses = []

    run_cycle(client, store, "1h", ["BTCUSDT", "ETHUSDT", "SOLUSDT"], 60, sleep=pauses.append)

    assert [b[1][0].crypto for b in store.batches] == ["BTCUSDT", "SOLUSDT"]
    assert pauses == [60, 60, 60]


def test_run_cycle_stops_when_sleep_signals_stop():
    client = FakeClient({"klines": _rows(2)})
    store = FakeStore()

    run_cycle(client, store, "1h", ["BTCUSDT", "ETHUSDT"], 60, sleep=lambda _: True)

    assert len(store.batches) == 1


def test_table_for_rejects_unknown_intervals():
    assert table_for("4h") == "candles_4h"
    with pytest.raises(ValueError):
        table_for("4h; DROP TABLE candles_1m")


def test_resolve_intervals():
    assert resolve_intervals(None, ()) == INTERVALS
    assert resolve_intervals(["1h", "4h"], ("1d",)) == ("1h", "4h")
    assert resolve_intervals(None, ("1d",)) == ("1d",)
    with pytest.raises(SystemExit):
        resolve_intervals(None, ("2h",))


def test_load_settings_defaults_and_overrides():
    defaults = load_settings({})
    assert defaults.binance_url == "https://fapi.binance.com"
    assert defaults.database.name == "bot-trading"
    assert defaults.symbols == DEFAULT_SYMBOLS

    custom = load_settings({"SYMBOLS": "BTCUSDT, ETHUSDT", "INTERVALS": "1h", "PORT_DATABASE": "6432"})
    assert custom.symbols == ("BTCUSDT", "ETHUSDT")
    assert custom.intervals == ("1h",)
    assert custom.database.port == 6432
