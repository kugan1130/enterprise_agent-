# ================================
# Stage 1: Builder
# ================================
FROM python:3.12-slim AS builder

WORKDIR /app

# System packages required to build/install Python dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy dependencies
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# ================================
# Stage 2: Runtime
# ================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Copy application
COPY backend /app/backend
COPY frontend /app/frontend
COPY main.py /app/main.py

# Application data directories
RUN mkdir -p /app/.data/chroma \
    /app/.data/reports

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]