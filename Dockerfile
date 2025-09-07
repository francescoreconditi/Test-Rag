# Multi-stage Docker build for Business Intelligence RAG API
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    tesseract-ocr \
    tesseract-ocr-ita \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install UV for faster package management
RUN pip install uv

WORKDIR /app

# Copy dependency files
COPY requirements.txt requirements-enterprise.txt pyproject.toml ./

# Install Python dependencies using UV
RUN uv pip install --system -r requirements.txt
RUN uv pip install --system -r requirements-enterprise.txt || echo "Enterprise requirements optional"

# Production stage
FROM base as production

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Copy application code
COPY --chown=appuser:appuser . /app

# Create necessary directories
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "-m", "uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM base as development

# Install additional development dependencies
RUN uv pip install --system pytest pytest-asyncio httpx

WORKDIR /app

# Mount point for source code
VOLUME ["/app"]

# Expose port
EXPOSE 8000

# Development command with auto-reload
CMD ["python", "-m", "uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]