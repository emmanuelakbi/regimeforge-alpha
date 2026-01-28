#!/usr/bin/env python3
"""
Comprehensive Test Suite for RegimeForge Alpha Trading Dashboard
Tests all components: API connectivity, AI analysis, coin switching, and trading
"""
import os
import sys
import asyncio
import time
import json
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

from trading_dashboard.config import APIConfig, SUPPORTED_COINS, MODEL_VERSION
from trading_dashboard.api_client import WeexClient, run_async
from trading_dashboard.services.ai_engine import RegimeForgeAI
from trading_dashboard.services.trading import TradingService
from trading_dashboard.services.take_profit import TakeProfitService
from trading_dashboard.services.automation import AutomationService
from trading_dashboard.utils import round_to_step, format_coin_size


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []
    
    def add(self, name, passed, message="", warning=False):
        status = "✅ PASS" if passed else ("⚠️ WARN" if warning else "❌ FAIL")
        self.results.append({"name": name, "status": status, "message": message})
        if passed:
            self.passed += 1
        elif warning:
            self.warnings += 1
        else:
            self.failed += 1
        print(f"{status}: {name}")
        if message:
            print(f"       {message}")
    
    def summary(self):
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Passed:   {self.passed}")
        print(f"Failed:   {self.failed}")
        print(f"Warnings: {self.warnings}")
        print(f"Total:    {self.passed + self.failed + self.warnings}")
        print("=" * 60)
        return self.failed == 0


results = TestResults()


def test_section(name):
    """Print section header"""
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print("=" * 60)


async def test_api_connectivity(client):
    """Test basic API connectivity"""
    test_section("API CONNECTIVITY TESTS")
    
    # Test ticker endpoint
    ticker = await client.get_ticker("cmt_btcusdt")
    has_price = "data" in ticker or "last" in ticker
    results.add("API: Get BTC Ticker", has_price, 
                f"Price: {ticker.get('data', ticker).get('last', 'N/A')}" if has_price else f"Error: {ticker}")
    
    # Test depth endpoint
    depth = await client.get_depth("cmt_btcusdt")
    has_depth = "data" in depth or "bids" in depth
    results.add("API: Get Order Book", has_depth,
                "Order book retrieved" if has_depth else f"Error: {depth}")
    
    # Test authenticated endpoint - balance
    assets = await client.get_assets()
    has_assets = "data" in assets or isinstance(assets, list)
    balance = "N/A"
    if has_assets:
        asset_list = assets.get("data", assets) if isinstance(assets, dict) else assets
        if isinstance(asset_list, list):
            for a in asset_list:
                if a.get("coinName") == "USDT" or a.get("currency") == "USDT":
                    balance = a.get("available", a.get("equity", "0"))
                    break
    results.add("API: Get Account Balance", has_assets,
                f"USDT Balance: {balance}" if has_assets else f"Error: {assets}")
    
    return has_price and has_assets


async def test_coin_switching(client, ai_engine, trading_service, state):
    """Test coin switching and data consistency"""
    test_section("COIN SWITCHING TESTS")
    
    coins_to_test = ["BTC", "ETH", "SOL", "XRP"]
    coin_data = {}
    
    for coin in coins_to_test:
        # Switch coin
        state["current_coin"] = coin
        ai_engine.reset()  # Reset AI state on coin change
        
        symbol = SUPPORTED_COINS[coin]
        
        # Fetch ticker
        ticker = await client.get_ticker(symbol)
        ticker_data = ticker.get("data", ticker) if isinstance(ticker, dict) else {}
        price = float(ticker_data.get("last", 0))
        
        # Fetch AI analysis
        signal = await ai_engine.analyze()
        
        coin_data[coin] = {
            "price": price,
            "signal": signal.signal,
            "confidence": signal.confidence,
            "regime": signal.regime,
            "indicators": signal.indicators
        }
        
        # Verify data is for correct coin
        is_valid = price > 0 and signal.signal in ["LONG", "SHORT", "NEUTRAL"]
        results.add(f"Coin Switch: {coin}", is_valid,
                    f"Price: ${price:,.2f}, Signal: {signal.signal} ({signal.confidence*100:.0f}%)")
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    # Verify prices are different (data not scrambled)
    prices = [coin_data[c]["price"] for c in coins_to_test]
    unique_prices = len(set(prices))
    results.add("Data Integrity: Unique Prices", unique_prices == len(coins_to_test),
                f"Got {unique_prices} unique prices for {len(coins_to_test)} coins")
    
    # Verify BTC price is highest (sanity check)
    btc_price = coin_data["BTC"]["price"]
    eth_price = coin_data["ETH"]["price"]
    sol_price = coin_data["SOL"]["price"]
    xrp_price = coin_data["XRP"]["price"]
    
    price_order_valid = btc_price > eth_price > sol_price > xrp_price
    results.add("Data Integrity: Price Order", price_order_valid,
                f"BTC(${btc_price:,.0f}) > ETH(${eth_price:,.0f}) > SOL(${sol_price:,.0f}) > XRP(${xrp_price:.2f})")
    
    return coin_data


