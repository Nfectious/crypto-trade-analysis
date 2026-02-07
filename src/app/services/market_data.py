"""Market data processing service."""

from typing import Any

import pandas as pd

from app.core.logging import get_logger
from app.integrations.exchanges import ExchangeClient
from app.schemas.live_data import Candle, LatestIndicators, LiveDataResponse
from app.services.indicators import calculate_indicators, clean_value

logger = get_logger(__name__)


def process_ohlcv_data(
    ohlcv_data: list[list[Any]], symbol: str, timeframe: str, exchange_name: str
) -> LiveDataResponse:
    """
    Process raw OHLCV data and calculate indicators.

    Args:
        ohlcv_data: Raw OHLCV data from exchange
        symbol: Trading pair symbol
        timeframe: Candle timeframe
        exchange_name: Exchange name

    Returns:
        LiveDataResponse with processed data and indicators
    """
    logger.info(f"Processing {len(ohlcv_data)} OHLCV candles")

    # Convert to DataFrame
    df = pd.DataFrame(
        ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )

    # Convert timestamp from milliseconds to datetime (UTC)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    # Round numeric values to 6 decimals
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].round(6)

    # Calculate indicators
    df = calculate_indicators(df)

    # Round indicator values to 6 decimals
    indicator_cols = ["ema_20", "ema_50", "ema_200", "rsi_14", "atr_14"]
    df[indicator_cols] = df[indicator_cols].round(6)

    # Get last price and timestamp
    last_row = df.iloc[-1]
    last_price = float(last_row["close"])
    last_timestamp = last_row["timestamp"].to_pydatetime()

    # Prepare latest indicators
    latest_indicators = LatestIndicators(
        ema_20=clean_value(last_row["ema_20"]),
        ema_50=clean_value(last_row["ema_50"]),
        ema_200=clean_value(last_row["ema_200"]),
        rsi_14=clean_value(last_row["rsi_14"]),
        atr_14=clean_value(last_row["atr_14"]),
    )

    # Get last 20 candles
    recent_df = df.tail(20)
    recent_candles = []

    for _, row in recent_df.iterrows():
        candle = Candle(
            timestamp=row["timestamp"].to_pydatetime(),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
            ema_20=clean_value(row["ema_20"]),
            ema_50=clean_value(row["ema_50"]),
            ema_200=clean_value(row["ema_200"]),
            rsi_14=clean_value(row["rsi_14"]),
            atr_14=clean_value(row["atr_14"]),
        )
        recent_candles.append(candle)

    # Build response
    response = LiveDataResponse(
        symbol=symbol,
        timeframe=timeframe,
        exchange=exchange_name,
        last_price=last_price,
        last_timestamp=last_timestamp,
        candles_count=len(df),
        recent_candles=recent_candles,
        latest_indicators=latest_indicators,
        meta={},
    )

    return response


def fetch_live_data(
    symbol: str, timeframe: str, limit: int, exchange_name: str, market_type: str
) -> LiveDataResponse:
    """
    Fetch and process live market data.

    Args:
        symbol: Trading pair symbol
        timeframe: Candle timeframe
        limit: Number of candles to fetch
        exchange_name: Exchange name
        market_type: Market type (spot, future, etc.)

    Returns:
        LiveDataResponse with market data and indicators
    """
    # Create exchange client
    exchange_client = ExchangeClient(exchange_name=exchange_name, market_type=market_type)

    # Fetch OHLCV data
    ohlcv_data = exchange_client.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)

    # Process the data
    response = process_ohlcv_data(
        ohlcv_data=ohlcv_data,
        symbol=symbol,
        timeframe=timeframe,
        exchange_name=exchange_client.get_exchange_name(),
    )

    return response
