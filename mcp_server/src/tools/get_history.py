"""Get historical price data."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..finnhub_client import FinnhubClient


def get_history(
    client: "FinnhubClient",
    symbol: str,
    resolution: str = "D",
    days: int = 30,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> dict:
    """Get historical candlestick data for a symbol.

    Args:
        client: Finnhub client instance
        symbol: Stock/ETF symbol
        resolution: Timeframe - 1, 5, 15, 30, 60 (minutes), D (day), W (week), M (month)
        days: Number of days of history (default 30, ignored if from_date set)
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)

    Returns:
        dict with timestamps and OHLCV data
    """
    if to_date:
        to_ts = int(datetime.strptime(to_date, "%Y-%m-%d").timestamp())
    else:
        to_ts = int(datetime.now().timestamp())

    if from_date:
        from_ts = int(datetime.strptime(from_date, "%Y-%m-%d").timestamp())
    else:
        from_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    candles = client.get_candles(symbol, resolution, from_ts, to_ts)

    if candles.get("s") == "no_data":
        return {"error": f"No historical data found for symbol: {symbol}"}

    data_points = []
    timestamps = candles.get("t", [])
    opens = candles.get("o", [])
    highs = candles.get("h", [])
    lows = candles.get("l", [])
    closes = candles.get("c", [])
    volumes = candles.get("v", [])

    for i in range(len(timestamps)):
        data_points.append(
            {
                "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                "open": opens[i],
                "high": highs[i],
                "low": lows[i],
                "close": closes[i],
                "volume": volumes[i],
            }
        )

    return {
        "symbol": symbol.upper(),
        "resolution": resolution,
        "data": data_points,
    }
