# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL org.opencontainers.image.title="AgriStack DBT Core" \
      org.opencontainers.image.description="Zero-Trust Sovereign DPI Orchestrator & G2P Connect (DCI) v1.0.0 Reference Implementation (DPGA GID0094462)" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/gargmishu/agristack-dbt-core"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Create dedicated non-root system user for Zero-Trust container isolation
RUN groupadd --gid 10001 agristack \
    && useradd --uid 10001 --gid agristack --shell /usr/sbin/nologin --create-home agristack

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY design-specs/step2-data-schemas/schema.sql ./design-specs/step2-data-schemas/schema.sql

RUN pip install --no-cache-dir . \
    && chown -R agristack:agristack /app

USER agristack

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]

CMD ["uvicorn", "src.public_agent.public_agent_http_server:create_public_agent_http_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
