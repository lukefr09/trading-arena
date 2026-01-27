#!/usr/bin/env python3
"""Initialize the game with all bots at starting cash."""

import argparse
import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

# Bot definitions
BOTS = [
    # Baseline bots (with constraints)
    {"id": "turtle", "name": "Turtle", "type": "baseline"},
    {"id": "degen", "name": "Degen", "type": "baseline"},
    {"id": "boomer", "name": "Boomer", "type": "baseline"},
    {"id": "quant", "name": "Quant", "type": "baseline"},
    {"id": "doomer", "name": "Doomer", "type": "baseline"},
    # Free agents (no constraints)
    {"id": "gary", "name": "Gary", "type": "free_agent"},
    {"id": "diana", "name": "Diana", "type": "free_agent"},
    {"id": "mel", "name": "Mel", "type": "free_agent"},
    {"id": "vince", "name": "Vince", "type": "free_agent"},
    {"id": "rei", "name": "Rei", "type": "free_agent"},
]


def init_game(api_url: str, api_key: str, starting_cash: float = 100000.0):
    """Initialize the game with all bots."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Build initial state
    bots = []
    for bot in BOTS:
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

    state = {
        "status": "paused",
        "starting_cash": starting_cash,
        "current_round": 0,
        "bots": bots,
    }

    print(f"Initializing game with {len(bots)} bots...")
    print(f"Starting cash: ${starting_cash:,.2f}")

    try:
        response = httpx.post(
            f"{api_url}/api/state",
            headers=headers,
            json=state,
            timeout=30.0,
        )
        response.raise_for_status()
        print("Game initialized successfully!")
        print("\nBots:")
        for bot in bots:
            print(f"  - {bot['name']} ({bot['type']})")
    except httpx.HTTPError as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Initialize Trading Arena game")
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
    args = parser.parse_args()

    if not args.api_url:
        print("Error: CF_API_URL not set")
        sys.exit(1)
    if not args.api_key:
        print("Error: CF_API_KEY not set")
        sys.exit(1)

    init_game(args.api_url, args.api_key, args.starting_cash)


if __name__ == "__main__":
    main()
