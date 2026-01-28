"""
Data models for RegimeForge Alpha
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timezone


@dataclass
class MarketData:
    """Market data snapshot for a trading pair"""
    price: float
    high_24h: float
    low_24h: float
    volume_24h: float
    change_24h_pct: float
    bid_price: float
    ask_price: float
    spread_pct: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @property
    def price_range(self) -> float:
        """24h price range"""
        return self.high_24h - self.low_24h
    
    @property
    def price_position(self) -> float:
        """Position within 24h range as percentage (0-100)"""
        if self.price_range <= 0:
            return 50.0
        return ((self.price - self.low_24h) / self.price_range) * 100
    
    @property
    def volatility_pct(self) -> float:
        """Volatility as percentage of price"""
        if self.price <= 0:
            return 2.0
        return (self.price_range / self.price) * 100


@dataclass
class AISignal:
    """AI-generated trading signal"""
    signal: str  # LONG, SHORT, NEUTRAL
    confidence: float
    regime: str  # BULL_TRENDING, BEAR_TRENDING, RANGE_BOUND, HIGH_VOLATILITY, LOW_VOLATILITY
    reasoning: List[str]
    indicators: Dict
    recommended_size: str = "0.001"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "signal": self.signal,
            "confidence": self.confidence,
            "regime": self.regime,
            "reasoning": self.reasoning,
            "indicators": self.indicators,
            "recommended_size": self.recommended_size
        }


@dataclass
class Position:
    """Trading position data"""
    coin: str
    symbol: str
    side: str  # LONG or SHORT
    size: float
    entry_price: float
    current_price: float
    leverage: int
    liquidation_price: float = 0.0
    
    @property
    def pnl_pct(self) -> float:
        """Profit/loss percentage"""
        if self.entry_price <= 0:
            return 0.0
        if self.side == "LONG":
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:
            return ((self.entry_price - self.current_price) / self.entry_price) * 100
    
    @property
    def pnl_usdt(self) -> float:
        """Profit/loss in USDT"""
        if self.side == "LONG":
            return (self.current_price - self.entry_price) * self.size
        else:
            return (self.entry_price - self.current_price) * self.size
    
    @property
    def value_usdt(self) -> float:
        """Position value in USDT"""
        return self.size * self.current_price
    
    @property
    def margin_usdt(self) -> float:
        """Margin used in USDT"""
        if self.leverage <= 0:
            return self.value_usdt
        return self.value_usdt / self.leverage
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "coin": self.coin,
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "leverage": self.leverage,
            "liquidation_price": self.liquidation_price,
            "pnl_pct": round(self.pnl_pct, 2),
            "pnl_usdt": round(self.pnl_usdt, 2),
            "value_usdt": round(self.value_usdt, 2),
            "margin_usdt": round(self.margin_usdt, 2)
        }


@dataclass
class TakeProfitSettings:
    """Take-profit configuration for a coin"""
    enabled: bool = False
    mode: str = "fixed"  # fixed or trailing
    fixed_target_pct: float = 1.5
    trailing_drop_pct: float = 0.5
    peak_profit_pct: float = 0.0
    entry_price: float = 0.0
    position_side: Optional[str] = None
    
    def reset_tracking(self):
        """Reset tracking state when position closes"""
        self.peak_profit_pct = 0.0
        self.entry_price = 0.0
        self.position_side = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "fixed_target_pct": self.fixed_target_pct,
            "trailing_drop_pct": self.trailing_drop_pct,
            "peak_profit_pct": self.peak_profit_pct,
            "entry_price": self.entry_price,
            "position_side": self.position_side
        }


@dataclass
class AutomationSettings:
    """Full automation configuration"""
    enabled: bool = False
    auto_entry: bool = False
    auto_take_profit: bool = False
    auto_stop_loss: bool = False
    margin_usdt: float = 30.0
    leverage: int = 20
    min_confidence: float = 0.65
    stop_loss_pct: float = 2.0
    max_trades_per_hour: int = 3
    cooldown_minutes: int = 5
    daily_loss_limit_usdt: float = 20.0
    # Tracking state
    trades_this_hour: int = 0
    hour_start: int = 0
    last_trade_time: float = 0
    daily_pnl: float = 0.0
    day_start: int = 0
    last_auto_action: str = ""
    
    @property
    def position_value(self) -> float:
        """Calculate position value from margin and leverage"""
        return self.margin_usdt * self.leverage
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "enabled": self.enabled,
            "auto_entry": self.auto_entry,
            "auto_take_profit": self.auto_take_profit,
            "auto_stop_loss": self.auto_stop_loss,
            "margin_usdt": self.margin_usdt,
            "leverage": self.leverage,
            "min_confidence": self.min_confidence,
            "stop_loss_pct": self.stop_loss_pct,
            "max_trades_per_hour": self.max_trades_per_hour,
            "cooldown_minutes": self.cooldown_minutes,
            "daily_loss_limit_usdt": self.daily_loss_limit_usdt,
            "trades_this_hour": self.trades_this_hour,
            "last_auto_action": self.last_auto_action,
            "daily_pnl": self.daily_pnl
        }
