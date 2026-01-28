"""Run bot trading sessions using Claude Code CLI."""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .models import Bot, GameState

logger = logging.getLogger(__name__)

# Path to prompts directory
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MCP_SERVER_DIR = Path(__file__).parent.parent.parent / "mcp_server"


class BotRunner:
    """Runs bot trading sessions via Claude Code CLI."""

    def __init__(
        self,
        model: str = "claude-opus-4-20250514",
        cf_api_url: Optional[str] = None,
        cf_api_key: Optional[str] = None,
        finnhub_api_key: Optional[str] = None,
    ):
        self.model = model
        self.cf_api_url = cf_api_url or os.environ.get("CF_API_URL", "")
        self.cf_api_key = cf_api_key or os.environ.get("CF_API_KEY", "")
        self.finnhub_api_key = finnhub_api_key or os.environ.get("FINNHUB_API_KEY", "")

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
            Context string with tools overview and workflow
        """
        portfolio_lines = [
            f"# Trading Round {state.current_round + 1}",
            "",
            "## Your MCP Tools",
            "",
            "You have access to the **trading-arena** MCP server with these tools:",
            "",
            "### Research Tools",
            "- `get_price(symbol)` - Get real-time price for a stock",
            "- `get_prices(symbols)` - Get prices for multiple stocks",
            "- `get_technicals(symbol, indicator)` - Get RSI, MACD, SMA, etc.",
            "- `get_history(symbol, days)` - Get historical price data",
            "- `search_news(symbol)` - Get recent news",
            "- `get_dividend(symbol)` - Get dividend yield and metrics",
            "",
            "### Trading Tools",
            "- `get_portfolio()` - Get your cash, equity, and all positions with P&L",
            "- `get_constraints()` - See your trading rules",
            "- `place_order(symbol, qty, side, reason)` - **Execute a trade** (validates constraints first!)",
            "- `get_leaderboard()` - See competition standings",
            "",
            "### Social Tools (THIS IS A COMPETITION!)",
            "- `get_round_context()` - **START HERE!** See leaderboard, all trades, chat, and DMs to you",
            "- `get_all_portfolios()` - See everyone's positions and P&L",
            "- `get_messages()` - See recent chat messages",
            "- `send_message(content, to?)` - Talk trash, react to trades, or DM a rival",
            "",
            "## How to Play",
            "",
            "**1. START with `get_round_context()`** - See what happened, who's winning, what people said",
            "",
            "**2. React in character!**",
            "- Someone made a big trade? Comment on it!",
            "- Rival passed you in rankings? Talk trash!",
            "- Got a DM? Respond!",
            "- Your trade got rejected? Complain about your constraints!",
            "",
            "**3. Make your trades (0-5 per round)**",
            "- `place_order(symbol, qty, side, reason)` handles everything",
            '- Returns `{"status": "filled", ...}` or `{"status": "rejected", "reason": "..."}`',
            "",
            "**4. Comment on your own trades!**",
            "- After trading, `send_message()` to explain your moves or taunt rivals",
            "",
            "## Remember",
            "- This is a COMPETITION. Other bots can see EVERYTHING you do.",
            "- Your personality matters. Stay in character!",
            "- Rejected trades are FUNNY. React to them!",
            "",
            "---",
        ]

        return "\n".join(portfolio_lines)

    def _generate_mcp_config(self, bot: Bot) -> dict:
        """Generate MCP config with unified Trading Arena server.

        The trading-arena MCP server handles EVERYTHING:
        - Market data (via Finnhub)
        - Constraint validation
        - Order execution (via Alpaca)
        - Trade recording (via Workers API)

        Args:
            bot: The bot to generate config for

        Returns:
            MCP config dict
        """
        env = {
            "BOT_ID": bot.id,
            "CF_API_URL": self.cf_api_url,
            "CF_API_KEY": self.cf_api_key,
            "FINNHUB_API_KEY": self.finnhub_api_key,
        }

        # Add Alpaca credentials if available
        if bot.alpaca_api_key and bot.alpaca_secret_key:
            env["ALPACA_API_KEY"] = bot.alpaca_api_key
            env["ALPACA_SECRET_KEY"] = bot.alpaca_secret_key
        else:
            logger.warning(f"Bot {bot.id} has no Alpaca credentials - trading will be unavailable")

        config: dict = {
            "mcpServers": {
                "trading-arena": {
                    "command": "python3",
                    "args": ["-m", "mcp_server.src.server"],
                    "cwd": str(MCP_SERVER_DIR.parent),
                    "env": env,
                },
            }
        }

        return config

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
        """Run bot with MCP servers for market data and trading.

        Args:
            bot: Bot to run
            state: Current game state
            mcp_config_path: Path to MCP config file (if None, generates per-bot config)
            timeout: Max seconds for bot

        Returns:
            Bot's output text or None on failure
        """
        system_prompt = self.get_system_prompt(bot)
        context = self.build_context(bot, state)

        # Generate per-bot MCP config if not provided
        config_file = None
        if mcp_config_path is None:
            mcp_config = self._generate_mcp_config(bot)
            config_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False,
            )
            json.dump(mcp_config, config_file)
            config_file.close()
            mcp_config_path = config_file.name
            logger.debug(f"Generated MCP config for {bot.id} at {mcp_config_path}")

        try:
            cmd = ["claude", "--model", self.model, "--print"]

            # Add MCP config
            if mcp_config_path and os.path.exists(mcp_config_path):
                cmd.extend(["--mcp-config", mcp_config_path])

            # Resume session if available
            if bot.session_id:
                cmd.extend(["--resume", bot.session_id])

            # System prompt as initial context
            cmd.extend(["--system-prompt", system_prompt])
            cmd.extend(["--prompt", context])

            logger.info(f"Running bot {bot.name} with MCP tools (BOT_ID={bot.id})")

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
        finally:
            # Clean up temp config file
            if config_file is not None:
                try:
                    os.unlink(config_file.name)
                except OSError:
                    pass
