#!/usr/bin/env python3
"""Set game status (running/paused)."""

import argparse
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()


def set_status(api_url: str, api_key: str, status: str):
    """Set the game status."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            f"{api_url}/api/state",
            headers=headers,
            json={"status": status},
            timeout=30.0,
        )
        response.raise_for_status()

        print(f"Game status set to: {status.upper()}")

        if status == "running":
            print("The orchestrator will now execute trades during market hours.")
        else:
            print("The orchestrator will skip trading rounds while paused.")

    except httpx.HTTPError as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Set Trading Arena game status")
    parser.add_argument(
        "status",
        choices=["running", "paused"],
        help="Game status to set",
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

    set_status(args.api_url, args.api_key, args.status)


if __name__ == "__main__":
    main()
