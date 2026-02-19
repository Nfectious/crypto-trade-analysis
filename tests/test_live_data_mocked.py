"""Mocked tests for live data endpoint.

These tests use monkeypatch to mock ccxt responses for deterministic CI testing.
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_ohlcv_data() -> list[list[Any]]:
    """Generate deterministic mock OHLCV data for testing."""
    # Create 100 candles of mock data
    base_timestamp = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
    candles = []
    
    for i in range(100):
        timestamp = base_timestamp + (i * 3600000)  # 1 hour intervals
        open_price = 40000.0 + (i * 10)
        high_price = open_price + 100
        low_price = open_price - 50
        close_price = open_price + 50
        volume = 100.0 + i
        
        candles.append([timestamp, open_price, high_price, low_price, close_price, volume])
    
    return candles


def test_live_data_endpoint_mocked(mock_ohlcv_data: list[list[Any]]) -> None:
    """Test live data endpoint with mocked exchange data."""
    # Create a mock exchange object
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = mock_ohlcv_data
    
    # Patch the ExchangeClient to return our mock exchange
    with patch(
        "app.integrations.exchanges.ExchangeClient._create_exchange",
        return_value=mock_exchange,
    ):
        # Make request
        response = client.get("/api/v1/live_data")
        
        # Validate response
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert data["symbol"] == "BTC/USDT"
        assert data["timeframe"] == "1h"
        assert data["exchange"] == "binance"
        assert "last_price" in data
        assert "last_timestamp" in data
        assert data["candles_count"] == 100
        
        # Check recent_candles (should be last 20)
        assert len(data["recent_candles"]) == 20
        
        # Verify first recent candle structure
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
        
        # Check latest_indicators
        indicators = data["latest_indicators"]
        assert "ema_20" in indicators
        assert "ema_50" in indicators
        assert "ema_200" in indicators
        assert "rsi_14" in indicators
        assert "atr_14" in indicators
        
        # With 100 candles, we should have all indicators calculated
        assert indicators["ema_20"] is not None
        assert indicators["ema_50"] is not None
        # EMA_200 might be None with only 100 candles
        assert indicators["rsi_14"] is not None
        assert indicators["atr_14"] is not None


def test_live_data_custom_params_mocked(mock_ohlcv_data: list[list[Any]]) -> None:
    """Test live data endpoint with custom parameters and mocked data."""
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = mock_ohlcv_data[:50]  # Return only 50 candles
    
    with patch(
        "app.integrations.exchanges.ExchangeClient._create_exchange",
        return_value=mock_exchange,
    ):
        # Make request with custom parameters
        response = client.get(
            "/api/v1/live_data",
            params={"symbol": "ETH/USDT", "timeframe": "1d", "limit": 50, "exchange": "binance"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == "ETH/USDT"
        assert data["timeframe"] == "1d"
        assert data["exchange"] == "binance"
        assert data["candles_count"] == 50
        assert len(data["recent_candles"]) == 20


def test_live_data_small_dataset_mocked() -> None:
    """Test with small dataset (20 candles) - minimum required."""
    # Create exactly 20 candles
    base_timestamp = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
    small_data = []
    
    for i in range(20):
        timestamp = base_timestamp + (i * 3600000)
        small_data.append([timestamp, 40000.0, 40100.0, 39900.0, 40050.0, 100.0])
    
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.return_value = small_data
    
    with patch(
        "app.integrations.exchanges.ExchangeClient._create_exchange",
        return_value=mock_exchange,
    ):
        response = client.get("/api/v1/live_data", params={"limit": 20})
        
        assert response.status_code == 200
        data = response.json()
        
        # With only 20 candles, should return all 20 as recent_candles
        assert data["candles_count"] == 20
        assert len(data["recent_candles"]) == 20
        
        # EMA-20 should be calculated, but EMA-50 and EMA-200 will be null
        indicators = data["latest_indicators"]
        assert indicators["ema_20"] is not None
        assert indicators["ema_50"] is None  # Not enough data
        assert indicators["ema_200"] is None  # Not enough data


def test_live_data_network_error_mocked() -> None:
    """Test handling of network errors."""
    import ccxt
    
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.side_effect = ccxt.NetworkError("Connection timeout")
    
    with patch(
        "app.integrations.exchanges.ExchangeClient._create_exchange",
        return_value=mock_exchange,
    ):
        response = client.get("/api/v1/live_data")
        
        # Should return 503 for network errors
        assert response.status_code == 503
        assert "Network error" in response.json()["detail"]


def test_live_data_exchange_error_mocked() -> None:
    """Test handling of exchange errors."""
    import ccxt
    
    mock_exchange = MagicMock()
    mock_exchange.fetch_ohlcv.side_effect = ccxt.ExchangeError("Invalid symbol")
    
    with patch(
        "app.integrations.exchanges.ExchangeClient._create_exchange",
        return_value=mock_exchange,
    ):
        response = client.get("/api/v1/live_data")
        
        # Should return 400 for exchange errors
        assert response.status_code == 400
        assert "Exchange error" in response.json()["detail"]


def test_live_data_invalid_exchange_mocked() -> None:
    """Test handling of invalid exchange name."""
    # Mock hasattr to return False for invalid exchange, causing ValueError in ExchangeClient
    with patch("app.integrations.exchanges.hasattr", return_value=False):
        response = client.get("/api/v1/live_data", params={"exchange": "invalid_exchange"})
        
        # Should return 400 for invalid exchange
        assert response.status_code == 400
        assert "not supported" in response.json()["detail"].lower()


def test_live_data_validation_errors() -> None:
    """Test query parameter validation."""
    # Test invalid symbol (too short)
    response = client.get("/api/v1/live_data", params={"symbol": "BT"})
    assert response.status_code == 422
    
    # Test invalid limit (too low)
    response = client.get("/api/v1/live_data", params={"limit": 10})
    assert response.status_code == 422
    
    # Test invalid limit (too high)
    response = client.get("/api/v1/live_data", params={"limit": 3000})
    assert response.status_code == 422
