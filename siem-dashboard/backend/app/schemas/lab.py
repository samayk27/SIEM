"""
Request schemas for the isolated Enterprise Security Lab.
"""

from typing import Literal

from pydantic import BaseModel, Field


LabAction = Literal[
    "login_failure",
    "login_success",
    "file_download",
    "privilege_change",
    "api_request",
    "device_register",
    "restricted_access",
    "disable_user",
    "block_ip",
    "revoke_session",
]


class LabActionRequest(BaseModel):
    """
    A safe, deterministic enterprise action executed inside the demo tenant.
    """

    action: LabAction
    username: str = Field(default="alex.chen", min_length=1, max_length=80)
    source_ip: str = Field(default="10.10.20.15", min_length=1, max_length=45)
    resource: str = Field(default="finance-q4.xlsx", min_length=1, max_length=120)
    target_username: str = Field(
        default="alex.chen",
        min_length=1,
        max_length=80,
    )
    role: str = Field(default="admin", min_length=1, max_length=40)