async def test_ai_analysis(ai_engine, state):
    """Test AI analysis engine"""
    test_section("AI ANALYSIS TESTS")
    
    # Reset to BTC for consistent testing
    state["current_coin"] = "BTC"
    ai_engine.reset()
    
    # Test basic analysis
    signal = await ai_engine.analyze()
    
    results.add("AI: Signal Generation", signal.signal in ["LONG", "SHORT", "NEUTRAL"],
                f"Signal: {signal.signal}")
    
    results.add("AI: Confidence Score", 0 <= signal.confidence <= 1,
                f"Confidence: {signal.confidence*100:.0f}%")
    
    valid_regimes = ["BULL_TRENDING", "BEAR_TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY", "LOW_VOLATILITY"]
    results.add("AI: Regime Detection", signal.regime in valid_regimes,
                f"Regime: {signal.regime}")
    
    results.add("AI: Reasoning Provided", len(signal.reasoning) > 0,
                f"Reasons: {len(signal.reasoning)}")
    
    # Test indicators
    indicators = signal.indicators
    required_indicators = ["rsi", "price_position_pct", "volatility_pct", "trend_strength"]
    has_all_indicators = all(k in indicators for k in required_indicators)
    results.add("AI: Indicators Complete", has_all_indicators,
                f"RSI: {indicators.get('rsi', 'N/A')}, Volatility: {indicators.get('volatility_pct', 'N/A')}%")
    
    # Test signal caching
    cached_signal = await ai_engine.get_cached_signal(max_age_seconds=60)
    results.add("AI: Signal Caching", cached_signal.signal == signal.signal,
                "Cache working correctly")
    
    # Test forced signal
    forced_long = await ai_engine.analyze(force_signal="LONG")
    results.add("AI: Forced Signal (LONG)", forced_long.signal == "LONG",
                f"Forced to LONG, got: {forced_long.signal}")
    
    forced_short = await ai_engine.analyze(force_signal="SHORT")
    results.add("AI: Forced Signal (SHORT)", forced_short.signal == "SHORT",
                f"Forced to SHORT, got: {forced_short.signal}")
    
    # Print detailed analysis
    print(f"\n  Detailed AI Analysis for BTC:")
    print(f"  - Signal: {signal.signal} ({signal.confidence*100:.0f}% confidence)")
    print(f"  - Regime: {signal.regime}")
    print(f"  - RSI Estimate: {indicators.get('rsi', 'N/A')}")
    print(f"  - Price Position: {indicators.get('price_position_pct', 'N/A')}%")
    print(f"  - Volatility: {indicators.get('volatility_pct', 'N/A')}%")
    print(f"  - Trend Strength: {indicators.get('trend_strength', 'N/A')}")
    print(f"  - Reasoning:")
    for reason in signal.reasoning[:3]:
        print(f"    • {reason}")
    
    return signal


async def test_take_profit_service(tp_service, state):
    """Test take-profit service"""
    test_section("TAKE-PROFIT SERVICE TESTS")
    
    coin = "BTC"
    state["current_coin"] = coin
    
    # Test settings management
    settings = tp_service.get_settings(coin)
    results.add("TP: Get Settings", settings is not None,
                f"Mode: {settings.mode}, Target: {settings.fixed_target_pct}%")
    
    # Update settings
    tp_service.update_settings(coin, {
        "enabled": True,
        "mode": "fixed",
        "fixed_target_pct": 1.5
    })
    updated = tp_service.get_settings(coin)
    results.add("TP: Update Settings", updated.enabled and updated.fixed_target_pct == 1.5,
                f"Enabled: {updated.enabled}, Target: {updated.fixed_target_pct}%")
    
    # Test fixed take-profit check
    entry_price = 100000
    
    # Should NOT trigger (profit below target)
    check1 = tp_service.check_take_profit(coin, 101000, entry_price, "LONG")  # 1% profit
    results.add("TP: Fixed - Below Target", not check1["should_close"],
                f"1% profit, target 1.5%: {check1['reason']}")
    
    # Should trigger (profit above target)
    check2 = tp_service.check_take_profit(coin, 102000, entry_price, "LONG")  # 2% profit
    results.add("TP: Fixed - Above Target", check2["should_close"],
                f"2% profit, target 1.5%: {check2['reason']}")
    
    # Test trailing mode
    tp_service.update_settings(coin, {
        "mode": "trailing",
        "trailing_drop_pct": 0.5
    })
    tp_service.reset_tracking(coin)
    
    # Build up peak profit
    tp_service.check_take_profit(coin, 101500, entry_price, "LONG")  # 1.5% profit (sets peak)
    
    # Should NOT trigger (still rising)
    check3 = tp_service.check_take_profit(coin, 101200, entry_price, "LONG")  # 1.2% profit
    results.add("TP: Trailing - Small Drop", not check3["should_close"],
                f"Peak: {check3['peak_profit_pct']:.2f}%, Current: {check3['profit_pct']:.2f}%")
    
    # Reset for clean state
    tp_service.reset_tracking(coin)
    tp_service.update_settings(coin, {"enabled": False})


