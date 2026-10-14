from decimal import Decimal

from candles_collector.models import Candle, closed_candles, parse_kline

ROW = [
    1499040000000,
    "0.01634790",
    "0.80000000",
    "0.01575800",
    "0.01577100",
    "148976.11427815",
    1499644799999,
    "2434.19055334",
    308,
    "1756.87402397",
    "28.46694368",
    "0",
]


def test_parse_kline_maps_binance_columns():
    candle = parse_kline(ROW, "klines", "BTCUSDT")

    assert candle == Candle(
        candle_type="klines",
        crypto="BTCUSDT",
        open_time=1499040000000,
        open_price=Decimal("0.01634790"),
        max_price=Decimal("0.80000000"),
        min_price=Decimal("0.01575800"),
        close_price=Decimal("0.01577100"),
        close_time=1499644799999,
        volume=Decimal("148976.11427815"),
    )


def test_parse_kline_keeps_decimal_precision():
    candle = parse_kline(ROW, "klines", "DOGEUSDT")

    assert str(candle.open_price) == "0.01634790"


def test_closed_candles_drops_the_candle_in_progress():
    rows = [ROW, [ROW[0] + 1, *ROW[1:]], [ROW[0] + 2, *ROW[1:]]]

    candles = closed_candles(rows, "markKlines", "ETHUSDT")

    assert [c.open_time for c in candles] == [ROW[0], ROW[0] + 1]
    assert all(c.candle_type == "markKlines" and c.crypto == "ETHUSDT" for c in candles)


def test_closed_candles_handles_empty_and_none():
    assert closed_candles([], "klines", "BTCUSDT") == []
    assert closed_candles(None, "klines", "BTCUSDT") == []
    assert closed_candles([ROW], "klines", "BTCUSDT") == []
