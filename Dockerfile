# Production Multi-Stage Dockerfile for Enterprise AI Assistant

FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt-get/lists/*

# Copy python dependency requirements
COPY backend/requirements.txt /app/requirements.txt

# Create virtualenv and install python dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime libpq for PostgreSQL connection
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt-get/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Copy application source code
COPY backend /app/backend
COPY frontend /app/frontend
COPY data/sql /app/data/sql
COPY main.py /app/main.py

# Create data directory for ChromaDB and PDF reports
RUN mkdir -p /app/.data/chroma /app/.data/reports

EXPOSE 8000

# Render dynamic $PORT support (defaults to 8000 if PORT is unset)
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
