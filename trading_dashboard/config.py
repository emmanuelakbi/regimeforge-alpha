"""
Configuration management for RegimeForge Alpha
Loads credentials from environment variables for security
"""
import os
from dataclasses import dataclass
from typing import Dict

# =============================================================================
# TRADING CONSTANTS
# =============================================================================

# Signal thresholds
STRONG_SUPPORT_THRESHOLD = 20
SUPPORT_THRESHOLD = 35
STRONG_RESISTANCE_THRESHOLD = 80
RESISTANCE_THRESHOLD = 65

# Signal scores
STRONG_SIGNAL_SCORE = 4
MODERATE_SIGNAL_SCORE = 2
WEAK_SIGNAL_SCORE = 1

# Volatility thresholds
HIGH_VOLATILITY_THRESHOLD = 4
LOW_VOLATILITY_THRESHOLD = 1
EXTREME_VOLATILITY_THRESHOLD = 5

# Trend thresholds
BULL_TREND_THRESHOLD = 0.6
BEAR_TREND_THRESHOLD = -0.6
RSI_BULL_THRESHOLD = 55
RSI_BEAR_THRESHOLD = 45

# Price change thresholds
STRONG_OVERSOLD_THRESHOLD = -3
MILD_OVERSOLD_THRESHOLD = -1
STRONG_OVERBOUGHT_THRESHOLD = 3
MILD_OVERBOUGHT_THRESHOLD = 1

# Confidence bounds
MAX_CONFIDENCE = 0.92
MIN_CONFIDENCE = 0.35
BASE_CONFIDENCE = 0.55
CONFIDENCE_INCREMENT = 0.04

# Trailing take-profit activation threshold
TRAILING_ACTIVATION_THRESHOLD = 0.3

# =============================================================================
# SUPPORTED TRADING PAIRS
# =============================================================================

SUPPORTED_COINS: Dict[str, str] = {
    "BTC": "cmt_btcusdt",
    "ETH": "cmt_ethusdt",
    "SOL": "cmt_solusdt",
    "XRP": "cmt_xrpusdt",
    "BNB": "cmt_bnbusdt",
    "ADA": "cmt_adausdt",
    "DOGE": "cmt_dogeusdt",
    "LTC": "cmt_ltcusdt"
}

# Decimal precision for each coin (WEEX requirements)
# BTC stepSize is 0.001 (3 decimals), not 0.0001
COIN_DECIMALS: Dict[str, int] = {
    "BTC": 3,
    "ETH": 3,
    "SOL": 2,
    "XRP": 1,
    "BNB": 3,
    "ADA": 1,
    "DOGE": 0,
    "LTC": 3
}

# =============================================================================
# API CONFIGURATION
# =============================================================================

@dataclass
class APIConfig:
    """WEEX API configuration loaded from environment"""
    api_key: str
    secret_key: str
    passphrase: str
    base_url: str = "https://api-contract.weex.com"
    
    @classmethod
    def from_env(cls) -> "APIConfig":
        """Load API configuration from environment variables"""
        api_key = os.environ.get("WEEX_API_KEY")
        secret_key = os.environ.get("WEEX_SECRET_KEY")
        passphrase = os.environ.get("WEEX_PASSPHRASE")
        
        if not all([api_key, secret_key, passphrase]):
            raise ValueError(
                "Missing required WEEX API credentials. "
                "Set WEEX_API_KEY, WEEX_SECRET_KEY, and WEEX_PASSPHRASE environment variables."
            )
        
        return cls(
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase
        )
    
    @classmethod
    def from_values(cls, api_key: str, secret_key: str, passphrase: str) -> "APIConfig":
        """Create config from explicit values (for testing)"""
        return cls(api_key=api_key, secret_key=secret_key, passphrase=passphrase)


# =============================================================================
# DEFAULT AUTOMATION SETTINGS
# =============================================================================

DEFAULT_AUTOMATION_SETTINGS = {
    "enabled": False,
    "auto_entry": False,
    "auto_take_profit": False,
    "auto_stop_loss": False,
    "margin_usdt": 30.0,
    "leverage": 20,
    "min_confidence": 0.65,
    "stop_loss_pct": 2.0,
    "max_trades_per_hour": 3,
    "cooldown_minutes": 5,
    "daily_loss_limit_usdt": 20.0,
    "trades_this_hour": 0,
    "hour_start": 0,
    "last_trade_time": 0,
    "daily_pnl": 0.0,
    "day_start": 0,
    "last_auto_action": ""
}

DEFAULT_TP_SETTINGS = {
    "enabled": False,
    "mode": "fixed",
    "fixed_target_pct": 1.5,
    "trailing_drop_pct": 0.5,
    "peak_profit_pct": 0.0,
    "entry_price": 0.0,
    "position_side": None
}

MODEL_VERSION = "RegimeForge-Alpha-v1.0.0"
