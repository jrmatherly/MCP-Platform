# Multi-stage build using official uv base image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as builder

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Runtime stage - using same base as builder for consistency
FROM python:3.11-bookworm-slim as runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
    python -c "import sys, urllib.request; \
    sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:7072/health').getcode() == 200 else sys.exit(1)"

# Expose port
EXPOSE 7072

# Run the server
CMD ["python", "server.py"]
