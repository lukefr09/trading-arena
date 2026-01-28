"""Search market news."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..finnhub_client import FinnhubClient


def search_news(
    client: "FinnhubClient",
    symbol: Optional[str] = None,
    days: int = 7,
    limit: int = 10,
) -> dict:
    """Search for market news.

    Args:
        client: Finnhub client instance
        symbol: Stock symbol for company-specific news (optional)
        days: Number of days to look back (default 7)
        limit: Maximum number of articles to return (default 10)

    Returns:
        dict with list of news articles
    """
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")

    articles = client.search_news(
        symbol=symbol,
        from_date=from_date if symbol else None,
        to_date=to_date if symbol else None,
    )

    # Limit and format results
    formatted = []
    for article in articles[:limit]:
        formatted.append({
            "headline": article.get("headline", ""),
            "summary": article.get("summary", "")[:500] if article.get("summary") else "",
            "source": article.get("source", ""),
            "url": article.get("url", ""),
            "datetime": datetime.fromtimestamp(article.get("datetime", 0)).strftime(
                "%Y-%m-%d %H:%M"
            ) if article.get("datetime") else "",
            "related": article.get("related", ""),
        })

    return {
        "symbol": symbol.upper() if symbol else "GENERAL",
        "articles": formatted,
        "count": len(formatted),
    }
