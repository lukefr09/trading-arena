#!/usr/bin/env python3
"""Reset the game - clear all trades and positions, restore starting cash."""

import argparse
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()


def reset_game(api_url: str, api_key: str, starting_cash: float = 100000.0):
    """Reset the game to initial state."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print("Fetching current state...")

    try:
        # Get current bots
        response = httpx.get(
            f"{api_url}/api/state",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        current_state = response.json()

        # Reset each bot
        bots = []
        for bot in current_state.get("bots", []):
            bots.append({
                "id": bot["id"],
                "name": bot["name"],
                "type": bot["type"],
                "cash": starting_cash,
                "total_value": starting_cash,
                "session_id": None,
                "last_commentary": None,
                "enabled": True,
                "positions": [],
            })

        # Build reset state
        state = {
            "status": "paused",
            "starting_cash": starting_cash,
            "current_round": 0,
            "bots": bots,
        }

        print(f"Resetting {len(bots)} bots to ${starting_cash:,.2f}...")

        response = httpx.post(
            f"{api_url}/api/state",
            headers=headers,
            json=state,
            timeout=30.0,
        )
        response.raise_for_status()

        print("Game reset successfully!")
        print(f"  - Round: 0")
        print(f"  - Status: paused")
        print(f"  - All bots: ${starting_cash:,.2f} cash, no positions")

    except httpx.HTTPError as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Reset Trading Arena game")
    parser.add_argument(
        "--starting-cash",
        type=float,
        default=100000.0,
        help="Starting cash for each bot (default: $100,000)",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("CF_API_URL"),
        help="Cloudflare Workers API URL",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("CF_API_KEY"),
        help="API key for authentication",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt",
    )
    args = parser.parse_args()

    if not args.api_url:
        print("Error: CF_API_URL not set")
        sys.exit(1)
    if not args.api_key:
        print("Error: CF_API_KEY not set")
        sys.exit(1)

    if not args.confirm:
        response = input("This will reset ALL game data. Are you sure? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    reset_game(args.api_url, args.api_key, args.starting_cash)


if __name__ == "__main__":
    main()
