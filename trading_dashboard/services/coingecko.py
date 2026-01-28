"""
CoinGecko API Client for RegimeForge Alpha
Provides global market data for enhanced AI signal generation
"""
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# CoinGecko coin ID mapping
COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "BNB": "binancecoin",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "LTC": "litecoin"
}


@dataclass
class GlobalMarketData:
    """Global cryptocurrency market data from CoinGecko"""
    total_market_cap_usd: float
    total_volume_24h_usd: float
    btc_dominance: float
    eth_dominance: float
    market_cap_change_24h_pct: float
    active_cryptocurrencies: int
    timestamp: float
    
    @property
    def market_sentiment(self) -> str:
        """Derive market sentiment from global data"""
        if self.market_cap_change_24h_pct > 3:
            return "BULLISH"
        elif self.market_cap_change_24h_pct > 1:
            return "SLIGHTLY_BULLISH"
        elif self.market_cap_change_24h_pct < -3:
            return "BEARISH"
        elif self.market_cap_change_24h_pct < -1:
            return "SLIGHTLY_BEARISH"
        return "NEUTRAL"
    
    @property
    def btc_dominance_trend(self) -> str:
        """Interpret BTC dominance for altcoin trading"""
        if self.btc_dominance > 55:
            return "HIGH"  # Altcoins may underperform
        elif self.btc_dominance < 45:
            return "LOW"   # Altcoin season potential
        return "NORMAL"


@dataclass
class CoinMarketData:
    """Individual coin market data from CoinGecko"""
    coin_id: str
    symbol: str
    current_price: float
    market_cap: int
    market_cap_rank: int
    price_change_24h_pct: float
    price_change_7d_pct: float
    total_volume: float
    high_24h: float
    low_24h: float
    ath: float
    ath_change_pct: float
    timestamp: float


