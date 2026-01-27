#!/usr/bin/env python3
"""View current game state."""

import argparse
import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()


def view_state(api_url: str, verbose: bool = False):
    """Fetch and display current game state."""
    try:
        response = httpx.get(
            f"{api_url}/api/state",
            timeout=30.0,
        )
        response.raise_for_status()
        state = response.json()

        print("=" * 60)
        print("TRADING ARENA - CURRENT STATE")
        print("=" * 60)

        print(f"\nStatus: {state['status'].upper()}")
        print(f"Round: {state['current_round']}")
        print(f"Starting Cash: ${state['starting_cash']:,.2f}")

        print("\n" + "-" * 60)
        print("LEADERBOARD")
        print("-" * 60)

        # Sort bots by total value
        bots = sorted(state.get("bots", []), key=lambda b: b["total_value"], reverse=True)

        for i, bot in enumerate(bots, 1):
            return_pct = ((bot["total_value"] / state["starting_cash"]) - 1) * 100
            sign = "+" if return_pct >= 0 else ""
            enabled = "" if bot.get("enabled", True) else " [DISABLED]"
            print(f"{i:2}. {bot['name']:10} ({bot['type']:10}) ${bot['total_value']:>12,.2f} ({sign}{return_pct:>6.2f}%){enabled}")

        if verbose:
            print("\n" + "-" * 60)
            print("POSITIONS")
            print("-" * 60)

            for bot in bots:
                positions = bot.get("positions", [])
                if positions:
                    print(f"\n{bot['name']}:")
                    for pos in positions:
                        price = pos.get("current_price") or pos.get("avg_cost")
                        value = pos["shares"] * price
                        print(f"  {pos['symbol']:6} {pos['shares']:>8.2f} shares @ ${pos['avg_cost']:>8.2f} (value: ${value:>10,.2f})")

            print("\n" + "-" * 60)
            print("RECENT TRADES")
            print("-" * 60)

            trades = state.get("recent_trades", [])[:20]
            for trade in trades:
                time_str = trade.get("executed_at", "")[:16] if trade.get("executed_at") else ""
                print(f"{time_str} | {trade['bot_id']:8} {trade['side']:4} {trade['shares']:>6} {trade['symbol']:6} @ ${trade['price']:>8.2f}")

        print("\n" + "=" * 60)

    except httpx.HTTPError as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="View Trading Arena game state")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("CF_API_URL"),
        help="Cloudflare Workers API URL",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show positions and recent trades",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON",
    )
    args = parser.parse_args()

    if not args.api_url:
        print("Error: CF_API_URL not set")
        sys.exit(1)

    if args.json:
        response = httpx.get(f"{args.api_url}/api/state", timeout=30.0)
        print(json.dumps(response.json(), indent=2))
    else:
        view_state(args.api_url, args.verbose)


if __name__ == "__main__":
    main()
