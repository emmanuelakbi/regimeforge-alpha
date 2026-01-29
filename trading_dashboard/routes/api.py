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


@api_bp.route("/global")
def get_global_market():
    """
    Get global market data from CoinGecko.
    
    Returns BTC dominance, market sentiment, trending coins.
    Used for enhanced AI signal generation.
    """
    async def fetch():
        _, _, ai, _, state = get_services()
        try:
            summary = await ai.coingecko.get_market_summary(state["current_coin"])
            return {
                "success": True,
                "global": summary["global"],
                "coin": summary["coin"],
                "trending": summary["trending"],
                "current_coin": state["current_coin"]
            }
        except Exception as e:
            logger.error(f"CoinGecko fetch error: {e}")
            return {"success": False, "error": str(e)}
    return jsonify(run_async(fetch()))


@api_bp.route("/brief")
def get_market_brief():
    """
    Get AI-generated market brief using Claude LLM.
    
    Combines WEEX price data + CoinGecko context into a natural language summary.
    """
    async def fetch():
        _, _, ai, _, state = get_services()
        claude = current_app.config.get("claude_service")
        
        try:
            # Get AI analysis
            signal = await ai.get_cached_signal(max_age_seconds=30)
            market_data = await ai.fetch_market_data()
            
            # Get global context
            global_ctx = await ai._fetch_global_context(state["current_coin"])
            
            # Generate brief with Claude
            brief = claude.generate_market_brief(
                coin=state["current_coin"],
                price=market_data.price,
                change_24h=market_data.change_24h_pct,
                signal=signal.signal,
                confidence=signal.confidence,
                regime=signal.regime,
                btc_dominance=global_ctx.get("btc_dominance", 0),
                market_sentiment=global_ctx.get("market_sentiment", "UNKNOWN"),
                reasoning=signal.reasoning
            ) if claude and claude.enabled else f"{state['current_coin']} is showing {signal.signal} signals with {signal.confidence:.0%} confidence in a {signal.regime.lower().replace('_', ' ')} market."
            
            return {
                "success": True,
                "brief": brief,
                "coin": state["current_coin"],
                "signal": signal.signal,
                "confidence": signal.confidence,
                "claude_enabled": claude.enabled if claude else False
            }
        except Exception as e:
            logger.error(f"Market brief error: {e}")
            return {"success": False, "error": str(e)}
    
    return jsonify(run_async(fetch()))


@api_bp.route("/explain", methods=["GET", "POST"])
def explain_signal():
    """
    Get Claude's explanation of the current AI signal.
    """
    async def fetch():
        _, _, ai, _, state = get_services()
        claude = current_app.config.get("claude_service")
        
        try:
            signal = await ai.get_cached_signal(max_age_seconds=30)
            
            explanation = claude.explain_signal(
                coin=state["current_coin"],
                signal=signal.signal,
                confidence=signal.confidence,
                indicators=signal.indicators,
                reasoning=signal.reasoning
            ) if claude and claude.enabled else f"The AI generated a {signal.signal} signal based on: {'; '.join(signal.reasoning[:3])}"
            
            return {
                "success": True,
                "explanation": explanation,
                "signal": signal.signal,
                "confidence": signal.confidence,
                "claude_enabled": claude.enabled if claude else False
            }
        except Exception as e:
            logger.error(f"Signal explanation error: {e}")
            return {"success": False, "error": str(e)}
    
    return jsonify(run_async(fetch()))


@api_bp.route("/risk", methods=["POST"])
def assess_risk():
    """
    Get Claude's risk assessment for a proposed trade.
    Input size_usdt is the POSITION SIZE (not margin).
    Margin = position_size / leverage
    """
    async def fetch():
        req = request.get_json(silent=True) or {}
        
        client, _, ai, _, state = get_services()
        claude = current_app.config.get("claude_service")
        
        try:
            # Get parameters - size_usdt is POSITION SIZE
            position_size_usdt = float(req.get("size_usdt", 10))
            leverage = int(req.get("leverage", 20))
            signal = req.get("signal", "LONG")
            
            # Calculate margin (what you actually risk)
            margin_usdt = position_size_usdt / leverage
            
            # Get balance
            balance = 0
            try:
                balance_data = await client.get_assets()
                if isinstance(balance_data, dict) and balance_data.get("code") == "00000":
                    assets = balance_data.get("data", [])
                    for asset in assets if isinstance(assets, list) else []:
                        if asset.get("coinName") == "USDT":
                            balance = float(asset.get("available", 0))
                            break
            except Exception as e:
                logger.warning(f"Balance fetch failed: {e}")
                balance = 2000  # Default fallback for risk calc
            
            # If balance still 0, use fallback
            if balance <= 0:
                balance = 2000
            
            # Get volatility from AI
            volatility = 2.0
            try:
                ai_signal = await ai.get_cached_signal(max_age_seconds=30)
                volatility = ai_signal.indicators.get("volatility_pct", 2.0)
            except:
                pass
            
            # Risk is based on MARGIN (what you can lose), not position size
            risk_pct = (margin_usdt / balance) * 100
            
            # Assess risk
            if claude and claude.enabled:
                assessment = claude.assess_risk(
                    coin=state["current_coin"],
                    signal=signal,
                    position_size_usdt=position_size_usdt,
                    leverage=leverage,
                    volatility=volatility,
                    balance=balance
                )
                # Override risk_pct with correct calculation
                assessment["risk_pct"] = round(risk_pct, 1)
            else:
                if risk_pct > 10 or volatility > 5:
                    level = "HIGH"
                elif risk_pct > 5 or volatility > 3:
                    level = "MEDIUM"
                else:
                    level = "LOW"
                assessment = {
                    "level": level,
                    "risk_pct": round(risk_pct, 1),
                    "assessment": f"${margin_usdt:.2f} margin ({risk_pct:.1f}% of ${balance:.0f} balance) at {leverage}x leverage."
                }
            
            return {
                "success": True,
                "level": assessment.get("level", "UNKNOWN"),
                "risk_pct": assessment.get("risk_pct", risk_pct),
                "assessment": assessment.get("assessment", ""),
                "margin_usdt": round(margin_usdt, 2),
                "balance": round(balance, 2),
                "claude_enabled": claude.enabled if claude else False
            }
        except Exception as e:
            logger.error(f"Risk assessment error: {e}")
            return {"success": False, "error": str(e)}
    
    return jsonify(run_async(fetch()))