class CoinGeckoClient:
    """
    CoinGecko API client with caching for rate limit compliance.
    
    Free tier: 30 calls/minute
    Caches responses to minimize API calls.
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    CACHE_TTL_GLOBAL = 120  # 2 minutes for global data
    CACHE_TTL_COINS = 60    # 1 minute for coin data
    CACHE_TTL_TRENDING = 300  # 5 minutes for trending
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_request_time = 0
        self._min_request_interval = 2.0  # 2 seconds between requests
    
    def _get_cached(self, key: str, ttl: int) -> Optional[Any]:
        """Get cached data if still valid"""
        if key in self._cache:
            cached = self._cache[key]
            if time.time() - cached["timestamp"] < ttl:
                return cached["data"]
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Store data in cache"""
        self._cache[key] = {"data": data, "timestamp": time.time()}
    
    async def _request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Make rate-limited request to CoinGecko API"""
        # Rate limiting
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            await self._async_sleep(self._min_request_interval - elapsed)
        
        url = f"{self.BASE_URL}{endpoint}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params)
                self._last_request_time = time.time()
                
                if response.status_code == 429:
                    logger.warning("CoinGecko rate limit hit, using cached data")
                    return {}
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"CoinGecko API error: {e}")
                return {}
    
    async def _async_sleep(self, seconds: float):
        """Async sleep helper"""
        import asyncio
        await asyncio.sleep(seconds)
    
    async def get_global_data(self) -> Optional[GlobalMarketData]:
        """
        Fetch global cryptocurrency market data.
        
        Endpoint: GET /global
        Used for: Market sentiment, BTC dominance analysis
        """
        cache_key = "global"
        cached = self._get_cached(cache_key, self.CACHE_TTL_GLOBAL)
        if cached:
            return cached
        
        data = await self._request("/global")
        if not data or "data" not in data:
            return None
        
        global_data = data["data"]
        
        result = GlobalMarketData(
            total_market_cap_usd=global_data.get("total_market_cap", {}).get("usd", 0),
            total_volume_24h_usd=global_data.get("total_volume", {}).get("usd", 0),
            btc_dominance=global_data.get("market_cap_percentage", {}).get("btc", 0),
            eth_dominance=global_data.get("market_cap_percentage", {}).get("eth", 0),
            market_cap_change_24h_pct=global_data.get("market_cap_change_percentage_24h_usd", 0),
            active_cryptocurrencies=global_data.get("active_cryptocurrencies", 0),
            timestamp=time.time()
        )
        
        self._set_cache(cache_key, result)
        logger.info(f"CoinGecko global data: BTC dom {result.btc_dominance:.1f}%, "
                   f"market sentiment: {result.market_sentiment}")
        return result
    
    async def get_coin_data(self, symbols: list = None) -> Dict[str, CoinMarketData]:
        """
        Fetch market data for specific coins.
        
        Endpoint: GET /coins/markets
        Used for: Cross-reference prices, 7d trends, ATH distance
        """
        if symbols is None:
            symbols = list(COINGECKO_IDS.keys())
        
        cache_key = f"coins_{'_'.join(sorted(symbols))}"
        cached = self._get_cached(cache_key, self.CACHE_TTL_COINS)
        if cached:
            return cached
        
        # Convert symbols to CoinGecko IDs
        ids = [COINGECKO_IDS[s] for s in symbols if s in COINGECKO_IDS]
        if not ids:
            return {}
        
        params = {
            "vs_currency": "usd",
            "ids": ",".join(ids),
            "order": "market_cap_desc",
            "sparkline": "false",
            "price_change_percentage": "24h,7d"
        }
        
        data = await self._request("/coins/markets", params)
        if not data:
            return {}
        
        result = {}
        for coin in data:
            symbol = coin.get("symbol", "").upper()
            result[symbol] = CoinMarketData(
                coin_id=coin.get("id", ""),
                symbol=symbol,
                current_price=coin.get("current_price", 0),
                market_cap=coin.get("market_cap", 0),
                market_cap_rank=coin.get("market_cap_rank", 0),
                price_change_24h_pct=coin.get("price_change_percentage_24h", 0),
                price_change_7d_pct=coin.get("price_change_percentage_7d_in_currency", 0),
                total_volume=coin.get("total_volume", 0),
                high_24h=coin.get("high_24h", 0),
                low_24h=coin.get("low_24h", 0),
                ath=coin.get("ath", 0),
                ath_change_pct=coin.get("ath_change_percentage", 0),
                timestamp=time.time()
            )
        
        self._set_cache(cache_key, result)
        return result
    
    async def get_trending(self) -> list:
        """
        Fetch trending coins.
        
        Endpoint: GET /search/trending
        Used for: Identify market attention, potential momentum plays
        """
        cache_key = "trending"
        cached = self._get_cached(cache_key, self.CACHE_TTL_TRENDING)
        if cached:
            return cached
        
        data = await self._request("/search/trending")
        if not data or "coins" not in data:
            return []
        
        result = []
        for item in data.get("coins", [])[:10]:
            coin = item.get("item", {})
            result.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "score": coin.get("score", 0)
            })
        
        self._set_cache(cache_key, result)
        return result
    
    async def get_market_summary(self, coin: str = "BTC") -> Dict[str, Any]:
        """
        Get comprehensive market summary for AI analysis.
        
        Combines global data + specific coin data for signal enhancement.
        """
        global_data = await self.get_global_data()
        coin_data = await self.get_coin_data([coin])
        trending = await self.get_trending()
        
        # Check if current coin is trending
        coin_is_trending = any(t["symbol"] == coin for t in trending)
        
        summary = {
            "global": {
                "btc_dominance": global_data.btc_dominance if global_data else 0,
                "market_sentiment": global_data.market_sentiment if global_data else "UNKNOWN",
                "market_cap_change_24h": global_data.market_cap_change_24h_pct if global_data else 0,
                "btc_dominance_trend": global_data.btc_dominance_trend if global_data else "UNKNOWN"
            },
            "coin": {},
            "trending": {
                "coins": [t["symbol"] for t in trending[:5]],
                "current_coin_trending": coin_is_trending
            }
        }
        
        if coin in coin_data:
            cd = coin_data[coin]
            summary["coin"] = {
                "price_change_7d": cd.price_change_7d_pct,
                "ath_distance_pct": cd.ath_change_pct,
                "market_cap_rank": cd.market_cap_rank
            }
        
        return summary
    
    def clear_cache(self):
        """Clear all cached data"""
        self._cache = {}
