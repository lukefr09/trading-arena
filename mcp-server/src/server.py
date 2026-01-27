"""MCP Server for Finnhub market data and Trading Arena integration."""

import os
from typing import Optional

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .finnhub_client import FinnhubClient
from .trading_client import TradingClient

load_dotenv()

server = Server("trading-arena")
finnhub_client: Optional[FinnhubClient] = None
trading_client: Optional[TradingClient] = None

# Bot ID from environment (set by orchestrator)
BOT_ID = os.environ.get("BOT_ID", "")


def get_finnhub_client() -> FinnhubClient:
    """Get or create Finnhub client."""
    global finnhub_client
    if finnhub_client is None:
        finnhub_client = FinnhubClient()
    return finnhub_client


def get_trading_client() -> Optional[TradingClient]:
    """Get or create Trading client if BOT_ID is set."""
    global trading_client
    if trading_client is None and BOT_ID:
        try:
            trading_client = TradingClient(bot_id=BOT_ID)
        except ValueError:
            # Missing API credentials - trading tools won't be available
            pass
    return trading_client


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    # Import tool functions
    from .tools import (
        get_dividend,
        get_history,
        get_price,
        get_prices,
        get_technicals,
        search_news,
    )

    tools = [
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

    # Add trading tools if BOT_ID is configured
    if BOT_ID:
        tools.extend([
            Tool(
                name="get_constraints",
                description="Get your trading constraints and rules. Call this to understand what trades are allowed for your bot type.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="validate_order",
                description="Check if a trade is allowed before placing it with Alpaca. Returns whether the trade passes your bot's constraints.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "side": {
                            "type": "string",
                            "enum": ["BUY", "SELL"],
                            "description": "Trade direction",
                        },
                        "shares": {
                            "type": "integer",
                            "description": "Number of shares",
                            "minimum": 1,
                        },
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol",
                        },
                        "price": {
                            "type": "number",
                            "description": "Current price per share (for position size validation)",
                        },
                        "current_cash": {
                            "type": "number",
                            "description": "Your current cash balance from Alpaca",
                        },
                        "current_equity": {
                            "type": "number",
                            "description": "Your current total equity from Alpaca",
                        },
                        "positions": {
                            "type": "array",
                            "description": "Your current positions from Alpaca [{symbol, qty, market_value}, ...]",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "symbol": {"type": "string"},
                                    "qty": {"type": "number"},
                                    "market_value": {"type": "number"},
                                },
                            },
                        },
                    },
                    "required": ["side", "shares", "symbol"],
                },
            ),
            Tool(
                name="record_trade",
                description="Record a completed trade for the dashboard. Call this AFTER successfully placing an order with Alpaca.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol that was traded",
                        },
                        "side": {
                            "type": "string",
                            "enum": ["BUY", "SELL"],
                            "description": "Trade direction",
                        },
                        "shares": {
                            "type": "integer",
                            "description": "Number of shares traded",
                        },
                        "price": {
                            "type": "number",
                            "description": "Fill price from Alpaca",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Your reasoning for this trade",
                        },
                    },
                    "required": ["symbol", "side", "shares", "price"],
                },
            ),
            Tool(
                name="get_leaderboard",
                description="View the current competition standings to see how you rank against other traders.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
        ])

    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    import json

    from .tools import (
        get_dividend,
        get_history,
        get_price,
        get_prices,
        get_technicals,
        search_news,
    )

    try:
        # Market data tools (use Finnhub client)
        if name in ("get_price", "get_prices", "get_history", "get_technicals", "search_news", "get_dividend"):
            finnhub = get_finnhub_client()

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

        # Trading tools (use Trading client)
        elif name in ("get_constraints", "validate_order", "record_trade", "get_leaderboard"):
            trading = get_trading_client()
            if trading is None:
                result = {"error": "Trading not available - BOT_ID not configured"}

            elif name == "get_constraints":
                constraints = trading.get_bot_constraints()
                result = {
                    "bot_id": trading.bot_id,
                    "type": constraints.type,
                    "rules": constraints.rules,
                }

            elif name == "validate_order":
                # If price/cash/equity provided, use full validation
                if all(k in arguments for k in ("price", "current_cash", "current_equity")):
                    result = trading.validate_order_with_price(
                        side=arguments["side"],
                        shares=arguments["shares"],
                        symbol=arguments["symbol"],
                        price=arguments["price"],
                        current_cash=arguments["current_cash"],
                        current_equity=arguments["current_equity"],
                        positions=arguments.get("positions", []),
                    )
                else:
                    # Basic validation (symbol-only constraints)
                    result = trading.validate_order(
                        side=arguments["side"],
                        shares=arguments["shares"],
                        symbol=arguments["symbol"],
                        current_cash=arguments.get("current_cash", 0),
                        current_equity=arguments.get("current_equity", 0),
                        positions=arguments.get("positions", []),
                    )

            elif name == "record_trade":
                result = trading.record_trade(
                    symbol=arguments["symbol"],
                    side=arguments["side"],
                    shares=arguments["shares"],
                    price=arguments["price"],
                    reason=arguments.get("reason"),
                )

            elif name == "get_leaderboard":
                state = trading.get_leaderboard()
                result = {
                    "round": state.round,
                    "standings": [
                        {"rank": e.rank, "name": e.name, "return_pct": e.return_pct}
                        for e in state.standings
                    ],
                }

        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
