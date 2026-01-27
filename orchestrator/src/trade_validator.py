"""Validate trades against bot constraints."""

from dataclasses import dataclass
from typing import Optional

from .config import DEGEN_FAVORITES, HEDGE_SYMBOLS, SP500_SYMBOLS, Config
from .models import Bot, ParsedTrade, Position


@dataclass
class ValidationResult:
    """Result of trade validation."""

    valid: bool
    trade: ParsedTrade
    rejection_reason: Optional[str] = None


class TradeValidator:
    """Validates trades against bot-specific constraints."""

    def __init__(self, config: Config):
        self.config = config

    def validate(
        self,
        bot: Bot,
        trade: ParsedTrade,
        current_prices: dict[str, float],
    ) -> ValidationResult:
        """Validate a trade for a specific bot.

        Args:
            bot: Bot attempting the trade
            trade: Trade to validate
            current_prices: Map of symbol to current price

        Returns:
            ValidationResult with valid flag and optional rejection reason
        """
        # Basic validation first
        result = self._validate_basic(bot, trade, current_prices)
        if not result.valid:
            return result

        # Bot-specific constraints
        if bot.type == "baseline":
            return self._validate_baseline(bot, trade, current_prices)

        # Free agents have no constraints
        return ValidationResult(valid=True, trade=trade)

    def _validate_basic(
        self,
        bot: Bot,
        trade: ParsedTrade,
        current_prices: dict[str, float],
    ) -> ValidationResult:
        """Basic validation common to all bots."""
        # Check if price data available
        if trade.symbol not in current_prices:
            return ValidationResult(
                valid=False,
                trade=trade,
                rejection_reason=f"No price data for {trade.symbol}",
            )

        current_price = current_prices[trade.symbol]

        # Price tolerance (allow 2% slippage)
        price_diff_pct = abs(trade.price - current_price) / current_price * 100
        if price_diff_pct > 2.0:
            return ValidationResult(
                valid=False,
                trade=trade,
                rejection_reason=f"Price {trade.price} too far from current {current_price} ({price_diff_pct:.1f}% diff)",
            )

        # Check for BUY - sufficient cash
        if trade.side == "BUY":
            total_cost = trade.shares * trade.price
            if total_cost > bot.cash:
                return ValidationResult(
                    valid=False,
                    trade=trade,
                    rejection_reason=f"Insufficient cash: need ${total_cost:.2f}, have ${bot.cash:.2f}",
                )

        # Check for SELL - sufficient shares
        if trade.side == "SELL":
            position = bot.get_position(trade.symbol)
            if position is None or position.shares < trade.shares:
                current_shares = position.shares if position else 0
                return ValidationResult(
                    valid=False,
                    trade=trade,
                    rejection_reason=f"Insufficient shares: need {trade.shares}, have {current_shares}",
                )

        return ValidationResult(valid=True, trade=trade)

    def _validate_baseline(
        self,
        bot: Bot,
        trade: ParsedTrade,
        current_prices: dict[str, float],
    ) -> ValidationResult:
        """Validate baseline bot constraints."""
        constraints = self.config.baseline_bots.get(bot.id, {})

        # Turtle: S&P 500 only, max 5% per position, min 30% cash
        if bot.id == "turtle":
            return self._validate_turtle(bot, trade, current_prices, constraints)

        # Degen: Max 20% cash
        if bot.id == "degen":
            return self._validate_degen(bot, trade, current_prices, constraints)

        # Boomer: Min 1% dividend yield
        if bot.id == "boomer":
            return self._validate_boomer(bot, trade, current_prices, constraints)

        # Quant: Must cite technical indicator (checked in commentary)
        if bot.id == "quant":
            return ValidationResult(valid=True, trade=trade)

        # Doomer: Max 30% long equity, must hold hedges
        if bot.id == "doomer":
            return self._validate_doomer(bot, trade, current_prices, constraints)

        return ValidationResult(valid=True, trade=trade)

    def _validate_turtle(
        self,
        bot: Bot,
        trade: ParsedTrade,
        current_prices: dict[str, float],
        constraints: dict,
    ) -> ValidationResult:
        """Validate Turtle bot constraints."""
        # S&P 500 only
        if constraints.get("sp500_only") and trade.symbol not in SP500_SYMBOLS:
            return ValidationResult(
                valid=False,
                trade=trade,
                rejection_reason=f"{trade.symbol} not in S&P 500 universe",
            )

        if trade.side == "BUY":
            # Max 5% per position
            max_position_pct = constraints.get("max_position_pct", 0.05)
            trade_value = trade.shares * trade.price
            max_allowed = bot.total_value * max_position_pct

            # Include existing position
            existing = bot.get_position(trade.symbol)
            existing_value = 0
            if existing and existing.current_price:
                existing_value = existing.shares * existing.current_price

            total_position = existing_value + trade_value
            if total_position > max_allowed:
                return ValidationResult(
                    valid=False,
                    trade=trade,
                    rejection_reason=f"Position would be {total_position/bot.total_value*100:.1f}% > {max_position_pct*100}% max",
                )

            # Min 30% cash after trade
            min_cash_pct = constraints.get("min_cash_pct", 0.30)
            cash_after = bot.cash - trade_value
            if cash_after < bot.total_value * min_cash_pct:
                return ValidationResult(
                    valid=False,
                    trade=trade,
                    rejection_reason=f"Cash after trade would be {cash_after/bot.total_value*100:.1f}% < {min_cash_pct*100}% min",
                )

        return ValidationResult(valid=True, trade=trade)

    def _validate_degen(
        self,
        bot: Bot,
        trade: ParsedTrade,
        current_prices: dict[str, float],
        constraints: dict,
    ) -> ValidationResult:
        """Validate Degen bot constraints."""
        if trade.side == "SELL":
            # Check if selling would put cash above 20%
            max_cash_pct = constraints.get("max_cash_pct", 0.20)
            trade_value = trade.shares * trade.price
            cash_after = bot.cash + trade_value

            if cash_after > bot.total_value * max_cash_pct:
                return ValidationResult(
                    valid=False,
                    trade=trade,
                    rejection_reason=f"Cash after sale would be {cash_after/bot.total_value*100:.1f}% > {max_cash_pct*100}% max - must stay invested",
                )

        return ValidationResult(valid=True, trade=trade)

    def _validate_boomer(
        self,
        bot: Bot,
        trade: ParsedTrade,
        current_prices: dict[str, float],
        constraints: dict,
    ) -> ValidationResult:
        """Validate Boomer bot constraints."""
        if trade.side == "BUY":
            # No crypto or leveraged ETFs
            if constraints.get("no_crypto") and trade.symbol in {"COIN", "MARA", "RIOT", "BITO"}:
                return ValidationResult(
                    valid=False,
                    trade=trade,
                    rejection_reason=f"{trade.symbol} is crypto-related - not allowed",
                )

            if constraints.get("no_leverage") and trade.symbol in DEGEN_FAVORITES:
                return ValidationResult(
                    valid=False,
                    trade=trade,
                    rejection_reason=f"{trade.symbol} is leveraged - not allowed",
                )

            # Note: Dividend yield check would require API call
            # For now, trust the bot to follow this constraint
            # and check in post-validation

        return ValidationResult(valid=True, trade=trade)

    def _validate_doomer(
        self,
        bot: Bot,
        trade: ParsedTrade,
        current_prices: dict[str, float],
        constraints: dict,
    ) -> ValidationResult:
        """Validate Doomer bot constraints."""
        # Calculate current long equity percentage
        long_equity = 0
        hedge_value = 0

        for pos in bot.positions:
            if pos.symbol in HEDGE_SYMBOLS:
                price = current_prices.get(pos.symbol, pos.current_price or pos.avg_cost)
                hedge_value += pos.shares * price
            else:
                price = current_prices.get(pos.symbol, pos.current_price or pos.avg_cost)
                long_equity += pos.shares * price

        if trade.side == "BUY" and trade.symbol not in HEDGE_SYMBOLS:
            # Buying more long equity
            max_long_pct = constraints.get("max_long_equity_pct", 0.30)
            trade_value = trade.shares * trade.price
            new_long = long_equity + trade_value

            if new_long > bot.total_value * max_long_pct:
                return ValidationResult(
                    valid=False,
                    trade=trade,
                    rejection_reason=f"Long equity would be {new_long/bot.total_value*100:.1f}% > {max_long_pct*100}% max",
                )

        if trade.side == "SELL" and trade.symbol in HEDGE_SYMBOLS:
            # Selling hedges - ensure we still have some
            required_hedges = set(constraints.get("requires_hedges", []))
            remaining_hedges = set()

            for pos in bot.positions:
                if pos.symbol in required_hedges:
                    if pos.symbol == trade.symbol:
                        if pos.shares > trade.shares:
                            remaining_hedges.add(pos.symbol)
                    else:
                        remaining_hedges.add(pos.symbol)

            if not remaining_hedges:
                return ValidationResult(
                    valid=False,
                    trade=trade,
                    rejection_reason="Must maintain at least one hedge position",
                )

        return ValidationResult(valid=True, trade=trade)


def validate_quant_commentary(commentary: Optional[str]) -> bool:
    """Check if Quant bot cited a technical indicator."""
    if not commentary:
        return False

    indicators = [
        "rsi", "macd", "sma", "ema", "bollinger", "stochastic",
        "momentum", "roc", "atr", "adx", "obv", "vwap",
        "moving average", "relative strength", "support", "resistance",
        "oversold", "overbought", "crossover", "divergence",
    ]

    commentary_lower = commentary.lower()
    return any(ind in commentary_lower for ind in indicators)
