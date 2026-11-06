# HealCloud Infrastructure — IaC, Docker & Helm

This directory contains Infrastructure as Code (IaC), container orchestration manifests, and local development configurations.

## 📁 Architecture Preview
```text
infrastructure/
├── docker/
│   ├── docker-compose.dev.yml     # Local PostgreSQL + TimescaleDB & Redis stack
│   └── Dockerfile.backend         # Production multi-stage backend image
├── helm/                          # Helm charts for deploying HealCloud to Kubernetes
│   ├── healcloud/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
└── terraform/                     # Cloud provider provisioning (AWS/GCP/Azure)
    ├── modules/
    └── environments/
        ├── staging/
        └── production/
```

## 🚀 Running Local Backing Services
```bash
docker compose -f docker/docker-compose.dev.yml up -d
```
Starts:
- **PostgreSQL 16 with TimescaleDB:** Port 5432
- **Redis 7:** Port 6379

