# HealCloud Worker — Autonomous Remediation Engine

This directory contains the distributed asynchronous worker engine responsible for executing self-healing actions across Kubernetes and multi-cloud infrastructure.

## 🛠️ Tech Stack
- **Framework:** Celery 5.3+ (Python 3.11+)
- **Broker / Results:** Redis 7
- **Cloud Clients:** `kubernetes-client`, `boto3` (AWS), `google-cloud-sdk`, `azure-mgmt`
- **Locking:** `redlock-py` (Distributed resource locks)

## 📁 Architecture Preview
```text
worker/
├── tasks/
│   ├── k8s/              # Kubernetes remediation actions (restart, rollback, scale)
│   ├── aws/              # AWS actions (ASG bump, EC2 reboot, target group drain)
│   ├── gcp/              # Google Cloud actions
│   └── verification.py   # Post-remediation health check verification & rollback
├── locks/                # Distributed resource locking mechanisms
├── celery_app.py         # Celery configuration & task routing
└── requirements.txt      # Worker dependencies
```

## 🚀 Quickstart
```bash
celery -A celery_app worker --loglevel=info --concurrency=4
```

