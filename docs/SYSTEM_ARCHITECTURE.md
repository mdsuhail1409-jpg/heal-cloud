# System Architecture Specification

| **Document Title** | HealCloud Distributed Architecture & Data Flow |
| :--- | :--- |
| **Document Version** | 1.0.0 |
| **Status** | Approved |

---

## 1. High-Level Architecture Overview

HealCloud is structured as an event-driven, decoupled microservices platform. The system operates on a closed-loop observability and remediation lifecycle:
1. **Ingest:** Telemetry, logs, and alerts stream into high-throughput API endpoints.
2. **Correlate & Diagnose:** Telemetry is debounced and correlated against a real-time topology map to identify root causes.
3. **Decide:** The policy engine selects an appropriate playbook and evaluates safety guardrails (cooldowns, rate limits, blast radius).
4. **Remediate:** The asynchronous worker engine executes actions against cloud/Kubernetes APIs under optional Human-in-the-Loop (HITL) gates.
5. **Verify & Audit:** The system validates system health post-remediation, rolling back if unhealed, and commits an immutable audit record.

```mermaid
flowchart TD
    subgraph ObservabilitySources["Observability & Cloud Sources"]
        Prom["Prometheus / Alertmanager"]
        OTel["OpenTelemetry Collector"]
        CW["AWS CloudWatch / Datadog"]
        K8sEvt["Kubernetes Event Exporter"]
    end

    subgraph HealCloudPlatform["HealCloud Core Platform"]
        IngestAPI["Ingestion API\n(FastAPI / REST / Webhooks)"]
        EventBus[("Event Stream & Queue\n(Redis Streams / Kafka)")]
        
        CoreAPI["Core Platform API\n(FastAPI / Auth / Policies / State)"]
        RCAEngine["RCA & Anomaly Engine\n(Correlation / Topology Graph)"]
        
        WorkerEngine["Remediation Worker\n(Celery / Redis / Temporal)"]
        Guardrails["Safety & Blast Radius Engine\n(Rate-limits, Cooldowns, Circuit Breakers)"]
        
        DB[("PostgreSQL + TimescaleDB\n(Incidents, Playbooks, Audit Logs, Metrics)")]
        Cache[("Redis Cache & Lock\n(Distributed State & Leases)")]
    end

    subgraph FrontendApp["User & Operator Interfaces"]
        NextUI["SRE Incident Console\n(Next.js 14 App Router)"]
        SlackBot["Slack / Teams HITL Notifier"]
    end

    subgraph ManagedInfrastructure["Target Cloud Infrastructure"]
        TargetK8s["Kubernetes Clusters\n(Pods, Deployments, Nodes)"]
        TargetAWS["AWS / GCP / Azure\n(ASGs, EC2, Cloud Databases)"]
    end

    ObservabilitySources -->|HTTP / Webhooks / OTLP| IngestAPI
    IngestAPI -->|Produce Events| EventBus
    EventBus -->|Consume & Correlate| RCAEngine
    RCAEngine <--> CoreAPI
    RCAEngine -->|Store Incident & Diagnosis| DB
    
    CoreAPI --> Guardrails
    Guardrails -->|Schedule Task| WorkerEngine
    WorkerEngine <-->|Distributed Locks| Cache
    WorkerEngine -->|Execute Action| TargetK8s
    WorkerEngine -->|Execute Action| TargetAWS
    
    CoreAPI <--> DB
    CoreAPI <--> Cache
    
    NextUI <-->|REST & WebSockets| CoreAPI
    WorkerEngine -->|HITL Approval Request| SlackBot
    SlackBot -->|Approve / Reject| CoreAPI
```

---

## 2. Component Deep-Dive

### 2.1 Telemetry Ingestion Layer (`backend/app/ingestion`)
- **FastAPI Ingestion Endpoints:** High-throughput, stateless endpoints running under ASGI (`uvicorn`) optimized for low-latency JSON and protobuf payloads.
- **Webhook Adapters:** Specialized adapters translating incoming webhook formats (Prometheus Alertmanager, Datadog v2, AWS SNS CloudWatch, PagerDuty) into standardized `TelemetryEvent` models.
- **Debounce Buffer:** Sliding window (30-second bucket) to group correlated alerts from flapping systems into a unified incident context.

### 2.2 Core API Service (`backend/app/api`)
- **Authentication & Multi-Tenancy:** JWT-based user authentication, API key validation (`hc_live_...`), and organization-level data segregation.
- **Incident State Machine:** Manages state transitions:
  `DETECTED` $\rightarrow$ `DIAGNOSING` $\rightarrow$ `AWAITING_APPROVAL` $\rightarrow$ `REMEDIATING` $\rightarrow$ `VERIFYING` $\rightarrow$ `RESOLVED` / `FAILED_ROLLED_BACK`.
