import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from flask import Flask, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash


ROOT = Path(__file__).parent
app = Flask(__name__, static_folder=str(ROOT / "static"))
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
app.config["SECRET_KEY"] = os.environ.get(
    "CLIENT_SECRET_KEY",
    "",
) or secrets.token_urlsafe(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "CLIENT_COOKIE_SECURE",
    "false",
).lower() == "true"
CLIENT_DB = os.environ.get("CLIENT_DB", str(ROOT / "client.db"))

ALLOWED_ACTIONS = {
    "download_document",
    "approve_request",
    "reject_request",
    "scenario_credential_replay",
    "scenario_data_exfiltration",
    "scenario_api_abuse",
}
SCENARIO_ROUTES = {
    "available": ("GET", "/available"),
    "running": ("GET", "/running"),
    "start": ("POST", "/start"),
    "stop": ("POST", "/{run_id}/stop"),
    "pause": ("POST", "/{run_id}/pause"),
    "resume": ("POST", "/{run_id}/resume"),
    "speed": ("PUT", "/{run_id}/speed"),
}
LOGIN_INJECTION_PATTERN = re.compile(
    r"(?:'\s*(?:or|and)\s+['\d]|union\s+select|select\s+.+\s+from|--|/\*)",
    re.IGNORECASE,
)


def _configured_username() -> str:
    return os.environ.get("CLIENT_USERNAME", "alex.chen")


def _db() -> sqlite3.Connection:
    connection = sqlite3.connect(CLIENT_DB)
    connection.row_factory = sqlite3.Row
    return connection


def _init_db() -> None:
    with _db() as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "username TEXT PRIMARY KEY, display_name TEXT NOT NULL, "
            "department TEXT NOT NULL, password_hash TEXT NOT NULL)"
        )
        if connection.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (_configured_username(),),
        ).fetchone() is None:
            connection.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?)",
                (
                    _configured_username(),
                    "Alex Chen",
                    "Security Engineering",
                    _configured_password_hash(),
                ),
            )


def _find_user(username: str) -> sqlite3.Row | None:
    _init_db()
    with _db() as connection:
        return connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def _configured_password_hash() -> str:
    configured = os.environ.get("CLIENT_PASSWORD_HASH")
    if configured:
        return configured
    configured_password = os.environ.get("CLIENT_PASSWORD")
    if configured_password:
        return generate_password_hash(configured_password)
    return (
        "scrypt:32768:8:1$vFmwHOZKvUTZi8yk$"
        "f1a2ae1ed29b9bb8afdf8a9a4503ef8c5481988dba007c4e2df3206eebbfb5890"
        "f1c7acf779de85d9b0c1091de3650fa1abeec3a8773737385516357c86c32af"
    )


def _current_user() -> dict[str, str] | None:
    username = session.get("username")
    user = _find_user(str(username)) if username else None
    if user is None:
        return None
    return {
        "username": user["username"],
        "display_name": user["display_name"],
        "department": user["department"],
    }


def _require_auth() -> tuple[dict[str, str] | None, Any]:
    user = _current_user()
    if user is None:
        return None, (jsonify({"error": "Authentication required"}), 401)
    g.client_user = user
    return user, None


def _scenario_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    base_url = os.environ.get(
        "SIEM_SCENARIO_URL",
        "http://backend:5000/v1/scenarios",
    )
    service_key = os.environ.get("SCENARIO_SERVICE_KEY", "")
    if not service_key:
        app.logger.error("SCENARIO_SERVICE_KEY is not configured")
        return jsonify({"error": "Scenario service is unavailable"}), 503
    try:
        response = requests.request(
            method,
            f"{base_url}{path}",
            json=payload,
            headers={"X-Scenario-Service-Key": service_key},
            timeout=5,
        )
        return jsonify(response.json()), response.status_code
    except (requests.RequestException, ValueError):
        app.logger.exception("Unable to reach scenario service")
        return jsonify({"error": "Scenario service is unavailable"}), 503


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _minutes_ago(minutes: int) -> str:
    return (_now() - timedelta(minutes=minutes)).isoformat()


