"""Main orchestration loop for Trading Arena.

Bot-Driven Execution Architecture:
- Bots trade directly via MCP tools (place_order)
- MCP server validates constraints and executes on Alpaca
- Orchestrator just coordinates timing and stores commentary
"""

import argparse
import logging
import random
import sys
from datetime import datetime
from typing import Optional

from .bot_runner import BotRunner
from .config import Config, load_config
from .models import Bot, GameState
from .state import StateManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TradingArena:
    """Main orchestrator for the trading arena.

    With bot-driven execution, the orchestrator's job is simple:
    1. Check if game is running
    2. Increment round
    3. Run each bot (they trade via MCP tools directly)
    4. Store commentary
    5. Push real-time updates
    """

    def __init__(self, config: Config):
        self.config = config
        self.state_manager = StateManager(config)
        self.bot_runner = BotRunner(
            model=config.claude_model,
            cf_api_url=config.cf_api_url,
            cf_api_key=config.cf_api_key,
            finnhub_api_key=config.finnhub_api_key,
        )

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

        # Randomize bot execution order (no information advantage)
        random.shuffle(bots)

        # Run each bot
        results = {}

        for bot in bots:
            logger.info(f"Running bot: {bot.name}")
            result = self._run_single_bot(bot, state)
            results[bot.id] = result

            # Update bot state (commentary)
            self.state_manager.update_bot(bot)

            # Push real-time update
            self.state_manager.push_update("bot_update", {
                "bot_id": bot.id,
                "bot_name": bot.name,
                "commentary": result.get("commentary"),
            })

        # Final state save
        state.updated_at = datetime.utcnow()
        self.state_manager.save_state(state)

        # Push leaderboard update
        self.state_manager.push_update("leaderboard", {
            "round": new_round,
            "leaderboard": [b.to_dict() for b in state.get_leaderboard()],
        })

        logger.info(f"Round {new_round} complete.")

        return {
            "round": new_round,
            "bots_run": len(bots),
            "results": results,
        }

    def _run_single_bot(
        self,
        bot: Bot,
        state: GameState,
    ) -> dict:
        """Run a single bot's trading session.

        Bots trade directly via MCP tools:
        - get_portfolio() to see their holdings
        - place_order() to execute trades (with constraint validation)
        - get_leaderboard() to see standings

        The orchestrator just captures the output/commentary.

        Args:
            bot: Bot to run
            state: Current game state

        Returns:
            Dict with bot's output and commentary
        """
        output = self.bot_runner.run_bot_with_mcp(bot, state)

        if output is None:
            logger.error(f"Bot {bot.name} failed to respond")
            return {"error": "Bot failed to respond", "commentary": None}

        # Extract commentary (everything the bot said)
        # Truncate for storage
        commentary = output[:2000] if output else None

        # Update bot's last commentary
        bot.last_commentary = commentary
        bot.updated_at = datetime.utcnow()

        return {
            "output": output[:1000] if output else None,
            "commentary": commentary,
        }

    def close(self):
        """Clean up resources."""
        self.state_manager.close()


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
