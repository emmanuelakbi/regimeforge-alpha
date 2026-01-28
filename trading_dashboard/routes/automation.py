"""
Automation routes for RegimeForge Alpha
"""
from flask import Blueprint, jsonify, request, current_app
import logging

from ..api_client import run_async
from ..utils import validate_json_request

logger = logging.getLogger(__name__)
automation_bp = Blueprint("automation", __name__, url_prefix="/api/automation")


def get_services():
    """Get services from app context"""
    return (
        current_app.config["automation_service"],
        current_app.config["state"]
    )


@automation_bp.route("/settings", methods=["GET"])
def get_automation_settings():
    """Get current automation settings"""
    automation, _ = get_services()
    return jsonify(automation.settings.to_dict())


@automation_bp.route("/settings", methods=["POST"])
def set_automation_settings():
    """Update automation settings"""
    req = request.get_json(silent=True)
    is_valid, error = validate_json_request(req)
    if not is_valid:
        return jsonify({"success": False, "error": error}), 400
    
    automation, _ = get_services()
    automation.update_settings(req)
    return jsonify({"success": True, "settings": automation.settings.to_dict()})


@automation_bp.route("/run", methods=["GET"])
def run_automation():
    """Run automation check and execute trades if conditions met"""
    async def execute():
        automation, _ = get_services()
        return await automation.run()
    return jsonify(run_async(execute()))
