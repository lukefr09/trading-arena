"""Get current prices for multiple symbols."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..finnhub_client import FinnhubClient


def get_prices(client: "FinnhubClient", symbols: list[str]) -> dict:
    """Get real-time price quotes for multiple symbols.

    Args:
        client: Finnhub client instance
        symbols: List of stock/ETF symbols

    Returns:
        dict mapping symbols to their price data
    """
    results = {}
    for symbol in symbols:
        try:
            quote = client.get_quote(symbol)
            if quote.get("c") == 0 and quote.get("pc") == 0:
                results[symbol.upper()] = {"error": f"No data found for symbol: {symbol}"}
            else:
                results[symbol.upper()] = {
                    "current": quote["c"],
                    "open": quote["o"],
                    "high": quote["h"],
                    "low": quote["l"],
                    "previous_close": quote["pc"],
                    "change": round(quote["c"] - quote["pc"], 2),
                    "change_percent": round(
                        ((quote["c"] - quote["pc"]) / quote["pc"] * 100)
                        if quote["pc"]
                        else 0,
                        2,
                    ),
                }
        except Exception as e:
            results[symbol.upper()] = {"error": str(e)}

    return results
