"""MCP Server for Finnhub market data."""

import os
from typing import Optional

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .finnhub_client import FinnhubClient
from .tools import (
    get_dividend,
    get_history,
    get_price,
    get_prices,
    get_technicals,
    search_news,
)

load_dotenv()

server = Server("finnhub-market-data")
client: Optional[FinnhubClient] = None


def get_client() -> FinnhubClient:
    """Get or create Finnhub client."""
    global client
    if client is None:
        client = FinnhubClient()
    return client


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_price",
            description="Get real-time price quote for a single stock or ETF symbol. Returns current price, open, high, low, previous close, and change percentage.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock or ETF symbol (e.g., AAPL, SPY, NVDA)",
                    }
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_prices",
            description="Get real-time price quotes for multiple symbols at once. Efficient for checking your portfolio or comparing stocks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of stock/ETF symbols",
                    }
                },
                "required": ["symbols"],
            },
        ),
        Tool(
            name="get_history",
            description="Get historical OHLCV candlestick data for a symbol. Useful for analyzing price trends and patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock or ETF symbol",
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Timeframe: 1, 5, 15, 30, 60 (minutes), D (day), W (week), M (month)",
                        "default": "D",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days of history",
                        "default": 30,
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD), overrides days",
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_technicals",
            description="Get technical indicator data (RSI, SMA, EMA, MACD, Bollinger Bands, etc.) for a symbol. Essential for quantitative analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock or ETF symbol",
                    },
                    "indicator": {
                        "type": "string",
                        "description": "Technical indicator: rsi, sma, ema, macd, bbands",
                        "default": "rsi",
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Timeframe: D (day), W (week), M (month)",
                        "default": "D",
                    },
                    "timeperiod": {
                        "type": "integer",
                        "description": "Number of periods for the indicator",
                        "default": 14,
                    },
                    "days": {
                        "type": "integer",
                        "description": "Days of history to analyze",
                        "default": 90,
                    },
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="search_news",
            description="Search for market news. Can get general market news or company-specific news for a symbol.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol for company-specific news (optional)",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Days to look back",
                        "default": 7,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum articles to return",
                        "default": 10,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_dividend",
            description="Get dividend yield and basic financial metrics for a stock. Includes P/E ratio, market cap, 52-week range, and beta.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol",
                    }
                },
                "required": ["symbol"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    finnhub = get_client()

    try:
        if name == "get_price":
            result = get_price(finnhub, arguments["symbol"])
        elif name == "get_prices":
            result = get_prices(finnhub, arguments["symbols"])
        elif name == "get_history":
            result = get_history(
                finnhub,
                arguments["symbol"],
                arguments.get("resolution", "D"),
                arguments.get("days", 30),
                arguments.get("from_date"),
                arguments.get("to_date"),
            )
        elif name == "get_technicals":
            result = get_technicals(
                finnhub,
                arguments["symbol"],
                arguments.get("indicator", "rsi"),
                arguments.get("resolution", "D"),
                arguments.get("timeperiod", 14),
                arguments.get("days", 90),
            )
        elif name == "search_news":
            result = search_news(
                finnhub,
                arguments.get("symbol"),
                arguments.get("days", 7),
                arguments.get("limit", 10),
            )
        elif name == "get_dividend":
            result = get_dividend(finnhub, arguments["symbol"])
        else:
            result = {"error": f"Unknown tool: {name}"}

        import json
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        import json
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
