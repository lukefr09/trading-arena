"""Get technical indicators."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..finnhub_client import FinnhubClient


def get_technicals(
    client: "FinnhubClient",
    symbol: str,
    indicator: str = "rsi",
    resolution: str = "D",
    timeperiod: int = 14,
    days: int = 90,
) -> dict:
    """Get technical indicator data for a symbol.

    Args:
        client: Finnhub client instance
        symbol: Stock/ETF symbol
        indicator: Technical indicator (rsi, sma, ema, macd, bbands, etc.)
        resolution: Timeframe - D (day), W (week), M (month)
        timeperiod: Number of periods for the indicator
        days: Days of history to analyze

    Returns:
        dict with indicator values and timestamps
    """
    to_ts = int(datetime.now().timestamp())
    from_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    result = client.get_technicals(
        symbol, resolution, indicator, timeperiod, from_ts, to_ts
    )

    if not result or result.get("s") == "no_data":
        return {"error": f"No technical data found for {symbol} with {indicator}"}

    # Parse timestamps and values
    timestamps = result.get("t", [])

    # Different indicators return different structures
    data_points = []

    if indicator.lower() in ["rsi", "sma", "ema"]:
        values = result.get(indicator.lower(), [])
        for i in range(len(timestamps)):
            if i < len(values):
                data_points.append({
                    "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                    "value": round(values[i], 2) if values[i] else None,
                })
    elif indicator.lower() == "macd":
        macd_vals = result.get("macd", [])
        signal_vals = result.get("macdSignal", [])
        hist_vals = result.get("macdHist", [])
        for i in range(len(timestamps)):
            data_points.append({
                "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                "macd": round(macd_vals[i], 2) if i < len(macd_vals) and macd_vals[i] else None,
                "signal": round(signal_vals[i], 2) if i < len(signal_vals) and signal_vals[i] else None,
                "histogram": round(hist_vals[i], 2) if i < len(hist_vals) and hist_vals[i] else None,
            })
    elif indicator.lower() == "bbands":
        upper = result.get("upperBand", [])
        middle = result.get("middleBand", [])
        lower = result.get("lowerBand", [])
        for i in range(len(timestamps)):
            data_points.append({
                "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                "upper": round(upper[i], 2) if i < len(upper) and upper[i] else None,
                "middle": round(middle[i], 2) if i < len(middle) and middle[i] else None,
                "lower": round(lower[i], 2) if i < len(lower) and lower[i] else None,
            })
    else:
        # Generic handling for other indicators
        for key in result:
            if key not in ["s", "t"] and isinstance(result[key], list):
                values = result[key]
                for i in range(len(timestamps)):
                    if len(data_points) <= i:
                        data_points.append({
                            "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                        })
                    if i < len(values):
                        data_points[i][key] = round(values[i], 2) if values[i] else None

    # Get latest value summary
    latest = data_points[-1] if data_points else None

    return {
        "symbol": symbol.upper(),
        "indicator": indicator.upper(),
        "timeperiod": timeperiod,
        "resolution": resolution,
        "latest": latest,
        "data": data_points[-30:],  # Return last 30 data points
    }
