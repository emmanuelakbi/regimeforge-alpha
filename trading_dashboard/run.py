#!/usr/bin/env python3
"""
RegimeForge Alpha - Entry Point
Run this file to start the trading dashboard
"""
from trading_dashboard.app import run_server

if __name__ == "__main__":
    run_server(host="0.0.0.0", port=5000, debug=False)
