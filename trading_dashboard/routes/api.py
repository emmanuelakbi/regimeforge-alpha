"""
Core API routes for RegimeForge Alpha
"""
from flask import Blueprint, jsonify, request, current_app
import logging

from ..api_client import run_async
from ..utils import validate_json_request
from ..config import SUPPORTED_COINS

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")


def get_services():
    """Get services from app context"""
    return (
        current_app.config["client"],
        current_app.config["trading_service"],
        current_app.config["ai_engine"],
        current_app.config["tp_service"],
        current_app.config["state"]
    )


@api_bp.route("/price")
def get_price():
    """Get current price for selected coin"""
    async def fetch():
        client, _, _, _, state = get_services()
        symbol = SUPPORTED_COINS.get(state["current_coin"], "cmt_btcusdt")
        data = await client.get_ticker(symbol)
        ticker = data.get("data", data) if isinstance(data, dict) else {}
        change = ticker.get("priceChangePercent", ticker.get("change24h", "0"))
        if change and abs(float(change)) < 1:
            change = float(change) * 100
        return {
            "price": ticker.get("last"),
            "high_24h": ticker.get("high_24h", ticker.get("high24h")),
            "low_24h": ticker.get("low_24h", ticker.get("low24h")),
            "change_24h": change,
            "coin": state["current_coin"]
        }
    return jsonify(run_async(fetch()))


@api_bp.route("/balance")
def get_balance():
    """Get account USDT balance"""
    async def fetch():
        client, _, _, _, _ = get_services()
        data = await client.get_assets()
        if isinstance(data, list):
            for asset in data:
                if asset.get("coinName") == "USDT" or asset.get("currency") == "USDT":
                    return {"balance": asset.get("available", asset.get("equity", "0"))}
        elif isinstance(data, dict):
            assets = data.get("data", data)
            if isinstance(assets, list):
                for asset in assets:
                    if asset.get("coinName") == "USDT" or asset.get("currency") == "USDT":
                        return {"balance": asset.get("available", asset.get("equity", "0"))}
        return {"balance": "0"}
    return jsonify(run_async(fetch()))


@api_bp.route("/position")
def get_position():
    """Get current position for selected coin"""
    async def fetch():
        _, trading, _, _, _ = get_services()
        position = await trading.get_position()
        if position:
            return {"position": {
                "side": position["side"],
                "size": str(position["size"]),
                "avg_price": str(position["avg_price"]),
                "leverage": str(position["leverage"]),
                "unrealized_pnl": str(position["unrealized_pnl"]),
                "liquidation_price": str(position["liquidation_price"])
            }}
        return {"position": None}
    return jsonify(run_async(fetch()))


@api_bp.route("/orders")
def get_orders():
    """Get open orders for selected coin"""
    async def fetch():
        client, _, _, _, state = get_services()
        symbol = SUPPORTED_COINS.get(state["current_coin"], "cmt_btcusdt")
        data = await client.get_orders(symbol)
        orders = data.get("data", data) if isinstance(data, dict) else data
        return {"orders": orders if isinstance(orders, list) else []}
    return jsonify(run_async(fetch()))


@api_bp.route("/history")
def get_history():
    """Get trade history for selected coin"""
    async def fetch():
        client, _, _, _, state = get_services()
        symbol = SUPPORTED_COINS.get(state["current_coin"], "cmt_btcusdt")
        data = await client.get_history(symbol)
        trades = data.get("data", data) if isinstance(data, dict) else data
        return {"trades": trades if isinstance(trades, list) else []}
    return jsonify(run_async(fetch()))


@api_bp.route("/all_positions")
def get_all_positions():
    """Get all open positions across all coins"""
    async def fetch():
        _, trading, _, _, _ = get_services()
        positions = await trading.get_all_positions()
        return {"positions": positions}
    return jsonify(run_async(fetch()))


@api_bp.route("/coins")
def get_coins():
    """Get list of supported coins"""
    _, _, _, _, state = get_services()
    return jsonify({"coins": list(SUPPORTED_COINS.keys()), "current": state["current_coin"]})


@api_bp.route("/coin", methods=["POST"])
def set_coin():
    """Set the current trading coin"""
    req = request.get_json(silent=True)
    is_valid, error = validate_json_request(req)
    if not is_valid:
        return jsonify({"success": False, "error": error}), 400
    coin = req.get("coin", "").upper()
    if not coin:
        return jsonify({"success": False, "error": "Missing coin parameter"}), 400
    if coin not in SUPPORTED_COINS:
        return jsonify({"success": False, "error": f"Unsupported coin: {coin}"}), 400
    _, _, ai, _, state = get_services()
    state["current_coin"] = coin
    ai.reset()
    return jsonify({"success": True, "coin": coin, "symbol": SUPPORTED_COINS[coin]})


