"""
Flask application factory for RegimeForge Alpha
"""
from flask import Flask, render_template
import logging
import os

from .config import APIConfig, MODEL_VERSION
from .api_client import WeexClient
from .services.ai_engine import RegimeForgeAI
from .services.trading import TradingService
from .services.take_profit import TakeProfitService
from .services.automation import AutomationService
from .routes import api_bp, ai_bp, automation_bp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(config: APIConfig = None) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config: Optional API configuration. If not provided,
                loads from environment variables.
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    
    # Load config
    if config is None:
        config = APIConfig.from_env()
    
    # Shared state (replaces global variables)
    state = {"current_coin": "BTC"}
    
    def get_current_coin():
        return state["current_coin"]
    
    # Initialize services
    client = WeexClient(config)
    ai_engine = RegimeForgeAI(client, get_current_coin)
    trading_service = TradingService(client, get_current_coin)
    tp_service = TakeProfitService()
    automation_service = AutomationService(ai_engine, trading_service, tp_service, get_current_coin)
    
    # Store in app config for route access
    app.config["client"] = client
    app.config["ai_engine"] = ai_engine
    app.config["trading_service"] = trading_service
    app.config["tp_service"] = tp_service
    app.config["automation_service"] = automation_service
    app.config["state"] = state
    
    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(automation_bp)
    
    # Dashboard route
    @app.route("/")
    def dashboard():
        resp = app.make_response(render_template("dashboard.html"))
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp
    
    logger.info("=" * 60)
    logger.info("  RegimeForge Alpha - AI Trading Dashboard")
    logger.info(f"  Model: {MODEL_VERSION}")
    logger.info("=" * 60)
    
    return app


def run_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """
    Run the Flask development server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug mode
    """
    app = create_app()
    
    print("=" * 60)
    print("  RegimeForge Alpha - AI Trading Dashboard")
    print(f"  Model: {MODEL_VERSION}")
    print("=" * 60)
    print(f"\n  Dashboard: http://{host}:{port}")
    print("  AI Features: Regime Detection, Signal Generation, Auto Log Submission")
    print("\n  All trades automatically submit AI logs to WEEX")
    print("=" * 60)
    
    app.run(host=host, port=port, debug=debug)
