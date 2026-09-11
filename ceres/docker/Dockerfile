# Railway API and worker image. The worker service overrides CMD with
# `python -m backend.worker`; both services run the same reviewed code image.
FROM python:3.12.10-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.production.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --upgrade pip \
    && /opt/venv/bin/python -m pip install --no-cache-dir -r requirements.production.txt

FROM python:3.12.10-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONPYCACHEPREFIX=/tmp/python-cache \
    HOME=/tmp \
    PATH=/opt/venv/bin:$PATH \
    PORT=8000

# libgomp is required by the XGBoost/scikit-learn runtime. libpq is used by
# asyncpg's PostgreSQL connectivity; no database files are stored in image.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home --uid 10001 tupan

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
# Copy only source required by the canonical FastAPI/worker runtime. .dockerignore
# excludes .env files, local Chroma data, logs, build artifacts, and UI assets.
COPY --chown=tupan:tupan backend ./backend
COPY --chown=tupan:tupan train ./train
COPY --chown=tupan:tupan radar ./radar

USER tupan
EXPOSE 8000
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT', '8000') + '/health', timeout=3).read()" || exit 1

# `exec` forwards Railway SIGTERM to Uvicorn. No reload mode and no local
# filesystem persistence are used. Railway provides PORT at runtime.
CMD ["/bin/sh", "-c", "exec python -m uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*' --timeout-graceful-shutdown 30"]