DOCUMENTS = [
    {"id": "finance-q4", "name": "Finance Q4 Forecast.xlsx", "classification": "confidential", "updated_at": _now().isoformat()},
    {"id": "customer-export", "name": "Customer Export.csv", "classification": "restricted", "updated_at": _now().isoformat()},
    {"id": "engineering-wiki", "name": "Engineering Wiki", "classification": "internal", "updated_at": _now().isoformat()},
]

APPROVALS: list[dict[str, Any]] = [
    {"id": "APR-1042", "requester": "maya.patel", "resource": "Customer Export.csv", "status": "pending"},
]

ACTIVITY: list[dict[str, str]] = [
    {"timestamp": _minutes_ago(2), "title": "MFA verification completed", "detail": "Alex Chen · Security Engineering"},
    {"timestamp": _minutes_ago(5), "title": "Customer Export.csv access requested", "detail": "Approval APR-1042 · Maya Patel"},
]
EXTERNAL_MESSAGES: list[dict[str, str]] = []


def _client_id() -> str:
    return str(session.get("session_id", "anonymous"))[:80]


def _emit(
    action: str,
    details: dict[str, Any],
    event_count: int = 1,
) -> tuple[bool, list[str]]:
    ingest_url = os.environ.get("SIEM_INGEST_URL", "")
    if not ingest_url:
        app.logger.error("SIEM_INGEST_URL is not configured")
        return False, []
    event_type = {
        "download_document": "file_download",
        "api_request": "rate_limit_blocked",
        "scenario_credential_replay": "login_failure",
        "scenario_data_exfiltration": "file_download",
        "scenario_api_abuse": "rate_limit_blocked",
        "approve_request": "approval_granted",
        "reject_request": "approval_denied",
    }.get(action, action)
    source_type = (
        "endpoint"
        if action in {"download_document", "scenario_data_exfiltration"}
        else "proxy"
        if action in {"api_request", "scenario_api_abuse"}
        else "generic"
        if action == "external_message"
        else "auth"
    )
    event_ids: list[str] = []
    for attempt in range(event_count):
        occurred_at = _now().isoformat()
        payload = {
            "source_type": source_type,
            "event_type": event_type,
            "timestamp": occurred_at,
            "hostname": "enterprise-workspace",
            "username": details.get("username", "alex.chen"),
            "source_ip": details.get("source_ip", "10.10.20.15"),
            "message": f"Enterprise workspace action: {action}",
            "metadata": {
                "client_app": "enterprise-workspace",
                "client_session": _client_id(),
                "occurred_at": occurred_at,
                "attempt": attempt + 1,
                **details,
            },
        }
        try:
            response = requests.post(ingest_url, json=payload, timeout=3)
            response.raise_for_status()
            event_id = response.json().get("id")
            if event_id:
                event_ids.append(event_id)
        except (requests.RequestException, ValueError):
            app.logger.exception("Unable to forward client telemetry")
            return False, event_ids
    return True, event_ids


@app.post("/api/login")
def login() -> Any:
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip().lower()
    password = str(body.get("password", ""))
    user = _find_user(username)
    if user is None or not check_password_hash(user["password_hash"], password):
        suspicious_input = bool(
            LOGIN_INJECTION_PATTERN.search(username)
            or LOGIN_INJECTION_PATTERN.search(password)
        )
        _emit(
            "login_sql_injection" if suspicious_input else "login_failure",
            {
                "username": username[:80] or "unknown",
                "source_ip": request.remote_addr or "client-unknown",
                "user_agent": request.user_agent.string[:160],
                "authentication_method": "password",
                "failure_reason": "invalid_credentials",
                "suspicious_input": suspicious_input,
            },
        )
        return jsonify({"error": "Invalid username or password"}), 401
    session.clear()
    session["username"] = username
    session["session_id"] = secrets.token_urlsafe(24)
    session.permanent = True
    return jsonify({"ok": True})


