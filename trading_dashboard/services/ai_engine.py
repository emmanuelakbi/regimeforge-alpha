"""
RegimeForge Alpha AI Engine
Market regime detection and signal generation with CoinGecko integration
"""
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from ..models import MarketData, AISignal
from ..api_client import WeexClient
from ..utils import parse_ticker_data, parse_depth_data
from ..config import (
    SUPPORTED_COINS,
    MODEL_VERSION,
    STRONG_SUPPORT_THRESHOLD,
    SUPPORT_THRESHOLD,
    STRONG_RESISTANCE_THRESHOLD,
    RESISTANCE_THRESHOLD,
    STRONG_SIGNAL_SCORE,
    MODERATE_SIGNAL_SCORE,
    HIGH_VOLATILITY_THRESHOLD,
    LOW_VOLATILITY_THRESHOLD,
    EXTREME_VOLATILITY_THRESHOLD,
    BULL_TREND_THRESHOLD,
    BEAR_TREND_THRESHOLD,
    RSI_BULL_THRESHOLD,
    RSI_BEAR_THRESHOLD,
    STRONG_OVERSOLD_THRESHOLD,
    MILD_OVERSOLD_THRESHOLD,
    STRONG_OVERBOUGHT_THRESHOLD,
    MILD_OVERBOUGHT_THRESHOLD,
    MAX_CONFIDENCE,
    MIN_CONFIDENCE,
    BASE_CONFIDENCE,
    CONFIDENCE_INCREMENT,
)
from .coingecko import CoinGeckoClient

logger = logging.getLogger(__name__)