- **Playbook Registry:** CRUD management, YAML schema validation, and version control for automated remediation playbooks.

### 2.3 Anomaly Correlation & RCA Engine (`backend/app/engine`)
- **Topology Graph Provider:** Maintains an in-memory graph of resource relationships (e.g., `Cluster` $\rightarrow$ `Namespace` $\rightarrow$ `Deployment` $\rightarrow$ `Pod` $\rightarrow$ `Node` $\rightarrow$ `VPC`).
- **Statistical Analyzers:** Exponentially Weighted Moving Average (EWMA) and dynamic thresholds to detect metric deviations across error rates, CPU/Memory saturation, and connection pools.
- **Diagnosis Generator:** Synthesizes anomalous signals, queries the topology graph for the bottleneck resource, and calculates confidence scores for probable root causes.

### 2.4 Remediation Worker Engine (`worker/`)
- **Asynchronous Task Queue:** Powered by Celery with Redis broker (with roadmap migration to Temporal for long-running workflows).
- **Execution Sandbox:** Every cloud action runs inside an isolated worker process with strict timeouts (default 60s per task).
- **Distributed Locking:** Uses Redis distributed locks (`redlock`) keyed on the target resource ID (e.g., `lock:k8s:pod:prod-checkout-service`) to prevent concurrent competing remediation actions.
- **Rollback Engine:** Each action plugin defines a corresponding reverse `rollback()` function executed automatically if post-remediation health probes fail.

### 2.5 Safety & Blast Radius Control (`backend/app/guardrails`)
- **Rate-Limiter:** Enforces quotas per resource (e.g., maximum 2 pod restarts per 10 minutes per deployment).
- **Circuit Breaker:** Automatically trips to open state if consecutive remediations fail or if cluster health worsens, freezing automated execution and paging on-call engineers.
- **Maintenance Windows:** Suppresses automated actions during scheduled deployment or maintenance windows.

### 2.6 Frontend SRE Console (`frontend/`)
- **Framework:** Next.js 14 (App Router) with React, Tailwind CSS, and TanStack Query.
- **Real-Time Updates:** WebSocket connection to `/api/v1/ws/incidents` delivering instant updates as state changes occur.
- **Interactive Visualizations:** Topology graph rendering, incident timeline scrubber, and visual playbook builder.

---

## 3. Incident Lifecycle & Remediation Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Cloud as Target Cloud / K8s
    participant Ingest as Ingestion API
    participant RCA as RCA Engine
    participant Core as Core API
    participant Guard as Guardrail Engine
    participant UI as SRE Console / Slack
    participant Worker as Remediation Worker

    Cloud->>Ingest: Webhook / Telemetry Alert (OOMKill Alert)
    Ingest->>RCA: Forward Normalized TelemetryEvent
    RCA->>RCA: Correlate with Topology Graph & Logs
    RCA->>Core: Create Incident (Status: DIAGNOSING)
    Core->>UI: Broadcast Incident Detected via WebSocket
    
    RCA->>Core: Incident Diagnosed (Confidence: 94%, Playbook: pod_memory_boost)
    Core->>Guard: Evaluate Playbook Safety & Risk Tier
    
    alt Low Risk (Tier 1) - Auto Approve
        Guard-->>Core: Safety Approved (Under Quota & Circuit Closed)
        Core->>Worker: Enqueue Remediation Job
    else High Risk (Tier 3) - Human Approval Required
        Guard-->>Core: Requires Manual Approval
        Core->>UI: Request Approval (Slack / Dashboard Notification)
        UI->>Core: Operator Clicks "Approve Remediation"
        Core->>Worker: Enqueue Remediation Job
    end

    Worker->>Worker: Acquire Distributed Resource Lock
    Worker->>Cloud: Execute Action (Patch K8s Deployment Memory & Restart)
    Worker->>Cloud: Run Post-Remediation Health Verification (60s)
    
    alt Health Verification Passes
        Worker->>Core: Report Success
        Core->>Core: Update Incident (Status: RESOLVED)
        Core->>UI: Broadcast Incident Resolved
    else Health Verification Fails
        Worker->>Cloud: Trigger Automatic Rollback
        Worker->>Core: Report Failure & Escalation
        Core->>Core: Trip Circuit Breaker & Page On-Call
        Core->>UI: Broadcast Failure & Paged Alert
    end
    Worker->>Worker: Release Distributed Resource Lock
```

---

## 4. Fault Tolerance & Self-Protection

1. **Dead-Man Switch:** If the HealCloud agent loses connectivity to target clusters or heartbeat expires, automated actions are suspended.
2. **Idempotent Operations:** All remediation actions are implemented to be strictly idempotent; re-running an action produces no unintended secondary side-effects.
3. **Database Write Resiliency:** Telemetry ingestion buffers incoming spikes in Redis Streams, decoupling ingestion throughput from database write limits.
