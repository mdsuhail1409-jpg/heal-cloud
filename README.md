# HealCloud

<p align="center">
  <strong>Intelligent Cloud Reliability & Self-Healing Platform</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/Architecture-Distributed%20Microservices-emerald" alt="Architecture" />
  <img src="https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python-3776AB?logo=fastapi" alt="Backend" />
  <img src="https://img.shields.io/badge/Worker-Celery%20%2F%20Redis-red?logo=redis" alt="Worker" />
  <img src="https://img.shields.io/badge/Frontend-Next.js%20%7C%20React-black?logo=next.js" alt="Frontend" />
  <img src="https://img.shields.io/badge/Status-Phase%201%20Planning-amber" alt="Status" />
</p>

---

## 📌 Overview

**HealCloud** is an autonomous cloud reliability and self-healing platform engineered to detect, diagnose, and remediate cloud infrastructure and microservice failures in real time. 

By unifying telemetry ingestion (metrics, logs, traces), automated Root Cause Analysis (RCA), and a deterministic playbook-driven remediation engine, HealCloud dramatically cuts **Mean Time to Resolution (MTTR)** from hours to seconds while enforcing strict safety guardrails and Human-in-the-Loop (HITL) approvals.

---

## ✨ Key Features

- **🌐 Multi-Cloud & Kubernetes Telemetry Ingestion**  
  Seamlessly collects real-time metrics, logs, and events from AWS, GCP, Azure, and Kubernetes via OpenTelemetry, Prometheus, and cloud-native webhooks.

- **🧠 Intelligent Root Cause Analysis (RCA)**  
  Correlates error spikes, latency anomalies, and infrastructure topology to pinpoint the exact failure vector rather than firing isolated alert floods.

- **⚡ Autonomous & Safe Self-Healing**  
  Executes declarative remediation playbooks (pod restarts, traffic shedding, auto-rollback of failed deployments, memory leak mitigation, and resource auto-scaling).

- **🛡️ Multi-Layer Guardrails & Blast Radius Control**  
  Enforces circuit breakers, execution rate limits, cooldown periods, and dual-custody approval gates for destructive operations.

- **🖥️ SRE Incident War Room & Live Dashboard**  
  Real-time visualization of infrastructure health, incident timelines, diagnostic confidence scores, and one-click manual overrides.

- **🔒 Enterprise Audit & Non-Repudiation**  
  Cryptographically verifiable audit log of every automated diagnostic check and remediation action taken across your cloud estate.

---

## 🏗️ Repository Structure

```text
healcloud/
│
├── README.md               # Main project documentation & overview
├── LICENSE                 # MIT Open-Source License
├── .gitignore              # Multi-stack ignore rules (Python, Node, Docker, Terraform)
│
├── docs/                   # Core architecture & specifications
│   ├── PRD.md                     # Product Requirements Document
│   ├── SYSTEM_ARCHITECTURE.md     # High-level architecture & data flows
│   ├── DATABASE_DESIGN.md         # Relational & time-series database schemas
│   ├── API_SPECIFICATION.md       # OpenAPI / RESTful endpoint reference
│   ├── SECURITY_DESIGN.md         # Threat model, RBAC, and guardrail design
│   ├── UI_UX_SPECIFICATION.md     # SRE console wireframes & design system
│   ├── DEVELOPMENT_ROADMAP.md     # Milestones & phased delivery schedule
│   └── DECISION_LOG.md            # Architecture Decision Records (ADRs)
│
├── frontend/               # Next.js / React SRE dashboard & incident console
├── backend/                # FastAPI / Python core REST API & telemetry ingestion
├── worker/                 # Asynchronous remediation engine (Celery / Redis / Temporal)
├── infrastructure/         # Terraform, Helm charts, Docker Compose configurations
├── tests/                  # End-to-end, integration, and chaos simulation suites
└── postman/                # Postman API collections & environment templates
```

---

## 📚 Documentation Quick Links

| Document | Description |
| :--- | :--- |
| [docs/PRD.md](docs/PRD.md) | Product vision, target personas, functional & non-functional requirements |
| [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | Component architecture, event flows, and reliability design |
| [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md) | PostgreSQL + TimescaleDB ERD, tables, and indexing policies |
| [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md) | REST API endpoints, payloads, WebSocket contracts, and error schemes |
| [docs/SECURITY_DESIGN.md](docs/SECURITY_DESIGN.md) | STRIDE threat model, IAM delegation, safety guardrails, and compliance |
| [docs/UI_UX_SPECIFICATION.md](docs/UI_UX_SPECIFICATION.md) | SRE user flows, component system, dark-mode ergonomics, and shortcuts |
| [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) | 6-phase development milestones and risk management plan |
| [docs/DECISION_LOG.md](docs/DECISION_LOG.md) | Architectural Decision Records (ADR 001–006) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+ & pnpm
- Docker & Docker Compose
- PostgreSQL 16+ (with TimescaleDB extension recommended)
- Redis 7+

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-org>/healcloud.git
   cd healcloud
   ```

2. **Start backing services (PostgreSQL & Redis):**
   ```bash
   docker compose -f infrastructure/docker-compose.dev.yml up -d
   ```

3. **Initialize the Backend API:**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

4. **Start the Remediation Worker:**
   ```bash
   cd ../worker
   celery -A worker.celery_app worker --loglevel=info
   ```

5. **Start the Frontend SRE Console:**
   ```bash
   cd ../frontend
   pnpm install
   pnpm dev
   ```

---

## 📄 License

This project is licensed under the terms of the [MIT License](LICENSE).
