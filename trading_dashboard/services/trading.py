"""
Trading Service for RegimeForge Alpha
Handles order execution and AI log submission
"""
import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..api_client import WeexClient
from ..models import AISignal, MarketData
from ..utils import extract_order_id
from ..config import SUPPORTED_COINS, MODEL_VERSION

logger = logging.getLogger(__name__)


class TradingService:
    """
    Service for executing trades and submitting AI logs.
    
    Handles order placement, cancellation, and WEEX hackathon
    AI log submission.
    """
    
    def __init__(self, client: WeexClient, current_coin_getter):
        """
        Initialize the trading service.
        
        Args:
            client: WEEX API client
            current_coin_getter: Callable that returns current coin symbol
        """
        self.client = client
        self.get_current_coin = current_coin_getter
    
    def get_symbol(self) -> str:
        """Get current trading symbol"""
        coin = self.get_current_coin()
        return SUPPORTED_COINS.get(coin, "cmt_btcusdt")
    
    async def submit_ai_log(
        self,
        order_id: Optional[str],
        market_data: Dict[str, Any],
        ai_signal: AISignal,
        trade_action: str
    ) -> tuple:
        """
        Submit AI log to WEEX for hackathon verification.
        
        Args:
            order_id: Order ID from trade execution
            market_data: Market data at time of trade
            ai_signal: AI signal that triggered the trade
            trade_action: Description of trade action
            
        Returns:
            Tuple of (API result, AI log dict)
        """
        coin = self.get_current_coin()
        ind = ai_signal.indicators
        
        explanation = (
            f"RegimeForge Alpha {MODEL_VERSION} analyzed {coin}/USDT. "
            f"Technical indicators: RSI={ind.get('rsi', 'N/A')}, "
            f"EMA crossover={ind.get('trend_strength', 0):.3f}, "
            f"24h range position={ind.get('price_position_pct', 50):.1f}%, "
            f"volatility={ind.get('volatility_pct', 0):.2f}%. "
            f"Detected {ai_signal.regime} regime. "
            f"Generated {ai_signal.signal} signal with {ai_signal.confidence*100:.0f}% confidence. "
            f"Reasoning: {'; '.join(ai_signal.reasoning[:3])}."
        )
        
        ai_log = {
            "orderId": int(order_id) if order_id else None,
            "stage": "Strategy Generation",
            "model": MODEL_VERSION,
            "input": {
                "prompt": f"Analyze {coin}/USDT and generate {trade_action} signal",
                "data": {
                    "symbol": f"{coin}/USDT",
                    "price": market_data.get("price", 0),
                    "indicators": ai_signal.indicators,
                    "timestamp": market_data.get("timestamp", datetime.now(timezone.utc).isoformat())
                }
            },
            "output": {
                "signal": ai_signal.signal,
                "confidence": ai_signal.confidence,
                "regime": ai_signal.regime,
                "reasoning": ai_signal.reasoning,
                "indicators": ai_signal.indicators
            },
            "explanation": explanation[:1000]
        }
        
        result = await self.client.upload_ai_log(ai_log)
        return result, ai_log
    
    async def place_order(
        self,
        side: str,
        size: str,
        order_type: str = "market",
        price: Optional[str] = None,
        client_oid_prefix: str = "manual"
    ) -> Dict[str, Any]:
        """
        Place a new order.
        
        Args:
            side: "long" or "short"
            size: Position size in coin units
            order_type: "market" or "limit"
            price: Limit price (required for limit orders)
            client_oid_prefix: Prefix for client order ID
            
        Returns:
            Dict with success status and order_id or error
        """
        symbol = self.get_symbol()
        
        order_data = {
            "symbol": symbol,
            "client_oid": f"{client_oid_prefix}_{int(time.time())}",
            "size": str(size),
            "type": "1" if side.lower() == "long" else "2"
        }
        
        if order_type == "market":
            order_data["order_type"] = "0"
            order_data["match_price"] = "1"
        else:
            order_data["order_type"] = "1"
            order_data["price"] = str(price)
            order_data["match_price"] = "0"
        
        result = await self.client.place_order(order_data)
        order_id = extract_order_id(result)
        
        if order_id:
            return {"success": True, "order_id": order_id}
        return {"success": False, "error": result}
    
    async def close_position(
        self,
        size: float,
        side: str,
        client_oid_prefix: str = "close"
    ) -> Dict[str, Any]:
        """
        Close an existing position.
        
        Args:
            size: Position size to close
            side: Current position side ("LONG" or "SHORT")
            client_oid_prefix: Prefix for client order ID
            
        Returns:
            Dict with success status and order_id or error
        """
        symbol = self.get_symbol()
        
        # Close type: 3 = close long, 4 = close short
        close_type = "3" if side.upper() == "LONG" else "4"
        
        order_data = {
            "symbol": symbol,
            "client_oid": f"{client_oid_prefix}_{int(time.time())}",
            "size": str(size),
            "type": close_type,
            "order_type": "0",
            "match_price": "1"
        }
        
        result = await self.client.place_order(order_data)
        order_id = extract_order_id(result)
        
        if order_id:
            return {"success": True, "order_id": order_id}
        return {"success": False, "error": result}
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an existing order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Dict with success status
        """
        symbol = self.get_symbol()
        result = await self.client.cancel_order(symbol, order_id)
        
        success = result.get("result") == True or result.get("code") in ["00000", "200"]
        return {"success": success, "response": result}
    
    async def get_position(self) -> Optional[Dict[str, Any]]:
        """
        Get current position for the selected coin.
        
        Returns:
            Position dict or None if no position
        """
        symbol = self.get_symbol()
        data = await self.client.get_position(symbol)
        
        positions = data.get("data", data) if isinstance(data, dict) else data
        
        if isinstance(positions, list) and len(positions) > 0:
            pos = positions[0]
            size = float(pos.get("size", pos.get("total", 0)))
            
            if size > 0:
                open_value = float(pos.get("open_value", pos.get("openValue", 0)))
                return {
                    "side": pos.get("side", pos.get("holdSide", "LONG")).upper(),
                    "size": size,
                    "avg_price": open_value / size if size > 0 else 0,
                    "leverage": int(float(pos.get("leverage", 20))),
                    "unrealized_pnl": float(pos.get("unrealized_pnl", pos.get("unrealizedPL", 0))),
                    "liquidation_price": float(pos.get("liquidation_price", pos.get("liq_price", pos.get("liquidationPrice", 0))))
                }
        
        return None
    
    async def get_all_positions(self) -> list:
        """
        Get all open positions across all supported coins.
        
        Returns:
            List of position dicts
        """
        positions = []
        
        for coin, symbol in SUPPORTED_COINS.items():
            try:
                data = await self.client.get_position(symbol)
                pos_list = data.get("data", data) if isinstance(data, dict) else data
                
                if pos_list and isinstance(pos_list, list) and len(pos_list) > 0:
                    pos = pos_list[0]
                    size = float(pos.get("size", pos.get("total", 0)))
                    
                    if size > 0:
                        open_value = float(pos.get("open_value", pos.get("openValue", 0)))
                        entry_price = open_value / size if size > 0 else 0
                        
                        # Get current price
                        ticker = await self.client.get_ticker(symbol)
                        ticker_data = ticker.get("data", ticker) if isinstance(ticker, dict) else {}
                        current_price = float(ticker_data.get("last", 0))
                        
                        side = pos.get("side", pos.get("holdSide", "LONG")).upper()
                        
                        # Calculate P/L
                        if current_price > 0 and entry_price > 0:
                            if side == "LONG":
                                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                                pnl_usdt = (current_price - entry_price) * size
                            else:
                                pnl_pct = ((entry_price - current_price) / entry_price) * 100
                                pnl_usdt = (entry_price - current_price) * size
                        else:
                            pnl_pct = 0
                            pnl_usdt = 0
                        
                        positions.append({
                            "coin": coin,
                            "symbol": symbol,
                            "side": side,
                            "size": size,
                            "entry_price": entry_price,
                            "current_price": current_price,
                            "leverage": pos.get("leverage", "20"),
                            "pnl_pct": round(pnl_pct, 2),
                            "pnl_usdt": round(pnl_usdt, 2),
                            "value_usdt": round(size * current_price, 2)
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch position for {coin}: {e}")
        
        return positions