@app.post("/api/signup")
def signup() -> Any:
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip().lower()
    password = str(body.get("password", ""))
    display_name = str(body.get("display_name", "")).strip()
    department = str(body.get("department", "Engineering")).strip()
    if not username or len(username) < 3 or len(password) < 10 or not display_name:
        return jsonify({
            "error": "Username, display name, and a password of at least 10 characters are required",
        }), 422
    _init_db()
    try:
        with _db() as connection:
            connection.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?)",
                (username, display_name[:80], department[:80], generate_password_hash(password)),
            )
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409
    session.clear()
    session["username"] = username
    session["session_id"] = secrets.token_urlsafe(24)
    session.permanent = True
    return jsonify({"ok": True}), 201


@app.post("/api/logout")
def logout() -> Any:
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/session")
def session_status() -> Any:
    user = _current_user()
    return jsonify({"authenticated": user is not None, "user": user})


@app.post("/api/external/messages")
def external_message() -> Any:
    expected = os.environ.get("CLIENT_EXTERNAL_KEY", "")
    supplied = request.headers.get("X-External-Key", "")
    if not expected or not secrets.compare_digest(supplied, expected):
        return jsonify({"error": "Invalid external source key"}), 401
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()
    if not message:
        return jsonify({"error": "message is required"}), 422
    details = {
        "username": str(body.get("username", "external.integration"))[:80],
        "source_ip": str(body.get("source_ip", "10.10.30.20"))[:45],
        "integration": str(body.get("integration", "external-app"))[:80],
        "message": message[:500],
    }
    occurred_at = _now().isoformat()
    details["occurred_at"] = occurred_at
    EXTERNAL_MESSAGES.insert(0, {
        "timestamp": occurred_at,
        "integration": details["integration"],
        "message": message,
        "username": details["username"],
    })
    del EXTERNAL_MESSAGES[50:]
    emitted, event_ids = _emit("external_message", details)
    if not emitted:
        return jsonify({"error": "The SIEM telemetry service is unavailable"}), 503
    return jsonify({"ok": True, "event_ids": event_ids, "occurred_at": occurred_at}), 201


@app.get("/")
def index() -> Any:
    return send_from_directory(app.static_folder or "", "index.html")


@app.get("/workspace")
def workspace() -> Any:
    return send_from_directory(app.static_folder or "", "workspace.html")


@app.get("/scenarios")
def scenarios_page() -> Any:
    return send_from_directory(app.static_folder or "", "scenarios.html")


@app.get("/signup")
def signup_page() -> Any:
    return send_from_directory(app.static_folder or "", "signup.html")


@app.get("/signup/")
def signup_page_trailing_slash() -> Any:
    return send_from_directory(app.static_folder or "", "signup.html")


@app.get("/assets/<path:name>")
def assets(name: str) -> Any:
    return send_from_directory(Path(app.static_folder or "") / "assets", name)


@app.get("/api/state")
def state() -> Any:
    user, error = _require_auth()
    if error:
        return error
    return jsonify({
        "tenant": "Acme Enterprise Workspace",
        "user": {**user, "mfa": True},
        "documents": DOCUMENTS,
        "approvals": APPROVALS,
        "activity": ACTIVITY,
        "external_messages": EXTERNAL_MESSAGES,
        "server_time": _now().isoformat(),
        "metrics": {
            "documents": len(DOCUMENTS),
            "pending_approvals": sum(item["status"] == "pending" for item in APPROVALS),
        },
    })


@app.get("/api/scenarios/available")
def scenarios_available() -> Any:
    _, error = _require_auth()
    if error:
        return error
    return _scenario_request(*SCENARIO_ROUTES["available"])


@app.get("/api/scenarios/running")
def scenarios_running() -> Any:
    _, error = _require_auth()
    if error:
        return error
    return _scenario_request(*SCENARIO_ROUTES["running"])


