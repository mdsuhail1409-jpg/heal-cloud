# API Specification & Contracts

| **Document Title** | HealCloud Core RESTful & WebSocket API Reference |
| :--- | :--- |
| **Document Version** | 1.0.0 |
| **API Version** | `v1` |
| **Status** | Approved |

---

## 1. Overview & Conventions

HealCloud exposes a RESTful API for platform management and telemetry ingestion, alongside a WebSocket API for real-time incident event streaming.

- **Base URL:** `https://api.healcloud.io/api/v1` (Production) / `http://localhost:8000/api/v1` (Local Dev)
- **Data Format:** Requests and responses use UTF-8 `application/json`.
- **Date/Time Standard:** ISO-8601 UTC timestamps (e.g., `2026-11-06T12:00:00Z`).
- **Error Standard:** Compliant with [RFC 7807 (Problem Details for HTTP APIs)](https://tools.ietf.org/html/rfc7807).

---

## 2. Authentication & Authorization

All requests outside public webhook endpoints require an `Authorization` header:

- **User JWT Token:** `Authorization: Bearer <jwt_token>`
- **API Key (Agents / CI/CD):** `Authorization: Bearer hc_live_9f83b2a14e...`

### Standard Error Response Format (RFC 7807)
```json
{
  "type": "https://errors.healcloud.io/insufficient_permissions",
  "title": "Insufficient Permissions",
  "status": 403,
  "detail": "User role 'VIEWER' is not authorized to trigger remediation actions.",
  "instance": "/api/v1/incidents/inc-4291/remediate",
  "timestamp": "2026-11-06T12:35:00Z"
}
```

---

## 3. Endpoints Reference

### 3.1 Authentication

#### `POST /api/v1/auth/login`
Authenticates a user and returns a JWT access token.

- **Request:**
```json
{
  "email": "sarah.sre@acme-cloud.io",
  "password": "SecurePassword123!"
}
```

- **Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "c1f7a049-74d6-444a-9db1-30ef48e83311",
    "email": "sarah.sre@acme-cloud.io",
    "full_name": "Sarah Chen",
    "role": "SRE_LEAD",
    "organization_id": "9a38f711-e402-45e6-b632-132d72120023"
  }
}
```

---

### 3.2 Telemetry & Webhook Ingestion

#### `POST /api/v1/telemetry/events`
High-velocity ingest endpoint for custom agents or OTel forwarders.

- **Request:**
```json
{
  "events": [
    {
      "timestamp": "2026-11-06T12:30:15Z",
      "service_id": "srv-prod-checkout",
      "event_type": "metric_anomaly",
      "severity": "CRITICAL",
      "metric_name": "container_memory_working_set_bytes",
      "metric_value": 1048576000.0,
      "tags": {
        "namespace": "production",
        "pod": "checkout-api-79b8c645b-x7zpq",
        "node": "ip-10-0-14-22.ec2.internal"
      }
    }
  ]
}
```

- **Response (`202 Accepted`):**
```json
{
  "status": "accepted",
  "events_ingested": 1,
  "batch_id": "batch-88914-uuid"
}
```

#### `POST /api/v1/webhooks/{provider}`
Generic webhook receiver supporting Prometheus Alertmanager, Datadog, AWS CloudWatch, and PagerDuty.
- Providers supported: `prometheus`, `datadog`, `aws_sns`, `pagerduty`

---

### 3.3 Incidents & Diagnostics (RCA)

#### `GET /api/v1/incidents`
Lists all active or historic incidents with filtering and pagination.

- **Query Parameters:**
  - `status`: Filter by status (`DETECTED`, `DIAGNOSING`, `AWAITING_APPROVAL`, `REMEDIATING`, `RESOLVED`, `FAILED`)
  - `severity`: Filter by severity (`P1_CRITICAL`, `P2_HIGH`, `P3_MEDIUM`)
  - `page`: Page number (default: 1)
  - `limit`: Items per page (default: 20, max: 100)

- **Response (`200 OK`):**
```json
{
  "data": [
    {
      "id": "e4a2c071-8bc9-4b47-9877-2e2e9cba0012",
      "incident_number": "INC-2026-1049",
      "title": "Severe Memory Saturation & OOMKill risk in checkout-api",
      "severity": "P1_CRITICAL",
      "status": "AWAITING_APPROVAL",
      "service": {
        "id": "srv-prod-checkout",
        "name": "checkout-api",
        "environment": "production"
      },
      "rca_confidence": 0.94,
      "triggered_at": "2026-11-06T12:31:00Z"
    }
  ],
  "pagination": {
    "total_count": 1,
    "page": 1,
    "limit": 20,
    "total_pages": 1
  }
}
```

#### `GET /api/v1/incidents/{id}`
Retrieves full incident dossier including evidence, correlated traces, and recommended playbook.

- **Response (`200 OK`):**
```json
{
  "id": "e4a2c071-8bc9-4b47-9877-2e2e9cba0012",
  "incident_number": "INC-2026-1049",
  "title": "Severe Memory Saturation & OOMKill risk in checkout-api",
  "severity": "P1_CRITICAL",
  "status": "AWAITING_APPROVAL",
  "root_cause_summary": "Heap memory leak detected following canary release v2.14.0. Working set memory exceeded 92% of pod limit (1024MiB).",
  "rca_confidence": 0.94,
  "evidence": [
    {
      "type": "metric_threshold_breach",
      "metric": "container_memory_working_set_bytes",
      "threshold": 950000000,
      "observed": 1024000000
    },
    {
      "type": "log_pattern",
      "pattern": "java.lang.OutOfMemoryError: Java heap space",
      "occurrence_count": 18
    }
  ],
  "recommended_playbook": {
    "id": "pb-k8s-rollback-canary",
    "name": "Canary Rollback & Memory Limit Boost",
    "risk_tier": "TIER_3_HIGH",
    "requires_hitl": true
  }
}
```

#### `POST /api/v1/incidents/{id}/remediate`
Manually or programmatically triggers an automated remediation execution.

- **Request:**
```json
{
  "playbook_id": "pb-k8s-rollback-canary",
  "override_parameters": {
    "target_revision": "v2.13.9",
    "drain_grace_period_sec": 30
  }
}
```

- **Response (`202 Accepted`):**
```json
{
  "remediation_run_id": "run-f9821034-77a4-44cf",
  "incident_id": "e4a2c071-8bc9-4b47-9877-2e2e9cba0012",
  "status": "QUEUED",
  "estimated_duration_sec": 45
}
```

---

### 3.4 Remediation Approvals (Human-in-the-Loop)

#### `POST /api/v1/remediations/{id}/approve`
Grants operator authorization for Tier 3 remediation actions.

- **Request:**
```json
{
  "approval_notes": "Reviewed heap metrics. Approved rollback to v2.13.9."
}
```

- **Response (`200 OK`):**
```json
{
  "remediation_run_id": "run-f9821034-77a4-44cf",
  "status": "RUNNING",
  "authorized_by": "sarah.sre@acme-cloud.io",
  "authorized_at": "2026-11-06T12:36:10Z"
}
```

---

### 3.5 Real-Time WebSockets

#### `GET /api/v1/ws/incidents`
Full-duplex WebSocket connection for streaming incident lifecycle transitions and telemetry graphs to the frontend.

- **Client Handshake:**
  `ws://localhost:8000/api/v1/ws/incidents?token=<jwt_token>`

- **Server Stream Message Example:**
```json
{
  "event": "INCIDENT_STATE_CHANGED",
  "payload": {
    "incident_id": "e4a2c071-8bc9-4b47-9877-2e2e9cba0012",
    "old_status": "AWAITING_APPROVAL",
    "new_status": "REMEDIATING",
    "active_step": "Patching Kubernetes deployment to revision v2.13.9",
    "progress_percent": 40,
    "timestamp": "2026-11-06T12:36:12Z"
  }
}
```

