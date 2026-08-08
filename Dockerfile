# Multi-stage production Dockerfile for Enterprise AI Assistant
FROM python:3.12-slim as builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runner stage
FROM python:3.12-slim as runner

WORKDIR /app

# Install runtime dependencies (libpq for postgres, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root application user
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser

# Copy application source code
COPY backend ./backend
COPY frontend ./frontend

# Create directory structure for uploads & vector store with correct permissions
RUN mkdir -p /app/data/uploads /app/.data/chroma \
    && chown -R appuser:appgroup /app

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    APP_DEBUG=False

EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

USER appuser

# Startup command
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
