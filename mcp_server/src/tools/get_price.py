"""Get current price for a single symbol."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..finnhub_client import FinnhubClient


def get_price(client: "FinnhubClient", symbol: str) -> dict:
    """Get real-time price quote for a symbol.

    Args:
        client: Finnhub client instance
        symbol: Stock/ETF symbol (e.g., AAPL, SPY)

    Returns:
        dict with current price, open, high, low, previous close
    """
    quote = client.get_quote(symbol)

    if quote.get("c") == 0 and quote.get("pc") == 0:
        return {"error": f"No data found for symbol: {symbol}"}

    return {
        "symbol": symbol.upper(),
        "current": quote["c"],
        "open": quote["o"],
        "high": quote["h"],
        "low": quote["l"],
        "previous_close": quote["pc"],
        "change": round(quote["c"] - quote["pc"], 2),
        "change_percent": round(
            ((quote["c"] - quote["pc"]) / quote["pc"] * 100) if quote["pc"] else 0, 2
        ),
    }
