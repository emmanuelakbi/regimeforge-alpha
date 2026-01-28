"""
Routes module for RegimeForge Alpha
"""
from .api import api_bp
from .ai import ai_bp
from .automation import automation_bp

__all__ = ["api_bp", "ai_bp", "automation_bp"]
