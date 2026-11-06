# HealCloud Test Suite — Unit, Integration & Chaos Tests

This directory contains automated test suites ensuring reliability, safety guardrail enforcement, and chaos resilience.

## 📁 Test Hierarchy
```text
tests/
├── unit/                 # Fast, isolated unit tests (FastAPI routes, schema validation)
├── integration/          # Database, Redis queue, and mock cloud connector tests
├── e2e/                  # End-to-end incident lifecycle simulation
└── chaos/                # Chaos Mesh and failure-injection simulations
```

## 🚀 Running Tests
```bash
pytest tests/unit/ -v
pytest tests/integration/ -v
```