@api_bp.route("/claude/status")
def claude_status():
    """Check if Claude LLM is enabled"""
    claude = current_app.config.get("claude_service")
    return jsonify({
        "enabled": claude.enabled if claude else False,
        "model": claude.config.model_id if claude and claude.config else None
    })


@api_bp.route("/chat", methods=["POST"])
def chat():
    """
    AI Chat Advisor endpoint.
    Accepts a message and conversation history, returns Claude's response with full market context.
    """
    async def fetch():
        req = request.get_json(silent=True) or {}
        message = req.get("message", "").strip()
        history = req.get("history", [])  # List of {role, content} dicts
        
        if not message:
            return {"success": False, "error": "Message is required"}
        
        client, _, ai, _, state = get_services()
        claude = current_app.config.get("claude_service")
        
        if not claude:
            return {"success": False, "error": "Chat service unavailable"}
        
        try:
            # Gather context
            coin = state["current_coin"]
            
            # Get price
            price_data = {}
            try:
                symbol = SUPPORTED_COINS.get(coin, "cmt_btcusdt")
                ticker = await client.get_ticker(symbol)
                ticker_data = ticker.get("data", ticker) if isinstance(ticker, dict) else {}
                price_data = {
                    "price": float(ticker_data.get("last", 0)),
                    "change_24h": float(ticker_data.get("priceChangePercent", 0))
                }
            except:
                pass
            
            # Get AI signal
            signal_data = {}
            try:
                signal = await ai.get_cached_signal(max_age_seconds=60)
                signal_data = {
                    "signal": signal.signal,
                    "confidence": signal.confidence,
                    "regime": signal.regime
                }
            except:
                pass
            
            # Get balance
            balance = 0
            try:
                balance_resp = await client.get_assets()
                logger.info(f"Balance response type: {type(balance_resp)}, content: {balance_resp}")
                # Handle both list response and dict response
                assets = []
                if isinstance(balance_resp, list):
                    assets = balance_resp
                elif isinstance(balance_resp, dict):
                    assets = balance_resp.get("data", [])
                    if not assets and isinstance(balance_resp, dict):
                        # Maybe the response itself is the asset list wrapper
                        assets = [balance_resp] if balance_resp.get("coinName") or balance_resp.get("currency") else []
                
                logger.info(f"Assets to check: {assets}")
                for asset in assets:
                    coin_name = asset.get("coinName") or asset.get("currency") or asset.get("coin")
                    if coin_name == "USDT":
                        balance = float(asset.get("available") or asset.get("equity") or asset.get("balance") or 0)
                        logger.info(f"Found USDT balance: {balance}")
                        break
            except Exception as e:
                logger.error(f"Balance fetch error in chat: {e}")
                pass
            
            # Get position
            position = {}
            try:
                symbol = SUPPORTED_COINS.get(coin, "cmt_btcusdt")
                pos_resp = await client.get_position(symbol)
                pos_list = pos_resp.get("data", pos_resp) if isinstance(pos_resp, dict) else pos_resp
                
                if pos_list and isinstance(pos_list, list) and len(pos_list) > 0:
                    pos = pos_list[0]
                    size = float(pos.get("size", pos.get("total", 0)))
                    
                    if size > 0:
                        open_value = float(pos.get("open_value", pos.get("openValue", 0)))
                        side = pos.get("side", pos.get("holdSide", "LONG")).upper()
                        leverage = int(float(pos.get("leverage", 20)))
                        entry_price = open_value / size if size > 0 else 0
                        position = {
                            "side": side,
                            "size": size,
                            "entry_price": entry_price,
                            "leverage": leverage,
                            "margin": (size * entry_price) / leverage if leverage > 0 else 0,
                            "pnl": float(pos.get("unrealized_pnl", pos.get("unrealizedPL", 0)))
                        }
            except:
                pass
            
            # Get global market data
            global_data = {}
            try:
                global_ctx = await ai._fetch_global_context(coin)
                global_data = {
                    "btc_dominance": global_ctx.get("btc_dominance", 0),
                    "market_sentiment": global_ctx.get("market_sentiment", "UNKNOWN"),
                    "trending_coins": global_ctx.get("trending_coins", [])
                }
            except:
                pass
            
            # Build full context
            context = {
                "coin": coin,
                **price_data,
                **signal_data,
                "balance": balance,
                "position": position if position else None,
                **global_data
            }
            
            # Get Claude's response with conversation history
            response = claude.chat(message, context, history)
            
            return {
                "success": True,
                "response": response,
                "context": {
                    "coin": coin,
                    "price": price_data.get("price", 0),
                    "signal": signal_data.get("signal", "NEUTRAL"),
                    "has_position": bool(position)
                },
                "claude_enabled": claude.enabled
            }
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {"success": False, "error": str(e)}
    
    return jsonify(run_async(fetch()))


