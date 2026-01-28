"""
Take-Profit Service for RegimeForge Alpha
Manages take-profit settings and monitoring
"""
import logging
from typing import Dict, Any, Optional

from ..models import TakeProfitSettings
from ..config import TRAILING_ACTIVATION_THRESHOLD

logger = logging.getLogger(__name__)


class TakeProfitService:
    """
    Service for managing take-profit settings and checking conditions.
    
    Supports both fixed percentage and trailing stop modes.
    """
    
    def __init__(self):
        """Initialize the take-profit service"""
        self._settings: Dict[str, TakeProfitSettings] = {}
    
    def get_settings(self, coin: str) -> TakeProfitSettings:
        """
        Get take-profit settings for a specific coin.
        
        Args:
            coin: Coin symbol (e.g., "BTC")
            
        Returns:
            TakeProfitSettings for the coin
        """
        if coin not in self._settings:
            self._settings[coin] = TakeProfitSettings()
        return self._settings[coin]
    
    def update_settings(self, coin: str, updates: Dict[str, Any]) -> TakeProfitSettings:
        """
        Update take-profit settings for a coin.
        
        Args:
            coin: Coin symbol
            updates: Dictionary of settings to update
            
        Returns:
            Updated TakeProfitSettings
        """
        settings = self.get_settings(coin)
        
        if "enabled" in updates:
            settings.enabled = bool(updates["enabled"])
        if "mode" in updates and updates["mode"] in ["fixed", "trailing"]:
            settings.mode = updates["mode"]
        if "fixed_target_pct" in updates:
            settings.fixed_target_pct = float(updates["fixed_target_pct"])
        if "trailing_drop_pct" in updates:
            settings.trailing_drop_pct = float(updates["trailing_drop_pct"])
        
        return settings
    
    def reset_tracking(self, coin: str):
        """
        Reset tracking state for a coin (after position close).
        
        Args:
            coin: Coin symbol
        """
        settings = self.get_settings(coin)
        settings.reset_tracking()
    
    def check_take_profit(
        self,
        coin: str,
        current_price: float,
        entry_price: float,
        side: str
    ) -> Dict[str, Any]:
        """
        Check if take-profit should trigger.
        
        Args:
            coin: Coin symbol
            current_price: Current market price
            entry_price: Position entry price
            side: Position side ("LONG" or "SHORT")
            
        Returns:
            Dict with should_close, reason, and profit info
        """
        settings = self.get_settings(coin)
        
        if not settings.enabled:
            return {"should_close": False, "reason": "Take-profit disabled"}
        
        if current_price <= 0 or entry_price <= 0:
            return {"should_close": False, "reason": "Invalid prices"}
        
        # Update tracking
        settings.entry_price = entry_price
        settings.position_side = side
        
        # Calculate profit percentage
        if side.upper() == "LONG":
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Update peak profit
        if profit_pct > settings.peak_profit_pct:
            settings.peak_profit_pct = profit_pct
        
        result = {
            "should_close": False,
            "reason": "",
            "current_price": current_price,
            "entry_price": entry_price,
            "profit_pct": round(profit_pct, 3),
            "peak_profit_pct": round(settings.peak_profit_pct, 3),
            "side": side,
            "mode": settings.mode
        }
        
        if settings.mode == "fixed":
            target = settings.fixed_target_pct
            if profit_pct >= target:
                result["should_close"] = True
                result["reason"] = f"Fixed target reached: {profit_pct:.2f}% >= {target}%"
            else:
                result["reason"] = f"Waiting for {target}% (current: {profit_pct:.2f}%)"
        
        elif settings.mode == "trailing":
            drop_threshold = settings.trailing_drop_pct
            peak = settings.peak_profit_pct
            
            # Only trigger if we've had some profit
            if peak >= TRAILING_ACTIVATION_THRESHOLD:
                drop_from_peak = peak - profit_pct
                if drop_from_peak >= drop_threshold:
                    result["should_close"] = True
                    result["reason"] = f"Trailing stop: dropped {drop_from_peak:.2f}% from peak {peak:.2f}%"
                else:
                    result["reason"] = f"Peak: {peak:.2f}%, Current: {profit_pct:.2f}%, Drop: {drop_from_peak:.2f}%"
            else:
                result["reason"] = f"Waiting for profit (current: {profit_pct:.2f}%, need {TRAILING_ACTIVATION_THRESHOLD}% to activate trailing)"
        
        return result
    
    def enable_trailing_for_auto_trade(self, coin: str, entry_price: float, side: str):
        """
        Enable trailing take-profit for an automated trade.
        
        Args:
            coin: Coin symbol
            entry_price: Trade entry price
            side: Trade side
        """
        settings = self.get_settings(coin)
        settings.enabled = True
        settings.mode = "trailing"
        settings.peak_profit_pct = 0.0
        settings.entry_price = entry_price
        settings.position_side = side.upper()