@app.post("/api/scenarios/start")
def scenarios_start() -> Any:
    _, error = _require_auth()
    if error:
        return error
    body = request.get_json(silent=True) or {}
    return _scenario_request("POST", "/start", {"filename": body.get("filename")})


def _scenario_control(run_id: str, action: str) -> Any:
    _, error = _require_auth()
    if error:
        return error
    method, path = SCENARIO_ROUTES[action]
    payload = request.get_json(silent=True) if method == "PUT" else None
    return _scenario_request(method, path.format(run_id=run_id), payload)


@app.post("/api/scenarios/<run_id>/stop")
def scenarios_stop(run_id: str) -> Any:
    return _scenario_control(run_id, "stop")


@app.post("/api/scenarios/<run_id>/pause")
def scenarios_pause(run_id: str) -> Any:
    return _scenario_control(run_id, "pause")


@app.post("/api/scenarios/<run_id>/resume")
def scenarios_resume(run_id: str) -> Any:
    return _scenario_control(run_id, "resume")


@app.put("/api/scenarios/<run_id>/speed")
def scenarios_speed(run_id: str) -> Any:
    return _scenario_control(run_id, "speed")


@app.post("/api/actions")
def actions() -> Any:
    user, error = _require_auth()
    if error:
        return error
    body = request.get_json(silent=True) or {}
    action = body.get("action")
    if action not in ALLOWED_ACTIONS:
        return jsonify({"error": "Unsupported action"}), 400
    username = user["username"]
    resource = str(body.get("resource", "Customer Export.csv"))[:120]
    event_details = {"username": username, "resource": resource}
    event_count = 1

    if action == "scenario_credential_replay":
        event_details.update({"attack_stage": "credential_access", "blocked": True})
        event_count = 3
        message = "Credential replay sequence blocked and reported to the SOC."
    elif action == "scenario_data_exfiltration":
        event_details.update({
            "classification": "restricted",
            "resource": "Customer Export.csv",
            "collection_stage": "bulk_export",
        })
        event_count = 5
        message = "Bulk restricted-data download sequence reported to the SOC."
    elif action == "scenario_api_abuse":
        event_details.update({
            "endpoint": "/v1/customers/export",
            "policy": "customer-export-rate-limit",
        })
        event_count = 3
        message = "API abuse sequence blocked by the production policy."
    elif action == "approve_request":
        for approval in APPROVALS:
            if approval["status"] == "pending":
                approval["status"] = "approved"
                break
        message = "Approval completed. The decision was recorded for audit."
    elif action == "reject_request":
        for approval in APPROVALS:
            if approval["status"] == "pending":
                approval["status"] = "rejected"
                break
        message = "Approval rejected. The decision was recorded for audit."
    elif action == "download_document":
        event_details["classification"] = next(
            (doc["classification"] for doc in DOCUMENTS if doc["name"] == resource),
            "internal",
        )
        message = "Download request submitted and logged."
    elif action == "api_request":
        event_details["endpoint"] = "/v1/customers/export"
        event_count = 1
        message = "API request completed and rate-limit telemetry emitted."
    else:
        event_count = 1
        message = "Action completed and sent to the security monitoring pipeline."

    event_details["occurred_at"] = _now().isoformat()
    emitted, event_ids = _emit(action, event_details, event_count)
    if not emitted:
        return jsonify({"error": "The SIEM telemetry service is unavailable"}), 503
    ACTIVITY.insert(0, {
        "timestamp": _now().isoformat(),
        "title": message.split(".")[0],
        "detail": f"{user['display_name']} · Enterprise Workspace · {action}",
    })
    del ACTIVITY[8:]
    return jsonify({
        "ok": True,
        "message": message,
        "request_id": f"REQ-{secrets.token_hex(4).upper()}",
        "event_ids": event_ids,
        "occurred_at": event_details["occurred_at"],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7357)
