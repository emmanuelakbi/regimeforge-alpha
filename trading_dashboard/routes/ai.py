"""
AI-related routes for RegimeForge Alpha
"""
from flask import Blueprint, jsonify, request, current_app
import logging

from ..api_client import run_async
from ..utils import validate_json_request, round_to_step, format_coin_size
from ..config import MODEL_VERSION

logger = logging.getLogger(__name__)
ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


def get_services():
    """Get services from app context"""
    return (
        current_app.config["client"],
        current_app.config["trading_service"],
        current_app.config["ai_engine"],
        current_app.config["tp_service"],
        current_app.config["state"]
    )


@ai_bp.route("/analyze")
def ai_analyze():
    """Run AI analysis and return signal"""
    async def analyze():
        try:
            _, _, ai, _, state = get_services()
            signal = await ai.get_cached_signal(max_age_seconds=10)
            return {
                "signal": signal.signal,
                "confidence": signal.confidence,
                "regime": signal.regime,
                "reasoning": signal.reasoning,
                "indicators": signal.indicators,
                "model": MODEL_VERSION,
                "coin": state["current_coin"]
            }
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return {"error": str(e)}
    return jsonify(run_async(analyze()))


@ai_bp.route("/trade", methods=["POST"])
def ai_trade():
    """Execute AI-driven trade with automatic log submission"""
    async def execute():
        try:
            req = request.get_json(silent=True)
            is_valid, error = validate_json_request(req)
            if not is_valid:
                return {"success": False, "error": error}
            
            direction = req.get("direction", "long")
            size = req.get("size", "0.001")
            
            if not size or float(size) <= 0:
                return {"success": False, "error": "Invalid size"}
            
            _, trading, ai, _, state = get_services()
            
            signal = await ai.analyze(force_signal=direction.upper())
            market_data = await ai.fetch_market_data()
            
            result = await trading.place_order(
                side=direction,
                size=size,
                order_type="market",
                client_oid_prefix="ai"
            )
            
            if result.get("success"):
                market_dict = {
                    "price": market_data.price,
                    "high_24h": market_data.high_24h,
                    "low_24h": market_data.low_24h,
                    "timestamp": market_data.timestamp
                }
                log_result, _ = await trading.submit_ai_log(
                    result.get("order_id"),
                    market_dict,
                    signal,
                    direction.upper()
                )
                
                return {
                    "success": True,
                    "order_id": result.get("order_id"),
                    "signal": signal.signal,
                    "confidence": signal.confidence,
                    "regime": signal.regime,
                    "ai_log_submitted": log_result.get("code") == "00000" or "success" in str(log_result.get("data", "")).lower()
                }
            else:
                return {"success": False, "error": result.get("error", "Trade failed")}
        except Exception as e:
            logger.error(f"AI trade error: {e}")
            return {"success": False, "error": str(e)}
    
    return jsonify(run_async(execute()))
