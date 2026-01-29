"""HTTP client for Trading Arena API - constraint validation and trade recording."""

import os
from dataclasses import dataclass, field
from typing import Callable, Optional

import httpx


@dataclass
class BotConstraints:
    """Trading constraints for a bot."""

    type: str  # 'baseline' or 'free_agent'
    rules: list[str]
    max_position_pct: Optional[float] = None
    min_cash_pct: Optional[float] = None
    max_cash_pct: Optional[float] = None
    sp500_only: bool = False
    max_long_equity_pct: Optional[float] = None
    requires_hedges: bool = False
    no_crypto: bool = False
    no_leverage: bool = False
    min_dividend_yield: Optional[float] = None
    requires_technical_citation: bool = False
    options_allowed: bool = True  # All bots can trade options


@dataclass
class ValidationResult:
    """Result of constraint validation."""

    allowed: bool
    reason: Optional[str] = None


@dataclass
class LeaderboardEntry:
    """Entry in the leaderboard."""

    rank: int
    name: str
    return_pct: float


@dataclass
class LeaderboardState:
    """Current leaderboard state."""

    round: int
    standings: list[LeaderboardEntry]


# S&P 500 symbols (subset for Turtle validation)
SP500_SYMBOLS = {
    'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'GOOG', 'META', 'TSLA', 'BRK.B',
    'UNH', 'XOM', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV',
    'LLY', 'PEP', 'KO', 'COST', 'AVGO', 'WMT', 'MCD', 'CSCO', 'TMO', 'ACN',
    'ABT', 'DHR', 'NEE', 'DIS', 'VZ', 'ADBE', 'WFC', 'PM', 'CMCSA', 'CRM',
    'NKE', 'TXN', 'RTX', 'BMY', 'UPS', 'QCOM', 'HON', 'ORCL', 'T', 'COP',
    'AMGN', 'INTC', 'IBM', 'CAT', 'SPGI', 'PLD', 'LOW', 'BA', 'GS', 'INTU',
    'SBUX', 'MDLZ', 'AMD', 'BLK', 'DE', 'AXP', 'ELV', 'GILD', 'LMT', 'ISRG',
    'ADI', 'CVS', 'BKNG', 'TJX', 'VRTX', 'REGN', 'SYK', 'TMUS', 'MMC', 'PGR',
    'ADP', 'ZTS', 'CI', 'LRCX', 'SCHW', 'NOW', 'MO', 'EOG', 'BDX', 'C',
    'PYPL', 'SO', 'ETN', 'DUK', 'SLB', 'CB', 'ITW', 'NOC', 'BSX', 'EQIX',
    'CME', 'APD', 'MU', 'SNPS', 'ATVI', 'ICE', 'AON', 'HUM', 'FCX', 'CSX',
    'CL', 'WM', 'GD', 'MCK', 'USB', 'EMR', 'PXD', 'KLAC', 'NSC', 'ORLY',
    'SHW', 'MAR', 'MCO', 'PNC', 'CDNS', 'NXPI', 'F', 'GM', 'ROP', 'HCA',
    'AZO', 'FDX', 'PSA', 'TRV', 'D', 'AEP', 'TFC', 'KMB', 'MRNA', 'OXY',
    # Major ETFs allowed for Turtle
    'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'BND', 'AGG', 'TLT',
}

# Hedge symbols for Doomer (inverse ETFs, volatility, precious metals, bonds)
HEDGE_SYMBOLS = {
    'SQQQ', 'UVXY', 'SH', 'SPXS', 'VXX', 'SDOW', 'SPXU', 'QID', 'SDS', 'TZA',
    'GLD', 'SLV', 'TLT', 'BND', 'IEF',  # Precious metals and bonds
}

# Leveraged/meme stocks
LEVERAGED_SYMBOLS = {
    'TQQQ', 'SOXL', 'UPRO', 'SPXL', 'TECL', 'FAS', 'LABU', 'FNGU', 'WEBL',
    'SQQQ', 'SOXS', 'SPXS', 'SPXU', 'UVXY', 'SVXY',
}

# Crypto-related stocks
CRYPTO_STOCKS = {'COIN', 'MARA', 'RIOT', 'BITO', 'MSTR', 'GBTC'}

