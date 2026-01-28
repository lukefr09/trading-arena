"""MCP Server for Finnhub market data and Trading Arena integration."""

import os
from typing import Optional

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .alpaca_client import AlpacaClient
from .finnhub_client import FinnhubClient
from .trading_client import TradingClient

load_dotenv()

server = Server("trading-arena")
finnhub_client: Optional[FinnhubClient] = None
trading_client: Optional[TradingClient] = None
alpaca_client: Optional[AlpacaClient] = None

# Bot ID from environment (set by orchestrator)
BOT_ID = os.environ.get("BOT_ID", "")
# Alpaca credentials from environment (set by orchestrator)
ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")


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


def get_alpaca_client() -> Optional[AlpacaClient]:
    """Get or create Alpaca client if credentials are set."""
    global alpaca_client
    if alpaca_client is None and ALPACA_API_KEY and ALPACA_SECRET_KEY:
        try:
            alpaca_client = AlpacaClient(
                api_key=ALPACA_API_KEY,
                secret_key=ALPACA_SECRET_KEY,
            )
        except ValueError:
            pass
    return alpaca_client


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
                name="get_portfolio",
                description="Get your current portfolio from Alpaca - cash, equity, buying power, and all positions with P&L.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="place_order",
                description="Place a trade order. Validates against your constraints FIRST, then executes on Alpaca if allowed, then records for dashboard. Returns success/rejection.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol to trade",
                        },
                        "qty": {
                            "type": "number",
                            "description": "Number of shares",
                        },
                        "side": {
                            "type": "string",
                            "enum": ["buy", "sell"],
                            "description": "Trade direction",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Your reasoning for this trade. REQUIRED for Quant (must cite technical indicator).",
                        },
                    },
                    "required": ["symbol", "qty", "side"],
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
            # Social tools
            Tool(
                name="send_message",
                description="Send a public message to all bots (trash talk, commentary) or a private DM to a specific bot. Use this to react to trades, taunt rivals, or coordinate.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Your message content. Be in character!",
                        },
                        "to": {
                            "type": "string",
                            "description": "Bot ID for private DM (turtle, degen, boomer, quant, doomer, gary, diana, mel, vince, rei). Omit for public message.",
                        },
                    },
                    "required": ["content"],
                },
            ),
            Tool(
                name="get_messages",
                description="Get recent chat messages (public + DMs to you). See what other bots are saying.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max messages to return",
                            "default": 30,
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="get_all_portfolios",
                description="See EVERYONE's portfolios - cash, positions, and P&L. Know your competition.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="get_round_context",
                description="Get the FULL picture: leaderboard, all recent trades with commentary, rejected trades, chat messages, and DMs to you. Call this at the start of each round!",
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

        # Trading tools (use Trading client + Alpaca client)
        elif name in ("get_constraints", "get_portfolio", "place_order", "get_leaderboard",
                      "send_message", "get_messages", "get_all_portfolios", "get_round_context"):
            trading = get_trading_client()
            alpaca = get_alpaca_client()

            if trading is None:
                result = {"error": "Trading not available - BOT_ID not configured"}

            elif name == "get_constraints":
                constraints = trading.get_bot_constraints()
                result = {
                    "bot_id": trading.bot_id,
                    "type": constraints.type,
                    "rules": constraints.rules,
                }

            elif name == "get_portfolio":
                if alpaca is None:
                    result = {"error": "Alpaca not configured - missing API credentials"}
                else:
                    portfolio = alpaca.get_portfolio()
                    result = {
                        "cash": portfolio.cash,
                        "equity": portfolio.equity,
                        "buying_power": portfolio.buying_power,
                        "positions": [
                            {
                                "symbol": p.symbol,
                                "qty": p.qty,
                                "market_value": p.market_value,
                                "avg_entry_price": p.avg_entry_price,
                                "current_price": p.current_price,
                                "unrealized_pl": p.unrealized_pl,
                                "unrealized_plpc": round(p.unrealized_plpc * 100, 2),
                            }
                            for p in portfolio.positions
                        ],
                    }

            elif name == "place_order":
                if alpaca is None:
                    result = {"error": "Alpaca not configured - missing API credentials"}
                else:
                    symbol = arguments["symbol"].upper()
                    qty = float(arguments["qty"])
                    side = arguments["side"].upper()
                    reason = arguments.get("reason")

                    # 1. Get current portfolio
                    portfolio = alpaca.get_portfolio()
                    positions = [
                        {
                            "symbol": p.symbol,
                            "qty": p.qty,
                            "market_value": p.market_value,
                        }
                        for p in portfolio.positions
                    ]

                    # 2. Get current price
                    finnhub = get_finnhub_client()
                    quote = finnhub.get_quote(symbol)
                    price = quote.get("c", 0)  # Current price

                    if price <= 0:
                        result = {"status": "rejected", "reason": f"Could not get price for {symbol}"}
                    else:
                        # 3. Get dividend yield if needed (for Boomer)
                        dividend_yield = None
                        if trading.bot_id == "boomer" and side == "BUY":
                            try:
                                financials = finnhub.get_basic_financials(symbol)
                                metrics = financials.get("metric", {})
                                # Dividend yield is returned as percentage
                                div_yield_annual = metrics.get("dividendYieldIndicatedAnnual", 0)
                                dividend_yield = div_yield_annual / 100 if div_yield_annual else 0
                            except Exception:
                                dividend_yield = 0

                        # 4. Validate constraints
                        validation = trading.validate_order_full(
                            side=side,
                            shares=int(qty),
                            symbol=symbol,
                            price=price,
                            current_cash=portfolio.cash,
                            current_equity=portfolio.equity,
                            positions=positions,
                            technical_reason=reason,
                            dividend_yield=dividend_yield,
                        )

                        if not validation.allowed:
                            # Record rejected trade for entertainment
                            trading.record_rejected_trade(
                                symbol=symbol,
                                side=side,
                                shares=int(qty),
                                reason=validation.reason or "Unknown",
                            )
                            result = {
                                "status": "rejected",
                                "reason": validation.reason,
                            }
                        else:
                            # 5. Execute on Alpaca
                            order_result = alpaca.place_order(
                                symbol=symbol,
                                qty=qty,
                                side=side.lower(),
                                order_type="market",
                                time_in_force="day",
                            )

                            if not order_result.success:
                                result = {
                                    "status": "rejected",
                                    "reason": order_result.error,
                                }
                            else:
                                # 6. Record trade for dashboard
                                fill_price = order_result.filled_avg_price or price
                                trading.record_trade(
                                    symbol=symbol,
                                    side=side,
                                    shares=int(qty),
                                    price=fill_price,
                                    reason=reason,
                                )

                                result = {
                                    "status": "filled",
                                    "symbol": symbol,
                                    "qty": qty,
                                    "side": side.lower(),
                                    "price": fill_price,
                                    "order_id": order_result.order_id,
                                }

            elif name == "get_leaderboard":
                state = trading.get_leaderboard()
                result = {
                    "round": state.round,
                    "standings": [
                        {"rank": e.rank, "name": e.name, "return_pct": e.return_pct}
                        for e in state.standings
                    ],
                }

            # Social tools
            elif name == "send_message":
                result = trading.send_message(
                    content=arguments["content"],
                    to_bot=arguments.get("to"),
                )

            elif name == "get_messages":
                messages = trading.get_messages(
                    limit=arguments.get("limit", 30),
                )
                result = {"messages": messages}

            elif name == "get_all_portfolios":
                result = trading.get_all_portfolios()

            elif name == "get_round_context":
                result = trading.get_round_context()

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
