#!/bin/bash
# Database Reset Utility for Linux/Mac
# Usage: ./reset_databases.sh [options]

set -e  # Exit on any error

echo ""
echo "======================================================"
echo "   RAG System Database Reset Utility"
echo "======================================================"
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "ERROR: Python not found. Please install Python or activate virtual environment."
    echo "Try: source .venv/bin/activate"
    exit 1
fi

# Check if virtual environment exists
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "Warning: Virtual environment not found at .venv/bin/activate"
    echo "Continuing with system Python..."
fi

# Run the database reset utility
echo "Running database reset utility..."
echo ""

if [ $# -eq 0 ]; then
    # No arguments, reset all with samples
    python utils/database_reset.py --all --samples
else
    # Pass all arguments to Python script
    python utils/database_reset.py "$@"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================"
    echo "   Database reset completed successfully!"
    echo "======================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Streamlit if running"
    echo "  2. Check Qdrant: docker-compose up qdrant"
    echo "  3. Test with: streamlit run app.py"
else
    echo ""
    echo "======================================================"
    echo "   Database reset failed. Check errors above."
    echo "======================================================"
fi

echo ""