# Technical indicators that Quant must cite
TECHNICAL_INDICATORS = [
    "rsi", "macd", "sma", "ema", "bollinger", "stochastic",
    "momentum", "roc", "atr", "adx", "obv", "vwap",
    "moving average", "relative strength", "support", "resistance",
    "oversold", "overbought", "crossover", "divergence",
    "50-day", "200-day", "golden cross", "death cross",
]

# Constraint definitions for each bot type
CONSTRAINT_DEFINITIONS: dict[str, BotConstraints] = {
    "turtle": BotConstraints(
        type="baseline",
        rules=[
            "Max 5% of portfolio per position",
            "Min 30% cash at all times",
            "S&P 500 stocks and major ETFs only",
        ],
        max_position_pct=0.05,
        min_cash_pct=0.30,
        sp500_only=True,
    ),
    "degen": BotConstraints(
        type="baseline",
        rules=[
            "Max 20% cash (must stay invested)",
            "Leveraged ETFs and meme stocks encouraged",
        ],
        max_cash_pct=0.20,
    ),
    "boomer": BotConstraints(
        type="baseline",
        rules=[
            "Only dividend-paying stocks with 1%+ yield",
            "No crypto-related stocks (COIN, MARA, RIOT, etc.)",
            "No leveraged ETFs",
        ],
        no_crypto=True,
        no_leverage=True,
        min_dividend_yield=0.01,  # 1%
    ),
    "quant": BotConstraints(
        type="baseline",
        rules=[
            "Must cite technical indicator for every trade",
            "RSI, MACD, MA, Bollinger Bands, etc.",
        ],
        requires_technical_citation=True,
    ),
    "doomer": BotConstraints(
        type="baseline",
        rules=[
            "Max 30% in long equity positions",
            "Must maintain hedge positions (SQQQ, UVXY, SH, GLD, etc.)",
        ],
        max_long_equity_pct=0.30,
        requires_hedges=True,
    ),
}


