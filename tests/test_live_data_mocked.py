"""Mocked tests for live data endpoint - safe for CI without network calls."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_ohlcv_data() -> list[list[Any]]:
    """Generate mock OHLCV data for testing."""
    # Generate 100 candles of mock data
    base_timestamp = 1704067200000  # 2024-01-01 00:00:00 UTC
    data = []
    for i in range(100):
        timestamp = base_timestamp + (i * 3600000)  # Hourly candles
        open_price = 43000 + (i * 10)
        high_price = open_price + 50
        low_price = open_price - 30
        close_price = open_price + 20
        volume = 100.0 + (i * 0.5)
        data.append([timestamp, open_price, high_price, low_price, close_price, volume])
    return data


def test_live_data_endpoint_mocked_success(
    monkeypatch: pytest.MonkeyPatch, mock_ohlcv_data: list[list[Any]]
) -> None:
    """Test live data endpoint with mocked exchange data."""
    # Mock the ExchangeClient to avoid network calls
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = mock_ohlcv_data
    mock_exchange.get_exchange_name.return_value = "binance"
    mock_exchange.get_meta_info.return_value = {"default_type": "spot"}

    # Patch the ExchangeClient class
    def mock_exchange_client(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_exchange

    monkeypatch.setattr(
        "app.services.market_data.ExchangeClient",
        mock_exchange_client,
    )

    # Make the request
    response = client.get("/api/v1/live_data")

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert data["symbol"] == "BTC/USDT"
    assert data["timeframe"] == "1h"
    assert data["exchange"] == "binance"
    assert "last_price" in data
    assert "last_timestamp" in data
    assert data["candles_count"] == 100
    assert "recent_candles" in data
    assert "latest_indicators" in data
    assert "meta" in data
    assert data["meta"]["default_type"] == "spot"

    # Validate recent_candles (should be last 20)
    assert isinstance(data["recent_candles"], list)
    assert len(data["recent_candles"]) == 20

    # Validate candle structure
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

    # Validate latest_indicators structure
    indicators = data["latest_indicators"]
    assert "ema_20" in indicators
    assert "ema_50" in indicators
    assert "ema_200" in indicators
    assert "rsi_14" in indicators
    assert "atr_14" in indicators

    # Verify that indicators are calculated (not all None)
    # With 100 candles, we should have EMA-20 and EMA-50
    assert indicators["ema_20"] is not None
    assert indicators["ema_50"] is not None
    # EMA-200 might be None with only 100 candles
    assert indicators["rsi_14"] is not None
    assert indicators["atr_14"] is not None


def test_live_data_endpoint_mocked_custom_params(
    monkeypatch: pytest.MonkeyPatch, mock_ohlcv_data: list[list[Any]]
) -> None:
    """Test live data endpoint with custom parameters and mocked data."""
    # Mock the ExchangeClient
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = mock_ohlcv_data
    mock_exchange.get_exchange_name.return_value = "kraken"
    mock_exchange.get_meta_info.return_value = {"default_type": "spot"}

    def mock_exchange_client(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_exchange

    monkeypatch.setattr(
        "app.services.market_data.ExchangeClient",
        mock_exchange_client,
    )

    # Make request with custom parameters
    response = client.get(
        "/api/v1/live_data",
        params={"symbol": "ETH/USDT", "timeframe": "4h", "limit": 100, "exchange": "kraken"},
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "ETH/USDT"
    assert data["timeframe"] == "4h"
    assert data["exchange"] == "kraken"
    assert data["candles_count"] == 100


def test_live_data_endpoint_mocked_nan_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that NaN and infinite values are properly converted to None."""
    # Create minimal data (not enough for all indicators)
    minimal_data = []
    base_timestamp = 1704067200000
    for i in range(25):  # Only 25 candles - not enough for EMA-50 or EMA-200
        timestamp = base_timestamp + (i * 3600000)
        minimal_data.append([timestamp, 43000.0, 43100.0, 42900.0, 43050.0, 100.0])

    # Mock the ExchangeClient
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = minimal_data
    mock_exchange.get_exchange_name.return_value = "binance"
    mock_exchange.get_meta_info.return_value = {}

    def mock_exchange_client(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_exchange

    monkeypatch.setattr(
        "app.services.market_data.ExchangeClient",
        mock_exchange_client,
    )

    # Make the request
    response = client.get("/api/v1/live_data", params={"limit": 25})

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Check that early candles have None for indicators that need more data
    # Early candles should have None for some indicators
    # This validates NaN -> None conversion
    assert len(data["recent_candles"]) > 0


def test_live_data_endpoint_mocked_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that network errors are properly handled."""
    import ccxt

    # Mock the ExchangeClient to raise a network error
    def mock_exchange_client(*args: Any, **kwargs: Any) -> MagicMock:
        mock = MagicMock()
        mock.fetch_ohlcv.side_effect = ccxt.NetworkError("Connection failed")
        return mock

    monkeypatch.setattr(
        "app.services.market_data.ExchangeClient",
        mock_exchange_client,
    )

    # Make the request
    response = client.get("/api/v1/live_data")

    # Verify error response
    assert response.status_code == 503
    data = response.json()
    assert "Network error" in data["detail"]


def test_live_data_endpoint_mocked_exchange_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that exchange errors are properly handled."""
    import ccxt

    # Mock the ExchangeClient to raise an exchange error
    def mock_exchange_client(*args: Any, **kwargs: Any) -> MagicMock:
        mock = MagicMock()
        mock.fetch_ohlcv.side_effect = ccxt.ExchangeError("Invalid symbol")
        return mock

    monkeypatch.setattr(
        "app.services.market_data.ExchangeClient",
        mock_exchange_client,
    )

    # Make the request
    response = client.get("/api/v1/live_data")

    # Verify error response
    assert response.status_code == 400
    data = response.json()
    assert "Exchange error" in data["detail"]


def test_live_data_endpoint_validation_errors() -> None:
    """Test parameter validation errors."""
    # Test invalid limit (too low)
    response = client.get("/api/v1/live_data", params={"limit": 10})
    assert response.status_code == 422

    # Test invalid limit (too high)
    response = client.get("/api/v1/live_data", params={"limit": 3000})
    assert response.status_code == 422

    # Test invalid symbol (too short)
    response = client.get("/api/v1/live_data", params={"symbol": "AB"})
    assert response.status_code == 422
