"""Mocked tests for live data endpoint using synthetic data.

These tests use monkeypatch to stub ExchangeClient.fetch_ohlcv with synthetic OHLCV
data to ensure deterministic and reliable CI testing without network calls.
"""

import pytest
from fastapi.testclient import TestClient

from app.integrations.exchanges import ExchangeClient
from app.main import app

client = TestClient(app)

# Type alias for OHLCV candle data: [timestamp, open, high, low, close, volume]
OHLCVCandle = list[int | float]
OHLCVData = list[OHLCVCandle]


def generate_synthetic_ohlcv(
    count: int, base_price: float = 40000.0, base_timestamp: int = 1704067200000
) -> OHLCVData:
    """
    Generate synthetic OHLCV data for testing.

    Args:
        count: Number of candles to generate
        base_price: Base price for the first candle
        base_timestamp: Base timestamp in milliseconds

    Returns:
        List of OHLCV data in the format [timestamp, open, high, low, close, volume]
    """
    ohlcv_data = []
    timestamp = base_timestamp
    price = base_price

    for i in range(count):
        # Simple price variation
        open_price = price
        high_price = price + (i % 5) * 10
        low_price = price - (i % 3) * 10
        close_price = price + (i % 7 - 3) * 5
        volume = 100.0 + (i % 10) * 10

        ohlcv_data.append(
            [timestamp, open_price, high_price, low_price, close_price, volume]
        )

        # Increment timestamp by 1 hour (3600000 ms)
        timestamp += 3600000
        price = close_price

    return ohlcv_data


def test_live_data_endpoint_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test live data endpoint with mocked OHLCV data."""

    # Generate synthetic OHLCV data (300 candles to ensure all indicators can be calculated)
    synthetic_ohlcv = generate_synthetic_ohlcv(count=300)

    # Mock the fetch_ohlcv method
    def mock_fetch_ohlcv(
        self: ExchangeClient, symbol: str, timeframe: str, limit: int
    ) -> OHLCVData:
        return synthetic_ohlcv

    monkeypatch.setattr(ExchangeClient, "fetch_ohlcv", mock_fetch_ohlcv)

    # Make request
    response = client.get("/api/v1/live_data")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert data["symbol"] == "BTC/USDT"
    assert data["timeframe"] == "1h"
    assert data["exchange"] == "binance"
    assert "last_price" in data
    assert "last_timestamp" in data
    assert data["candles_count"] == 300
    assert isinstance(data["recent_candles"], list)
    assert len(data["recent_candles"]) == 20
    assert "latest_indicators" in data
    assert "meta" in data

    # Validate candle structure
    first_candle = data["recent_candles"][0]
    assert "timestamp" in first_candle
    assert "open" in first_candle
    assert "high" in first_candle
    assert "low" in first_candle
    assert "close" in first_candle
    assert "volume" in first_candle
    assert "ema_20" in first_candle
    assert "ema_50" in first_candle
    assert "ema_200" in first_candle
    assert "rsi_14" in first_candle
    assert "atr_14" in first_candle

    # Validate latest indicators
    indicators = data["latest_indicators"]
    assert "ema_20" in indicators
    assert "ema_50" in indicators
    assert "ema_200" in indicators
    assert "rsi_14" in indicators
    assert "atr_14" in indicators

    # With 300 candles, all indicators should have values
    assert indicators["ema_20"] is not None
    assert indicators["ema_50"] is not None
    assert indicators["ema_200"] is not None
    assert indicators["rsi_14"] is not None
    assert indicators["atr_14"] is not None


def test_live_data_with_custom_parameters_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test live data endpoint with custom parameters using mocked data."""

    # Generate synthetic OHLCV data
    synthetic_ohlcv = generate_synthetic_ohlcv(count=100, base_price=2000.0)

    # Mock the fetch_ohlcv method
    def mock_fetch_ohlcv(
        self: ExchangeClient, symbol: str, timeframe: str, limit: int
    ) -> OHLCVData:
        return synthetic_ohlcv[:limit]

    monkeypatch.setattr(ExchangeClient, "fetch_ohlcv", mock_fetch_ohlcv)

    # Make request with custom parameters
    response = client.get(
        "/api/v1/live_data",
        params={"symbol": "ETH/USDT", "timeframe": "1d", "limit": 100, "exchange": "binance"},
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()

    assert data["symbol"] == "ETH/USDT"
    assert data["timeframe"] == "1d"
    assert data["exchange"] == "binance"
    assert data["candles_count"] == 100


def test_live_data_insufficient_data_for_indicators(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that early candles have null indicators when insufficient data."""

    # Generate only 30 candles (not enough for EMA-50, EMA-200)
    synthetic_ohlcv = generate_synthetic_ohlcv(count=30)

    def mock_fetch_ohlcv(
        self: ExchangeClient, symbol: str, timeframe: str, limit: int
    ) -> OHLCVData:
        return synthetic_ohlcv

    monkeypatch.setattr(ExchangeClient, "fetch_ohlcv", mock_fetch_ohlcv)

    # Make request
    response = client.get("/api/v1/live_data")

    # Assertions
    assert response.status_code == 200
    data = response.json()

    # Should have EMA-20 and possibly RSI/ATR, but not EMA-50 or EMA-200
    indicators = data["latest_indicators"]

    # EMA-20 should exist (we have 30 candles)
    assert indicators["ema_20"] is not None

    # EMA-50 should be None (not enough data)
    assert indicators["ema_50"] is None

    # EMA-200 should be None (not enough data)
    assert indicators["ema_200"] is None


def test_live_data_network_error_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that network errors are properly handled."""
    import ccxt

    # Mock the fetch_ohlcv method to raise NetworkError
    def mock_fetch_ohlcv_network_error(
        self: ExchangeClient, symbol: str, timeframe: str, limit: int
    ) -> OHLCVData:
        raise ccxt.NetworkError("Simulated network error")

    monkeypatch.setattr(ExchangeClient, "fetch_ohlcv", mock_fetch_ohlcv_network_error)

    # Make request
    response = client.get("/api/v1/live_data")

    # Should return 503 for network errors
    assert response.status_code == 503
    assert "Network error" in response.json()["detail"]


def test_live_data_exchange_error_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that exchange errors are properly handled."""
    import ccxt

    # Mock the fetch_ohlcv method to raise ExchangeError
    def mock_fetch_ohlcv_exchange_error(
        self: ExchangeClient, symbol: str, timeframe: str, limit: int
    ) -> OHLCVData:
        raise ccxt.ExchangeError("Invalid symbol")

    monkeypatch.setattr(ExchangeClient, "fetch_ohlcv", mock_fetch_ohlcv_exchange_error)

    # Make request
    response = client.get("/api/v1/live_data")

    # Should return 400 for exchange errors
    assert response.status_code == 400
    assert "Exchange error" in response.json()["detail"]


def test_live_data_validation_errors() -> None:
    """Test that validation errors are properly handled."""

    # Test with invalid limit (too small)
    response = client.get("/api/v1/live_data", params={"limit": 10})
    assert response.status_code == 422

    # Test with invalid limit (too large)
    response = client.get("/api/v1/live_data", params={"limit": 3000})
    assert response.status_code == 422

    # Test with invalid symbol (too short)
    response = client.get("/api/v1/live_data", params={"symbol": "BT"})
    assert response.status_code == 422

    # Test with invalid timeframe (empty)
    response = client.get("/api/v1/live_data", params={"timeframe": ""})
    assert response.status_code == 422
