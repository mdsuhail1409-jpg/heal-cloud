# Multi-stage Dockerfile for HealCloud FastAPI Backend
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 healcloud \
    && chown -R healcloud:healcloud /app

COPY --from=builder /root/.local /home/healcloud/.local
COPY --chown=healcloud:healcloud . .

RUN chown -R healcloud:healcloud /app

USER healcloud
ENV PATH=/home/healcloud/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python seed_demo_data.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
