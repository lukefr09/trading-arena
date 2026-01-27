"""Bot data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from .position import Position


@dataclass
class Bot:
    """Represents a trading bot in the arena."""

    id: str
    name: str
    type: Literal["baseline", "free_agent"]
    cash: float
    total_value: float
    positions: list[Position] = field(default_factory=list)
    session_id: Optional[str] = None
    last_commentary: Optional[str] = None
    enabled: bool = True
    updated_at: Optional[datetime] = None

    @property
    def position_value(self) -> float:
        """Calculate total value of all positions."""
        return sum(p.market_value for p in self.positions)

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        for pos in self.positions:
            if pos.symbol == symbol:
                return pos
        return None

    def calculate_total_value(self) -> float:
        """Recalculate total portfolio value."""
        self.total_value = self.cash + self.position_value
        return self.total_value

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "cash": self.cash,
            "total_value": self.total_value,
            "positions": [p.to_dict() for p in self.positions],
            "session_id": self.session_id,
            "last_commentary": self.last_commentary,
            "enabled": self.enabled,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Bot":
        """Create Bot from dictionary."""
        positions = [Position.from_dict(p) for p in data.get("positions", [])]
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            id=data["id"],
            name=data["name"],
            type=data["type"],
            cash=data["cash"],
            total_value=data["total_value"],
            positions=positions,
            session_id=data.get("session_id"),
            last_commentary=data.get("last_commentary"),
            enabled=data.get("enabled", True),
            updated_at=updated_at,
        )
