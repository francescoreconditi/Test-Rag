#!/bin/bash

echo "Starting Business Intelligence RAG System..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and configure your settings."
    exit 1
fi

# Check if Docker is running
if ! docker version > /dev/null 2>&1; then
    echo "ERROR: Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "Starting Qdrant vector database..."
docker-compose up -d qdrant

# Wait for Qdrant to be ready
echo "Waiting for Qdrant to initialize..."
sleep 5

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    if ! command -v uv &> /dev/null; then
        echo "ERROR: Failed to install uv. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
    echo "uv installed successfully. Please restart this script or run: export PATH=\"\$HOME/.cargo/bin:\$PATH\""
    exit 0
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with uv..."
    uv venv
    echo "Installing dependencies with uv..."
    uv pip install -r requirements.txt
fi

# Activate virtual environment
source .venv/bin/activate

echo ""
echo "Starting Streamlit application..."
echo ""
echo "The application will open in your browser at http://localhost:8501"
echo "Press Ctrl+C to stop the application"
echo ""

streamlit run app.py