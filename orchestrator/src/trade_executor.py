"""Execute validated trades and update bot state."""

import logging
from datetime import datetime
from typing import Optional

from .models import Bot, ParsedTrade, Position, Trade

logger = logging.getLogger(__name__)


class TradeExecutor:
    """Executes trades and updates bot portfolios."""

    def execute(
        self,
        bot: Bot,
        trade: ParsedTrade,
        round_num: int,
        commentary: Optional[str] = None,
    ) -> Trade:
        """Execute a trade for a bot.

        Args:
            bot: Bot executing the trade
            trade: Validated trade to execute
            round_num: Current round number
            commentary: Optional commentary from bot

        Returns:
            Executed Trade object

        Updates bot.cash and bot.positions in place.
        """
        executed_trade = Trade(
            bot_id=bot.id,
            symbol=trade.symbol,
            side=trade.side,
            shares=trade.shares,
            price=trade.price,
            round=round_num,
            commentary=commentary,
            executed_at=datetime.utcnow(),
        )

        if trade.side == "BUY":
            self._execute_buy(bot, trade)
        else:
            self._execute_sell(bot, trade)

        # Recalculate total value
        bot.calculate_total_value()
        bot.updated_at = datetime.utcnow()

        logger.info(
            f"Executed {trade.side} {trade.shares} {trade.symbol} @ ${trade.price:.2f} "
            f"for {bot.name} (cash: ${bot.cash:.2f}, total: ${bot.total_value:.2f})"
        )

        return executed_trade

    def _execute_buy(self, bot: Bot, trade: ParsedTrade) -> None:
        """Execute a buy order."""
        total_cost = trade.shares * trade.price
        bot.cash -= total_cost

        # Update or create position
        position = bot.get_position(trade.symbol)
        if position:
            # Calculate new average cost
            old_value = position.shares * position.avg_cost
            new_value = trade.shares * trade.price
            total_shares = position.shares + trade.shares
            position.avg_cost = (old_value + new_value) / total_shares
            position.shares = total_shares
            position.current_price = trade.price
        else:
            # Create new position
            new_position = Position(
                symbol=trade.symbol,
                shares=trade.shares,
                avg_cost=trade.price,
                current_price=trade.price,
            )
            bot.positions.append(new_position)

    def _execute_sell(self, bot: Bot, trade: ParsedTrade) -> None:
        """Execute a sell order."""
        total_proceeds = trade.shares * trade.price
        bot.cash += total_proceeds

        # Update position
        position = bot.get_position(trade.symbol)
        if position:
            position.shares -= trade.shares
            position.current_price = trade.price

            # Remove position if fully sold
            if position.shares <= 0:
                bot.positions = [p for p in bot.positions if p.symbol != trade.symbol]


def update_position_prices(bot: Bot, prices: dict[str, float]) -> None:
    """Update all position prices for a bot.

    Args:
        bot: Bot to update
        prices: Map of symbol to current price
    """
    for position in bot.positions:
        if position.symbol in prices:
            position.current_price = prices[position.symbol]

    bot.calculate_total_value()
