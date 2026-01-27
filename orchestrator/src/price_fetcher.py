"""Fetch current prices from Finnhub API."""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class PriceFetcher:
    """Fetches current market prices from Finnhub API."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY is required")
        self._client = httpx.Client(timeout=30.0)

    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a single symbol.

        Args:
            symbol: Stock/ETF symbol

        Returns:
            Current price or None if unavailable
        """
        try:
            response = self._client.get(
                f"{self.BASE_URL}/quote",
                params={"symbol": symbol.upper(), "token": self.api_key},
            )
            response.raise_for_status()
            data = response.json()

            price = data.get("c")  # Current price
            if price and price > 0:
                return float(price)
            return None

        except Exception as e:
            logger.warning(f"Failed to get price for {symbol}: {e}")
            return None

    def get_prices(self, symbols: list[str]) -> dict[str, float]:
        """Get current prices for multiple symbols.

        Args:
            symbols: List of stock/ETF symbols

        Returns:
            Dict mapping symbols to prices (only includes successful lookups)
        """
        prices = {}
        for symbol in symbols:
            price = self.get_price(symbol)
            if price is not None:
                prices[symbol.upper()] = price
        return prices

    def get_all_bot_symbols(self, bots: list) -> set[str]:
        """Get all unique symbols held by bots.

        Args:
            bots: List of Bot objects

        Returns:
            Set of unique symbols
        """
        symbols = set()
        for bot in bots:
            for position in bot.positions:
                symbols.add(position.symbol)
        return symbols

    def update_all_prices(self, bots: list) -> dict[str, float]:
        """Fetch prices for all symbols held by bots.

        Args:
            bots: List of Bot objects

        Returns:
            Dict mapping symbols to prices
        """
        symbols = self.get_all_bot_symbols(bots)
        if not symbols:
            return {}
        return self.get_prices(list(symbols))

    def close(self):
        """Close HTTP client."""
        self._client.close()
