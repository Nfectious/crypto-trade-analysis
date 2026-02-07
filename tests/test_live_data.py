"""Tests for live data endpoint.

Note: This is a smoke test that makes real network calls to exchanges.
For CI reliability, consider adding mocked tests.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_live_data_endpoint_smoke() -> None:
    """Smoke test for live data endpoint with default parameters."""
    response = client.get("/api/v1/live_data")

    # This might fail due to network issues, so we handle both success and network errors
    if response.status_code == 200:
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

        # Validate recent_candles structure
        assert isinstance(data["recent_candles"], list)
        assert len(data["recent_candles"]) <= 20

        if len(data["recent_candles"]) > 0:
            candle = data["recent_candles"][0]
            assert "timestamp" in candle
            assert "open" in candle
            assert "high" in candle
            assert "low" in candle
            assert "close" in candle
            assert "volume" in candle

        # Validate latest_indicators structure
        indicators = data["latest_indicators"]
        assert "ema_20" in indicators
        assert "ema_50" in indicators
        assert "ema_200" in indicators
        assert "rsi_14" in indicators
        assert "atr_14" in indicators

    elif response.status_code == 503:
        # Network error is acceptable for smoke test
        assert "Network error" in response.json()["detail"]
    else:
        # Other errors should be investigated
        assert False, f"Unexpected status code: {response.status_code}"


def test_live_data_with_custom_parameters() -> None:
    """Test live data endpoint with custom parameters."""
    response = client.get(
        "/api/v1/live_data",
        params={"symbol": "ETH/USDT", "timeframe": "1d", "limit": 100, "exchange": "binance"},
    )

    # Similar to above, handle both success and network errors
    if response.status_code == 200:
        data = response.json()
        assert data["symbol"] == "ETH/USDT"
        assert data["timeframe"] == "1d"
        assert data["exchange"] == "binance"
    elif response.status_code == 503:
        # Network error is acceptable
        pass
    else:
        assert False, f"Unexpected status code: {response.status_code}"
