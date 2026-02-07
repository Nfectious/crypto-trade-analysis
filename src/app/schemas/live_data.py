"""Pydantic schemas for live data API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class LatestIndicators(BaseModel):
    """Latest technical indicator values."""

    ema_20: Optional[float] = Field(None, description="20-period EMA")
    ema_50: Optional[float] = Field(None, description="50-period EMA")
    ema_200: Optional[float] = Field(None, description="200-period EMA")
    rsi_14: Optional[float] = Field(None, description="14-period RSI")
    atr_14: Optional[float] = Field(None, description="14-period ATR")


class Candle(BaseModel):
    """OHLCV candle with technical indicators."""

    timestamp: datetime = Field(..., description="Candle timestamp")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: float = Field(..., description="Trading volume")
    ema_20: Optional[float] = Field(None, description="20-period EMA")
    ema_50: Optional[float] = Field(None, description="50-period EMA")
    ema_200: Optional[float] = Field(None, description="200-period EMA")
    rsi_14: Optional[float] = Field(None, description="14-period RSI")
    atr_14: Optional[float] = Field(None, description="14-period ATR")


class LiveDataResponse(BaseModel):
    """Response model for live data endpoint."""

    symbol: str = Field(..., description="Trading pair symbol")
    timeframe: str = Field(..., description="Timeframe for candles")
    exchange: str = Field(..., description="Exchange name")
    last_price: float = Field(..., description="Most recent closing price")
    last_timestamp: datetime = Field(..., description="Most recent candle timestamp")
    candles_count: int = Field(..., description="Total number of candles fetched")
    recent_candles: list[Candle] = Field(
        ..., description="Last 20 candles with indicators"
    )
    latest_indicators: LatestIndicators = Field(
        ..., description="Most recent indicator values"
    )
    meta: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
