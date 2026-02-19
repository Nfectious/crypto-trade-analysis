"""WebSocket endpoint for streaming live data updates."""

import asyncio

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
        default=60,
        ge=10,
        le=300,
        description="Update interval in seconds",
    ),
) -> None:
    """
    WebSocket endpoint for streaming cryptocurrency data.

    Streams updated market data at configurable intervals.
    Send 'close' message to gracefully disconnect.
    """
    await websocket.accept()
    logger.info(
        f"WebSocket connection established: {symbol} {timeframe} "
        f"exchange={exchange} interval={interval}s"
    )

    try:
        while True:
            try:
                # Fetch fresh data
                response = fetch_live_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit,
                    exchange_name=exchange,
                    market_type=settings.default_market_type,
                )

                # Convert to dict for JSON serialization
                data = response.model_dump(mode="json")

                # Send data to client
                await websocket.send_json(data)
                logger.debug(f"Sent data update: {symbol} @ {response.last_price}")

                # Wait for next interval or check for close message
                try:
                    # Use asyncio.wait_for to check for messages during wait
                    message = await asyncio.wait_for(
                        websocket.receive_text(), timeout=interval
                    )
                    if message.lower() == "close":
                        logger.info("Client requested disconnect")
                        await websocket.close()
                        break
                except TimeoutError:
                    # Timeout is expected - continue to next update
                    pass

            except ccxt.NetworkError as e:
                logger.error(f"Network error: {e}")
                error_msg = {"error": "network_error", "detail": str(e)}
                await websocket.send_json(error_msg)
                # Wait before retry
                await asyncio.sleep(interval)

            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error: {e}")
                error_msg = {"error": "exchange_error", "detail": str(e)}
                await websocket.send_json(error_msg)
                # Wait before retry
                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Unexpected error in WebSocket: {e}", exc_info=True)
                error_msg = {"error": "internal_error", "detail": str(e)}
                await websocket.send_json(error_msg)
                # Wait before retry
                await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {symbol} {timeframe}")
    except Exception as e:
        logger.error(f"Fatal WebSocket error: {e}", exc_info=True)
        try:
            await websocket.close()
        except Exception as close_error:
            logger.debug(f"Error closing WebSocket: {close_error}")
