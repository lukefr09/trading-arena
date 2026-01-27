"""Main orchestration loop for Trading Arena."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .bot_runner import BotRunner
from .config import Config, load_config
from .models import Bot, GameState, Trade
from .price_fetcher import PriceFetcher
from .state import StateManager
from .trade_executor import TradeExecutor, update_position_prices
from .trade_parser import extract_commentary, parse_trades
from .trade_validator import TradeValidator, validate_quant_commentary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TradingArena:
    """Main orchestrator for the trading arena."""

    def __init__(self, config: Config):
        self.config = config
        self.state_manager = StateManager(config)
        self.price_fetcher = PriceFetcher(config.finnhub_api_key)
        self.bot_runner = BotRunner(config.claude_model)
        self.validator = TradeValidator(config)
        self.executor = TradeExecutor()

    def run_round(self, bot_ids: Optional[list[str]] = None) -> dict:
        """Run a single trading round.

        Args:
            bot_ids: Optional list of specific bots to run (default: all enabled)

        Returns:
            Summary dict with round results
        """
        logger.info("Starting trading round...")

        # Load current state
        state = self.state_manager.load_state()

        if state.status != "running":
            logger.warning(f"Game is not running (status: {state.status})")
            return {"error": "Game is not running"}

        # Get bots to run
        bots = state.get_enabled_bots()
        if bot_ids:
            bots = [b for b in bots if b.id in bot_ids]

        if not bots:
            logger.warning("No bots to run")
            return {"error": "No bots to run"}

        # Increment round
        new_round = self.state_manager.increment_round()
        state.current_round = new_round
        logger.info(f"Round {new_round}")

        # Update all position prices
        logger.info("Fetching current prices...")
        prices = self.price_fetcher.update_all_prices(bots)

        for bot in bots:
            update_position_prices(bot, prices)

        # Run each bot
        all_trades: list[Trade] = []
        results = {}

        for bot in bots:
            logger.info(f"Running bot: {bot.name}")
            result = self._run_single_bot(bot, state, prices)
            results[bot.id] = result

            if result.get("trades"):
                all_trades.extend(result["trades"])

            # Update bot state
            self.state_manager.update_bot(bot)

            # Push real-time update
            self.state_manager.push_update("bot_update", {
                "bot": bot.to_dict(),
                "trades": [t.to_dict() for t in result.get("trades", [])],
            })

        # Record all trades
        if all_trades:
            self.state_manager.record_trades(all_trades)

        # Final state save
        state.updated_at = datetime.utcnow()
        self.state_manager.save_state(state)

        # Push leaderboard update
        self.state_manager.push_update("leaderboard", {
            "round": new_round,
            "leaderboard": [b.to_dict() for b in state.get_leaderboard()],
        })

        logger.info(f"Round {new_round} complete. {len(all_trades)} trades executed.")

        return {
            "round": new_round,
            "bots_run": len(bots),
            "trades_executed": len(all_trades),
            "results": results,
        }

    def _run_single_bot(
        self,
        bot: Bot,
        state: GameState,
        prices: dict[str, float],
    ) -> dict:
        """Run a single bot and process its trades.

        Args:
            bot: Bot to run
            state: Current game state
            prices: Current market prices

        Returns:
            Dict with bot's output, trades, and any errors
        """
        mcp_config = Path(__file__).parent.parent / "mcp-config.json"

        output = self.bot_runner.run_bot_with_mcp(
            bot,
            state,
            mcp_config_path=str(mcp_config) if mcp_config.exists() else None,
        )

        if output is None:
            return {"error": "Bot failed to respond", "trades": []}

        # Parse trades from output
        parsed_trades = parse_trades(output)
        commentary = extract_commentary(output)

        # Update bot commentary
        bot.last_commentary = commentary

        # Special check for Quant bot
        if bot.id == "quant" and parsed_trades:
            if not validate_quant_commentary(commentary):
                logger.warning(f"Quant bot did not cite technical indicator")
                # Still allow trades but log warning

        # Validate and execute trades
        executed_trades: list[Trade] = []
        validation_errors: list[str] = []

        # Limit trades per round
        for parsed in parsed_trades[: self.config.max_trades_per_round]:
            # Get latest price for symbol
            if parsed.symbol not in prices:
                price = self.price_fetcher.get_price(parsed.symbol)
                if price:
                    prices[parsed.symbol] = price

            # Validate trade
            result = self.validator.validate(bot, parsed, prices)

            if result.valid:
                # Execute trade
                trade = self.executor.execute(
                    bot, parsed, state.current_round, commentary
                )
                executed_trades.append(trade)
                logger.info(f"{bot.name}: {trade.side} {trade.shares} {trade.symbol}")
            else:
                validation_errors.append(result.rejection_reason or "Validation failed")
                logger.warning(
                    f"{bot.name}: Trade rejected - {result.rejection_reason}"
                )

        return {
            "output": output[:1000] if output else None,  # Truncate for storage
            "trades": executed_trades,
            "commentary": commentary,
            "validation_errors": validation_errors,
        }

    def close(self):
        """Clean up resources."""
        self.state_manager.close()
        self.price_fetcher.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Trading Arena Orchestrator")
    parser.add_argument(
        "--bots",
        nargs="*",
        help="Specific bot IDs to run (default: all enabled)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without saving state changes",
    )
    args = parser.parse_args()

    try:
        config = load_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    arena = TradingArena(config)

    try:
        result = arena.run_round(bot_ids=args.bots)
        logger.info(f"Round complete: {result}")
    except Exception as e:
        logger.exception(f"Round failed: {e}")
        sys.exit(1)
    finally:
        arena.close()


if __name__ == "__main__":
    main()
