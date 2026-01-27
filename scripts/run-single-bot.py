#!/usr/bin/env python3
"""Run a single bot for testing."""

import argparse
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from orchestrator.src.bot_runner import BotRunner
from orchestrator.src.config import load_config
from orchestrator.src.models import Bot, GameState, Position
from orchestrator.src.price_fetcher import PriceFetcher
from orchestrator.src.state import StateManager
from orchestrator.src.trade_executor import TradeExecutor, update_position_prices
from orchestrator.src.trade_parser import extract_commentary, parse_trades
from orchestrator.src.trade_validator import TradeValidator


def run_single_bot(bot_id: str, dry_run: bool = False):
    """Run a single bot's trading session."""
    config = load_config()
    state_manager = StateManager(config)
    price_fetcher = PriceFetcher(config.finnhub_api_key)
    bot_runner = BotRunner(config.claude_model)
    validator = TradeValidator(config)
    executor = TradeExecutor()

    print(f"Loading game state...")
    state = state_manager.load_state()

    # Find the bot
    bot = state.get_bot(bot_id)
    if not bot:
        print(f"Error: Bot '{bot_id}' not found")
        print(f"Available bots: {[b.id for b in state.bots]}")
        sys.exit(1)

    print(f"\nRunning bot: {bot.name} ({bot.type})")
    print(f"  Cash: ${bot.cash:,.2f}")
    print(f"  Total Value: ${bot.total_value:,.2f}")
    print(f"  Positions: {len(bot.positions)}")

    # Update position prices
    print("\nFetching current prices...")
    prices = price_fetcher.update_all_prices([bot])
    update_position_prices(bot, prices)

    # Run the bot
    print("\nRunning bot session...")
    output = bot_runner.run_bot(bot, state)

    if output is None:
        print("Error: Bot failed to respond")
        sys.exit(1)

    print("\n--- Bot Output ---")
    print(output[:2000])  # Truncate for display
    if len(output) > 2000:
        print("... (truncated)")
    print("--- End Output ---\n")

    # Parse trades
    parsed_trades = parse_trades(output)
    commentary = extract_commentary(output)

    print(f"Parsed {len(parsed_trades)} trades:")
    for trade in parsed_trades:
        print(f"  {trade.side} {trade.shares} {trade.symbol} @ ${trade.price:.2f}")

    if commentary:
        print(f"\nCommentary: {commentary[:200]}...")

    if dry_run:
        print("\n[Dry run - trades not executed]")
        return

    # Validate and execute
    print("\nValidating and executing trades...")
    for parsed in parsed_trades[:config.max_trades_per_round]:
        # Get price if needed
        if parsed.symbol not in prices:
            price = price_fetcher.get_price(parsed.symbol)
            if price:
                prices[parsed.symbol] = price

        result = validator.validate(bot, parsed, prices)

        if result.valid:
            trade = executor.execute(bot, parsed, state.current_round, commentary)
            print(f"  EXECUTED: {trade.side} {trade.shares} {trade.symbol}")
        else:
            print(f"  REJECTED: {parsed.side} {parsed.symbol} - {result.rejection_reason}")

    # Save state
    print("\nSaving bot state...")
    state_manager.update_bot(bot)

    print(f"\nFinal state:")
    print(f"  Cash: ${bot.cash:,.2f}")
    print(f"  Total Value: ${bot.total_value:,.2f}")

    state_manager.close()
    price_fetcher.close()


def main():
    parser = argparse.ArgumentParser(description="Run a single trading bot")
    parser.add_argument(
        "bot_id",
        help="Bot ID to run (e.g., turtle, degen, gary)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse trades but don't execute",
    )
    args = parser.parse_args()

    run_single_bot(args.bot_id, args.dry_run)


if __name__ == "__main__":
    main()
