"""
WEEX API Client for RegimeForge Alpha
Handles authentication, signing, and API requests
"""
import hmac
import hashlib
import base64
import time
import json
import asyncio
from typing import Dict, Any, Optional
import httpx

from .config import APIConfig


class WeexClient:
    """
    Async client for WEEX Contract API.
    
    Handles request signing and authentication.
    """
    
    def __init__(self, config: APIConfig):
        """
        Initialize the WEEX client.
        
        Args:
            config: API configuration with credentials
        """
        self.config = config
        self.timeout = 30.0
    
    def _create_signature(
        self,
        timestamp: str,
        method: str,
        path: str,
        query_string: str = "",
        body: str = ""
    ) -> str:
        """
        Create HMAC-SHA256 signature for request authentication.
        
        Args:
            timestamp: Unix timestamp in milliseconds
            method: HTTP method (GET/POST)
            path: API endpoint path
            query_string: URL query string (including ?)
            body: Request body for POST requests
            
        Returns:
            Base64-encoded signature
        """
        message = timestamp + method.upper() + path + query_string + body
        signature = hmac.new(
            self.config.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode()
    
    def _create_headers(
        self,
        method: str,
        path: str,
        body: str = "",
        query_string: str = ""
    ) -> Dict[str, str]:
        """
        Create authenticated headers for API request.
        
        Args:
            method: HTTP method
            path: API endpoint path
            body: Request body
            query_string: URL query string
            
        Returns:
            Headers dictionary
        """
        timestamp = str(int(time.time() * 1000))
        return {
            "ACCESS-KEY": self.config.api_key,
            "ACCESS-SIGN": self._create_signature(timestamp, method, path, query_string, body),
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.config.passphrase,
            "Content-Type": "application/json",
            "locale": "en-US"
        }
    
    async def request(
        self,
        method: str,
        path: str,
        query_string: str = "",
        body: str = ""
    ) -> Dict[str, Any]:
        """
        Make an authenticated API request.
        
        Args:
            method: HTTP method (GET/POST)
            path: API endpoint path
            query_string: URL query string (including ?)
            body: JSON body for POST requests
            
        Returns:
            Parsed JSON response or error dict
        """
        headers = self._create_headers(method, path, body, query_string)
        url = self.config.base_url + path + query_string
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    response = await client.post(url, headers=headers, content=body)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "error": response.text,
                        "status": response.status_code
                    }
            except httpx.TimeoutException:
                return {"error": "Request timeout", "status": 408}
            except Exception as e:
                return {"error": str(e), "status": 500}
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get price ticker for a symbol."""
        return await self.request("GET", "/capi/v2/market/ticker", f"?symbol={symbol}")
    
    async def get_depth(self, symbol: str) -> Dict[str, Any]:
        """Get order book depth for a symbol."""
        return await self.request("GET", "/capi/v2/market/depth", f"?symbol={symbol}")
    
    async def get_assets(self) -> Dict[str, Any]:
        """Get account assets/balance."""
        return await self.request("GET", "/capi/v2/account/assets", "")
    
    async def get_position(self, symbol: str) -> Dict[str, Any]:
        """Get position for a symbol."""
        return await self.request("GET", "/capi/v2/account/position/singlePosition", f"?symbol={symbol}")
    
    async def get_orders(self, symbol: str) -> Dict[str, Any]:
        """Get open orders for a symbol."""
        return await self.request("GET", "/capi/v2/order/current", f"?symbol={symbol}")
    
    async def get_history(self, symbol: str, page_size: int = 10) -> Dict[str, Any]:
        """Get order history for a symbol."""
        return await self.request("GET", "/capi/v2/order/history", f"?symbol={symbol}&pageSize={page_size}")
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place a new order."""
        body = json.dumps(order_data)
        return await self.request("POST", "/capi/v2/order/placeOrder", "", body)
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order."""
        body = json.dumps({"symbol": symbol, "orderId": order_id})
        return await self.request("POST", "/capi/v2/order/cancel_order", "", body)
    
    async def upload_ai_log(self, ai_log: Dict[str, Any]) -> Dict[str, Any]:
        """Upload AI log for hackathon verification."""
        body = json.dumps(ai_log)
        return await self.request("POST", "/capi/v2/order/uploadAiLog", "", body)


def run_async(coro):
    """
    Run an async coroutine synchronously.
    
    Note: This creates a new event loop for each call.
    For production, consider using quart or flask-async.
    
    Args:
        coro: Coroutine to execute
        
    Returns:
        Result of the coroutine
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
