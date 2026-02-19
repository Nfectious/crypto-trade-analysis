"""Exchange integration using ccxt library."""

from typing import Any

import ccxt

from app.core.logging import get_logger

logger = get_logger(__name__)


class ExchangeClient:
    """Wrapper for ccxt exchange interactions."""

    def __init__(self, exchange_name: str = "binance", market_type: str = "spot") -> None:
        """
        Initialize exchange client.

        Args:
            exchange_name: Name of the exchange (e.g., 'binance', 'coinbase')
            market_type: Market type ('spot', 'future', etc.)
        """
        self.exchange_name = exchange_name.lower()
        self.market_type = market_type
        self._exchange: ccxt.Exchange = self._create_exchange()

    def _create_exchange(self) -> ccxt.Exchange:
        """Create and configure the exchange instance."""
        if not hasattr(ccxt, self.exchange_name):
            raise ValueError(f"Exchange '{self.exchange_name}' not supported by ccxt")

        exchange_class = getattr(ccxt, self.exchange_name)
        exchange = exchange_class({"enableRateLimit": True})

        if self.market_type:
            exchange.options["defaultType"] = self.market_type

        logger.info(f"Initialized {self.exchange_name} exchange with {self.market_type} market")
        return exchange

    def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 250
    ) -> list[list[Any]]:
        """
        Fetch OHLCV data from the exchange.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1h', '1d')
            limit: Number of candles to fetch

        Returns:
            List of OHLCV candles [timestamp, open, high, low, close, volume]

        Raises:
            ccxt.NetworkError: Network-related issues
            ccxt.ExchangeError: Exchange-specific errors
        """
        logger.info(
            f"Fetching {limit} {timeframe} candles for {symbol} from {self.exchange_name}"
        )
        return self._exchange.fetch_ohlcv(  # type: ignore[no-any-return]
            symbol, timeframe=timeframe, limit=limit
        )

    def get_exchange_name(self) -> str:
        """Get the exchange name."""
        return self.exchange_name

    def get_metadata(self) -> dict[str, Any]:
        """Get exchange metadata including defaultType."""
        meta: dict[str, Any] = {}
        if hasattr(self._exchange, "options") and "defaultType" in self._exchange.options:
            meta["defaultType"] = self._exchange.options["defaultType"]
        return meta
