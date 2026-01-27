"""Tests for trade parser."""

import pytest

from orchestrator.src.trade_parser import (
    extract_commentary,
    parse_trades,
    validate_trade_format,
)


class TestParseTrades:
    def test_single_buy(self):
        output = "TRADE: BUY 50 NVDA @ 142.30"
        trades = parse_trades(output)
        assert len(trades) == 1
        assert trades[0].side == "BUY"
        assert trades[0].shares == 50
        assert trades[0].symbol == "NVDA"
        assert trades[0].price == 142.30

    def test_single_sell(self):
        output = "TRADE: SELL 100 AAPL @ 189.50"
        trades = parse_trades(output)
        assert len(trades) == 1
        assert trades[0].side == "SELL"
        assert trades[0].shares == 100
        assert trades[0].symbol == "AAPL"
        assert trades[0].price == 189.50

    def test_multiple_trades(self):
        output = """
        Looking at the market today...
        TRADE: BUY 50 NVDA @ 142.30
        TRADE: SELL 100 AAPL @ 189.50
        TRADE: BUY 25 MSFT @ 420.00
        That's my thesis.
        """
        trades = parse_trades(output)
        assert len(trades) == 3
        assert trades[0].symbol == "NVDA"
        assert trades[1].symbol == "AAPL"
        assert trades[2].symbol == "MSFT"

    def test_case_insensitive(self):
        output = "trade: buy 50 nvda @ 142.30"
        trades = parse_trades(output)
        assert len(trades) == 1
        assert trades[0].side == "BUY"
        assert trades[0].symbol == "NVDA"

    def test_decimal_shares(self):
        output = "TRADE: BUY 50.5 SPY @ 500.00"
        trades = parse_trades(output)
        assert len(trades) == 1
        assert trades[0].shares == 50.5

    def test_no_trades(self):
        output = "I'm not making any trades this round."
        trades = parse_trades(output)
        assert len(trades) == 0

    def test_invalid_format_ignored(self):
        output = """
        TRADE: BUY NVDA @ 142.30
        TRADE: BUY 50 NVDA
        TRADE BUY 50 NVDA @ 142.30
        TRADE: BUY 50 NVDA @ 142.30
        """
        trades = parse_trades(output)
        assert len(trades) == 1  # Only the valid one

    def test_zero_shares_rejected(self):
        output = "TRADE: BUY 0 NVDA @ 142.30"
        trades = parse_trades(output)
        assert len(trades) == 0

    def test_zero_price_rejected(self):
        output = "TRADE: BUY 50 NVDA @ 0"
        trades = parse_trades(output)
        assert len(trades) == 0


class TestExtractCommentary:
    def test_simple_commentary(self):
        output = """
        TRADE: BUY 50 NVDA @ 142.30
        This is my reasoning for the trade.
        """
        commentary = extract_commentary(output)
        assert "reasoning" in commentary.lower()

    def test_no_commentary(self):
        output = "TRADE: BUY 50 NVDA @ 142.30"
        commentary = extract_commentary(output)
        assert commentary is None

    def test_truncates_long_commentary(self):
        output = """
        TRADE: BUY 50 NVDA @ 142.30
        """ + "A" * 1000
        commentary = extract_commentary(output)
        assert len(commentary) <= 503  # 500 + "..."

    def test_filters_trade_lines(self):
        output = """
        TRADE: BUY 50 NVDA @ 142.30
        I'm buying NVDA because of AI demand.
        TRADE: SELL 100 AAPL @ 189.50
        Selling AAPL to rebalance.
        """
        commentary = extract_commentary(output)
        assert "TRADE:" not in commentary


class TestValidateTradeFormat:
    def test_valid_buy(self):
        assert validate_trade_format("TRADE: BUY 50 NVDA @ 142.30")

    def test_valid_sell(self):
        assert validate_trade_format("TRADE: SELL 100 AAPL @ 189.50")

    def test_invalid_missing_price(self):
        assert not validate_trade_format("TRADE: BUY 50 NVDA")

    def test_invalid_missing_shares(self):
        assert not validate_trade_format("TRADE: BUY NVDA @ 142.30")

    def test_invalid_no_colon(self):
        assert not validate_trade_format("TRADE BUY 50 NVDA @ 142.30")
