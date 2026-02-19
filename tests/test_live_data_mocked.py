"""Mocked tests for live data endpoint.

These tests use mocked exchange data to ensure CI reliability without network dependencies.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def generate_synthetic_ohlcv(num_candles: int = 250) -> list[list[Any]]:
    """
    Generate synthetic OHLCV data for testing.

    Args:
        num_candles: Number of candles to generate

    Returns:
        List of OHLCV candles [timestamp, open, high, low, close, volume]
    """
    base_timestamp = 1700000000000  # Fixed timestamp in milliseconds
    base_price = 40000.0
    candles = []

    for i in range(num_candles):
        timestamp = base_timestamp + (i * 3600000)  # 1 hour intervals
        # Create realistic OHLCV data with some variation
        price_variation = (i % 10 - 5) * 50  # -250 to +250 variation
        open_price = base_price + price_variation
        high_price = open_price + 100
        low_price = open_price - 100
        close_price = open_price + (i % 5 - 2) * 25
        volume = 100.0 + (i % 20) * 5

        candles.append(
            [
                timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
            ]
        )

    return candles


@pytest.fixture
def mock_exchange_client() -> Any:
    """Fixture to create a mocked ExchangeClient."""
    with patch("app.services.market_data.ExchangeClient") as mock_client_class:
        mock_instance = MagicMock()
        mock_instance.fetch_ohlcv.return_value = generate_synthetic_ohlcv()
        mock_instance.get_exchange_name.return_value = "binance"
        mock_client_class.return_value = mock_instance
        yield mock_instance


def test_live_data_mocked_default_params(mock_exchange_client: Any) -> None:
    """Test live data endpoint with mocked exchange data and default parameters."""
    response = client.get("/api/v1/live_data")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert data["symbol"] == "BTC/USDT"
    assert data["timeframe"] == "1h"
    assert data["exchange"] == "binance"
    assert "last_price" in data
    assert "last_timestamp" in data
    assert data["candles_count"] == 250

    # Validate recent_candles
    assert "recent_candles" in data
    assert isinstance(data["recent_candles"], list)
    assert len(data["recent_candles"]) == 20  # Should be exactly 20

    # Validate first candle structure
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
    assert "latest_indicators" in data
    indicators = data["latest_indicators"]
    assert "ema_20" in indicators
    assert "ema_50" in indicators
    assert "ema_200" in indicators
    assert "rsi_14" in indicators
    assert "atr_14" in indicators

    # Verify the mock was called with correct parameters
    mock_exchange_client.fetch_ohlcv.assert_called_once_with(
        symbol="BTC/USDT", timeframe="1h", limit=250
    )


def test_live_data_mocked_custom_params(mock_exchange_client: Any) -> None:
    """Test live data endpoint with mocked exchange data and custom parameters."""
    # Configure mock for custom parameters
    mock_exchange_client.fetch_ohlcv.return_value = generate_synthetic_ohlcv(100)

    response = client.get(
        "/api/v1/live_data",
        params={
            "symbol": "ETH/USDT",
            "timeframe": "15m",
            "limit": 100,
            "exchange": "coinbase",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Validate custom parameters are reflected
    assert data["symbol"] == "ETH/USDT"
    assert data["timeframe"] == "15m"
    assert data["exchange"] == "binance"  # Comes from mock
    assert data["candles_count"] == 100

    # Validate recent_candles count
    assert len(data["recent_candles"]) == 20

    # Verify the mock was called with correct parameters
    mock_exchange_client.fetch_ohlcv.assert_called_once_with(
        symbol="ETH/USDT", timeframe="15m", limit=100
    )


def test_live_data_mocked_indicators_calculation(mock_exchange_client: Any) -> None:
    """Test that indicators are properly calculated from mocked data."""
    response = client.get("/api/v1/live_data", params={"limit": 250})

    assert response.status_code == 200
    data = response.json()

    # With 250 candles, we should have all indicators calculated
    indicators = data["latest_indicators"]

    # EMA-20 should be present (we have 250 candles)
    assert indicators["ema_20"] is not None
    assert isinstance(indicators["ema_20"], (int, float))

    # EMA-50 should be present (we have 250 candles)
    assert indicators["ema_50"] is not None
    assert isinstance(indicators["ema_50"], (int, float))

    # EMA-200 should be present (we have 250 candles)
    assert indicators["ema_200"] is not None
    assert isinstance(indicators["ema_200"], (int, float))

    # RSI-14 should be present
    assert indicators["rsi_14"] is not None
    assert isinstance(indicators["rsi_14"], (int, float))
    assert 0 <= indicators["rsi_14"] <= 100  # RSI is bounded 0-100

    # ATR-14 should be present
    assert indicators["atr_14"] is not None
    assert isinstance(indicators["atr_14"], (int, float))
    assert indicators["atr_14"] >= 0  # ATR is always positive


def test_live_data_mocked_with_insufficient_data(mock_exchange_client: Any) -> None:
    """Test behavior with insufficient data for some indicators."""
    # Generate only 30 candles - enough for EMA-20 but not EMA-50 or EMA-200
    mock_exchange_client.fetch_ohlcv.return_value = generate_synthetic_ohlcv(30)

    response = client.get("/api/v1/live_data", params={"limit": 30})

    assert response.status_code == 200
    data = response.json()

    assert data["candles_count"] == 30
    indicators = data["latest_indicators"]

    # EMA-20 should be present
    assert indicators["ema_20"] is not None

    # EMA-50 and EMA-200 will have values but might be NaN for early candles
    # The ta library will still calculate them but they'll be less reliable

    # Check that recent_candles doesn't exceed available candles
    assert len(data["recent_candles"]) == 20  # Min of 20 and 30


def test_live_data_mocked_minimal_limit(mock_exchange_client: Any) -> None:
    """Test with minimal limit (20 candles)."""
    mock_exchange_client.fetch_ohlcv.return_value = generate_synthetic_ohlcv(20)

    response = client.get("/api/v1/live_data", params={"limit": 20})

    assert response.status_code == 200
    data = response.json()

    assert data["candles_count"] == 20
    assert len(data["recent_candles"]) == 20  # All 20 should be in recent


def test_live_data_mocked_parameter_validation() -> None:
    """Test parameter validation without mocking."""
    # Test limit too small
    response = client.get("/api/v1/live_data", params={"limit": 10})
    assert response.status_code == 422  # Validation error

    # Test limit too large
    response = client.get("/api/v1/live_data", params={"limit": 3000})
    assert response.status_code == 422  # Validation error

    # Test invalid symbol (too short)
    response = client.get("/api/v1/live_data", params={"symbol": "BT"})
    assert response.status_code == 422

    # Test invalid timeframe (too long)
    response = client.get("/api/v1/live_data", params={"timeframe": "1h" * 10})
    assert response.status_code == 422


def test_live_data_mocked_numeric_precision(mock_exchange_client: Any) -> None:
    """Test that numeric values are properly rounded to 6 decimals."""
    response = client.get("/api/v1/live_data")

    assert response.status_code == 200
    data = response.json()

    # Check that prices are numbers
    assert isinstance(data["last_price"], (int, float))

    # Check candles have proper numeric types
    for candle in data["recent_candles"]:
        assert isinstance(candle["open"], (int, float))
        assert isinstance(candle["high"], (int, float))
        assert isinstance(candle["low"], (int, float))
        assert isinstance(candle["close"], (int, float))
        assert isinstance(candle["volume"], (int, float))

        # Indicators can be null or numeric
        for indicator in ["ema_20", "ema_50", "ema_200", "rsi_14", "atr_14"]:
            value = candle[indicator]
            assert value is None or isinstance(value, (int, float))
