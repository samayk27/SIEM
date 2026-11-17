"""
Enterprise Security Lab operations.

The lab is intentionally isolated: every action affects only the local demo
tenant and emits a normal SIEM event through the production ingestion path.
"""

from datetime import datetime, timedelta, UTC
from typing import Any, cast

from flask import g

from app.controllers.log_ctrl import ingest_event
from app.models.LabState import LabState
from app.models.LogEvent import LogEvent


DEFAULT_USERS = [
    {
        "username": "alex.chen",
        "email": "alex.chen@acme.test",
        "role": "analyst",
        "status": "active",
        "mfa_enabled": True,
        "risk": "normal",
    },
    {
        "username": "maya.patel",
        "email": "maya.patel@acme.test",
        "role": "finance",
        "status": "active",
        "mfa_enabled": False,
        "risk": "elevated",
    },
    {
        "username": "service.backup",
        "email": "service.backup@acme.test",
        "role": "service",
        "status": "active",
        "mfa_enabled": False,
        "risk": "normal",
    },
]

DEFAULT_RESOURCES = [
    {"name": "finance-q4.xlsx", "classification": "confidential"},
    {"name": "customer-export.csv", "classification": "restricted"},
    {"name": "engineering-wiki", "classification": "internal"},
]

DEFAULT_POLICIES = {
    "api_requests_per_minute": 8,
    "downloads_per_window": 5,
    "download_window_seconds": 120,
    "lockout_failed_logins": 5,
    "require_mfa_for_role_changes": True,
}


def _get_state() -> LabState:
    state = cast(LabState | None, LabState.objects(key="default").first())
    if state is None:
        state = LabState(
            users=DEFAULT_USERS,
            resources=DEFAULT_RESOURCES,
            policies=DEFAULT_POLICIES,
            blocked_ips=[],
            revoked_sessions=[],
            action_history=[],
        )
        state.save()
    return state


def get_overview() -> dict[str, Any]:
    state = _get_state()
    recent_events = LogEvent.objects(
        source_type="auth",
        event_type__in=[
            "login_failure",
            "login_success",
            "file_download",
            "privilege_change",
            "api_request",
            "rate_limit_blocked",
            "access_blocked",
        ],
    ).order_by("-timestamp").limit(15)
    return {
        "tenant": {
            "name": "Acme Demo Enterprise",
            "environment": "isolated-lab",
            "status": "protected",
        },
        "users": state.users,
        "resources": state.resources,
        "policies": state.policies,
        "blocked_ips": state.blocked_ips,
        "revoked_sessions": state.revoked_sessions,
        "recent_events": list(recent_events),
    }


def perform_action() -> dict[str, Any]:
    data = g.validated
    state = _get_state()
    now = datetime.now(UTC)
    event_type = data.action
    blocked = False
    control = "allowed"
    message = "Action completed in the isolated enterprise tenant."

    if data.action == "api_request":
        recent = _recent_actions(state, "api_request", data.username, now, 60)
        if len(recent) >= state.policies["api_requests_per_minute"]:
            event_type = "rate_limit_blocked"
            blocked = True
            control = "rate_limited"
            message = "API request blocked by the per-user rate limit."

    if data.action == "file_download":
        recent = _recent_actions(
            state,
            "file_download",
            data.username,
            now,
            state.policies["download_window_seconds"],
        )
        if len(recent) >= state.policies["downloads_per_window"]:
            event_type = "access_blocked"
            blocked = True
            control = "blocked"
            message = "Download blocked by the sensitive-data policy."

    if data.action == "restricted_access":
        event_type = "access_blocked"
        blocked = True
        control = "blocked"
        message = "Access denied because the resource is restricted."

    if data.action == "block_ip":
        if data.source_ip not in state.blocked_ips:
            state.blocked_ips.append(data.source_ip)
        control = "ip_blocked"
        message = f"Source IP {data.source_ip} was added to the block list."

    if data.source_ip in state.blocked_ips and data.action in {
        "api_request",
        "file_download",
        "login_success",
    }:
        event_type = "access_blocked"
        blocked = True
        control = "blocked"
        message = f"Action blocked for quarantined IP {data.source_ip}."

    if data.action == "disable_user":
        _set_user_status(state, data.target_username, "disabled")
        control = "user_disabled"
        message = f"User {data.target_username} was disabled."

    if data.action == "revoke_session":
        session_key = f"{data.target_username}:{data.source_ip}"
        if session_key not in state.revoked_sessions:
            state.revoked_sessions.append(session_key)
        control = "session_revoked"
        message = f"Sessions for {data.target_username} were revoked."

    event = ingest_event(
        {
            "source_type": "auth",
            "event_type": event_type,
            "source_ip": data.source_ip,
            "hostname": "enterprise-workspace",
            "username": data.username,
            "message": message,
            "metadata": {
                "lab_action": data.action,
                "resource": data.resource,
                "target_username": data.target_username,
                "role": data.role,
                "control": control,
                "blocked": blocked,
            },
        },
    )

    history_entry = {
        "action": data.action,
        "username": data.username,
        "source_ip": data.source_ip,
        "resource": data.resource,
        "control": control,
        "blocked": blocked,
        "timestamp": now.isoformat(),
    }
    state.action_history = [history_entry, *state.action_history[:49]]
    state.save()

    return {
        "action": history_entry,
        "message": message,
        "event": event,
        "control": control,
        "blocked": blocked,
    }


def _recent_actions(
    state: LabState,
    action: str,
    username: str,
    now: datetime,
    seconds: int,
) -> list[dict[str, Any]]:
    cutoff = now - timedelta(seconds=seconds)
    return [
        entry
        for entry in state.action_history
        if entry.get("action") == action
        and entry.get("username") == username
        and datetime.fromisoformat(entry["timestamp"]) >= cutoff
    ]


def _set_user_status(state: LabState, username: str, status: str) -> None:
    for user in state.users:
        if user.get("username") == username:
            user["status"] = status
            return
