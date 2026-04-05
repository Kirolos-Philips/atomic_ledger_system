# ──────────────────────────────────────────────────────────────
# Stage 1: Build — install dependencies with uv
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /usr/local/bin/

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Install dependencies separately for caching
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# ──────────────────────────────────────────────────────────────
# Stage 2: Runtime — minimal production image
# ──────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm

# Runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        postgresql-client \
        netcat-openbsd \
        gettext \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary into runtime stage as well
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /usr/local/bin/

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

WORKDIR /app

# Environment configuration
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy venv and application code
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --chown=appuser:appgroup . .

# Ensure entrypoint is executable (relative to context root)
RUN chmod +x /app/docker/entrypoint.sh

USER appuser

EXPOSE 8000

# Default entrypoint and command
CMD ["/app/docker/entrypoint.sh", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "config.wsgi:application"]
