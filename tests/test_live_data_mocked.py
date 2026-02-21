"""Mocked tests for live data endpoint.

These tests use pytest monkeypatch to stub ccxt exchange.fetch_ohlcv
to make tests deterministic and avoid network calls during CI.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# Sample OHLCV data for mocking
SAMPLE_OHLCV_DATA = [
    [
        1704067200000,  # 2024-01-01 00:00:00 UTC
        42000.0,
        42500.0,
        41500.0,
        42300.0,
        100.5,
    ],
    [
        1704070800000,  # 2024-01-01 01:00:00 UTC
        42300.0,
        42800.0,
        42100.0,
        42600.0,
        120.3,
    ],
    [
        1704074400000,  # 2024-01-01 02:00:00 UTC
        42600.0,
        43000.0,
        42400.0,
        42800.0,
        110.7,
    ],
] + [
    [
        1704067200000 + (i * 3600000),
        42000.0 + (i * 100),
        42500.0 + (i * 100),
        41500.0 + (i * 100),
        42300.0 + (i * 100),
        100.5 + (i * 5),
    ]
    for i in range(3, 250)
]


class MockExchange:
    """Mock ccxt exchange for testing."""

    def __init__(self, config: dict[str, bool] | None = None) -> None:
        """Initialize mock exchange."""
        self.options = {"defaultType": "spot"}

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 250
    ) -> list[list[float]]:
        """Mock fetch_ohlcv method."""
        return SAMPLE_OHLCV_DATA[:limit]


def test_live_data_endpoint_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test live data endpoint with mocked ccxt exchange."""
    # Mock the ccxt.binance exchange
    monkeypatch.setattr("ccxt.binance", lambda config: MockExchange(config))

    response = client.get("/api/v1/live_data")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "symbol" in data
    assert "timeframe" in data
    assert "exchange" in data
    assert "last_price" in data
    assert "last_timestamp" in data
    assert "candles_count" in data
    assert "recent_candles" in data
    assert "latest_indicators" in data
    assert "meta" in data

    # Validate data values
    assert data["symbol"] == "BTC/USDT"
    assert data["timeframe"] == "1h"
    assert data["exchange"] == "binance"
    assert data["candles_count"] == 250

    # Validate recent_candles
    assert isinstance(data["recent_candles"], list)
    assert len(data["recent_candles"]) == 20  # Should return last 20 candles

    # Validate candle structure
    if len(data["recent_candles"]) > 0:
        candle = data["recent_candles"][0]
        assert "timestamp" in candle
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle
        assert "volume" in candle
        assert "ema_20" in candle
        assert "ema_50" in candle
        assert "ema_200" in candle
        assert "rsi_14" in candle
        assert "atr_14" in candle

    # Validate latest_indicators
    indicators = data["latest_indicators"]
    assert "ema_20" in indicators
    assert "ema_50" in indicators
    assert "ema_200" in indicators
    assert "rsi_14" in indicators
    assert "atr_14" in indicators

    # Validate meta contains defaultType
    assert "defaultType" in data["meta"]
    assert data["meta"]["defaultType"] == "spot"


def test_live_data_with_custom_parameters_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test live data endpoint with custom parameters using mocked exchange."""
    monkeypatch.setattr("ccxt.binance", lambda config: MockExchange(config))

    response = client.get(
        "/api/v1/live_data",
        params={"symbol": "ETH/USDT", "timeframe": "1d", "limit": 100, "exchange": "binance"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["symbol"] == "ETH/USDT"
    assert data["timeframe"] == "1d"
    assert data["exchange"] == "binance"
    assert data["candles_count"] == 100


def test_live_data_invalid_exchange(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test live data endpoint with invalid exchange name."""
    # Don't mock anything - let it fail naturally
    response = client.get(
        "/api/v1/live_data",
        params={"exchange": "invalid_exchange_that_doesnt_exist"},
    )

    # Should return a 500 error because exchange doesn't exist
    assert response.status_code in [400, 500]
    assert "detail" in response.json()


def test_live_data_invalid_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test live data endpoint with invalid symbol format."""
    response = client.get(
        "/api/v1/live_data",
        params={"symbol": "AB"},  # Too short (min_length=3)
    )

    # Should return validation error
    assert response.status_code == 422


def test_live_data_invalid_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test live data endpoint with invalid limit."""
    response = client.get(
        "/api/v1/live_data",
        params={"limit": 10},  # Too small (ge=20)
    )

    # Should return validation error
    assert response.status_code == 422


def test_live_data_limit_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test live data endpoint with limit that's too large."""
    response = client.get(
        "/api/v1/live_data",
        params={"limit": 3000},  # Too large (le=2000)
    )

    # Should return validation error
    assert response.status_code == 422
