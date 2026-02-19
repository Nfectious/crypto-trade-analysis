"""WebSocket endpoint for live data streaming."""

import asyncio
import json
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
    symbol: str = Query(default="BTC/USDT", description="Trading pair symbol"),
    timeframe: str = Query(default="1h", description="Candle timeframe"),
    limit: int = Query(default=250, ge=20, le=2000, description="Number of candles to fetch"),
    exchange: str = Query(default=settings.default_exchange, description="Exchange name"),
    interval: int = Query(
        default=10, ge=1, le=300, description="Update interval in seconds"
    ),
) -> None:
    """
    WebSocket endpoint that streams recent candle data with indicators.

    Sends updates every N seconds based on the interval parameter.
    """
    await websocket.accept()
    logger.info(
        f"WebSocket connection established: {symbol} {timeframe} "
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

                # Prepare payload with recent candles
                payload: dict[str, Any] = {
                    "symbol": response.symbol,
                    "timeframe": response.timeframe,
                    "exchange": response.exchange,
                    "last_price": response.last_price,
                    "last_timestamp": response.last_timestamp.isoformat(),
                    "candles_count": response.candles_count,
                    "recent_candles": [
                        {
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
                        for candle in response.recent_candles
                    ],
                    "latest_indicators": {
                        "ema_20": response.latest_indicators.ema_20,
                        "ema_50": response.latest_indicators.ema_50,
                        "ema_200": response.latest_indicators.ema_200,
                        "rsi_14": response.latest_indicators.rsi_14,
                        "atr_14": response.latest_indicators.atr_14,
                    },
                    "meta": response.meta,
                }

                # Send data to client
                await websocket.send_text(json.dumps(payload))
                logger.debug(
                    f"Sent WebSocket update: {symbol} {timeframe} "
                    f"price={response.last_price}"
                )

            except ccxt.NetworkError as e:
                logger.error(f"Network error in WebSocket: {e}")
                error_payload = {
                    "error": "Network error",
                    "detail": f"Failed to fetch data from exchange: {str(e)}",
                }
                await websocket.send_text(json.dumps(error_payload))

            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error in WebSocket: {e}")
                error_payload = {
                    "error": "Exchange error",
                    "detail": str(e),
                }
                await websocket.send_text(json.dumps(error_payload))

            except Exception as e:
                logger.error(f"Unexpected error in WebSocket: {e}", exc_info=True)
                error_payload = {
                    "error": "Internal error",
                    "detail": str(e),
                }
                await websocket.send_text(json.dumps(error_payload))

            # Wait for the specified interval before next update
            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {symbol} {timeframe}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.close()
