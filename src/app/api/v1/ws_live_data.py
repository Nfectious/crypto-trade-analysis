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
        default=5,
        ge=1,
        le=60,
        description="Update interval in seconds",
    ),
) -> None:
    """
    WebSocket endpoint that streams recent candle data.

    Streams live market data with technical indicators at regular intervals.
    The client receives a JSON payload every `interval` seconds.

    Error Handling:
    - NetworkError and ExchangeError: Sends error message and retries after interval
    - ValueError (invalid parameters): Sends error message and closes connection
    - Other exceptions: Sends error message and retries after interval
    """
    await websocket.accept()
    logger.info(
        f"WebSocket connection established for {symbol} {timeframe} "
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

                # Convert to dict for JSON serialization
                data: dict[str, Any] = response.model_dump(mode="json")

                # Send data to client
                await websocket.send_json(data)
                logger.debug(f"Sent data for {symbol} to WebSocket client")

                # Wait for the specified interval
                await asyncio.sleep(interval)

            except ccxt.NetworkError as e:
                logger.error(f"Network error in WebSocket: {e}")
                await websocket.send_json(
                    {
                        "error": "network_error",
                        "message": f"Network error connecting to exchange: {str(e)}",
                        "status_code": 503,
                    }
                )
                await asyncio.sleep(interval)

            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error in WebSocket: {e}")
                await websocket.send_json(
                    {
                        "error": "exchange_error",
                        "message": f"Exchange error: {str(e)}",
                        "status_code": 400,
                    }
                )
                await asyncio.sleep(interval)

            except ValueError as e:
                logger.error(f"Value error in WebSocket: {e}")
                await websocket.send_json(
                    {
                        "error": "value_error",
                        "message": f"Invalid parameter: {str(e)}",
                        "status_code": 400,
                    }
                )
                # Close connection on value error since parameters won't change
                break

            except Exception as e:
                logger.error(f"Unexpected error in WebSocket: {e}", exc_info=True)
                await websocket.send_json(
                    {
                        "error": "internal_error",
                        "message": f"Internal server error: {str(e)}",
                        "status_code": 500,
                    }
                )
                # Continue on unexpected errors, but wait
                await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for {symbol}")

    except Exception as e:
        logger.error(f"Fatal WebSocket error: {e}", exc_info=True)

    finally:
        logger.info(f"WebSocket connection closed for {symbol}")