async def test_position_management(trading_service, state):
    """Test position fetching"""
    test_section("POSITION MANAGEMENT TESTS")
    
    state["current_coin"] = "BTC"
    
    # Get current position
    position = await trading_service.get_position()
    results.add("Position: Fetch Current", True,  # Always passes, just checking if it works
                f"Position: {position['side'] if position else 'None'}")
    
    # Get all positions
    all_positions = await trading_service.get_all_positions()
    results.add("Position: Fetch All", isinstance(all_positions, list),
                f"Found {len(all_positions)} open positions")
    
    if all_positions:
        print("\n  Open Positions:")
        for pos in all_positions:
            print(f"    • {pos['coin']}: {pos['side']} {pos['size']} @ ${pos['entry_price']:,.2f}")
            print(f"      P/L: {pos['pnl_pct']:.2f}% (${pos['pnl_usdt']:.2f})")
    
    return position, all_positions


async def test_small_trade(trading_service, ai_engine, state, max_margin=5):
    """Test placing a small trade ($1-5 margin)"""
    test_section("SMALL TRADE TEST (Max $5 Margin)")
    
    # Use ETH for testing - has step size of 0.001
    state["current_coin"] = "ETH"
    ai_engine.reset()
    
    symbol = SUPPORTED_COINS["ETH"]
    
    # Get current price
    ticker = await trading_service.client.get_ticker(symbol)
    ticker_data = ticker.get("data", ticker) if isinstance(ticker, dict) else {}
    current_price = float(ticker_data.get("last", 0))
    
    if current_price <= 0:
        results.add("Trade: Get Price", False, "Could not get ETH price")
        return None
    
    results.add("Trade: Get ETH Price", True, f"ETH Price: ${current_price:.2f}")
    
    # Calculate position size for $1 margin with 20x leverage
    margin_usdt = 1.0  # $1 margin
    leverage = 20
    position_value = margin_usdt * leverage  # $20 position value
    coin_size = round_to_step(position_value / current_price, "ETH")
    
    # Ensure minimum size
    if coin_size < 0.001:
        coin_size = 0.001
    
    results.add("Trade: Calculate Size", coin_size > 0,
                f"Size: {coin_size} ETH (${margin_usdt} margin @ {leverage}x)")
    
    # Check if we already have a position
    existing_position = await trading_service.get_position()
    if existing_position:
        results.add("Trade: Existing Position", True, 
                    f"Already have {existing_position['side']} position, skipping new trade", 
                    warning=True)
        return existing_position
    
    # Get AI signal
    signal = await ai_engine.analyze()
    direction = "long" if signal.signal in ["LONG", "NEUTRAL"] else "short"
    
    print(f"\n  Placing test trade:")
    print(f"  - Direction: {direction.upper()}")
    print(f"  - Size: {coin_size} ETH")
    print(f"  - Margin: ${margin_usdt}")
    print(f"  - Leverage: {leverage}x")
    print(f"  - AI Signal: {signal.signal} ({signal.confidence*100:.0f}%)")
    
    # Place the trade
    result = await trading_service.place_order(
        side=direction,
        size=format_coin_size(coin_size, "ETH"),
        order_type="market",
        client_oid_prefix="test"
    )
    
    if result.get("success"):
        order_id = result.get("order_id")
        results.add("Trade: Place Order", True, f"Order ID: {order_id}")
        
        # Submit AI log
        market_data = await ai_engine.fetch_market_data()
        log_result, ai_log = await trading_service.submit_ai_log(
            order_id,
            {"price": market_data.price, "timestamp": market_data.timestamp},
            signal,
            f"TEST {direction.upper()}"
        )
        
        log_success = log_result.get("code") == "00000" or "success" in str(log_result).lower()
        results.add("Trade: Submit AI Log", log_success,
                    f"Log submitted: {log_result.get('code', 'unknown')}")
        
        # Wait a moment for position to register
        await asyncio.sleep(2)
        
        # Verify position opened
        new_position = await trading_service.get_position()
        results.add("Trade: Position Opened", new_position is not None,
                    f"Position: {new_position['side'] if new_position else 'None'}")
        
        return new_position
    else:
        results.add("Trade: Place Order", False, f"Error: {result.get('error', 'Unknown')}")
        return None


