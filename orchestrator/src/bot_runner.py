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

    # Port assignments for each bot's persistent MCP server
    BOT_PORTS = {
        "turtle": 8081,
        "degen": 8082,
        "boomer": 8083,
        "quant": 8084,
        "doomer": 8085,
        "gary": 8086,
        "diana": 8087,
        "mel": 8088,
        "vince": 8089,
        "rei": 8090,
        "test": 8091,  # Test bot for debugging
    }

    def __init__(
        self,
        model: str = "claude-opus-4-5-20251101",
        cf_api_url: Optional[str] = None,
        cf_api_key: Optional[str] = None,
        finnhub_api_key: Optional[str] = None,
        use_sse: bool = True,  # Use SSE transport by default
    ):
        self.model = model
        self.cf_api_url = cf_api_url or os.environ.get("CF_API_URL", "")
        self.cf_api_key = cf_api_key or os.environ.get("CF_API_KEY", "")
        self.finnhub_api_key = finnhub_api_key or os.environ.get("FINNHUB_API_KEY", "")
        self.use_sse = use_sse

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
        lines = [
            f"# Round {state.current_round + 1}",
            "",
            "Start with `get_round_context()` to see what happened.",
            "",
            "## Tools",
            "",
            "**Info**",
            "- `get_round_context()` — Leaderboard, recent trades, chat, DMs. Start here.",
            "- `get_portfolio()` — Your cash, positions, P&L",
            "- `get_all_portfolios()` — Everyone's positions and P&L",
            "- `get_leaderboard()` — Rankings and performance",
            "- `get_constraints()` — Your trading rules",
            "",
            "**Market Data**",
            "- `get_price(symbol)` — Current price",
            "- `get_prices(symbols)` — Multiple prices at once",
            "- `get_history(symbol, days)` — Historical prices",
            "- `get_dividend(symbol)` — Yield and dividend metrics",
            "- `search_news(symbol)` — Recent headlines",
            "",
            "**Actions**",
            '- `place_order(symbol, qty, side, reason)` — Buy or sell. Side is "buy" or "sell".',
            "- `send_message(content, to?)` — Chat. Leave `to` empty for public, or name a bot to DM.",
            "",
            "---",
            "",
            "0-5 trades per round. Everyone sees everything.",
        ]

        return "\n".join(lines)

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
        if self.use_sse:
            # Use SSE transport - connect to persistent MCP server
            port = self.BOT_PORTS.get(bot.id, 8091)  # Default to test port
            config: dict = {
                "mcpServers": {
                    "trading-arena": {
                        "type": "sse",
                        "url": f"http://localhost:{port}/sse",
                    },
                }
            }
            logger.info(f"Using SSE MCP config for {bot.id} on port {port}")
            return config

        # Fallback: spawn process (original behavior)
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

        config = {
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
        timeout: int = 300,
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
        # Use a fixed path in home directory (temp files in /tmp have issues with MCP loading)
        config_file_path = None
        if mcp_config_path is None:
            mcp_config = self._generate_mcp_config(bot)
            config_file_path = Path.home() / f"mcp-config-{bot.id}.json"
            with open(config_file_path, 'w') as f:
                json.dump(mcp_config, f)
            mcp_config_path = str(config_file_path)
            logger.debug(f"Generated MCP config for {bot.id} at {mcp_config_path}")

        try:
            # Build command - order matters! MCP config before --print, prompt at end
            cmd = ["claude"]

            # Add MCP config first
            if mcp_config_path and os.path.exists(mcp_config_path):
                cmd.extend(["--mcp-config", mcp_config_path])

            # Model and print mode, skip permission prompts (requires non-root user)
            cmd.extend(["--model", self.model, "--print", "--dangerously-skip-permissions"])

            # Resume session if available
            if bot.session_id:
                cmd.extend(["--resume", bot.session_id])

            # System prompt
            cmd.extend(["--system-prompt", system_prompt])

            # Prompt is positional - must be last
            cmd.append(context)

            logger.info(f"Running bot {bot.name} with MCP tools (BOT_ID={bot.id})")
            logger.info(f"MCP config path: {mcp_config_path}")
            logger.info(f"Command: {' '.join(cmd)}")

            # Log MCP config contents
            if mcp_config_path:
                with open(mcp_config_path, 'r') as f:
                    logger.info(f"MCP config contents: {f.read()}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path.home()),  # Run from home directory where MCP config is
            )

            if result.returncode != 0:
                logger.error(f"Bot {bot.name} failed with code {result.returncode}")
                logger.error(f"STDERR: {result.stderr}")
                logger.error(f"STDOUT: {result.stdout}")
                return None

            # Log stderr even on success - might show MCP issues
            if result.stderr:
                logger.warning(f"Bot {bot.name} stderr: {result.stderr}")

            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error(f"Bot {bot.name} timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Error running bot {bot.name}: {e}")
            return None
        finally:
            # Clean up config file
            if config_file_path is not None:
                try:
                    os.unlink(config_file_path)
                except OSError:
                    pass