class TradingClient:
    """HTTP client for Workers API - constraint validation and trade recording."""

    def __init__(
        self,
        bot_id: str,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize the trading client.

        Args:
            bot_id: The bot making API calls
            api_url: Base URL for the API (defaults to CF_API_URL env var)
            api_key: API key for authentication (defaults to CF_API_KEY env var)
        """
        self.bot_id = bot_id
        self.api_url = api_url or os.environ.get("CF_API_URL", "")
        self.api_key = api_key or os.environ.get("CF_API_KEY", "")

        if not self.api_url:
            raise ValueError("CF_API_URL environment variable is required")
        if not self.api_key:
            raise ValueError("CF_API_KEY environment variable is required")

        self._client = httpx.Client(
            base_url=self.api_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def close(self) -> None:
        """Close HTTP client."""
        self._client.close()

    def get_bot_constraints(self) -> BotConstraints:
        """Get constraint definition for this bot.

        Returns:
            BotConstraints for the bot type
        """
        return CONSTRAINT_DEFINITIONS.get(
            self.bot_id,
            BotConstraints(
                type="free_agent",
                rules=["No trading constraints"],
            ),
        )

    def validate_order(
        self,
        side: str,
        shares: int,
        symbol: str,
        current_cash: float,
        current_equity: float,
        positions: list[dict],
    ) -> dict:
        """Validate a trade against bot constraints.

        Args:
            side: "BUY" or "SELL"
            shares: Number of shares
            symbol: Stock symbol
            current_cash: Current cash from Alpaca account
            current_equity: Current equity from Alpaca account
            positions: Current positions from Alpaca (list of {symbol, qty, market_value})

        Returns:
            {"allowed": True} or {"allowed": False, "reason": "..."}
        """
        constraints = self.get_bot_constraints()
        symbol = symbol.upper()
        side = side.upper()

        # Free agents have no constraints
        if constraints.type == "free_agent":
            return {"allowed": True}

        # Turtle constraints
        if self.bot_id == "turtle":
            # S&P 500 only
            if constraints.sp500_only and symbol not in SP500_SYMBOLS:
                return {
                    "allowed": False,
                    "reason": f"{symbol} not in S&P 500 universe. Turtle can only trade S&P 500 stocks and major ETFs.",
                }

            if side == "BUY":
                # We need price to calculate trade value - caller should provide estimated price
                # For now, we'll do symbol-only validation and trust Alpaca for the rest
                pass

        # Boomer constraints
        if self.bot_id == "boomer" and side == "BUY":
            if constraints.no_crypto and symbol in CRYPTO_STOCKS:
                return {
                    "allowed": False,
                    "reason": f"{symbol} is crypto-related. Boomer doesn't trust crypto.",
                }
            if constraints.no_leverage and symbol in LEVERAGED_SYMBOLS:
                return {
                    "allowed": False,
                    "reason": f"{symbol} is a leveraged ETF. Boomer considers that gambling, not investing.",
                }

        # Doomer constraints - selling last hedge
        if self.bot_id == "doomer" and side == "SELL":
            is_hedge = symbol in HEDGE_SYMBOLS
            if is_hedge and constraints.requires_hedges:
                hedge_positions = [p for p in positions if p.get("symbol") in HEDGE_SYMBOLS]
                current_pos = next((p for p in hedge_positions if p.get("symbol") == symbol), None)

                if current_pos:
                    current_qty = current_pos.get("qty", 0)
                    remaining = current_qty - shares
                    other_hedges = [p for p in hedge_positions if p.get("symbol") != symbol]

                    if remaining <= 0 and len(other_hedges) == 0:
                        return {
                            "allowed": False,
                            "reason": "Cannot sell last hedge position. Doomer must maintain at least one hedge (SQQQ, UVXY, SH, etc.).",
                        }

        return {"allowed": True}

    def validate_order_with_price(
        self,
        side: str,
        shares: int,
        symbol: str,
        price: float,
        current_cash: float,
        current_equity: float,
        positions: list[dict],
    ) -> dict:
        """Validate a trade with price for value-based constraints.

        Args:
            side: "BUY" or "SELL"
            shares: Number of shares
            symbol: Stock symbol
            price: Current/estimated price per share
            current_cash: Current cash from Alpaca account
            current_equity: Current equity from Alpaca account
            positions: Current positions from Alpaca (list of {symbol, qty, market_value})

        Returns:
            {"allowed": True} or {"allowed": False, "reason": "..."}
        """
        # First do basic validation
        basic_result = self.validate_order(
            side, shares, symbol, current_cash, current_equity, positions
        )
        if not basic_result.get("allowed"):
            return basic_result

        constraints = self.get_bot_constraints()
        symbol = symbol.upper()
        side = side.upper()
        trade_value = shares * price

        # Turtle position size and cash constraints
        if self.bot_id == "turtle" and side == "BUY":
            # Max position size
            if constraints.max_position_pct:
                existing_pos = next((p for p in positions if p.get("symbol") == symbol), None)
                existing_value = existing_pos.get("market_value", 0) if existing_pos else 0
                new_position_value = existing_value + trade_value
                position_pct = new_position_value / current_equity if current_equity > 0 else 1

                if position_pct > constraints.max_position_pct:
                    return {
                        "allowed": False,
                        "reason": f"Position would be {position_pct * 100:.1f}% of portfolio, exceeding {constraints.max_position_pct * 100:.0f}% max. Turtle must stay diversified.",
                    }

            # Min cash
            if constraints.min_cash_pct:
                cash_after = current_cash - trade_value
                cash_pct = cash_after / current_equity if current_equity > 0 else 0

                if cash_pct < constraints.min_cash_pct:
                    return {
                        "allowed": False,
                        "reason": f"Cash after trade would be {cash_pct * 100:.1f}%, below {constraints.min_cash_pct * 100:.0f}% minimum. Turtle needs that safety buffer.",
                    }

        # Degen max cash constraint
        if self.bot_id == "degen" and side == "SELL":
            if constraints.max_cash_pct:
                cash_after = current_cash + trade_value
                cash_pct = cash_after / current_equity if current_equity > 0 else 1

                if cash_pct > constraints.max_cash_pct:
                    return {
                        "allowed": False,
                        "reason": f"Cash after sale would be {cash_pct * 100:.1f}%, exceeding {constraints.max_cash_pct * 100:.0f}% max. Degen must stay invested!",
                    }

        # Doomer long equity constraint
        if self.bot_id == "doomer" and side == "BUY":
            is_hedge = symbol in HEDGE_SYMBOLS

            if not is_hedge and constraints.max_long_equity_pct:
                # Calculate current long equity (non-hedge positions)
                long_equity = sum(
                    p.get("market_value", 0) for p in positions
                    if p.get("symbol") not in HEDGE_SYMBOLS
                )
                new_long_equity = long_equity + trade_value
                long_pct = new_long_equity / current_equity if current_equity > 0 else 1

                if long_pct > constraints.max_long_equity_pct:
                    return {
                        "allowed": False,
                        "reason": f"Long equity would be {long_pct * 100:.1f}%, exceeding {constraints.max_long_equity_pct * 100:.0f}% max. Doomer must stay defensive.",
                    }

        return {"allowed": True}

    def validate_order_full(
        self,
        side: str,
        shares: int,
        symbol: str,
        price: float,
        current_cash: float,
        current_equity: float,
        positions: list[dict],
        technical_reason: Optional[str] = None,
        dividend_yield: Optional[float] = None,
    ) -> ValidationResult:
        """Full constraint validation with all checks.

        Args:
            side: "BUY" or "SELL"
            shares: Number of shares
            symbol: Stock symbol
            price: Current/estimated price per share
            current_cash: Current cash from Alpaca account
            current_equity: Current equity from Alpaca account
            positions: Current positions from Alpaca (list of {symbol, qty, market_value})
            technical_reason: Technical justification (required for Quant)
            dividend_yield: Dividend yield as decimal (required for Boomer buys)

        Returns:
            ValidationResult with allowed flag and optional reason
        """
        constraints = self.get_bot_constraints()
        symbol = symbol.upper()
        side = side.upper()
        trade_value = shares * price

        # Free agents have no constraints
        if constraints.type == "free_agent":
            return ValidationResult(allowed=True)

        # --- TURTLE CONSTRAINTS ---
        if self.bot_id == "turtle":
            # S&P 500 only
            if constraints.sp500_only and symbol not in SP500_SYMBOLS:
                return ValidationResult(
                    allowed=False,
                    reason=f"{symbol} not in S&P 500 universe. Turtle can only trade S&P 500 stocks and major ETFs.",
                )

            if side == "BUY":
                # Max position size (5%)
                if constraints.max_position_pct:
                    existing_pos = next((p for p in positions if p.get("symbol") == symbol), None)
                    existing_value = existing_pos.get("market_value", 0) if existing_pos else 0
                    new_position_value = existing_value + trade_value
                    position_pct = new_position_value / current_equity if current_equity > 0 else 1

                    if position_pct > constraints.max_position_pct:
                        return ValidationResult(
                            allowed=False,
                            reason=f"Position would be {position_pct * 100:.1f}% of portfolio, exceeding {constraints.max_position_pct * 100:.0f}% max.",
                        )

                # Min cash (30%)
                if constraints.min_cash_pct:
                    cash_after = current_cash - trade_value
                    cash_pct = cash_after / current_equity if current_equity > 0 else 0

                    if cash_pct < constraints.min_cash_pct:
                        return ValidationResult(
                            allowed=False,
                            reason=f"Cash after trade would be {cash_pct * 100:.1f}%, below {constraints.min_cash_pct * 100:.0f}% minimum.",
                        )

        # --- DEGEN CONSTRAINTS ---
        if self.bot_id == "degen" and side == "SELL":
            if constraints.max_cash_pct:
                cash_after = current_cash + trade_value
                cash_pct = cash_after / current_equity if current_equity > 0 else 1

                if cash_pct > constraints.max_cash_pct:
                    return ValidationResult(
                        allowed=False,
                        reason=f"Cash after sale would be {cash_pct * 100:.1f}%, exceeding {constraints.max_cash_pct * 100:.0f}% max. Must stay invested!",
                    )

        # --- BOOMER CONSTRAINTS ---
        if self.bot_id == "boomer" and side == "BUY":
            # No crypto
            if constraints.no_crypto and symbol in CRYPTO_STOCKS:
                return ValidationResult(
                    allowed=False,
                    reason=f"{symbol} is crypto-related. That's not investing, that's speculation.",
                )

            # No leveraged ETFs
            if constraints.no_leverage and symbol in LEVERAGED_SYMBOLS:
                return ValidationResult(
                    allowed=False,
                    reason=f"{symbol} is a leveraged ETF. That's gambling, not investing.",
                )

            # Minimum dividend yield (1%)
            if constraints.min_dividend_yield is not None:
                if dividend_yield is None:
                    return ValidationResult(
                        allowed=False,
                        reason=f"Dividend yield required for {symbol}. Use get_dividend() first.",
                    )
                if dividend_yield < constraints.min_dividend_yield:
                    yield_pct = dividend_yield * 100
                    min_pct = constraints.min_dividend_yield * 100
                    return ValidationResult(
                        allowed=False,
                        reason=f"{symbol} yields only {yield_pct:.2f}%, below {min_pct:.0f}% minimum. If it doesn't pay you to hold it, why hold it?",
                    )

        # --- QUANT CONSTRAINTS ---
        if self.bot_id == "quant":
            if constraints.requires_technical_citation:
                if not technical_reason:
                    return ValidationResult(
                        allowed=False,
                        reason="No technical indicator cited. Every trade must reference RSI, MACD, moving averages, or other technical signals.",
                    )

                # Check that citation mentions actual indicators
                reason_lower = technical_reason.lower()
                has_indicator = any(ind in reason_lower for ind in TECHNICAL_INDICATORS)

                if not has_indicator:
                    return ValidationResult(
                        allowed=False,
                        reason=f"Technical reason doesn't cite a valid indicator. Use RSI, MACD, moving averages, support/resistance, etc.",
                    )

        # --- DOOMER CONSTRAINTS ---
        if self.bot_id == "doomer":
            is_hedge = symbol in HEDGE_SYMBOLS

            # Max 30% long equity
            if side == "BUY" and not is_hedge and constraints.max_long_equity_pct:
                long_equity = sum(
                    p.get("market_value", 0) for p in positions
                    if p.get("symbol") not in HEDGE_SYMBOLS
                )
                new_long_equity = long_equity + trade_value
                long_pct = new_long_equity / current_equity if current_equity > 0 else 1

                if long_pct > constraints.max_long_equity_pct:
                    return ValidationResult(
                        allowed=False,
                        reason=f"Long equity would be {long_pct * 100:.1f}%, exceeding {constraints.max_long_equity_pct * 100:.0f}% max. The crash is coming.",
                    )

            # Must maintain hedges
            if side == "SELL" and is_hedge and constraints.requires_hedges:
                hedge_positions = [p for p in positions if p.get("symbol") in HEDGE_SYMBOLS]
                current_pos = next((p for p in hedge_positions if p.get("symbol") == symbol), None)

                if current_pos:
                    current_qty = current_pos.get("qty", 0)
                    remaining = current_qty - shares
                    other_hedges = [p for p in hedge_positions if p.get("symbol") != symbol]

                    if remaining <= 0 and len(other_hedges) == 0:
                        return ValidationResult(
                            allowed=False,
                            reason="Cannot sell last hedge position. Must maintain at least one hedge.",
                        )

        return ValidationResult(allowed=True)

    def record_trade(
        self,
        symbol: str,
        side: str,
        shares: int,
        price: float,
        reason: Optional[str] = None,
    ) -> dict:
        """Record an executed trade in D1 for dashboard display.

        Args:
            symbol: Stock symbol
            side: BUY or SELL
            shares: Number of shares
            price: Fill price
            reason: Trade commentary

        Returns:
            {"success": True} or {"success": False, "error": "..."}
        """
        try:
            response = self._client.post(
                f"/api/bot/{self.bot_id}/trade",
                json={
                    "symbol": symbol.upper(),
                    "side": side.upper(),
                    "shares": shares,
                    "price": price,
                    "commentary": reason,
                },
            )
            response.raise_for_status()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_leaderboard(self) -> LeaderboardState:
        """Get the current leaderboard standings.

        Returns:
            LeaderboardState with round and standings
        """
        response = self._client.get("/api/leaderboard")
        response.raise_for_status()
        data = response.json()

        standings = []
        for entry in data.get("leaderboard", []):
            standings.append(LeaderboardEntry(
                rank=entry.get("rank", 0),
                name=entry.get("name", ""),
                return_pct=round(entry.get("return_pct", 0), 2),
            ))

        return LeaderboardState(
            round=data.get("current_round", 0),
            standings=standings,
        )

    # ==================== SOCIAL FEATURES ====================

    def send_message(self, content: str, to_bot: Optional[str] = None) -> dict:
        """Send a public message or DM to another bot.

        Args:
            content: Message content
            to_bot: Bot ID for DM, or None for public message

        Returns:
            {"success": True, "message_id": ...} or {"success": False, "error": ...}
        """
        try:
            response = self._client.post(
                "/api/social/messages",
                json={
                    "from_bot": self.bot_id,
                    "to_bot": to_bot,
                    "content": content,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_messages(self, limit: int = 30) -> list[dict]:
        """Get recent messages visible to this bot (public + DMs to me).

        Args:
            limit: Max messages to return

        Returns:
            List of messages
        """
        try:
            response = self._client.get(
                f"/api/social/messages/{self.bot_id}",
                params={"limit": limit},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("messages", [])
        except Exception:
            return []

    def get_all_portfolios(self) -> dict:
        """Get all bot portfolios with positions and P&L.

        Returns:
            {"round": ..., "portfolios": [...]}
        """
        try:
            response = self._client.get("/api/social/portfolios")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_round_context(self) -> dict:
        """Get full round context including leaderboard, trades, messages, portfolios.

        Returns:
            Full context dict for this bot
        """
        try:
            response = self._client.get(f"/api/social/context/{self.bot_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def record_rejected_trade(
        self,
        symbol: str,
        side: str,
        shares: int,
        reason: str,
    ) -> dict:
        """Record a rejected trade for entertainment/dashboard.

        Args:
            symbol: Stock symbol
            side: BUY or SELL
            shares: Number of shares attempted
            reason: Why it was rejected

        Returns:
            {"success": True} or {"success": False, "error": ...}
        """
        try:
            response = self._client.post(
                "/api/social/rejected",
                json={
                    "bot_id": self.bot_id,
                    "symbol": symbol.upper(),
                    "side": side.upper(),
                    "shares": shares,
                    "reason": reason,
                },
            )
            response.raise_for_status()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== MEMORY FEATURES ====================

    # Valid memory types
    MEMORY_TYPES = ['trade', 'rival', 'strategy', 'reflection', 'note']

    def save_memory(
        self,
        memory_type: str,
        content: str,
        importance: int = 5,
    ) -> dict:
        """Save a memory for persistence across rounds.

        Args:
            memory_type: One of 'trade', 'rival', 'strategy', 'reflection', 'note'
            content: The memory content (what to remember)
            importance: 1-10 scale (10 = most important, persists longer)

        Returns:
            {"success": True, "memory_id": ...} or {"success": False, "error": ...}
        """
        if memory_type not in self.MEMORY_TYPES:
            return {
                "success": False,
                "error": f"Invalid type. Must be one of: {', '.join(self.MEMORY_TYPES)}",
            }

        if importance < 1 or importance > 10:
            return {"success": False, "error": "Importance must be between 1 and 10"}

        try:
            response = self._client.post(
                "/api/memory",
                json={
                    "bot_id": self.bot_id,
                    "type": memory_type,
                    "content": content,
                    "importance": importance,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_memories(
        self,
        memory_type: Optional[str] = None,
        count: int = 20,
        min_importance: int = 1,
        target_bot: Optional[str] = None,
    ) -> dict:
        """Get memories for this bot.

        Args:
            memory_type: Filter by type (trade, rival, strategy, reflection, note)
            count: Max memories to return
            min_importance: Minimum importance level (1-10)
            target_bot: For rival notes, filter by target bot ID

        Returns:
            {"bot_id": ..., "count": ..., "memories": [...]}
        """
        try:
            params: dict[str, str | int] = {"count": count}
            if memory_type:
                params["type"] = memory_type
            if min_importance > 1:
                params["min_importance"] = min_importance
            if target_bot:
                params["target_bot"] = target_bot

            response = self._client.get(
                f"/api/memory/{self.bot_id}",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "memories": []}

    def get_memory_context(self) -> dict:
        """Get organized memories for context (short-term and long-term).

        Returns:
            {
                "current_round": ...,
                "short_term": {...},  # Last 3 rounds grouped by type
                "long_term": [...],   # High importance older memories
                "active_strategy": {...},
                "rival_notes": [...]
            }
        """
        try:
            response = self._client.get(f"/api/memory/{self.bot_id}/context")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
