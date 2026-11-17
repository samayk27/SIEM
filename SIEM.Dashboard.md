# SIEM Dashboard

## Overview

This project is a working SIEM demonstration. It ingests normalized events,
classifies severity, correlates events with threshold, sequence, and
aggregation rules, and presents alerts and investigations in a React dashboard.

It also includes a separate enterprise client at `http://localhost:7357`.
The client represents a monitored business application with signup, login,
document access, approvals, audit activity, and an external message integration.
Client activity is forwarded server-side to SIEM ingestion; ingestion
credentials are never exposed to the browser.

## Current Capabilities

- Flask, MongoDB, and Redis Streams backend
- React 19 dashboard with filterable logs, alert lifecycle management, and detail views
- Live log and alert SSE streams
- Manual refresh controls for alert and log queries
- Audible alert notifications and browser notifications for new alerts
- HTTP and UDP syslog ingestion
- Four YAML MITRE ATT&CK scenario playbooks
- Persistent client signup using SQLite and hashed passwords
- Client authentication telemetry for repeated failed logins
- Detection of SQL-injection-shaped input submitted to the client login endpoint
- Signed external application messages through `POST /api/external/messages`
- Re-triggerable correlation windows after a detection fires

## Quick Start

```bash
cd siem-dashboard
docker compose -f dev.compose.yml up --build
```

Open:

- Dashboard: `http://localhost:8431`
- Enterprise client: `http://localhost:7357`
- Client signup: `http://localhost:7357/signup`
- Backend: `http://localhost:5113`

## External Client Messages

Configure `CLIENT_EXTERNAL_KEY`, then send a message from another application:

```bash
curl -X POST http://localhost:7357/api/external/messages \
  -H "Content-Type: application/json" \
  -H "X-External-Key: $CLIENT_EXTERNAL_KEY" \
  -d '{"message":"Customer export job failed","integration":"billing"}'
```

The client displays the message in its integration activity panel and forwards
an auditable generic event to the SIEM.

## Learning Goals

- Log aggregation and normalization
- Sliding-window event correlation
- Alert lifecycle and analyst workflows
- Secure application telemetry
- React data fetching and SSE streams
- Dockerized multi-service deployment
