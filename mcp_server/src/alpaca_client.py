"""Alpaca API client for paper trading."""

import os
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class Position:
    """A position in the portfolio."""

    symbol: str
    qty: float
    market_value: float
    avg_entry_price: float
    current_price: float
    unrealized_pl: float
    unrealized_plpc: float  # Percentage


@dataclass
class Portfolio:
    """Portfolio state from Alpaca."""

    cash: float
    equity: float
    buying_power: float
    positions: list[Position]

    @property
    def positions_value(self) -> float:
        """Total value of all positions."""
        return sum(p.market_value for p in self.positions)


@dataclass
class OrderResult:
    """Result of an order placement."""

    success: bool
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    qty: Optional[float] = None
    side: Optional[str] = None
    filled_avg_price: Optional[float] = None
    status: Optional[str] = None
    error: Optional[str] = None


class AlpacaClient:
    """Client for Alpaca paper trading API."""

    BASE_URL = "https://paper-api.alpaca.markets"

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """Initialize Alpaca client.

        Args:
            api_key: Alpaca API key (or ALPACA_API_KEY env var)
            secret_key: Alpaca secret key (or ALPACA_SECRET_KEY env var)
        """
        self.api_key = api_key or os.environ.get("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.environ.get("ALPACA_SECRET_KEY", "")

        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API credentials required")

        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.secret_key,
            },
            timeout=30.0,
        )

    def close(self) -> None:
        """Close HTTP client."""
        self._client.close()

    def get_account(self) -> dict:
        """Get account information."""
        response = self._client.get("/v2/account")
        response.raise_for_status()
        return response.json()

    def get_positions(self) -> list[dict]:
        """Get all open positions."""
        response = self._client.get("/v2/positions")
        response.raise_for_status()
        return response.json()

    def get_portfolio(self) -> Portfolio:
        """Get full portfolio state.

        Returns:
            Portfolio with cash, equity, and positions
        """
        account = self.get_account()
        positions_data = self.get_positions()

        positions = []
        for p in positions_data:
            positions.append(
                Position(
                    symbol=p["symbol"],
                    qty=float(p["qty"]),
                    market_value=float(p["market_value"]),
                    avg_entry_price=float(p["avg_entry_price"]),
                    current_price=float(p["current_price"]),
                    unrealized_pl=float(p["unrealized_pl"]),
                    unrealized_plpc=float(p["unrealized_plpc"]),
                )
            )

        return Portfolio(
            cash=float(account["cash"]),
            equity=float(account["equity"]),
            buying_power=float(account["buying_power"]),
            positions=positions,
        )

    def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
    ) -> OrderResult:
        """Place an order.

        Args:
            symbol: Stock symbol
            qty: Number of shares
            side: "buy" or "sell"
            order_type: "market", "limit", etc.
            time_in_force: "day", "gtc", etc.

        Returns:
            OrderResult with success status and order details
        """
        try:
            response = self._client.post(
                "/v2/orders",
                json={
                    "symbol": symbol.upper(),
                    "qty": str(qty),
                    "side": side.lower(),
                    "type": order_type,
                    "time_in_force": time_in_force,
                },
            )
            response.raise_for_status()
            order = response.json()

            return OrderResult(
                success=True,
                order_id=order.get("id"),
                symbol=order.get("symbol"),
                qty=float(order.get("qty", 0)),
                side=order.get("side"),
                filled_avg_price=float(order.get("filled_avg_price") or 0),
                status=order.get("status"),
            )

        except httpx.HTTPStatusError as e:
            error_detail = "Unknown error"
            try:
                error_body = e.response.json()
                error_detail = error_body.get("message", str(error_body))
            except Exception:
                error_detail = e.response.text or str(e)

            return OrderResult(
                success=False,
                error=f"Alpaca API error: {error_detail}",
            )
        except Exception as e:
            return OrderResult(
                success=False,
                error=f"Order failed: {str(e)}",
            )

    def get_last_trade(self, symbol: str) -> Optional[float]:
        """Get last trade price for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Last trade price or None
        """
        try:
            # Use data API for latest trade
            response = self._client.get(
                f"/v2/stocks/{symbol.upper()}/trades/latest",
                headers={
                    "APCA-API-KEY-ID": self.api_key,
                    "APCA-API-SECRET-KEY": self.secret_key,
                },
            )
            response.raise_for_status()
            data = response.json()
            return float(data.get("trade", {}).get("p", 0))
        except Exception:
            return None

    def is_market_open(self) -> bool:
        """Check if the market is currently open."""
        try:
            response = self._client.get("/v2/clock")
            response.raise_for_status()
            clock = response.json()
            return clock.get("is_open", False)
        except Exception:
            return False
