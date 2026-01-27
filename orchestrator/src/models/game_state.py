"""Game state data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from .bot import Bot
from .trade import Trade


@dataclass
class GameState:
    """Represents the full game state."""

    status: Literal["running", "paused"] = "paused"
    starting_cash: float = 100000.0
    current_round: int = 0
    bots: list[Bot] = field(default_factory=list)
    recent_trades: list[Trade] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def get_bot(self, bot_id: str) -> Optional[Bot]:
        """Get bot by ID."""
        for bot in self.bots:
            if bot.id == bot_id:
                return bot
        return None

    def get_enabled_bots(self) -> list[Bot]:
        """Get all enabled bots."""
        return [bot for bot in self.bots if bot.enabled]

    def get_leaderboard(self) -> list[Bot]:
        """Get bots sorted by total value (descending)."""
        return sorted(self.bots, key=lambda b: b.total_value, reverse=True)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status,
            "starting_cash": self.starting_cash,
            "current_round": self.current_round,
            "bots": [b.to_dict() for b in self.bots],
            "recent_trades": [t.to_dict() for t in self.recent_trades],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        """Create GameState from dictionary."""
        bots = [Bot.from_dict(b) for b in data.get("bots", [])]
        trades = [Trade.from_dict(t) for t in data.get("recent_trades", [])]

        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            status=data.get("status", "paused"),
            starting_cash=data.get("starting_cash", 100000.0),
            current_round=data.get("current_round", 0),
            bots=bots,
            recent_trades=trades,
            created_at=created_at,
            updated_at=updated_at,
        )
