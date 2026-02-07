"""Technical indicators calculation using the ta library."""

import math
from typing import Any

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange

from app.core.logging import get_logger

logger = get_logger(__name__)


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical indicators on OHLCV dataframe.

    Args:
        df: DataFrame with columns: timestamp, open, high, low, close, volume

    Returns:
        DataFrame with additional indicator columns
    """
    logger.info(f"Calculating indicators for {len(df)} candles")

    # Ensure we have numeric types
    df = df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")

    # Calculate EMAs
    df["ema_20"] = EMAIndicator(close=df["close"], window=20).ema_indicator()
    df["ema_50"] = EMAIndicator(close=df["close"], window=50).ema_indicator()
    df["ema_200"] = EMAIndicator(close=df["close"], window=200).ema_indicator()

    # Calculate RSI
    df["rsi_14"] = RSIIndicator(close=df["close"], window=14).rsi()

    # Calculate ATR
    df["atr_14"] = AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=14
    ).average_true_range()

    return df


def clean_value(value: Any) -> Any:
    """
    Clean a value to ensure JSON serialization.

    Converts NaN and infinity to None.
    """
    if pd.isna(value) or (isinstance(value, float) and not math.isfinite(value)):
        return None
    return value
