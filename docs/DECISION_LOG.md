# Architecture Decision Log (ADR)

| **Document Title** | HealCloud Architectural Decision Records (ADR 001–006) |
| :--- | :--- |
| **Document Version** | 1.0.0 |
| **Status** | Active |

---

## ADR-001: Monorepo Architecture for HealCloud Codebase

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  HealCloud consists of multiple interconnected subsystems: the telemetry ingestion backend, an asynchronous remediation worker engine, an SRE web dashboard, infrastructure IaC configurations, tests, and documentation. We evaluated whether to split these into distinct repositories or unify them under a single monorepo.
- **Decision:**
  Adopt a structured monorepo containing `backend/`, `worker/`, `frontend/`, `infrastructure/`, `tests/`, `postman/`, and `docs/`.
- **Consequences:**
  - *Positive:* Atomic commits across API schemas and frontend consumers; unified CI/CD pipelines; shared documentation and data models; simplified developer onboarding.
  - *Trade-offs:* Requires robust path-based CI filtering so frontend changes do not re-run backend test pipelines.

---

## ADR-002: Python FastAPI for Core Backend & Ingestion API

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  The core API must handle high-throughput telemetry ingestion, interface with cloud provider SDKs (Boto3, Kubernetes Python client, Google Cloud SDK), and perform data analysis for anomaly detection. We considered Go, Node.js (TypeScript), and Python.
- **Decision:**
  Select Python 3.11+ with **FastAPI** running under Uvicorn/Gunicorn.
- **Consequences:**
  - *Positive:* Native support for asynchronous I/O (`async`/`await`); direct access to Python's rich data science and ML ecosystem (NumPy, Scikit-learn, PyTorch, LangChain); first-class SDK support from all major cloud providers; automatic OpenAPI 3.0 interactive documentation.
  - *Trade-offs:* Raw CPU-bound ingestion throughput is slightly lower than compiled Go; mitigated by offloading event streams to Redis and using C-optimized libraries (uvloop, orjson).

---

## ADR-003: Distributed Task Orchestration with Redis & Celery

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  Remediation workflows require decoupled, reliable background execution outside the HTTP request/response cycle. Actions must be queued, retried with exponential backoff, rate-limited, and protected by distributed locks.
- **Decision:**
  Deploy **Celery** with **Redis** as both the message broker and result backend, with an architecture designed to support a gradual migration to **Temporal** for multi-step durable orchestrations in Phase 5.
- **Consequences:**
  - *Positive:* Proven stability in production environments; native Python integration; rich support for task routing, retries, and rate limits; Redis delivers sub-millisecond dispatch latencies.
  - *Trade-offs:* Celery lacks native durable workflow state machines for long pauses; addressed by maintaining workflow state in PostgreSQL.

---

## ADR-004: Hybrid Storage Model (PostgreSQL + TimescaleDB + Redis)

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  HealCloud manages two distinct data access patterns: relational, transactional data (users, organizations, playbooks, incidents, audit records) and high-velocity time-series telemetry (metrics, alerts, traces).
- **Decision:**
  Implement a unified PostgreSQL 16 datastore enhanced with the **TimescaleDB** extension for time-series hypertables, complemented by **Redis 7** for ephemeral caching and distributed locks.
- **Consequences:**
  - *Positive:* Avoids the operational overhead of running separate relational and NoSQL/time-series database clusters (e.g., Cassandra or InfluxDB); allows unified SQL joins between telemetry events and incident metadata; TimescaleDB provides automated 1-day chunking and zstd compression.
  - *Trade-offs:* Requires the TimescaleDB extension in PostgreSQL containers; requires managed PostgreSQL instances that support custom extensions in cloud deployments.

---

## ADR-005: Next.js 14 App Router for SRE Operational Console

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  The frontend console must provide real-time updates during incidents, load instantly under high-stress conditions, and render complex topology maps and telemetry graphs. We evaluated single-page Vite/React, Remix, and Next.js.
- **Decision:**
  Build the frontend console using **Next.js 14 (App Router)** with React, Tailwind CSS, TanStack Query, and Lucide Icons.
- **Consequences:**
  - *Positive:* Fast initial page loads via Server Components; unified TypeScript types with backend OpenAPI generators; built-in routing and layout persistence; effortless integration with WebSocket clients.
  - *Trade-offs:* Need to separate client components (`"use client"`) for real-time WebSocket listeners and interactive Canvas/SVG topology graphs.

---

## ADR-006: Multi-Layer Guardrail Architecture for Automated Remediation

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  Automated cloud remediations introduce the danger of "automation runaway" (e.g., an automated reboot loop that crashes an entire cluster, or cascading restarts that exhaust cloud quotas).
- **Decision:**
  Enforce a non-bypassable, multi-tier Guardrail Engine embedded in the execution pipeline:
  1. *Resource-level cooldowns (anti-flapping):* 300s minimum between actions on the same resource.
  2. *Cluster concurrency caps:* Max 2 concurrent automated remediations per cluster.
  3. *Circuit breaker:* 2 consecutive failures immediately lock the service into `MANUAL_ONLY` mode.
  4. *Risk classification:* Tier 1 (safe/read-only) runs automatically; Tier 3 (destructive) strictly requires Human-in-the-Loop (HITL) dual-custody authorization.
- **Consequences:**
  - *Positive:* Eliminates risk of catastrophic cascading failures; establishes confidence with enterprise security and operations leadership.
  - *Trade-offs:* Slightly increases resolution time for high-risk incidents due to manual approval delays, which is an intentional safety compromise.
