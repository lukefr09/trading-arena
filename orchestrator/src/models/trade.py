"""Trade data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class Trade:
    """Represents a trade executed by a bot."""

    bot_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    shares: float
    price: float
    round: int
    commentary: Optional[str] = None
    executed_at: Optional[datetime] = None
    id: Optional[int] = None

    @property
    def total_value(self) -> float:
        """Calculate total trade value."""
        return self.shares * self.price

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "bot_id": self.bot_id,
            "symbol": self.symbol,
            "side": self.side,
            "shares": self.shares,
            "price": self.price,
            "round": self.round,
            "commentary": self.commentary,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Trade":
        """Create Trade from dictionary."""
        executed_at = None
        if data.get("executed_at"):
            executed_at = datetime.fromisoformat(data["executed_at"])

        return cls(
            id=data.get("id"),
            bot_id=data["bot_id"],
            symbol=data["symbol"],
            side=data["side"],
            shares=data["shares"],
            price=data["price"],
            round=data["round"],
            commentary=data.get("commentary"),
            executed_at=executed_at,
        )


@dataclass
class ParsedTrade:
    """Represents a trade parsed from bot output (not yet validated/executed)."""

    side: Literal["BUY", "SELL"]
    shares: float
    symbol: str
    price: float

    def to_trade(self, bot_id: str, round_num: int, commentary: Optional[str] = None) -> Trade:
        """Convert to Trade with bot and round info."""
        return Trade(
            bot_id=bot_id,
            symbol=self.symbol,
            side=self.side,
            shares=self.shares,
            price=self.price,
            round=round_num,
            commentary=commentary,
        )