class RegimeForgeAI:
    """
    RegimeForge Alpha ML Engine for market regime detection and signal generation.
    
    Analyzes market data to detect regimes (trending, ranging, volatile) and
    generates trading signals with confidence scores.
    """
    
    def __init__(self, client: WeexClient, current_coin_getter):
        """
        Initialize the AI engine.
        
        Args:
            client: WEEX API client for market data
            current_coin_getter: Callable that returns current coin symbol
        """
        self.client = client
        self.get_current_coin = current_coin_getter
        self.model_version = MODEL_VERSION
        self.last_signal = "NEUTRAL"
        self.signal_history: List[str] = []
        self.last_analysis_time = 0
        self._cache = {"signal": None, "timestamp": 0}
        
        # CoinGecko integration for global market context
        self.coingecko = CoinGeckoClient()
        self._global_market_cache: Dict[str, Any] = {}
    
    def get_symbol(self) -> str:
        """Get current trading symbol"""
        coin = self.get_current_coin()
        return SUPPORTED_COINS.get(coin, "cmt_btcusdt")
    
    async def fetch_market_data(self) -> MarketData:
        """
        Fetch comprehensive market data for AI analysis.
        
        Returns:
            MarketData object with current market state
        """
        symbol = self.get_symbol()
        
        ticker = await self.client.get_ticker(symbol)
        depth = await self.client.get_depth(symbol)
        
        ticker_data = parse_ticker_data(ticker)
        price = ticker_data["price"]
        
        depth_data = parse_depth_data(depth, price)
        
        spread_pct = 0.0
        if price > 0:
            spread_pct = ((depth_data["ask_price"] - depth_data["bid_price"]) / price) * 100
        
        return MarketData(
            price=price,
            high_24h=ticker_data["high_24h"],
            low_24h=ticker_data["low_24h"],
            volume_24h=ticker_data["volume"],
            change_24h_pct=ticker_data["change_pct"],
            bid_price=depth_data["bid_price"],
            ask_price=depth_data["ask_price"],
            spread_pct=spread_pct
        )
    
    def detect_regime(self, market_data: MarketData, indicators: dict) -> str:
        """
        Detect market regime based on indicators.
        
        Args:
            market_data: Current market data
            indicators: Calculated indicators
            
        Returns:
            Regime string: BULL_TRENDING, BEAR_TRENDING, RANGE_BOUND, 
                          HIGH_VOLATILITY, or LOW_VOLATILITY
        """
        rsi = indicators.get("rsi", 50)
        volatility = indicators.get("volatility_pct", 2)
        trend_strength = indicators.get("trend_strength", 0)
        
        if volatility > HIGH_VOLATILITY_THRESHOLD:
            return "HIGH_VOLATILITY"
        if volatility < LOW_VOLATILITY_THRESHOLD:
            return "LOW_VOLATILITY"
        if trend_strength > BULL_TREND_THRESHOLD and rsi > RSI_BULL_THRESHOLD:
            return "BULL_TRENDING"
        if trend_strength < BEAR_TREND_THRESHOLD and rsi < RSI_BEAR_THRESHOLD:
            return "BEAR_TRENDING"
        return "RANGE_BOUND"
    
    async def analyze(self, force_signal: Optional[str] = None) -> AISignal:
        """
        Run full AI analysis and generate trading signal.
        
        Combines WEEX market data with CoinGecko global market context
        for enhanced signal generation.
        
        Args:
            force_signal: Optional signal to force (LONG/SHORT) for user-requested trades
            
        Returns:
            AISignal with signal, confidence, regime, and reasoning
        """
        market_data = await self.fetch_market_data()
        
        # Fetch CoinGecko global market context
        coin = self.get_current_coin()
        global_context = await self._fetch_global_context(coin)
        
        # Calculate indicators
        price_position = market_data.price_position
        volatility_pct = market_data.volatility_pct
        
        # change_24h_pct is already converted to percentage in parse_ticker_data
        change_24h = market_data.change_24h_pct
        
        rsi_estimate = price_position
        trend_strength = max(-1, min(1, change_24h / 5))
        
        indicators = {
            "rsi": round(rsi_estimate, 1),
            "price_position_pct": round(price_position, 1),
            "volatility_pct": round(volatility_pct, 2),
            "trend_strength": round(trend_strength, 2),
            "spread_pct": round(market_data.spread_pct, 4),
            "price_change_24h": round(change_24h, 2),
            "high_24h": market_data.high_24h,
            "low_24h": market_data.low_24h,
            # CoinGecko indicators
            "btc_dominance": global_context.get("btc_dominance", 0),
            "market_sentiment": global_context.get("market_sentiment", "UNKNOWN"),
            "global_market_change_24h": global_context.get("market_cap_change_24h", 0),
            "price_change_7d": global_context.get("price_change_7d", 0),
            "coin_trending": global_context.get("coin_trending", False)
        }
        
        regime = self.detect_regime(market_data, indicators)
        
        # Generate signal
        reasoning = []
        long_score = 0
        short_score = 0
        
        # === CoinGecko Global Market Analysis ===
        market_sentiment = global_context.get("market_sentiment", "NEUTRAL")
        btc_dominance = global_context.get("btc_dominance", 50)
        global_change = global_context.get("market_cap_change_24h", 0)
        price_7d = global_context.get("price_change_7d", 0)
        coin_trending = global_context.get("coin_trending", False)
        
        # Global sentiment influence
        if market_sentiment == "BULLISH":
            long_score += MODERATE_SIGNAL_SCORE
            reasoning.append(f"🌍 Global market bullish (+{global_change:.1f}% 24h)")
        elif market_sentiment == "BEARISH":
            short_score += MODERATE_SIGNAL_SCORE
            reasoning.append(f"🌍 Global market bearish ({global_change:.1f}% 24h)")
        elif market_sentiment in ["SLIGHTLY_BULLISH", "SLIGHTLY_BEARISH"]:
            reasoning.append(f"🌍 Global market {market_sentiment.lower().replace('_', ' ')} ({global_change:+.1f}%)")
        
        # BTC dominance analysis (for altcoins)
        if coin != "BTC" and btc_dominance > 0:
            if btc_dominance > 55:
                short_score += 1
                reasoning.append(f"📊 High BTC dominance ({btc_dominance:.1f}%) - altcoin headwind")
            elif btc_dominance < 45:
                long_score += 1
                reasoning.append(f"📊 Low BTC dominance ({btc_dominance:.1f}%) - altcoin tailwind")
        
        # 7-day trend from CoinGecko
        if price_7d > 10:
            short_score += 1
            reasoning.append(f"📈 Strong 7d rally (+{price_7d:.1f}%) - potential exhaustion")
        elif price_7d < -10:
            long_score += 1
            reasoning.append(f"📉 7d decline ({price_7d:.1f}%) - potential reversal")
        
        # Trending coin boost
        if coin_trending:
            long_score += 1
            reasoning.append(f"🔥 {coin} is trending on CoinGecko - momentum boost")
        
        # === WEEX Price Position Analysis ===
        if price_position < STRONG_SUPPORT_THRESHOLD:
            long_score += STRONG_SIGNAL_SCORE
            reasoning.append(f"Price near 24h low ({price_position:.0f}%) - strong support zone")
        elif price_position < SUPPORT_THRESHOLD:
            long_score += MODERATE_SIGNAL_SCORE
            reasoning.append(f"Price in lower 24h range ({price_position:.0f}%) - potential bounce")
        elif price_position > STRONG_RESISTANCE_THRESHOLD:
            short_score += STRONG_SIGNAL_SCORE
            reasoning.append(f"Price near 24h high ({price_position:.0f}%) - strong resistance zone")
        elif price_position > RESISTANCE_THRESHOLD:
            short_score += MODERATE_SIGNAL_SCORE
            reasoning.append(f"Price in upper 24h range ({price_position:.0f}%) - potential pullback")
        else:
            reasoning.append(f"Price mid-range ({price_position:.0f}%) - no clear direction")
        
        # 24h change analysis
        if change_24h < STRONG_OVERSOLD_THRESHOLD:
            long_score += MODERATE_SIGNAL_SCORE
            reasoning.append(f"24h down {change_24h:.1f}% - oversold, reversal potential")
        elif change_24h < MILD_OVERSOLD_THRESHOLD:
            long_score += 1
            reasoning.append(f"24h slightly down {change_24h:.1f}%")
        elif change_24h > STRONG_OVERBOUGHT_THRESHOLD:
            short_score += MODERATE_SIGNAL_SCORE
            reasoning.append(f"24h up {change_24h:.1f}% - overbought, pullback potential")
        elif change_24h > MILD_OVERBOUGHT_THRESHOLD:
            short_score += 1
            reasoning.append(f"24h slightly up {change_24h:.1f}%")
        
        # Volatility note
        if volatility_pct > EXTREME_VOLATILITY_THRESHOLD:
            reasoning.append(f"High volatility ({volatility_pct:.1f}%) - increased risk")
        elif volatility_pct < 1.5:
            reasoning.append(f"Low volatility ({volatility_pct:.1f}%) - consolidation phase")
        
        # Calculate raw signal
        score_diff = long_score - short_score
        raw_signal = "NEUTRAL"
        confidence = 0.5
        
        if score_diff >= 3:
            raw_signal = "LONG"
            confidence = min(0.85, BASE_CONFIDENCE + score_diff * CONFIDENCE_INCREMENT)
        elif score_diff <= -3:
            raw_signal = "SHORT"
            confidence = min(0.85, BASE_CONFIDENCE + abs(score_diff) * CONFIDENCE_INCREMENT)
        else:
            raw_signal = "NEUTRAL"
            confidence = 0.45
        
        # Update signal history
        self.signal_history.append(raw_signal)
        if len(self.signal_history) > 10:
            self.signal_history = self.signal_history[-10:]
        
        # Apply signal smoothing
        signal = self._smooth_signal(raw_signal, price_position, reasoning)
        
        self.last_signal = signal
        
        # Adjust confidence for regime
        if regime == "HIGH_VOLATILITY":
            confidence *= 0.85
            reasoning.append(f"High volatility ({volatility_pct:.1f}%) - reduced confidence")
        elif regime == "LOW_VOLATILITY":
            confidence *= 0.9
            reasoning.append(f"Low volatility ({volatility_pct:.1f}%) - range-bound market")
        
        # Boost confidence if global sentiment aligns with signal
        if (signal == "LONG" and market_sentiment in ["BULLISH", "SLIGHTLY_BULLISH"]) or \
           (signal == "SHORT" and market_sentiment in ["BEARISH", "SLIGHTLY_BEARISH"]):
            confidence = min(MAX_CONFIDENCE, confidence * 1.05)
            reasoning.append("✓ Signal aligned with global market sentiment")
        
        # Handle forced signal
        if force_signal and force_signal in ["LONG", "SHORT"]:
            original_signal = signal
            signal = force_signal
            if original_signal != force_signal:
                reasoning.insert(0, f"User requested {signal} (AI suggested {original_signal})")
            else:
                reasoning.insert(0, f"AI confirms {signal} signal")
        
        confidence = min(MAX_CONFIDENCE, max(MIN_CONFIDENCE, confidence))
        
        if not reasoning:
            reasoning.append("Market conditions neutral")
        
        return AISignal(
            signal=signal,
            confidence=round(confidence, 2),
            regime=regime,
            reasoning=reasoning,
            indicators=indicators,
            recommended_size="0.001"
        )
    
    async def _fetch_global_context(self, coin: str) -> Dict[str, Any]:
        """
        Fetch global market context from CoinGecko.
        
        Uses CoinGecko API to get:
        - Global market sentiment (total market cap change)
        - BTC dominance (affects altcoin performance)
        - 7-day price trend for the specific coin
        - Trending status
        
        Returns:
            Dict with global market indicators
        """
        try:
            summary = await self.coingecko.get_market_summary(coin)
            
            return {
                "btc_dominance": summary["global"]["btc_dominance"],
                "market_sentiment": summary["global"]["market_sentiment"],
                "market_cap_change_24h": summary["global"]["market_cap_change_24h"],
                "btc_dominance_trend": summary["global"]["btc_dominance_trend"],
                "price_change_7d": summary["coin"].get("price_change_7d", 0),
                "ath_distance": summary["coin"].get("ath_distance_pct", 0),
                "coin_trending": summary["trending"]["current_coin_trending"],
                "trending_coins": summary["trending"]["coins"]
            }
        except Exception as e:
            logger.warning(f"CoinGecko fetch failed: {e}, using defaults")
            return {
                "btc_dominance": 0,
                "market_sentiment": "UNKNOWN",
                "market_cap_change_24h": 0,
                "btc_dominance_trend": "UNKNOWN",
                "price_change_7d": 0,
                "ath_distance": 0,
                "coin_trending": False,
                "trending_coins": []
            }
    
    def _smooth_signal(self, raw_signal: str, price_position: float, reasoning: list) -> str:
        """
        Apply signal smoothing to reduce whipsaws.
        
        Args:
            raw_signal: The raw calculated signal
            price_position: Current price position percentage
            reasoning: List to append reasoning to
            
        Returns:
            Smoothed signal
        """
        # Strong signal bypass for extreme price positions
        if price_position < STRONG_SUPPORT_THRESHOLD and raw_signal == "LONG":
            reasoning.insert(0, f"⚡ Strong buy zone (RSI {price_position:.0f}%) - immediate signal")
            return "LONG"
        elif price_position > STRONG_RESISTANCE_THRESHOLD and raw_signal == "SHORT":
            reasoning.insert(0, f"⚡ Strong sell zone (RSI {price_position:.0f}%) - immediate signal")
            return "SHORT"
        
        # Apply history-based smoothing
        if len(self.signal_history) >= 5:
            recent = self.signal_history[-5:]
            if recent.count(raw_signal) >= 4:
                return raw_signal
            elif recent.count(self.last_signal) >= 2:
                if raw_signal != self.last_signal:
                    reasoning.append(f"Maintaining {self.last_signal} (awaiting confirmation)")
                return self.last_signal
            else:
                return "NEUTRAL"
        
        return raw_signal
    
    async def get_cached_signal(self, max_age_seconds: int = 10) -> AISignal:
        """
        Get cached AI signal if fresh, otherwise compute new one.
        
        Args:
            max_age_seconds: Maximum age of cached signal
            
        Returns:
            AISignal (cached or fresh)
        """
        if time.time() - self._cache["timestamp"] < max_age_seconds and self._cache["signal"]:
            return self._cache["signal"]
        
        signal = await self.analyze()
        self._cache["signal"] = signal
        self._cache["timestamp"] = time.time()
        return signal
    
    def reset(self):
        """Reset AI state for coin change"""
        self.signal_history = []
        self.last_signal = "NEUTRAL"
        self._cache = {"signal": None, "timestamp": 0}
