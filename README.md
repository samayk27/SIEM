```ruby
███████╗██╗███████╗███╗   ███╗
██╔════╝██║██╔════╝████╗ ████║
███████╗██║█████╗  ██╔████╔██║
╚════██║██║██╔══╝  ██║╚██╔╝██║
███████║██║███████╗██║ ╚═╝ ██║
╚══════╝╚═╝╚══════╝╚═╝     ╚═╝
```

[![Cybersecurity Projects](https://img.shields.io/badge/Cybersecurity--Projects-Project%20%2314-red?style=flat&logo=github)](https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/intermediate/siem-dashboard)
[![Python](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![License: AGPLv3](https://img.shields.io/badge/License-AGPL_v3-purple.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Live Demo](https://img.shields.io/badge/Live-siem.carterperez--dev.com-green?style=flat&logo=googlechrome)](https://siem.carterperez-dev.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker)](https://www.docker.com)

> Full-stack SIEM dashboard with real-time log correlation, alert workflows, and an isolated enterprise client demo.

*This is a quick overview — security theory, architecture, and full walkthroughs are in the [learn modules](#learn).*

**[Screenshots & live demo →](DEMO.md)**

## What It Does

- Real-time log ingestion and event correlation with three rule types (Threshold, Sequence, Aggregation)
- Four YAML-based attack playbooks mapped to MITRE ATT&CK (brute force, DNS tunneling, phishing, privilege escalation)
- Server-Sent Events for live alert feed with paginated, filterable log viewer
- Manual refresh controls for alert and log queries, plus audible/browser alert notifications
- Alert lifecycle management (acknowledge, investigate, resolve, false positive)
- Attack simulation engine that generates realistic multi-stage security events
- Client workspace with signup, secure sessions, approvals, document activity, and external message ingestion
- Client login telemetry for repeated failed passwords and SQL-injection-shaped authentication requests
- Built with Just for task automation with full Docker Compose deployment

## Quick Start

```bash
docker compose up -d
```

Visit `http://localhost:8431` or the live demo at [siem.carterperez-dev.com](https://siem.carterperez-dev.com/)

The isolated enterprise client demo is available at `http://localhost:7357`.
Users can sign in with the configured client identity or create an account
from `/signup`. Client actions such as document access, approvals, and failed
login requests are forwarded through the normal ingestion pipeline, so the
correlation engine creates alerts visible in the SIEM Alerts page.
The development default is `alex.chen` / `AcmeDemo!2026`; set
`CLIENT_SECRET_KEY` and `CLIENT_PASSWORD_HASH` in `.env` for a deployment.
It is a separate application and service: browser actions go to the client
service, which forwards only allowlisted telemetry to the SIEM over the
internal Docker network. The browser never receives the SIEM ingestion key.
External applications can send a signed message to
`POST /api/external/messages` using the `X-External-Key` header and a JSON
body such as `{"message":"Customer export job failed","integration":"billing"}`.
The client forwards the message into SIEM ingestion as an auditable event.
Configure `CLIENT_EXTERNAL_KEY` before using this integration.

The client also exposes an authenticated external message source:

```bash
curl -X POST http://localhost:7357/api/external/messages \
  -H "Content-Type: application/json" \
  -H "X-External-Key: $CLIENT_EXTERNAL_KEY" \
  -d '{"message":"Customer export job failed","integration":"billing"}'
```

> [!TIP]
> This project uses [`just`](https://github.com/casey/just) as a command runner. Type `just` to see all available commands.
>
> Install: `curl -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin`

## Stack

**Backend:** Flask, MongoEngine, Redis Streams, Pydantic, Argon2, JWT, Gunicorn

**Frontend:** React 19, TypeScript, Vite, TanStack Query, Zustand, visx, SCSS Modules

**Data:** MongoDB 8, Redis 7

## Learn

This project includes step-by-step learning materials covering security theory, architecture, and implementation.

| Module | Topic |
|--------|-------|
| [00 - Overview](siem-dashboard/learn/00-OVERVIEW.md) | Prerequisites and quick start |
| [01 - Concepts](siem-dashboard/learn/01-CONCEPTS.md) | Security theory and real-world breaches |
| [02 - Architecture](siem-dashboard/learn/02-ARCHITECTURE.md) | System design and data flow |
| [03 - Implementation](siem-dashboard/learn/03-IMPLEMENTATION.md) | Code walkthrough |
| [04 - Challenges](siem-dashboard/learn/04-CHALLENGES.md) | Extension ideas and exercises |

## License

AGPL 3.0
