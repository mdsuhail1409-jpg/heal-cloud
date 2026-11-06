# HealCloud Backend — Ingestion & Core API Service

This directory contains the core RESTful API, telemetry ingestion pipelines, and RCA correlation engine.

## 🛠️ Tech Stack
- **Framework:** FastAPI (Python 3.11+)
- **Server:** Uvicorn (ASGI)
- **Database ORM:** SQLAlchemy 2.0 (Async) + Alembic migrations
- **Datastore:** PostgreSQL 16 with TimescaleDB
- **Cache & Event Bus:** Redis 7 (Streams + In-memory cache)

## 📁 Architecture Preview
```text
backend/
├── app/
│   ├── api/              # REST API v1 endpoints
│   │   ├── auth.py       # Authentication & JWT tokens
│   │   ├── incidents.py  # Incident management & diagnosis
│   │   ├── playbooks.py  # Playbook registry & validation
│   │   └── webhooks.py   # Ingestion webhook receivers
│   ├── core/             # Configuration, logging & security
│   ├── engine/           # RCA & anomaly correlation logic
│   ├── guardrails/       # Safety checks, rate limits & circuit breakers
│   ├── models/           # SQLAlchemy database models
│   ├── schemas/          # Pydantic v2 validation schemas
│   └── main.py           # FastAPI application entrypoint
├── alembic/              # Database migration scripts
├── requirements.txt      # Python dependencies
└── Dockerfile            # Container definition
```

## 🚀 Quickstart
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API Documentation available at `http://localhost:8000/docs`.

