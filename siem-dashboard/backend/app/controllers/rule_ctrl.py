"""
©AngelaMos | 2026
rule_ctrl.py

Business logic for correlation rule management

CRUD operations plus a test function that replays historical log
events through a rule using an isolated CorrelationState, returning
what alerts would have fired without touching production state or
publishing real alerts.

Key exports:
  list_rules, get_rule, create_rule, update_rule, delete_rule, test_rule

Connects to:
  models/CorrelationRule.py - CRUD operations
  models/LogEvent.py - reads historical events for test_rule
  engine/correlation.py - imports CorrelationState, evaluate_rule
  routes/rules.py - called from route handlers
"""

from typing import Any
from datetime import datetime, timedelta, UTC

from flask import g

from app.engine.correlation import (
    CorrelationState,
    evaluate_rule,
)
from app.models.CorrelationRule import CorrelationRule
from app.models.LogEvent import LogEvent
from app.models.LogEvent import Severity
from app.models.CorrelationRule import RuleType


DEFAULT_RULES = [
    {
        "name": "Excessive Failed Logins",
        "description": "Detects repeated authentication failures from one source.",
        "rule_type": RuleType.THRESHOLD,
        "conditions": {
            "event_filter": {"event_type": "login_failure"},
            "threshold": 3,
            "window_seconds": 60,
            "group_by": "source_ip",
        },
        "severity": Severity.HIGH,
        "mitre_tactic": "Credential Access",
        "mitre_technique": "T1110 Brute Force",
    },
    {
        "name": "SQL Injection in Authentication",
        "description": "Detects SQL injection syntax submitted to the enterprise sign-in endpoint.",
        "rule_type": RuleType.THRESHOLD,
        "conditions": {
            "event_filter": {"event_type": "login_sql_injection"},
            "threshold": 1,
            "window_seconds": 300,
            "group_by": "source_ip",
        },
        "severity": Severity.CRITICAL,
        "mitre_tactic": "Initial Access",
        "mitre_technique": "T1190 Exploit Public-Facing Application",
    },
    {
        "name": "Bulk Sensitive Downloads",
        "description": "Detects rapid file downloads by one enterprise user.",
        "rule_type": RuleType.THRESHOLD,
        "conditions": {
            "event_filter": {"event_type": "file_download"},
            "threshold": 5,
            "window_seconds": 120,
            "group_by": "username",
        },
        "severity": Severity.HIGH,
        "mitre_tactic": "Collection",
        "mitre_technique": "T1530 Data from Cloud Storage",
    },
    {
        "name": "API Rate Limit Abuse",
        "description": "Detects requests blocked by the enterprise API policy.",
        "rule_type": RuleType.THRESHOLD,
        "conditions": {
            "event_filter": {"event_type": "rate_limit_blocked"},
            "threshold": 3,
            "window_seconds": 300,
            "group_by": "source_ip",
        },
        "severity": Severity.MEDIUM,
        "mitre_tactic": "Impact",
        "mitre_technique": "T1499 Endpoint Denial of Service",
    },
    {
        "name": "Network Reconnaissance Burst",
        "description": "Detects repeated port scans from one source against the enterprise network.",
        "rule_type": RuleType.THRESHOLD,
        "conditions": {
            "event_filter": {"event_type": "port_scan"},
            "threshold": 3,
            "window_seconds": 180,
            "group_by": "source_ip",
        },
        "severity": Severity.MEDIUM,
        "mitre_tactic": "Reconnaissance",
        "mitre_technique": "T1046 Network Service Scanning",
    },
    {
        "name": "DNS Tunneling Activity",
        "description": "Detects sustained DNS query activity associated with covert data movement.",
        "rule_type": RuleType.THRESHOLD,
        "conditions": {
            "event_filter": {"event_type": "dns_query"},
            "threshold": 5,
            "window_seconds": 300,
            "group_by": "source_ip",
        },
        "severity": Severity.HIGH,
        "mitre_tactic": "Command and Control",
        "mitre_technique": "T1071.004 DNS",
    },
    {
        "name": "Privilege Escalation Detected",
        "description": "Detects a privilege escalation event requiring immediate analyst review.",
        "rule_type": RuleType.THRESHOLD,
        "conditions": {
            "event_filter": {"event_type": "privilege_escalation"},
            "threshold": 1,
            "window_seconds": 300,
            "group_by": "username",
        },
        "severity": Severity.CRITICAL,
        "mitre_tactic": "Privilege Escalation",
        "mitre_technique": "T1548 Abuse Elevation Control Mechanism",
    },
]
OBSOLETE_DEMO_RULES = {
    "SQL Injection Attempts",
    "Suspicious Command Execution",
    "Suspicious PowerShell Activity",
}


