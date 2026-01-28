#!/usr/bin/env python3
"""
RegimeForge Alpha - Entry Point
Run this file to start the trading dashboard

Usage:
    python run.py

Environment Variables Required:
    WEEX_API_KEY - Your WEEX API key
    WEEX_SECRET_KEY - Your WEEX secret key
    WEEX_PASSPHRASE - Your WEEX passphrase

Or set them before running:
    export WEEX_API_KEY=your_key
    export WEEX_SECRET_KEY=your_secret
    export WEEX_PASSPHRASE=your_passphrase
    python run.py
"""
import os
import sys

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from trading_dashboard.app import run_server

if __name__ == "__main__":
    # Check for required environment variables
    required_vars = ["WEEX_API_KEY", "WEEX_SECRET_KEY", "WEEX_PASSPHRASE"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    
    if missing:
        print("ERROR: Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nSet them in your environment or create a .env file.")
        print("See .env.example for reference.")
        sys.exit(1)
    
    run_server(host="0.0.0.0", port=5000, debug=False)
