FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies and curl for health check
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the direct download method
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set environment variables for uv
ENV PATH="/root/.local/bin:${PATH}"
ENV UV_CACHE_DIR=/tmp/uv-cache

# Copy project files for dependency installation
COPY pyproject.toml .
COPY requirements.txt .

# Create virtual environment and install dependencies with uv
RUN /root/.local/bin/uv venv .venv --python 3.10
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

# Install dependencies using uv (much faster than pip)
RUN /root/.local/bin/uv pip install -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/uploads data/cache

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]