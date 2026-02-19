"""WebSocket endpoint for streaming live data."""

import asyncio
from typing import Any

import ccxt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.logging import get_logger
from app.services.market_data import fetch_live_data

logger = get_logger(__name__)

router = APIRouter(prefix="/live_data", tags=["live_data"])


def candle_to_dict(candle: Any) -> dict[str, Any]:
    """Convert a Candle model to a JSON-serializable dict."""
    return {
        "timestamp": candle.timestamp.isoformat(),
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "ema_20": candle.ema_20,
        "ema_50": candle.ema_50,
        "ema_200": candle.ema_200,
        "rsi_14": candle.rsi_14,
        "atr_14": candle.atr_14,
    }


def response_to_dict(response: Any) -> dict[str, Any]:
    """Convert a LiveDataResponse to a JSON-serializable dict."""
    return {
        "symbol": response.symbol,
        "timeframe": response.timeframe,
        "exchange": response.exchange,
        "last_price": response.last_price,
        "last_timestamp": response.last_timestamp.isoformat(),
        "candles_count": response.candles_count,
        "recent_candles": [candle_to_dict(c) for c in response.recent_candles],
        "latest_indicators": {
            "ema_20": response.latest_indicators.ema_20,
            "ema_50": response.latest_indicators.ema_50,
            "ema_200": response.latest_indicators.ema_200,
            "rsi_14": response.latest_indicators.rsi_14,
            "atr_14": response.latest_indicators.atr_14,
        },
        "meta": response.meta,
    }


@router.websocket("/ws")
async def websocket_live_data(
    websocket: WebSocket,
    symbol: str = Query(
        default="BTC/USDT",
        description="Trading pair symbol",
    ),
    timeframe: str = Query(
        default="1h",
        description="Candle timeframe",
    ),
    limit: int = Query(
        default=250,
        description="Number of candles to fetch",
    ),
    exchange: str = Query(
        default=settings.default_exchange,
        description="Exchange name",
    ),
    interval: int = Query(
        default=5,
        description="Update interval in seconds",
    ),
) -> None:
    """
    WebSocket endpoint for streaming live cryptocurrency data.

    Continuously streams market data with technical indicators at the specified interval.
    """
    await websocket.accept()
    logger.info(
        f"WebSocket connection accepted: {symbol} {timeframe} "
        f"exchange={exchange} interval={interval}s"
    )

    try:
        while True:
            try:
                # Fetch live data
                response = fetch_live_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit,
                    exchange_name=exchange,
                    market_type=settings.default_market_type,
                )

                # Convert to dict and send as JSON
                data = response_to_dict(response)
                await websocket.send_json(data)

                logger.debug(f"Sent data for {symbol} via WebSocket")

            except ccxt.NetworkError as e:
                logger.error(f"Network error in WebSocket: {e}")
                error_msg = {
                    "error": "network_error",
                    "detail": f"Network error connecting to exchange: {str(e)}",
                }
                await websocket.send_json(error_msg)

            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error in WebSocket: {e}")
                error_msg = {
                    "error": "exchange_error",
                    "detail": f"Exchange error: {str(e)}",
                }
                await websocket.send_json(error_msg)

            except Exception as e:
                logger.error(f"Unexpected error in WebSocket: {e}", exc_info=True)
                error_msg = {
                    "error": "internal_error",
                    "detail": f"Internal server error: {str(e)}",
                }
                await websocket.send_json(error_msg)

            # Wait for the specified interval before next update
            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.close()
