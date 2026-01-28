"""
Utility functions for RegimeForge Alpha
"""
import math
from typing import Optional, Dict, Any

from .config import COIN_DECIMALS


def extract_order_id(result: Dict[str, Any]) -> Optional[str]:
    """
    Extract order_id from various WEEX response formats.
    
    WEEX API returns order IDs in different formats:
    - {"order_id": "123"}
    - {"orderId": "123"}
    - {"data": {"order_id": "123"}}
    - {"data": "123"}
    
    Args:
        result: API response dictionary
        
    Returns:
        Order ID as string, or None if not found
    """
    if not isinstance(result, dict):
        return None
    
    # Try top-level keys first
    order_id = result.get("order_id") or result.get("orderId")
    if order_id:
        return str(order_id)
    
    # Try nested in data
    data = result.get("data")
    if isinstance(data, dict):
        order_id = data.get("order_id") or data.get("orderId")
        if order_id:
            return str(order_id)
    elif isinstance(data, str):
        return data
    
    return None


def get_coin_decimals(coin: str) -> int:
    """
    Get the decimal precision for a coin.
    
    Args:
        coin: Coin symbol (e.g., "BTC", "ETH")
        
    Returns:
        Number of decimal places for position sizing
    """
    return COIN_DECIMALS.get(coin, 4)


def round_to_step(value: float, coin: str) -> float:
    """
    Round a value down to the coin's step size.
    
    Uses floor to avoid exceeding maximum position size.
    
    Args:
        value: Value to round
        coin: Coin symbol for decimal precision
        
    Returns:
        Value rounded down to step size
    """
    decimals = get_coin_decimals(coin)
    multiplier = 10 ** decimals
    return math.floor(value * multiplier) / multiplier


def format_coin_size(value: float, coin: str) -> str:
    """
    Format a coin size with proper decimal places.
    
    Args:
        value: Size value
        coin: Coin symbol
        
    Returns:
        Formatted string with correct decimals
    """
    decimals = get_coin_decimals(coin)
    return f"{value:.{decimals}f}"


def parse_ticker_data(ticker: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse ticker data from WEEX API response.
    
    Handles both nested and flat response formats.
    
    Args:
        ticker: Raw ticker response
        
    Returns:
        Normalized ticker data
    """
    ticker_data = ticker.get("data", ticker) if isinstance(ticker, dict) else {}
    
    price = float(ticker_data.get("last", 0))
    high_24h = float(ticker_data.get("high_24h", ticker_data.get("high24h", 0)))
    low_24h = float(ticker_data.get("low_24h", ticker_data.get("low24h", 0)))
    volume = float(ticker_data.get("base_volume", ticker_data.get("baseVolume", 0)))
    change_pct = float(ticker_data.get("priceChangePercent", ticker_data.get("change24h", 0)))
    
    return {
        "price": price,
        "high_24h": high_24h if high_24h > 0 else price * 1.02,
        "low_24h": low_24h if low_24h > 0 else price * 0.98,
        "volume": volume,
        "change_pct": change_pct
    }


def parse_depth_data(depth: Dict[str, Any], fallback_price: float) -> Dict[str, float]:
    """
    Parse order book depth data.
    
    Args:
        depth: Raw depth response
        fallback_price: Price to use if depth unavailable
        
    Returns:
        Dict with bid_price and ask_price
    """
    bid_price = fallback_price
    ask_price = fallback_price
    
    if isinstance(depth, dict):
        depth_data = depth.get("data", depth)
        bids = depth_data.get("bids", [])
        asks = depth_data.get("asks", [])
        
        if bids:
            if isinstance(bids[0], list):
                bid_price = float(bids[0][0])
            elif isinstance(bids[0], dict):
                bid_price = float(bids[0].get("price", fallback_price))
        
        if asks:
            if isinstance(asks[0], list):
                ask_price = float(asks[0][0])
            elif isinstance(asks[0], dict):
                ask_price = float(asks[0].get("price", fallback_price))
    
    return {"bid_price": bid_price, "ask_price": ask_price}


def validate_json_request(request_json: Optional[Dict], required_fields: list = None) -> tuple:
    """
    Validate JSON request data.
    
    Args:
        request_json: The request JSON (may be None)
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, error_message or None)
    """
    if request_json is None:
        return False, "Invalid JSON body"
    
    if required_fields:
        missing = [f for f in required_fields if f not in request_json]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
    
    return True, None
