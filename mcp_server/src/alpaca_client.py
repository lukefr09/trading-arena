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

    def get_crypto_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a crypto symbol (e.g., BTC/USD).

        Args:
            symbol: Crypto pair (e.g., BTC/USD, ETH/USD)

        Returns:
            Latest price or None
        """
        try:
            # Alpaca crypto data API
            data_client = httpx.Client(
                base_url="https://data.alpaca.markets",
                headers={
                    "APCA-API-KEY-ID": self.api_key,
                    "APCA-API-SECRET-KEY": self.secret_key,
                },
                timeout=10.0,
            )
            # Use query param with original symbol format (BTC/USD)
            response = data_client.get(f"/v1beta3/crypto/us/latest/trades?symbols={symbol}")
            response.raise_for_status()
            data = response.json()
            data_client.close()
            # Response is {"trades": {"BTC/USD": {"p": 12345.67, ...}}}
            trades = data.get("trades", {})
            trade = trades.get(symbol, {})
            return float(trade.get("p", 0))
        except Exception:
            return None

    def get_stock_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a stock symbol.

        Args:
            symbol: Stock symbol (e.g., AAPL, SPY)

        Returns:
            Latest price or None
        """
        try:
            data_client = httpx.Client(
                base_url="https://data.alpaca.markets",
                headers={
                    "APCA-API-KEY-ID": self.api_key,
                    "APCA-API-SECRET-KEY": self.secret_key,
                },
                timeout=10.0,
            )
            response = data_client.get(f"/v2/stocks/{symbol.upper()}/trades/latest")
            response.raise_for_status()
            data = response.json()
            data_client.close()
            return float(data.get("trade", {}).get("p", 0))
        except Exception:
            return None

    def get_options_chain(
        self,
        underlying_symbol: str,
        expiration_date: Optional[str] = None,
        option_type: Optional[str] = None,
        strike_price_gte: Optional[float] = None,
        strike_price_lte: Optional[float] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get options contracts for an underlying symbol.

        Args:
            underlying_symbol: The stock symbol (e.g., AAPL, SPY)
            expiration_date: Filter by expiration (YYYY-MM-DD)
            option_type: Filter by 'call' or 'put'
            strike_price_gte: Min strike price
            strike_price_lte: Max strike price
            limit: Max contracts to return (default 50)

        Returns:
            List of option contracts with symbol, strike, expiration, type, etc.
        """
        try:
            params = {
                "underlying_symbols": underlying_symbol.upper(),
                "limit": limit,
                "status": "active",
            }
            if expiration_date:
                params["expiration_date"] = expiration_date
            if option_type:
                params["type"] = option_type.lower()
            if strike_price_gte:
                params["strike_price_gte"] = str(strike_price_gte)
            if strike_price_lte:
                params["strike_price_lte"] = str(strike_price_lte)

            response = self._client.get("/v2/options/contracts", params=params)
            response.raise_for_status()
            data = response.json()

            contracts = []
            for c in data.get("option_contracts", []):
                contracts.append({
                    "symbol": c.get("symbol"),
                    "name": c.get("name"),
                    "underlying": c.get("underlying_symbol"),
                    "type": c.get("type"),
                    "strike": float(c.get("strike_price", 0)),
                    "expiration": c.get("expiration_date"),
                    "tradable": c.get("tradable", False),
                    "open_interest": c.get("open_interest"),
                })
            return contracts

        except Exception as e:
            return [{"error": str(e)}]

    def get_option_quote(self, option_symbol: str) -> Optional[dict]:
        """Get latest quote for an options contract.

        Args:
            option_symbol: OCC symbol (e.g., AAPL240119C00100000)

        Returns:
            Quote with bid, ask, last price
        """
        try:
            data_client = httpx.Client(
                base_url="https://data.alpaca.markets",
                headers={
                    "APCA-API-KEY-ID": self.api_key,
                    "APCA-API-SECRET-KEY": self.secret_key,
                },
                timeout=10.0,
            )
            response = data_client.get(
                f"/v1beta1/options/quotes/latest",
                params={"symbols": option_symbol}
            )
            response.raise_for_status()
            data = response.json()
            data_client.close()

            quote = data.get("quotes", {}).get(option_symbol, {})
            return {
                "symbol": option_symbol,
                "bid": float(quote.get("bp", 0)),
                "ask": float(quote.get("ap", 0)),
                "bid_size": quote.get("bs", 0),
                "ask_size": quote.get("as", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def place_options_order(
        self,
        option_symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        limit_price: Optional[float] = None,
    ) -> OrderResult:
        """Place an options order.

        Args:
            option_symbol: OCC symbol (e.g., AAPL240119C00100000)
            qty: Number of contracts (must be whole number)
            side: "buy" or "sell"
            order_type: "market" or "limit"
            limit_price: Required if order_type is "limit"

        Returns:
            OrderResult with success status and order details
        """
        try:
            order_data = {
                "symbol": option_symbol.upper(),
                "qty": str(int(qty)),  # Must be whole number
                "side": side.lower(),
                "type": order_type,
                "time_in_force": "day",  # Options must be day orders
            }
            if order_type == "limit" and limit_price:
                order_data["limit_price"] = str(limit_price)

            response = self._client.post("/v2/orders", json=order_data)
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
                error=f"Options order failed: {error_detail}",
            )
        except Exception as e:
            return OrderResult(
                success=False,
                error=f"Options order failed: {str(e)}",
            )
