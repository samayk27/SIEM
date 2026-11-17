"""
MongoEngine state for the isolated Enterprise Security Lab.
"""

from typing import Any

from mongoengine import DictField, ListField, StringField

from app.models.Base import BaseDocument


class LabState(BaseDocument):
    """
    Stores the demo tenant's users, resources, policies, and controls.
    """

    meta: dict[str, Any] = {  # type: ignore[assignment]  # noqa: RUF012
        "collection": "lab_state",
    }

    key = StringField(required=True, unique=True, default="default")
    users = ListField(DictField())
    resources = ListField(DictField())
    policies = DictField()
    blocked_ips = ListField(StringField())
    revoked_sessions = ListField(StringField())
    action_history = ListField(DictField())
