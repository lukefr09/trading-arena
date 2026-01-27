"""Run bot trading sessions using Claude Code CLI."""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from .models import Bot, GameState

logger = logging.getLogger(__name__)

# Path to prompts directory
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class BotRunner:
    """Runs bot trading sessions via Claude Code CLI."""

    def __init__(self, model: str = "claude-opus-4-20250514"):
        self.model = model

    def get_system_prompt(self, bot: Bot) -> str:
        """Load system prompt for a bot."""
        prompt_file = PROMPTS_DIR / f"{bot.id}.md"
        if not prompt_file.exists():
            raise FileNotFoundError(f"No prompt file for bot: {bot.id}")
        return prompt_file.read_text()

    def build_context(self, bot: Bot, state: GameState) -> str:
        """Build context message for bot's trading decision.

        Args:
            bot: The bot making decisions
            state: Current game state

        Returns:
            Context string with portfolio and market info
        """
        # Portfolio summary
        portfolio_lines = [
            f"# Your Portfolio (Round {state.current_round + 1})",
            f"Cash: ${bot.cash:,.2f}",
            f"Total Value: ${bot.total_value:,.2f}",
            f"Return: {((bot.total_value / state.starting_cash) - 1) * 100:+.2f}%",
            "",
            "## Positions:",
        ]

        if bot.positions:
            for pos in bot.positions:
                value = pos.shares * (pos.current_price or pos.avg_cost)
                pnl = pos.unrealized_pnl
                pnl_pct = pos.unrealized_pnl_percent
                portfolio_lines.append(
                    f"- {pos.symbol}: {pos.shares} shares @ ${pos.avg_cost:.2f} avg "
                    f"(current: ${pos.current_price:.2f}, value: ${value:,.2f}, P&L: {pnl_pct:+.2f}%)"
                )
        else:
            portfolio_lines.append("- No positions")

        # Leaderboard context
        portfolio_lines.extend(["", "## Leaderboard:"])
        for i, b in enumerate(state.get_leaderboard(), 1):
            marker = " <- You" if b.id == bot.id else ""
            portfolio_lines.append(
                f"{i}. {b.name}: ${b.total_value:,.2f} ({((b.total_value / state.starting_cash) - 1) * 100:+.2f}%){marker}"
            )

        # Recent trades by this bot
        bot_trades = [t for t in state.recent_trades if t.bot_id == bot.id][-5:]
        if bot_trades:
            portfolio_lines.extend(["", "## Your Recent Trades:"])
            for trade in bot_trades:
                portfolio_lines.append(
                    f"- Round {trade.round}: {trade.side} {trade.shares} {trade.symbol} @ ${trade.price:.2f}"
                )

        portfolio_lines.extend([
            "",
            "---",
            "",
            "Use the MCP tools to check prices, news, and technical indicators.",
            "When ready to trade, output your trades in this exact format:",
            "TRADE: BUY 50 NVDA @ 142.30",
            "TRADE: SELL 100 AAPL @ 189.50",
            "",
            "You may make 0-5 trades this round. Include brief commentary on your reasoning.",
        ])

        return "\n".join(portfolio_lines)

    def run_bot(
        self,
        bot: Bot,
        state: GameState,
        timeout: int = 120,
    ) -> Optional[str]:
        """Run a single bot's trading session.

        Args:
            bot: Bot to run
            state: Current game state
            timeout: Max seconds for bot to respond

        Returns:
            Bot's output text or None on failure
        """
        system_prompt = self.get_system_prompt(bot)
        context = self.build_context(bot, state)

        # Build the full prompt
        full_prompt = f"{context}"

        try:
            # If we have a session ID, resume that session
            cmd = ["claude", "--model", self.model, "--print"]

            if bot.session_id:
                cmd.extend(["--resume", bot.session_id])

            # Add the prompt
            cmd.extend(["--prompt", full_prompt])

            logger.info(f"Running bot {bot.name} (session: {bot.session_id or 'new'})")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path(__file__).parent.parent),
            )

            if result.returncode != 0:
                logger.error(f"Bot {bot.name} failed: {result.stderr}")
                return None

            output = result.stdout

            # Extract session ID from output if present
            # Claude Code outputs session info that we can parse
            # For now, we'll handle session management separately

            return output

        except subprocess.TimeoutExpired:
            logger.error(f"Bot {bot.name} timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Error running bot {bot.name}: {e}")
            return None

    def run_bot_with_mcp(
        self,
        bot: Bot,
        state: GameState,
        mcp_config_path: Optional[str] = None,
        timeout: int = 180,
    ) -> Optional[str]:
        """Run bot with MCP server for market data.

        Args:
            bot: Bot to run
            state: Current game state
            mcp_config_path: Path to MCP config file
            timeout: Max seconds for bot

        Returns:
            Bot's output text or None on failure
        """
        system_prompt = self.get_system_prompt(bot)
        context = self.build_context(bot, state)

        try:
            cmd = ["claude", "--model", self.model, "--print"]

            # Add MCP config if provided
            if mcp_config_path and os.path.exists(mcp_config_path):
                cmd.extend(["--mcp-config", mcp_config_path])

            # Resume session if available
            if bot.session_id:
                cmd.extend(["--resume", bot.session_id])

            # System prompt as initial context
            cmd.extend(["--system-prompt", system_prompt])
            cmd.extend(["--prompt", context])

            logger.info(f"Running bot {bot.name} with MCP tools")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path(__file__).parent.parent),
            )

            if result.returncode != 0:
                logger.error(f"Bot {bot.name} failed: {result.stderr}")
                return None

            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error(f"Bot {bot.name} timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Error running bot {bot.name}: {e}")
            return None
