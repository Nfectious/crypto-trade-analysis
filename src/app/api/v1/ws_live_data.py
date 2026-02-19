"""WebSocket endpoint for live data streaming."""

import asyncio
from typing import Any

import ccxt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.logging import get_logger
from app.services.market_data import fetch_live_data

logger = get_logger(__name__)

router = APIRouter(prefix="/live_data", tags=["websocket"])


@router.websocket("/ws")
async def websocket_live_data(
    websocket: WebSocket,
    symbol: str = Query(
        default="BTC/USDT",
        min_length=3,
        max_length=30,
        description="Trading pair symbol",
    ),
    timeframe: str = Query(
        default="1h",
        min_length=1,
        max_length=10,
        description="Candle timeframe",
    ),
    limit: int = Query(
        default=250,
        ge=20,
        le=2000,
        description="Number of candles to fetch",
    ),
    exchange: str = Query(
        default=settings.default_exchange,
        min_length=2,
        max_length=40,
        description="Exchange name",
    ),
    interval: int = Query(
        default=30,
        ge=5,
        le=300,
        description="Update interval in seconds",
    ),
) -> None:
    """
    WebSocket endpoint that streams recent candle data every N seconds.

    Sends live cryptocurrency OHLCV data with technical indicators at regular intervals.
    """
    await websocket.accept()
    logger.info(
        f"WebSocket connection established: {symbol} {timeframe} interval={interval}s"
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

                # Convert response to dict for JSON serialization
                data: dict[str, Any] = response.model_dump(mode="json")

                # Send data through websocket
                await websocket.send_json(data)
                logger.debug(f"Sent data update for {symbol}")

                # Wait for the specified interval
                await asyncio.sleep(interval)

            except ccxt.NetworkError as e:
                logger.error(f"Network error: {e}")
                await websocket.send_json(
                    {
                        "error": "network_error",
                        "detail": f"Network error connecting to exchange: {str(e)}",
                    }
                )
                await asyncio.sleep(interval)

            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error: {e}")
                await websocket.send_json(
                    {"error": "exchange_error", "detail": f"Exchange error: {str(e)}"}
                )
                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                await websocket.send_json(
                    {"error": "internal_error", "detail": f"Internal error: {str(e)}"}
                )
                await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for {symbol}")
