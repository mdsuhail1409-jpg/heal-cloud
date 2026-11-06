# Architecture Decision Log (ADR)

| **Document Title** | HealCloud Architectural Decision Records (ADR 001–006) |
| :--- | :--- |
| **Document Version** | 2.0.0 (Master Plan Aligned) |
| **Status** | Active |

---

## ADR-001: Modular Monolith Architecture with Separated Background Workers

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  HealCloud must support multiple operational domains (auth, tenancy, service inventory, active monitoring, incident detection, rule-based diagnosis, recovery policies, simulator, and audit logging). Microservices introduce operational complexity, network latency, distributed transactions, and deployment overhead not suitable for an initial SaaS MVP.
- **Decision:**
  Implement a **Modular Monolith** using FastAPI in Python, paired with independently running Celery/Redis background worker processes.
- **Consequences:**
  - *Positive:* High cohesion, explicit domain boundaries, simple local development, unified transactions where needed, and low latency between modules.
  - *Trade-offs:* Requires discipline in code boundaries to prevent circular dependencies between modules.

---

## ADR-002: Cloud-Agnostic Core with Provider Adapters

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  Many reliability tools become tightly coupled to specific cloud providers (e.g. AWS-only CloudWatch or Kubernetes-only controllers). HealCloud is a cloud-agnostic SaaS product that must operate across any infrastructure without requiring any single cloud provider as a prerequisite.
- **Decision:**
  Keep the core platform cloud-agnostic. Target services are registered via generic network/HTTP endpoints and abstracted health definitions. Any future cloud provider integrations (AWS, Azure, GCP, Kubernetes) must reside in isolated provider adapters.
- **Consequences:**
  - *Positive:* Broad market applicability, zero cloud vendor lock-in, runnable on local Docker, Render, Vercel, or on-premise.
  - *Trade-offs:* Cloud-specific advanced actions must be mapped through generic adapter interfaces.

---

## ADR-003: Safe Recovery Simulator for MVP

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  Allowing automated software or AI agents to issue arbitrary, uncontrolled terminal or cloud API commands against live infrastructure poses catastrophic availability and security risks.
- **Decision:**
  For the initial MVP, recovery actions are executed strictly through an isolated **Safe Recovery Simulator** against explicitly registered test services. No arbitrary terminal commands, unrestricted shell access, or unverified infrastructure modifications are permitted.
- **Consequences:**
  - *Positive:* Guarantees zero risk of accidental infrastructure destruction; enables full deterministic testing of detection, approval, recovery, and verification lifecycles.
  - *Trade-offs:* Real cloud infrastructure changes are deferred until adapter sandboxes and verification engines are fully hardened in post-MVP phases.

---

## ADR-004: React + Vite + TypeScript for Frontend Console

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  The frontend console requires fast page loads, rapid feedback loops, type safety, and real-time state management for SRE workflows.
- **Decision:**
  Build the frontend with **React, TypeScript, Vite, Tailwind CSS, React Router, and TanStack Query**.
- **Consequences:**
  - *Positive:* Sub-second Hot Module Replacement (HMR) with Vite; clean SPA deployment to static CDNs (Vercel); strong type guarantees shared with backend OpenAPI specifications; robust caching and refetching via TanStack Query.
  - *Trade-offs:* Client-side rendering requires proper loading skeletons and optimistic UI patterns.

---

## ADR-005: PostgreSQL Relational Database with Multi-Tenant Scoping

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  HealCloud is a multi-tenant SaaS requiring strict data isolation, foreign key referential integrity, and reliable transactions across 16 core entities.
- **Decision:**
  Standardize on **PostgreSQL 16** with SQLAlchemy 2.0 ORM and Alembic migrations. Enforce multi-tenancy at the data-access layer by always scoping queries to `organization_id` and `workspace_id`.
- **Consequences:**
  - *Positive:* Rock-solid ACID guarantees, rich JSONB support for flexible metadata and event payloads, excellent index performance.
  - *Trade-offs:* Tenant filtering must be rigorously enforced and verified with automated cross-tenant security tests.

---

## ADR-006: Celery + Redis Background Task Processing

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  Health checks, metric collection, and recovery simulations cannot block the web request loop. They must be executed on configurable schedules with timeouts and retry limits.
- **Decision:**
  Deploy **Celery** with **Redis** as the task broker and distributed mutex lock provider.
- **Consequences:**
  - *Positive:* Asynchronous execution, horizontal worker scalability, distributed locking (`redlock`) preventing duplicate executions on the same service.
  - *Trade-offs:* Requires running and monitoring separate worker processes alongside the web API.

---

## ADR-007: Threshold-Based Detection, Duplicate Incident Suppression & Explainable Diagnosis

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:**
  Observability systems suffer from alert storms where multiple failures for the same root cause spawn hundreds of disjointed tickets. Furthermore, automated root-cause engines must be explainable and deterministic—guessing or hallucinating causes when telemetry is insufficient causes operator distrust.
- **Decision:**
  Implement a deterministic detection engine with 5 explicit threshold rules (`SERVICE_UNAVAILABLE`, `REPEATED_HEALTH_CHECK_FAILURE`, `RESPONSE_TIME_EXCEEDED`, `EXCESSIVE_CONSECUTIVE_FAILURES`, and `RECOVERY_VERIFICATION_FAILURE`).
  Enforce **Duplicate Incident Suppression**: if an incident is active for `(workspace_id, service_id)`, new failures escalate severity and append chronological timeline events rather than spawning duplicate tickets.
  Enforce **Explainable Diagnosis**: every diagnosis record links concrete evidence observations and rule names to the hypothesis. When evidence is insufficient or nominal, the system returns `RULE_INSUFFICIENT_EVIDENCE` and flags `MANUAL_INVESTIGATION` rather than inventing speculative causes.
- **Consequences:**
  - *Positive:* Zero alert fatigue, single cohesive incident timeline per failure cycle, clear auditable evidence for SREs, automatic resolution when health is restored.
  - *Trade-offs:* Multi-service cascading correlation requires explicit dependency graph traversals in advanced tiers.
