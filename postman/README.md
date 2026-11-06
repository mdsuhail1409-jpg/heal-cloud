# HealCloud Postman Collection & API Testing

This directory provides exportable Postman collections and environment variables for exercising and testing the HealCloud Core API.

## 📦 Included Assets
- `healcloud.postman_collection.json`: Complete OpenAPI-aligned Postman Collection covering:
  - Authentication (`/api/v1/auth/login`, `/api/v1/auth/me`)
  - Telemetry Ingestion (`/api/v1/telemetry/events`, Webhooks)
  - Incident Management & On-Demand RCA (`/api/v1/incidents`)
  - Playbook Execution & Human-in-the-Loop Approvals (`/api/v1/remediations/{id}/approve`)

## 🚀 How to Use in Postman
1. Open Postman.
2. Click **Import** in the top navigation.
3. Select `healcloud.postman_collection.json`.
4. Configure collection variables (`baseUrl` set to `http://localhost:8000/api/v1`).
5. Execute the `Login` request to automatically populate the `bearerToken` environment variable.

