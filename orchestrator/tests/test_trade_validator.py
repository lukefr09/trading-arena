"""Tests for trade validator."""

import pytest

from orchestrator.src.config import Config
from orchestrator.src.models import Bot, ParsedTrade, Position
from orchestrator.src.trade_validator import TradeValidator, validate_quant_commentary


@pytest.fixture
def config():
    return Config(
        cf_api_url="http://localhost:8787",
        cf_api_key="test-key",
        finnhub_api_key="test-key",
    )


@pytest.fixture
def validator(config):
    return TradeValidator(config)


class TestBasicValidation:
    def test_buy_with_sufficient_cash(self, validator):
        bot = Bot(
            id="test",
            name="Test",
            type="free_agent",
            cash=10000,
            total_value=10000,
        )
        trade = ParsedTrade(side="BUY", shares=10, symbol="AAPL", price=150)
        prices = {"AAPL": 150}

        result = validator.validate(bot, trade, prices)
        assert result.valid

    def test_buy_with_insufficient_cash(self, validator):
        bot = Bot(
            id="test",
            name="Test",
            type="free_agent",
            cash=1000,
            total_value=1000,
        )
        trade = ParsedTrade(side="BUY", shares=10, symbol="AAPL", price=150)
        prices = {"AAPL": 150}

        result = validator.validate(bot, trade, prices)
        assert not result.valid
        assert "Insufficient cash" in result.rejection_reason

    def test_sell_with_sufficient_shares(self, validator):
        bot = Bot(
            id="test",
            name="Test",
            type="free_agent",
            cash=10000,
            total_value=25000,
            positions=[Position(symbol="AAPL", shares=100, avg_cost=140, current_price=150)],
        )
        trade = ParsedTrade(side="SELL", shares=50, symbol="AAPL", price=150)
        prices = {"AAPL": 150}

        result = validator.validate(bot, trade, prices)
        assert result.valid

    def test_sell_with_insufficient_shares(self, validator):
        bot = Bot(
            id="test",
            name="Test",
            type="free_agent",
            cash=10000,
            total_value=25000,
            positions=[Position(symbol="AAPL", shares=10, avg_cost=140, current_price=150)],
        )
        trade = ParsedTrade(side="SELL", shares=50, symbol="AAPL", price=150)
        prices = {"AAPL": 150}

        result = validator.validate(bot, trade, prices)
        assert not result.valid
        assert "Insufficient shares" in result.rejection_reason

    def test_price_slippage_tolerance(self, validator):
        bot = Bot(
            id="test",
            name="Test",
            type="free_agent",
            cash=10000,
            total_value=10000,
        )
        trade = ParsedTrade(side="BUY", shares=10, symbol="AAPL", price=151)  # 0.67% diff
        prices = {"AAPL": 150}

        result = validator.validate(bot, trade, prices)
        assert result.valid

    def test_price_too_far_from_market(self, validator):
        bot = Bot(
            id="test",
            name="Test",
            type="free_agent",
            cash=10000,
            total_value=10000,
        )
        trade = ParsedTrade(side="BUY", shares=10, symbol="AAPL", price=160)  # 6.67% diff
        prices = {"AAPL": 150}

        result = validator.validate(bot, trade, prices)
        assert not result.valid
        assert "too far from current" in result.rejection_reason


class TestTurtleConstraints:
    def test_sp500_only(self, validator):
        bot = Bot(
            id="turtle",
            name="Turtle",
            type="baseline",
            cash=100000,
            total_value=100000,
        )
        trade = ParsedTrade(side="BUY", shares=100, symbol="GME", price=20)  # Not in S&P 500
        prices = {"GME": 20}

        result = validator.validate(bot, trade, prices)
        assert not result.valid
        assert "not in S&P 500" in result.rejection_reason

    def test_max_position_size(self, validator):
        bot = Bot(
            id="turtle",
            name="Turtle",
            type="baseline",
            cash=100000,
            total_value=100000,
        )
        trade = ParsedTrade(side="BUY", shares=100, symbol="AAPL", price=100)  # 10% of portfolio
        prices = {"AAPL": 100}

        result = validator.validate(bot, trade, prices)
        assert not result.valid
        assert "5%" in result.rejection_reason

    def test_min_cash_requirement(self, validator):
        bot = Bot(
            id="turtle",
            name="Turtle",
            type="baseline",
            cash=35000,
            total_value=100000,
        )
        trade = ParsedTrade(side="BUY", shares=10, symbol="AAPL", price=1000)  # Would leave 25% cash
        prices = {"AAPL": 1000}

        result = validator.validate(bot, trade, prices)
        assert not result.valid
        assert "30%" in result.rejection_reason


class TestDegenConstraints:
    def test_max_cash_on_sell(self, validator):
        bot = Bot(
            id="degen",
            name="Degen",
            type="baseline",
            cash=15000,
            total_value=100000,
            positions=[Position(symbol="TQQQ", shares=1000, avg_cost=85, current_price=85)],
        )
        trade = ParsedTrade(side="SELL", shares=200, symbol="TQQQ", price=85)  # Would put cash at 32%
        prices = {"TQQQ": 85}

        result = validator.validate(bot, trade, prices)
        assert not result.valid
        assert "20%" in result.rejection_reason


class TestQuantCommentary:
    def test_rsi_mention(self):
        assert validate_quant_commentary("RSI at 28 showing oversold conditions")

    def test_macd_mention(self):
        assert validate_quant_commentary("MACD crossing bullish, time to buy")

    def test_moving_average_mention(self):
        assert validate_quant_commentary("Price above 50-day moving average")

    def test_no_indicator(self):
        assert not validate_quant_commentary("I think this stock will go up")

    def test_none_commentary(self):
        assert not validate_quant_commentary(None)