@api_bp.route("/open", methods=["POST"])
def open_position():
    """Open a new position with AI log submission"""
    async def execute():
        req = request.get_json(silent=True)
        is_valid, error = validate_json_request(req)
        if not is_valid:
            return {"success": False, "error": error}
        side = req.get("side", "long")
        size = req.get("size", "0.001")
        order_type = req.get("order_type", "market")
        price = req.get("price")
        if not size or float(size) <= 0:
            return {"success": False, "error": "Invalid size"}
        _, trading, ai, _, _ = get_services()
        signal = await ai.analyze(force_signal=side.upper())
        market_data = await ai.fetch_market_data()
        result = await trading.place_order(side=side, size=size, order_type=order_type, price=price)
        if result.get("success"):
            market_dict = {"price": market_data.price, "high_24h": market_data.high_24h, "low_24h": market_data.low_24h, "timestamp": market_data.timestamp}
            await trading.submit_ai_log(result.get("order_id"), market_dict, signal, f"Manual {side.upper()}")
        return result
    return jsonify(run_async(execute()))


@api_bp.route("/close", methods=["POST"])
def close_position():
    """Close current position with AI log"""
    async def execute():
        _, trading, ai, tp, state = get_services()
        position = await trading.get_position()
        if not position:
            return {"success": False, "error": "No position found"}
        size = position["size"]
        side = position["side"]
        if size <= 0:
            return {"success": False, "error": "No position to close"}
        signal = await ai.analyze()
        market_data = await ai.fetch_market_data()
        result = await trading.close_position(size=size, side=side)
        if result.get("success"):
            await trading.submit_ai_log(result.get("order_id"), {"price": market_data.price, "timestamp": market_data.timestamp}, signal, f"Close {side}")
            tp.reset_tracking(state["current_coin"])
        return result
    return jsonify(run_async(execute()))


@api_bp.route("/cancel", methods=["POST"])
def cancel_order():
    """Cancel an open order"""
    async def execute():
        req = request.get_json(silent=True)
        is_valid, error = validate_json_request(req)
        if not is_valid:
            return {"success": False, "error": error}
        order_id = req.get("orderId")
        if not order_id:
            return {"success": False, "error": "Missing orderId"}
        _, trading, _, _, _ = get_services()
        return await trading.cancel_order(str(order_id))
    return jsonify(run_async(execute()))


@api_bp.route("/takeprofit/settings", methods=["GET"])
def get_tp_settings():
    """Get take-profit settings for current coin"""
    _, _, _, tp, state = get_services()
    settings = tp.get_settings(state["current_coin"])
    return jsonify(settings.to_dict())


@api_bp.route("/takeprofit/settings", methods=["POST"])
def set_tp_settings():
    """Update take-profit settings for current coin"""
    req = request.get_json(silent=True)
    is_valid, error = validate_json_request(req)
    if not is_valid:
        return jsonify({"success": False, "error": error}), 400
    _, _, _, tp, state = get_services()
    settings = tp.update_settings(state["current_coin"], req)
    return jsonify({"success": True, "settings": settings.to_dict(), "coin": state["current_coin"]})


@api_bp.route("/takeprofit/check", methods=["GET"])
def check_take_profit():
    """Check if take-profit should trigger"""
    async def check():
        _, trading, _, tp, state = get_services()
        coin = state["current_coin"]
        settings = tp.get_settings(coin)
        if not settings.enabled:
            return {"should_close": False, "reason": "Take-profit disabled"}
        position = await trading.get_position()
        if not position:
            settings.reset_tracking()
            return {"should_close": False, "reason": "No position"}
        symbol = SUPPORTED_COINS.get(coin, "cmt_btcusdt")
        client, _, _, _, _ = get_services()
        ticker = await client.get_ticker(symbol)
        ticker_data = ticker.get("data", ticker) if isinstance(ticker, dict) else {}
        current_price = float(ticker_data.get("last", 0))
        if current_price <= 0:
            return {"should_close": False, "reason": "Price unavailable"}
        return tp.check_take_profit(coin, current_price, position["avg_price"], position["side"])
    return jsonify(run_async(check()))


@api_bp.route("/takeprofit/reset", methods=["POST"])
def reset_tp_tracking():
    """Reset take-profit tracking for current coin"""
    _, _, _, tp, state = get_services()
    tp.reset_tracking(state["current_coin"])
    return jsonify({"success": True, "message": f"Take-profit tracking reset for {state['current_coin']}"})