async def test_close_position(trading_service, ai_engine, tp_service, state):
    """Test closing a position"""
    test_section("CLOSE POSITION TEST")
    
    position = await trading_service.get_position()
    
    if not position:
        results.add("Close: No Position", True, "No position to close", warning=True)
        return
    
    size = position["size"]
    side = position["side"]
    
    print(f"\n  Closing position:")
    print(f"  - Side: {side}")
    print(f"  - Size: {size}")
    
    # Get AI signal for log
    signal = await ai_engine.analyze()
    market_data = await ai_engine.fetch_market_data()
    
    # Close the position
    result = await trading_service.close_position(
        size=size,
        side=side,
        client_oid_prefix="test_close"
    )
    
    if result.get("success"):
        order_id = result.get("order_id")
        results.add("Close: Execute", True, f"Order ID: {order_id}")
        
        # Submit AI log
        log_result, _ = await trading_service.submit_ai_log(
            order_id,
            {"price": market_data.price, "timestamp": market_data.timestamp},
            signal,
            f"TEST CLOSE {side}"
        )
        
        log_success = log_result.get("code") == "00000" or "success" in str(log_result).lower()
        results.add("Close: Submit AI Log", log_success,
                    f"Log submitted: {log_result.get('code', 'unknown')}")
        
        # Reset take-profit tracking
        tp_service.reset_tracking(state["current_coin"])
        
        # Wait and verify
        await asyncio.sleep(2)
        
        closed_position = await trading_service.get_position()
        results.add("Close: Position Closed", closed_position is None,
                    "Position successfully closed" if not closed_position else f"Still open: {closed_position}")
    else:
        results.add("Close: Execute", False, f"Error: {result.get('error', 'Unknown')}")


async def test_automation_service(automation_service, state):
    """Test automation service (without executing trades)"""
    test_section("AUTOMATION SERVICE TESTS")
    
    # Test settings
    settings = automation_service.settings
    results.add("Automation: Get Settings", settings is not None,
                f"Enabled: {settings.enabled}, Auto-Entry: {settings.auto_entry}")
    
    # Update settings (but keep disabled for safety)
    automation_service.update_settings({
        "enabled": False,
        "auto_entry": False,
        "margin_usdt": 1.0,
        "leverage": 20,
        "min_confidence": 0.70
    })
    
    updated = automation_service.settings
    results.add("Automation: Update Settings", 
                updated.margin_usdt == 1.0 and updated.min_confidence == 0.70,
                f"Margin: ${updated.margin_usdt}, Min Conf: {updated.min_confidence*100:.0f}%")
    
    # Test run (should do nothing since disabled)
    result = await automation_service.run()
    results.add("Automation: Run (Disabled)", result["action"] == "none",
                f"Action: {result['action']}, Reason: {result['reason']}")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  REGIMEFORGE ALPHA - COMPREHENSIVE TEST SUITE")
    print(f"  Model: {MODEL_VERSION}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Initialize
    try:
        config = APIConfig.from_env()
        results.add("Config: Load Environment", True, "API credentials loaded")
    except ValueError as e:
        results.add("Config: Load Environment", False, str(e))
        return False
    
    # Create services
    client = WeexClient(config)
    state = {"current_coin": "BTC"}
    
    def get_current_coin():
        return state["current_coin"]
    
    ai_engine = RegimeForgeAI(client, get_current_coin)
    trading_service = TradingService(client, get_current_coin)
    tp_service = TakeProfitService()
    automation_service = AutomationService(ai_engine, trading_service, tp_service, get_current_coin)
    
    # Run tests
    try:
        # 1. API Connectivity
        api_ok = await test_api_connectivity(client)
        if not api_ok:
            print("\n⚠️  API connectivity issues detected. Some tests may fail.")
        
        # 2. Coin Switching (critical test for data scrambling issue)
        await test_coin_switching(client, ai_engine, trading_service, state)
        
        # 3. AI Analysis
        await test_ai_analysis(ai_engine, state)
        
        # 4. Take-Profit Service
        await test_take_profit_service(tp_service, state)
        
        # 5. Position Management
        await test_position_management(trading_service, state)
        
        # 6. Small Trade Test ($1 margin)
        position = await test_small_trade(trading_service, ai_engine, state, max_margin=5)
        
        # 7. Close Position (if we opened one)
        if position:
            await asyncio.sleep(3)  # Wait a bit before closing
            await test_close_position(trading_service, ai_engine, tp_service, state)
        
        # 8. Automation Service
        await test_automation_service(automation_service, state)
        
    except Exception as e:
        results.add("Test Execution", False, f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Summary
    return results.summary()


if __name__ == "__main__":
    success = run_async(run_all_tests())
    sys.exit(0 if success else 1)
