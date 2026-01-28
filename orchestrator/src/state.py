"""State management - load/save game state via Cloudflare Workers API."""

import json
import logging
from typing import Optional

import httpx

from .config import Config
from .models import Bot, GameState, Position, Trade

logger = logging.getLogger(__name__)


class StateManager:
    """Manages game state persistence via Cloudflare Workers API."""

    def __init__(self, config: Config):
        self.config = config
        self._client = httpx.Client(timeout=30.0)

    def _headers(self) -> dict:
        """Get request headers with API key."""
        return {
            "Authorization": f"Bearer {self.config.cf_api_key}",
            "Content-Type": "application/json",
        }

    def load_state(self) -> GameState:
        """Load full game state from API."""
        try:
            response = self._client.get(
                f"{self.config.cf_api_url}/api/state",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            return GameState.from_dict(data)
        except httpx.HTTPError as e:
            logger.error(f"Failed to load state: {e}")
            raise

    def save_state(self, state: GameState) -> bool:
        """Save full game state to API."""
        try:
            response = self._client.post(
                f"{self.config.cf_api_url}/api/state",
                headers=self._headers(),
                json=state.to_dict(),
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to save state: {e}")
            raise

    def update_bot(self, bot: Bot) -> bool:
        """Update a single bot's state."""
        try:
            response = self._client.put(
                f"{self.config.cf_api_url}/api/bot/{bot.id}",
                headers=self._headers(),
                json=bot.to_dict(),
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to update bot {bot.id}: {e}")
            raise

    def record_trade(self, trade: Trade) -> bool:
        """Record a new trade."""
        try:
            response = self._client.post(
                f"{self.config.cf_api_url}/api/trades",
                headers=self._headers(),
                json=trade.to_dict(),
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to record trade: {e}")
            raise

    def record_trades(self, trades: list[Trade]) -> bool:
        """Record multiple trades at once."""
        try:
            response = self._client.post(
                f"{self.config.cf_api_url}/api/trades/batch",
                headers=self._headers(),
                json={"trades": [t.to_dict() for t in trades]},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to record trades: {e}")
            raise

    def increment_round(self) -> int:
        """Increment the round counter and return new round number."""
        try:
            response = self._client.post(
                f"{self.config.cf_api_url}/api/round/increment",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("round", 0)
        except httpx.HTTPError as e:
            logger.error(f"Failed to increment round: {e}")
            raise

    def push_update(self, update_type: str, data: dict) -> bool:
        """Push real-time update to WebSocket clients."""
        try:
            response = self._client.post(
                f"{self.config.cf_api_url}/api/broadcast",
                headers=self._headers(),
                json={"type": update_type, "data": data},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.warning(f"Failed to push update: {e}")
            return False

    def get_bot_credentials(self, bot_id: str) -> tuple[str, str] | None:
        """Fetch Alpaca credentials for a bot.

        Returns:
            Tuple of (api_key, secret_key) or None if not available
        """
        try:
            response = self._client.get(
                f"{self.config.cf_api_url}/api/bot/{bot_id}/credentials",
                headers=self._headers(),
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("alpaca_api_key"), data.get("alpaca_secret_key")
            return None
        except httpx.HTTPError as e:
            logger.warning(f"Failed to get credentials for bot {bot_id}: {e}")
            return None

    def close(self):
        """Close HTTP client."""
        self._client.close()
