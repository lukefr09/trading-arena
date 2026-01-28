"""Get dividend information."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..finnhub_client import FinnhubClient


def get_dividend(client: "FinnhubClient", symbol: str) -> dict:
    """Get dividend yield and basic financials for a symbol.

    Args:
        client: Finnhub client instance
        symbol: Stock symbol

    Returns:
        dict with dividend yield and related metrics
    """
    financials = client.get_basic_financials(symbol)

    if not financials or not financials.get("metric"):
        return {"error": f"No financial data found for symbol: {symbol}"}

    metric = financials.get("metric", {})

    return {
        "symbol": symbol.upper(),
        "dividend_yield_indicated_annual": metric.get("dividendYieldIndicatedAnnual"),
        "dividend_per_share_annual": metric.get("dividendPerShareAnnual"),
        "dividend_growth_rate_5y": metric.get("dividendGrowthRate5Y"),
        "payout_ratio": metric.get("payoutRatioAnnual"),
        "pe_ratio": metric.get("peBasicExclExtraTTM"),
        "market_cap": metric.get("marketCapitalization"),
        "52_week_high": metric.get("52WeekHigh"),
        "52_week_low": metric.get("52WeekLow"),
        "beta": metric.get("beta"),
    }
