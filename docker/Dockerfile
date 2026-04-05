# ──────────────────────────────────────────────────────────────
# Stage 1: Build — install dependencies with uv
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

# Copy uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /usr/local/bin/

WORKDIR /app

# Compile bytecode for faster cold starts
ENV UV_COMPILE_BYTECODE=1

# Install deps first (cached layer — only rebuilds when lock changes)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# ──────────────────────────────────────────────────────────────
# Stage 2: Runtime — minimal production image
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm

# Install only the runtime system deps we need (netcat for entrypoint health check)
RUN apt-get update && \
    apt-get install -y --no-install-recommends netcat-openbsd && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user before copying files
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

WORKDIR /app

# Venv path
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy venv from builder (--link for layer efficiency, --chown to skip extra chown layer)
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appgroup . .

# Make entrypoint executable
RUN chmod +x /app/docker/entrypoint.sh

USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "config.wsgi:application"]
