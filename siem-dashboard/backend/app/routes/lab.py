"""
Routes for the isolated Enterprise Security Lab.
"""

from typing import Any

from flask import Blueprint

from app.controllers import lab_ctrl
from app.core.decorators import R, S, endpoint
from app.schemas.lab import LabActionRequest


lab_bp = Blueprint("lab", __name__)


@lab_bp.get("/overview")
@endpoint()
@R()
def overview() -> Any:
    return lab_ctrl.get_overview()


@lab_bp.post("/actions")
@endpoint()
@S(LabActionRequest)
@R(status=201)
def actions() -> Any:
    return lab_ctrl.perform_action()
