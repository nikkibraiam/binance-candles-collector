from unittest.mock import Mock

import pytest
import requests

from candles_collector.binance import SOURCES, BinanceClient, build_url

BASE = "https://fapi.binance.com"


@pytest.mark.parametrize(
    ("candle_type", "expected"),
    [
        ("klines", "/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=1000"),
        (
            "continuosKlines",
            "/fapi/v1/continuousKlines?pair=BTCUSDT&contractType=PERPETUAL&interval=1h&limit=1000",
        ),
        ("indexKlines", "/fapi/v1/indexPriceKlines?pair=BTCUSDT&interval=1h&limit=1000"),
        ("markKlines", "/fapi/v1/markPriceKlines?symbol=BTCUSDT&interval=1h&limit=1000"),
    ],
)
def test_build_url_matches_binance_endpoints(candle_type, expected):
    source = next(s for s in SOURCES if s.candle_type == candle_type)

    assert build_url(BASE, source, "BTCUSDT", "1h") == BASE + expected


def test_build_url_tolerates_trailing_slash():
    assert build_url(BASE + "/", SOURCES[0], "ETHUSDT", "4h").startswith(BASE + "/fapi/v1/klines?")


def _client(response=None, error=None):
    session = Mock(spec=requests.Session)
    if error:
        session.get.side_effect = error
    else:
        session.get.return_value = response
    return BinanceClient(BASE, session=session), session


def test_get_klines_returns_json_on_200():
    response = Mock(status_code=200)
    response.json.return_value = [[1, "1", "1", "1", "1", "1", 2]]
    client, session = _client(response)

    assert client.get_klines(SOURCES[0], "BTCUSDT", "1d") == [[1, "1", "1", "1", "1", "1", 2]]
    session.get.assert_called_once_with(
        BASE + "/fapi/v1/klines?symbol=BTCUSDT&interval=1d&limit=1000", timeout=10.0
    )


def test_get_klines_returns_none_on_http_error():
    client, _ = _client(Mock(status_code=429))

    assert client.get_klines(SOURCES[0], "BTCUSDT", "1d") is None


def test_get_klines_returns_none_on_network_error():
    client, _ = _client(error=requests.ConnectionError("down"))

    assert client.get_klines(SOURCES[0], "BTCUSDT", "1d") is None
