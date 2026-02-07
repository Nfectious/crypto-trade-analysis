"""Live data API routes."""

import ccxt
from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.live_data import LiveDataResponse
from app.services.market_data import fetch_live_data

logger = get_logger(__name__)

router = APIRouter(prefix="/live_data", tags=["live_data"])


@router.get("", response_model=LiveDataResponse)
async def get_live_data(
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
) -> LiveDataResponse:
    """
    Fetch live cryptocurrency OHLCV data with technical indicators.

    Returns market data with calculated EMA, RSI, and ATR indicators.
    """
    try:
        logger.info(
            f"Fetching live data: {symbol} {timeframe} limit={limit} exchange={exchange}"
        )

        response = fetch_live_data(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            exchange_name=exchange,
            market_type=settings.default_market_type,
        )

        logger.info(f"Successfully fetched {response.candles_count} candles")
        return response

    except ccxt.NetworkError as e:
        logger.error(f"Network error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Network error connecting to exchange: {str(e)}",
        ) from e

    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Exchange error: {str(e)}",
        ) from e

    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid parameter: {str(e)}",
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        ) from e
