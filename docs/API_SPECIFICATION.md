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

All incident endpoints are tenant-scoped under an organization and workspace to enforce strict isolation.

#### `GET /api/v1/organizations/{org_id}/workspaces/{workspace_id}/incidents`
Lists all active or historic incidents within a workspace with filtering and pagination.

- **Query Parameters:**
  - `status`: Filter by status (`OPEN`, `ACKNOWLEDGED`, `INVESTIGATING`, `RECOVERY_PENDING`, `RECOVERING`, `RESOLVED`, `CLOSED`, `FAILED`)
  - `severity`: Filter by severity (`P1_CRITICAL`, `P2_HIGH`, `P3_MEDIUM`, `P4_LOW`)
  - `service_id`: Filter by target service UUID
  - `page`: Page number (default: 1)
  - `size`: Items per page (default: 20, max: 100)

- **Response (`200 OK`):**
```json
{
  "items": [
    {
      "id": "e4a2c071-8bc9-4b47-9877-2e2e9cba0012",
      "organization_id": "b1a2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "workspace_id": "c1f7a049-74d6-444a-9db1-30ef48e83311",
      "service_id": "srv-prod-checkout",
      "incident_number": "INC-2026-0001",
      "title": "Service Unavailable: checkout-api unreachable or HTTP 503",
      "description": "Automated incident triggered by RULE_SERVICE_UNAVAILABLE.",
      "severity": "P1_CRITICAL",
      "status": "OPEN",
      "assigned_to_user_id": null,
      "detected_at": "2026-11-06T12:31:00Z",
      "acknowledged_at": null,
      "resolved_at": null,
      "created_at": "2026-11-06T12:31:00Z",
      "updated_at": "2026-11-06T12:31:00Z",
      "service_name": "checkout-api",
      "events": [
        {
          "id": "evt-01",
          "incident_id": "e4a2c071-8bc9-4b47-9877-2e2e9cba0012",
          "event_type": "DETECTED",
          "message": "Incident detected by rule RULE_SERVICE_UNAVAILABLE: Service Unavailable: checkout-api unreachable",
          "payload": {"status_code": 503, "consecutive_failures": 3},
          "created_at": "2026-11-06T12:31:00Z"
        }
      ],
      "diagnoses": [
        {
          "id": "diag-01",
          "incident_id": "e4a2c071-8bc9-4b47-9877-2e2e9cba0012",
          "rule_name": "RULE_SERVICE_UNAVAILABLE",
          "root_cause_hypothesis": "Target endpoint is unreachable or returning server errors (HTTP 503). Process crash or port unresponsiveness likely.",
          "confidence_score": 0.85,
          "evidence": {"status_code": 503, "response_time_ms": 120.0},
          "recommended_action": "SIMULATE_RESTART",
          "created_at": "2026-11-06T12:31:00Z"
        }
      ]
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

#### `POST /api/v1/organizations/{org_id}/workspaces/{workspace_id}/incidents`
Manually opens an incident within a workspace. Requires `RELIABILITY_ENGINEER` role or higher.

- **Request:**
```json
{
  "service_id": "b1a2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "title": "Severe Database Connection Pool Exhaustion",
  "description": "Active connection pool utilization exceeded 98% with thread timeouts.",
  "severity": "P2_HIGH"
}
```

- **Response (`201 Created`):** Returns full `IncidentResponse` object with initial `DETECTED` event and explainable diagnosis.

#### `GET /api/v1/organizations/{org_id}/workspaces/{workspace_id}/incidents/{incident_id}`
Retrieves full incident dossier including service metadata, chronological event log, and root cause diagnostic history.

#### `POST /api/v1/organizations/{org_id}/workspaces/{workspace_id}/incidents/{incident_id}/acknowledge`
Acknowledges an open incident, setting status to `ACKNOWLEDGED` and recording operator identity and timestamp. Requires `RELIABILITY_ENGINEER` or higher.

- **Request:**
```json
{
  "note": "Investigating upstream dependency failure"
}
```

#### `POST /api/v1/organizations/{org_id}/workspaces/{workspace_id}/incidents/{incident_id}/assign`
Assigns an incident to an engineer. Requires `RELIABILITY_ENGINEER` or higher.

- **Request:**
```json
{
  "assigned_to_user_id": "c1f7a049-74d6-444a-9db1-30ef48e83311"
}
```

#### `PATCH /api/v1/organizations/{org_id}/workspaces/{workspace_id}/incidents/{incident_id}/status`
Updates incident status or severity, validating legal state transitions (e.g. `CLOSED` can only transition to `OPEN`). Requires `RELIABILITY_ENGINEER` or higher.

- **Request:**
```json
{
  "status": "INVESTIGATING",
  "severity": "P1_CRITICAL"
}
```

#### `POST /api/v1/organizations/{org_id}/workspaces/{workspace_id}/incidents/{incident_id}/diagnose`
Runs an on-demand explainable root-cause diagnosis evaluation. Never invents a cause when evidence is insufficient (returns `RULE_INSUFFICIENT_EVIDENCE` and recommends `MANUAL_INVESTIGATION`). Requires `RELIABILITY_ENGINEER` or higher.

- **Request:**
```json
{
  "force_re_evaluation": true
}
```

#### `POST /api/v1/organizations/{org_id}/workspaces/{workspace_id}/incidents/{incident_id}/remediate`
Manually or programmatically triggers an automated recovery execution under allowlisted policy guardrails. (Implemented in Phase 8).

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

