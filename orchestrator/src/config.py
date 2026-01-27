"""Configuration and environment variables."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    # Cloudflare API
    cf_api_url: str
    cf_api_key: str

    # Finnhub
    finnhub_api_key: str

    # Game settings
    starting_cash: float = 100000.0
    max_trades_per_round: int = 5

    # Claude settings
    claude_model: str = "claude-opus-4-20250514"

    # Bot constraints
    baseline_bots: dict = None
    free_agent_bots: list = None

    def __post_init__(self):
        if self.baseline_bots is None:
            self.baseline_bots = {
                "turtle": {
                    "max_position_pct": 0.05,  # 5% max per position
                    "min_cash_pct": 0.30,  # 30% minimum cash
                    "sp500_only": True,
                },
                "degen": {
                    "max_cash_pct": 0.20,  # Must stay invested
                    "allowed_types": ["leveraged", "meme", "crypto"],
                },
                "boomer": {
                    "min_dividend_yield": 0.01,  # 1% minimum
                    "no_crypto": True,
                    "no_leverage": True,
                },
                "quant": {
                    "requires_technical_citation": True,
                },
                "doomer": {
                    "max_long_equity_pct": 0.30,
                    "requires_hedges": ["SQQQ", "UVXY", "SH", "SPXS", "VXX"],
                },
            }

        if self.free_agent_bots is None:
            self.free_agent_bots = ["gary", "diana", "mel", "vince", "rei"]


def load_config() -> Config:
    """Load configuration from environment variables."""
    cf_api_url = os.environ.get("CF_API_URL")
    cf_api_key = os.environ.get("CF_API_KEY")
    finnhub_api_key = os.environ.get("FINNHUB_API_KEY")

    if not cf_api_url:
        raise ValueError("CF_API_URL environment variable is required")
    if not cf_api_key:
        raise ValueError("CF_API_KEY environment variable is required")
    if not finnhub_api_key:
        raise ValueError("FINNHUB_API_KEY environment variable is required")

    return Config(
        cf_api_url=cf_api_url,
        cf_api_key=cf_api_key,
        finnhub_api_key=finnhub_api_key,
        starting_cash=float(os.environ.get("STARTING_CASH", "100000")),
        max_trades_per_round=int(os.environ.get("MAX_TRADES_PER_ROUND", "5")),
        claude_model=os.environ.get("CLAUDE_MODEL", "claude-opus-4-20250514"),
    )


# S&P 500 symbols (subset for validation)
SP500_SYMBOLS = {
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "BRK.B",
    "UNH", "XOM", "JNJ", "JPM", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV",
    "LLY", "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO", "TMO", "ACN",
    "ABT", "DHR", "NEE", "DIS", "VZ", "ADBE", "WFC", "PM", "CMCSA", "CRM",
    "NKE", "TXN", "RTX", "BMY", "UPS", "QCOM", "HON", "ORCL", "T", "COP",
    "AMGN", "INTC", "IBM", "CAT", "SPGI", "PLD", "LOW", "BA", "GS", "INTU",
    "SBUX", "MDLZ", "AMD", "BLK", "DE", "AXP", "ELV", "GILD", "LMT", "ISRG",
    "ADI", "CVS", "BKNG", "TJX", "VRTX", "REGN", "SYK", "TMUS", "MMC", "PGR",
    "ADP", "ZTS", "CI", "LRCX", "SCHW", "NOW", "MO", "EOG", "BDX", "C",
    "PYPL", "SO", "ETN", "DUK", "SLB", "CB", "ITW", "NOC", "BSX", "EQIX",
    "CME", "APD", "MU", "SNPS", "ATVI", "ICE", "AON", "HUM", "FCX", "CSX",
    "CL", "WM", "GD", "MCK", "USB", "EMR", "PXD", "KLAC", "NSC", "ORLY",
    "SHW", "MAR", "MCO", "PNC", "CDNS", "NXPI", "F", "GM", "ROP", "HCA",
    "AZO", "FDX", "PSA", "TRV", "D", "AEP", "TFC", "KMB", "MRNA", "OXY",
    "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI",  # Major ETFs
}

# Inverse/leveraged ETFs for Doomer
HEDGE_SYMBOLS = {
    "SQQQ", "UVXY", "SH", "SPXS", "VXX", "SDOW", "SPXU", "QID", "SDS", "TZA",
}

# Leveraged/meme stocks for Degen
DEGEN_FAVORITES = {
    "TQQQ", "SOXL", "UPRO", "SPXL", "TECL", "FAS", "LABU", "FNGU", "WEBL",
    "GME", "AMC", "BBBY", "DWAC", "MARA", "RIOT", "COIN", "HOOD", "PLTR",
}
