"""Finnhub API client for market data."""

import os
from datetime import datetime, timedelta
from typing import Optional

import httpx


class FinnhubClient:
    """Client for Finnhub API."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY is required")
        self._client = httpx.Client(timeout=30.0)

    def _request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make a request to Finnhub API."""
        params = params or {}
        params["token"] = self.api_key
        response = self._client.get(f"{self.BASE_URL}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    def get_quote(self, symbol: str) -> dict:
        """Get real-time quote for a symbol.

        Returns:
            dict with keys: c (current), h (high), l (low), o (open),
                           pc (previous close), t (timestamp)
        """
        return self._request("quote", {"symbol": symbol.upper()})

    def get_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """Get quotes for multiple symbols."""
        results = {}
        for symbol in symbols:
            try:
                results[symbol.upper()] = self.get_quote(symbol)
            except Exception as e:
                results[symbol.upper()] = {"error": str(e)}
        return results

    def get_candles(
        self,
        symbol: str,
        resolution: str = "D",
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> dict:
        """Get historical candlestick data.

        Args:
            symbol: Stock symbol
            resolution: 1, 5, 15, 30, 60, D, W, M
            from_ts: Unix timestamp for start
            to_ts: Unix timestamp for end

        Returns:
            dict with keys: c (close), h (high), l (low), o (open),
                           t (timestamps), v (volume), s (status)
        """
        if to_ts is None:
            to_ts = int(datetime.now().timestamp())
        if from_ts is None:
            from_ts = int((datetime.now() - timedelta(days=30)).timestamp())

        return self._request(
            "stock/candle",
            {
                "symbol": symbol.upper(),
                "resolution": resolution,
                "from": from_ts,
                "to": to_ts,
            },
        )

    def get_technicals(
        self,
        symbol: str,
        resolution: str = "D",
        indicator: str = "rsi",
        timeperiod: int = 14,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> dict:
        """Get technical indicator data.

        Args:
            symbol: Stock symbol
            resolution: 1, 5, 15, 30, 60, D, W, M
            indicator: rsi, sma, ema, macd, etc.
            timeperiod: Number of periods
            from_ts: Unix timestamp for start
            to_ts: Unix timestamp for end
        """
        if to_ts is None:
            to_ts = int(datetime.now().timestamp())
        if from_ts is None:
            from_ts = int((datetime.now() - timedelta(days=90)).timestamp())

        return self._request(
            "indicator",
            {
                "symbol": symbol.upper(),
                "resolution": resolution,
                "indicator": indicator,
                "timeperiod": timeperiod,
                "from": from_ts,
                "to": to_ts,
            },
        )

    def search_news(
        self,
        query: Optional[str] = None,
        symbol: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[dict]:
        """Search for market news.

        Args:
            query: Search query (for general news)
            symbol: Stock symbol (for company news)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
        """
        if symbol:
            params = {"symbol": symbol.upper()}
            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date
            return self._request("company-news", params)
        else:
            return self._request("news", {"category": "general"})

    def get_basic_financials(self, symbol: str) -> dict:
        """Get basic financials including dividend yield."""
        return self._request(
            "stock/metric", {"symbol": symbol.upper(), "metric": "all"}
        )

    def symbol_search(self, query: str) -> list[dict]:
        """Search for symbols."""
        result = self._request("search", {"q": query})
        return result.get("result", [])

    def close(self):
        """Close the HTTP client."""
        self._client.close()
