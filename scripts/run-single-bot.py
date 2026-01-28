#!/usr/bin/env python3
"""Run a single bot for testing.

With bot-driven execution, the bot trades directly via MCP tools.
This script just runs the bot and displays what happens.
"""

import argparse
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from orchestrator.src.bot_runner import BotRunner
from orchestrator.src.config import load_config
from orchestrator.src.state import StateManager


def run_single_bot(bot_id: str, dry_run: bool = False):
    """Run a single bot's trading session.

    The bot trades directly via MCP tools:
    - get_portfolio() to see holdings
    - place_order() to execute trades (validates constraints first)
    - get_leaderboard() to see standings
    """
    config = load_config()
    state_manager = StateManager(config)
    bot_runner = BotRunner(
        model=config.claude_model,
        cf_api_url=config.cf_api_url,
        cf_api_key=config.cf_api_key,
        finnhub_api_key=config.finnhub_api_key,
    )

    print(f"Loading game state...")
    state = state_manager.load_state()

    # Find the bot
    bot = state.get_bot(bot_id)
    if not bot:
        print(f"Error: Bot '{bot_id}' not found")
        print(f"Available bots: {[b.id for b in state.bots]}")
        sys.exit(1)

    print(f"\nRunning bot: {bot.name} ({bot.type})")
    print(f"  Has Alpaca credentials: {bool(bot.alpaca_api_key)}")

    if dry_run:
        print("\n[Dry run - bot will not be invoked]")
        print("In production, the bot would:")
        print("  1. Check portfolio via get_portfolio()")
        print("  2. Research via get_price(), get_technicals(), etc.")
        print("  3. Execute trades via place_order()")
        print("     - Constraints validated automatically")
        print("     - Rejected trades returned with reason")
        print("  4. See standings via get_leaderboard()")
        state_manager.close()
        return

    # Run the bot with MCP tools
    print("\nRunning bot session with MCP tools...")
    print("The bot will trade directly via place_order().")
    print("Constraint violations will be returned as rejections.")
    print("-" * 50)

    output = bot_runner.run_bot_with_mcp(bot, state)

    if output is None:
        print("Error: Bot failed to respond")
        sys.exit(1)

    print("\n--- Bot Output ---")
    print(output[:3000])  # Show more output
    if len(output) > 3000:
        print("... (truncated)")
    print("--- End Output ---\n")

    # Update bot commentary
    bot.last_commentary = output[:2000] if output else None

    # Save bot state
    print("Saving bot state...")
    state_manager.update_bot(bot)

    print("\nDone! Check the dashboard to see any trades executed.")

    state_manager.close()


def main():
    parser = argparse.ArgumentParser(description="Run a single trading bot")
    parser.add_argument(
        "bot_id",
        help="Bot ID to run (e.g., turtle, degen, gary)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without running",
    )
    args = parser.parse_args()

    run_single_bot(args.bot_id, args.dry_run)


if __name__ == "__main__":
    main()
