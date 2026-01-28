"""
Automation Service for RegimeForge Alpha
Handles automated trading based on AI signals
"""
import time
import logging
from typing import Dict, Any, Optional

from ..models import AutomationSettings
from ..utils import round_to_step, format_coin_size
from .ai_engine import RegimeForgeAI
from .trading import TradingService
from .take_profit import TakeProfitService

logger = logging.getLogger(__name__)


class AutomationService:
    """
    Service for automated trading based on AI signals.
    
    Manages auto-entry, auto-take-profit, and auto-stop-loss
    with safety controls.
    """
    
    def __init__(
        self,
        ai_engine: RegimeForgeAI,
        trading_service: TradingService,
        tp_service: TakeProfitService,
        current_coin_getter
    ):
        """
        Initialize the automation service.
        
        Args:
            ai_engine: AI engine for signal generation
            trading_service: Trading service for order execution
            tp_service: Take-profit service
            current_coin_getter: Callable that returns current coin
        """
        self.ai = ai_engine
        self.trading = trading_service
        self.tp = tp_service
        self.get_current_coin = current_coin_getter
        self.settings = AutomationSettings()
    
    def update_settings(self, updates: Dict[str, Any]):
        """
        Update automation settings.
        
        Args:
            updates: Dictionary of settings to update
        """
        if "enabled" in updates:
            self.settings.enabled = bool(updates["enabled"])
        if "auto_entry" in updates:
            self.settings.auto_entry = bool(updates["auto_entry"])
        if "auto_take_profit" in updates:
            self.settings.auto_take_profit = bool(updates["auto_take_profit"])
        if "auto_stop_loss" in updates:
            self.settings.auto_stop_loss = bool(updates["auto_stop_loss"])
        if "margin_usdt" in updates:
            self.settings.margin_usdt = float(updates["margin_usdt"])
        if "leverage" in updates:
            self.settings.leverage = int(updates["leverage"])
        if "min_confidence" in updates:
            self.settings.min_confidence = float(updates["min_confidence"])
        if "stop_loss_pct" in updates:
            self.settings.stop_loss_pct = float(updates["stop_loss_pct"])
        if "cooldown_minutes" in updates:
            self.settings.cooldown_minutes = int(updates["cooldown_minutes"])
        if "max_trades_per_hour" in updates:
            self.settings.max_trades_per_hour = int(updates["max_trades_per_hour"])
        if "daily_loss_limit_usdt" in updates:
            self.settings.daily_loss_limit_usdt = float(updates["daily_loss_limit_usdt"])
    
    async def run(self) -> Dict[str, Any]:
        """
        Run automation check and execute trades if conditions met.
        
        Returns:
            Dict with action taken and reason
        """
        if not self.settings.enabled:
            return {"action": "none", "reason": "Automation disabled"}
        
        current_time = time.time()
        current_hour = int(current_time / 3600)
        current_day = int(current_time / 86400)
        
        # Reset hourly counter
        if current_hour != self.settings.hour_start:
            self.settings.hour_start = current_hour
            self.settings.trades_this_hour = 0
        
        # Reset daily P/L
        if current_day != self.settings.day_start:
            self.settings.day_start = current_day
            self.settings.daily_pnl = 0.0
        
        # Check daily loss limit
        if self.settings.daily_pnl <= -self.settings.daily_loss_limit_usdt:
            return {
                "action": "none",
                "reason": f"Daily loss limit reached (${self.settings.daily_pnl:.2f})"
            }
        
        coin = self.get_current_coin()
        
        # Get current position
        position = await self.trading.get_position()
        
        if position:
            return await self._handle_open_position(position, coin, current_time)
        else:
            return await self._handle_no_position(coin, current_time)
    
    async def _handle_open_position(
        self,
        position: Dict[str, Any],
        coin: str,
        current_time: float
    ) -> Dict[str, Any]:
        """Handle automation when there's an open position"""
        from ..api_client import WeexClient
        from ..config import SUPPORTED_COINS
        
        symbol = SUPPORTED_COINS.get(coin, "cmt_btcusdt")
        
        # Get current price
        ticker = await self.trading.client.get_ticker(symbol)
        ticker_data = ticker.get("data", ticker) if isinstance(ticker, dict) else {}
        current_price = float(ticker_data.get("last", 0))
        
        if current_price <= 0:
            return {"action": "none", "reason": "Price unavailable"}
        
        side = position["side"]
        size = position["size"]
        entry_price = position["avg_price"]
        
        # Calculate P/L
        if side == "LONG":
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            pnl_usdt = (current_price - entry_price) * size
        else:
            profit_pct = ((entry_price - current_price) / entry_price) * 100
            pnl_usdt = (entry_price - current_price) * size
        
        # Auto Stop-Loss
        if self.settings.auto_stop_loss and profit_pct <= -self.settings.stop_loss_pct:
            result = await self._execute_close(coin, size, side, "STOP_LOSS")
            if result.get("success"):
                self.settings.daily_pnl += pnl_usdt
                self.settings.last_auto_action = f"STOP_LOSS at {profit_pct:.2f}%"
                return {
                    "action": f"CLOSE {side} (Stop-Loss)",
                    "reason": f"Loss exceeded {self.settings.stop_loss_pct}% (was {profit_pct:.2f}%)",
                    "trade_executed": True,
                    "pnl": pnl_usdt
                }
        
        # Auto Take-Profit
        tp_settings = self.tp.get_settings(coin)
        if self.settings.auto_take_profit and tp_settings.enabled:
            tp_check = self.tp.check_take_profit(coin, current_price, entry_price, side)
            
            if tp_check["should_close"]:
                result = await self._execute_close(coin, size, side, "TAKE_PROFIT")
                if result.get("success"):
                    self.settings.daily_pnl += pnl_usdt
                    self.tp.reset_tracking(coin)
                    self.settings.last_auto_action = f"TAKE_PROFIT at {profit_pct:.2f}%"
                    return {
                        "action": f"CLOSE {side} (Take-Profit)",
                        "reason": tp_check["reason"],
                        "trade_executed": True,
                        "pnl": pnl_usdt
                    }
        
        return {"action": "none", "reason": f"Position open: {side} P/L: {profit_pct:.2f}%"}
    
    async def _handle_no_position(self, coin: str, current_time: float) -> Dict[str, Any]:
        """Handle automation when there's no open position"""
        from ..config import SUPPORTED_COINS
        
        if not self.settings.auto_entry:
            return {"action": "none", "reason": "Auto-entry disabled"}
        
        # Check cooldown
        cooldown_seconds = self.settings.cooldown_minutes * 60
        if current_time - self.settings.last_trade_time < cooldown_seconds:
            remaining = int(cooldown_seconds - (current_time - self.settings.last_trade_time))
            return {"action": "none", "reason": f"Cooldown: {remaining}s remaining"}
        
        # Check max trades per hour
        if self.settings.trades_this_hour >= self.settings.max_trades_per_hour:
            return {
                "action": "none",
                "reason": f"Max trades/hour reached ({self.settings.max_trades_per_hour})"
            }
        
        # Get AI signal
        signal = await self.ai.analyze()
        
        # Check confidence threshold
        if signal.confidence < self.settings.min_confidence:
            return {
                "action": "none",
                "reason": f"Low confidence: {signal.confidence*100:.0f}% < {self.settings.min_confidence*100:.0f}%"
            }
        
        # Check if signal is actionable
        if signal.signal == "NEUTRAL":
            return {"action": "none", "reason": "AI signal: NEUTRAL"}
        
        # Get current price
        symbol = SUPPORTED_COINS.get(coin, "cmt_btcusdt")
        ticker = await self.trading.client.get_ticker(symbol)
        ticker_data = ticker.get("data", ticker) if isinstance(ticker, dict) else {}
        current_price = float(ticker_data.get("last", 0))
        
        if current_price <= 0:
            return {"action": "none", "reason": "Price unavailable"}
        
        # Calculate position size
        position_value_usdt = self.settings.position_value
        coin_size = round_to_step(position_value_usdt / current_price, coin)
        
        if coin_size <= 0:
            return {"action": "none", "reason": "Position size too small"}
        
        # Execute trade
        direction = "long" if signal.signal == "LONG" else "short"
        result = await self._execute_open(coin, format_coin_size(coin_size, coin), direction, signal, current_price)
        
        if result.get("success"):
            self.settings.last_trade_time = current_time
            self.settings.trades_this_hour += 1
            self.settings.last_auto_action = f"OPEN {signal.signal}"
            return {
                "action": f"OPEN {signal.signal}",
                "reason": f"AI: {signal.signal} ({signal.confidence*100:.0f}% conf)",
                "trade_executed": True,
                "order_id": result.get("order_id")
            }
        else:
            return {"action": "none", "reason": f"Trade failed: {result.get('error', 'Unknown')}"}
    
    async def _execute_open(
        self,
        coin: str,
        size: str,
        direction: str,
        signal,
        current_price: float
    ) -> Dict[str, Any]:
        """Execute an automated trade open"""
        try:
            market_data = await self.ai.fetch_market_data()
            
            result = await self.trading.place_order(
                side=direction,
                size=size,
                order_type="market",
                client_oid_prefix="auto"
            )
            
            if result.get("success"):
                # Submit AI log
                market_dict = {
                    "price": market_data.price,
                    "high_24h": market_data.high_24h,
                    "low_24h": market_data.low_24h,
                    "timestamp": market_data.timestamp
                }
                await self.trading.submit_ai_log(
                    result.get("order_id"),
                    market_dict,
                    signal,
                    f"AUTO {direction.upper()}"
                )
                
                # Enable trailing take-profit
                self.tp.enable_trailing_for_auto_trade(coin, current_price, direction)
            
            return result
        except Exception as e:
            logger.error(f"Auto trade execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_close(
        self,
        coin: str,
        size: float,
        side: str,
        reason: str
    ) -> Dict[str, Any]:
        """Execute an automated position close"""
        try:
            signal = await self.ai.analyze()
            market_data = await self.ai.fetch_market_data()
            
            result = await self.trading.close_position(
                size=size,
                side=side,
                client_oid_prefix="auto_close"
            )
            
            if result.get("success"):
                market_dict = {
                    "price": market_data.price,
                    "timestamp": market_data.timestamp
                }
                await self.trading.submit_ai_log(
                    result.get("order_id"),
                    market_dict,
                    signal,
                    f"AUTO {reason} Close {side}"
                )
                
                self.tp.reset_tracking(coin)
            
            return result
        except Exception as e:
            logger.error(f"Auto close execution failed: {e}")
            return {"success": False, "error": str(e)}
