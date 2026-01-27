"""Position data model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Position:
    """Represents a stock position held by a bot."""

    symbol: str
    shares: float
    avg_cost: float
    current_price: Optional[float] = None

    @property
    def market_value(self) -> float:
        """Calculate current market value of position."""
        price = self.current_price if self.current_price is not None else self.avg_cost
        return self.shares * price

    @property
    def cost_basis(self) -> float:
        """Calculate total cost basis."""
        return self.shares * self.avg_cost

    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized profit/loss."""
        if self.current_price is None:
            return 0.0
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_percent(self) -> float:
        """Calculate unrealized P&L as percentage."""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "shares": self.shares,
            "avg_cost": self.avg_cost,
            "current_price": self.current_price,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        """Create Position from dictionary."""
        return cls(
            symbol=data["symbol"],
            shares=data["shares"],
            avg_cost=data["avg_cost"],
            current_price=data.get("current_price"),
        )
