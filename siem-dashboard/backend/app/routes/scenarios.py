"""
©AngelaMos | 2026
scenarios.py

Route handlers for the scenarios API (/v1/scenarios)

Mounts GET /available, GET /running, POST /start, POST /<id>/stop,
POST /<id>/pause, POST /<id>/resume, and PUT /<id>/speed.

Connects to:
  controllers/scenario_ctrl.py - business logic
  schemas/scenario.py - ScenarioStartRequest, SpeedRequest
  routes/__init__.py - scenarios_bp registered here
"""

from typing import Any
import secrets

from flask import Blueprint, g, request

from app.controllers import scenario_ctrl
from app.config import settings
from app.core.decorators import endpoint, S, R
from app.core.errors import AuthenticationError
from app.schemas.scenario import ScenarioStartRequest, SpeedRequest


scenarios_bp = Blueprint("scenarios", __name__)


def _require_scenario_access() -> None:
    """
    Allow dashboard users or the isolated client service to run playbooks.
    """
    if g.current_user is not None:
        return
    service_key = request.headers.get("X-Scenario-Service-Key", "")
    if not service_key or not settings.SCENARIO_SERVICE_KEY:
        raise AuthenticationError()
    if not secrets.compare_digest(service_key, settings.SCENARIO_SERVICE_KEY):
        raise AuthenticationError()


@scenarios_bp.get("/available")
@endpoint(auth_required=False)
@R()
def list_available() -> Any:
    """
    Return metadata for all available playbooks
    """
    _require_scenario_access()
    return scenario_ctrl.list_available()


@scenarios_bp.get("/running")
@endpoint(auth_required=False)
@R()
def list_running() -> Any:
    """
    Return all active scenario runs
    """
    _require_scenario_access()
    return scenario_ctrl.list_running()


@scenarios_bp.post("/start")
@endpoint(auth_required=False)
@S(ScenarioStartRequest)
@R(status = 201)
def start_scenario() -> Any:
    """
    Start a new scenario from a playbook file
    """
    _require_scenario_access()
    return scenario_ctrl.start_scenario()


@scenarios_bp.post("/<run_id>/stop")
@endpoint(auth_required=False)
@R()
def stop_scenario(run_id: str) -> Any:
    """
    Stop an active scenario run
    """
    _require_scenario_access()
    return scenario_ctrl.stop_scenario(run_id)


@scenarios_bp.post("/<run_id>/pause")
@endpoint(auth_required=False)
@R()
def pause_scenario(run_id: str) -> Any:
    """
    Pause an active scenario run
    """
    _require_scenario_access()
    return scenario_ctrl.pause_scenario(run_id)


@scenarios_bp.post("/<run_id>/resume")
@endpoint(auth_required=False)
@R()
def resume_scenario(run_id: str) -> Any:
    """
    Resume a paused scenario run
    """
    _require_scenario_access()
    return scenario_ctrl.resume_scenario(run_id)


@scenarios_bp.put("/<run_id>/speed")
@endpoint(auth_required=False)
@S(SpeedRequest)
@R()
def set_speed(run_id: str) -> Any:
    """
    Adjust playback speed of an active scenario
    """
    _require_scenario_access()
    return scenario_ctrl.set_speed(run_id)