@api_bp.route("/chat/quick", methods=["POST"])
def chat_quick():
    """
    Quick action chat - predefined prompts for common questions.
    """
    async def fetch():
        req = request.get_json(silent=True) or {}
        action = req.get("action", "")
        
        prompts = {
            "analyze_position": "Analyze my current position. Should I hold, add, or close?",
            "market_overview": "Give me a quick market overview. What's the sentiment and any opportunities?",
            "risk_check": "What's my current risk exposure? Am I overexposed?",
            "trade_idea": "Based on current conditions, what's a good trade setup?",
            "explain_signal": "Explain the current AI signal in detail. Why this recommendation?",
            "trending": "What coins are trending and why? Any momentum plays?"
        }
        
        message = prompts.get(action)
        if not message:
            return {"success": False, "error": f"Unknown action: {action}"}
        
        # Just call chat with the predefined message
        client, _, ai, _, state = get_services()
        claude = current_app.config.get("claude_service")
        
        if not claude:
            return {"success": False, "error": "Chat service unavailable"}
        
        try:
            coin = state["current_coin"]
            symbol = SUPPORTED_COINS.get(coin, "cmt_btcusdt")
            
            # Quick context gathering
            price = 0
            try:
                ticker = await client.get_ticker(symbol)
                ticker_data = ticker.get("data", ticker) if isinstance(ticker, dict) else {}
                price = float(ticker_data.get("last", 0))
            except:
                pass
            
            signal_data = {}
            try:
                signal = await ai.get_cached_signal(max_age_seconds=60)
                signal_data = {"signal": signal.signal, "confidence": signal.confidence, "regime": signal.regime}
            except:
                pass
            
            # Get balance
            balance = 0
            try:
                balance_resp = await client.get_assets()
                assets = []
                if isinstance(balance_resp, list):
                    assets = balance_resp
                elif isinstance(balance_resp, dict):
                    assets = balance_resp.get("data", [])
                for asset in assets:
                    coin_name = asset.get("coinName") or asset.get("currency") or asset.get("coin")
                    if coin_name == "USDT":
                        balance = float(asset.get("available") or asset.get("equity") or asset.get("balance") or 0)
                        break
            except:
                pass
            
            # Get position
            position = None
            try:
                pos_resp = await client.get_position(symbol)
                pos_list = pos_resp.get("data", pos_resp) if isinstance(pos_resp, dict) else pos_resp
                
                if pos_list and isinstance(pos_list, list) and len(pos_list) > 0:
                    pos = pos_list[0]
                    size = float(pos.get("size", pos.get("total", 0)))
                    
                    if size > 0:
                        open_value = float(pos.get("open_value", pos.get("openValue", 0)))
                        side = pos.get("side", pos.get("holdSide", "LONG")).upper()
                        leverage = int(float(pos.get("leverage", 20)))
                        entry_price = open_value / size if size > 0 else 0
                        position = {
                            "side": side,
                            "size": size,
                            "entry_price": entry_price,
                            "leverage": leverage,
                            "margin": (size * entry_price) / leverage if leverage > 0 else 0,
                            "pnl": float(pos.get("unrealized_pnl", pos.get("unrealizedPL", 0)))
                        }
            except:
                pass
            
            context = {
                "coin": coin,
                "price": price,
                **signal_data,
                "balance": balance,
                "position": position
            }
            
            response = claude.chat(message, context)
            
            return {
                "success": True,
                "action": action,
                "response": response,
                "claude_enabled": claude.enabled
            }
        except Exception as e:
            logger.error(f"Quick chat error: {e}")
            return {"success": False, "error": str(e)}
    
    return jsonify(run_async(fetch()))