def ensure_default_rules() -> None:
    """
    Seed useful enterprise detections without overwriting user-created rules.
    """
    for name in OBSOLETE_DEMO_RULES:
        CorrelationRule.objects(name=name).delete()
    for definition in DEFAULT_RULES:
        rule = CorrelationRule.objects(name=definition["name"]).first()
        if rule is None:
            CorrelationRule(**definition).save()
            continue
        if rule.conditions != definition["conditions"]:
            rule.conditions = definition["conditions"]
            rule.description = definition["description"]
            rule.mitre_tactic = definition["mitre_tactic"]
            rule.mitre_technique = definition["mitre_technique"]
            rule.save()  # type: ignore[no-untyped-call]


def list_rules() -> list[Any]:
    """
    Return all correlation rules
    """
    return list(CorrelationRule.objects.order_by("-created_at"))  # type: ignore[no-untyped-call]


def get_rule(rule_id: str) -> CorrelationRule:
    """
    Return a single correlation rule by ID
    """
    return CorrelationRule.get_by_id(rule_id)


def create_rule() -> CorrelationRule:
    """
    Create a new correlation rule from validated request data
    """
    data = g.validated
    rule = CorrelationRule(
        name=data.name,
        description=data.description,
        rule_type=data.rule_type,
        conditions=data.conditions,
        severity=data.severity,
        enabled=data.enabled,
        mitre_tactic=data.mitre_tactic,
        mitre_technique=data.mitre_technique,
    )
    rule.save()  # type: ignore[no-untyped-call]
    return rule


def update_rule(rule_id: str) -> CorrelationRule:
    """
    Partially update an existing correlation rule
    """
    data = g.validated
    rule = CorrelationRule.get_by_id(rule_id)
    updates = data.model_dump(exclude_none=True)
    for field_name, value in updates.items():
        setattr(rule, field_name, value)
    rule.save()  # type: ignore[no-untyped-call]
    return rule


def delete_rule(rule_id: str) -> dict[str, Any]:
    """
    Delete a correlation rule by ID
    """
    rule = CorrelationRule.get_by_id(rule_id)
    rule.delete()  # type: ignore[no-untyped-call]
    return {"deleted": True}


def test_rule(rule_id: str) -> dict[str, Any]:
    """
    Simulate a rule against historical log events and return matches
    """
    data = g.validated
    rule = CorrelationRule.get_by_id(rule_id)

    cutoff = datetime.now(UTC).replace(
        second=0, microsecond=0,
    )
    since = cutoff - timedelta(hours=data.hours)

    events = LogEvent.objects(timestamp__gte=since).order_by("timestamp")  # type: ignore[no-untyped-call]

    state = CorrelationState()
    alerts_fired: list[dict[str, Any]] = []

    for event in events:
        event_data = {
            "id": str(event.id),
            "timestamp": str(event.timestamp),
            "source_type": event.source_type,
            "severity": event.severity,
            "event_type": event.event_type,
            "source_ip": event.source_ip,
            "dest_ip": event.dest_ip,
            "hostname": event.hostname,
            "username": event.username,
        }

        result = evaluate_rule(rule, event_data, state)
        if result:
            alerts_fired.append({
                "group_value": result.group_value,
                "matched_event_count": len(result.matched_event_ids),
                "matched_event_ids": result.matched_event_ids,
            })

    return {
        "rule_id": str(rule.id),
        "rule_name": rule.name,
        "events_evaluated": events.count(),  # type: ignore[no-untyped-call]
        "alerts_would_fire": len(alerts_fired),
        "alerts": alerts_fired,
    }
