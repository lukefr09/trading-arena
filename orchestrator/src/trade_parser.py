"""Parse trades from bot output."""

import re
from typing import Optional

from .models import ParsedTrade

# Pattern to match: TRADE: BUY 50 NVDA @ 142.30
TRADE_PATTERN = re.compile(
    r"TRADE:\s*(BUY|SELL)\s+(\d+(?:\.\d+)?)\s+([A-Z]{1,5})\s+@\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def parse_trades(output: str) -> list[ParsedTrade]:
    """Parse trade commands from bot output.

    Args:
        output: Raw text output from bot

    Returns:
        List of parsed trades (not yet validated)
    """
    trades = []

    for match in TRADE_PATTERN.finditer(output):
        side = match.group(1).upper()
        shares = float(match.group(2))
        symbol = match.group(3).upper()
        price = float(match.group(4))

        if side in ("BUY", "SELL") and shares > 0 and price > 0:
            trades.append(
                ParsedTrade(
                    side=side,
                    shares=shares,
                    symbol=symbol,
                    price=price,
                )
            )

    return trades


def extract_commentary(output: str) -> Optional[str]:
    """Extract commentary/reasoning from bot output.

    Looks for text after trades or in specific commentary sections.
    """
    # Remove trade lines
    lines = output.split("\n")
    non_trade_lines = []

    for line in lines:
        if not TRADE_PATTERN.search(line):
            stripped = line.strip()
            if stripped:
                non_trade_lines.append(stripped)

    if not non_trade_lines:
        return None

    # Join and truncate
    commentary = " ".join(non_trade_lines)

    # Truncate to reasonable length
    if len(commentary) > 500:
        commentary = commentary[:497] + "..."

    return commentary


def validate_trade_format(trade_str: str) -> bool:
    """Validate a single trade string matches expected format."""
    return bool(TRADE_PATTERN.match(trade_str.strip()))
