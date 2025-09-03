# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Quick start (auto-installs uv if needed)
start.bat      # Windows
./start.sh     # Linux/Mac

# Manual setup with uv (preferred)
uv venv                              # Creates .venv environment
uv pip install -r requirements.txt  # Installs dependencies (10-100x faster than pip)
source .venv/bin/activate           # Linux/Mac
.venv\Scripts\activate             # Windows

# Docker deployment
docker-compose up -d               # Starts Qdrant + Streamlit app
```

### Running the Application
```bash
streamlit run app.py              # Local development (localhost:8501)
docker-compose up app             # Containerized with Qdrant
```

### Development Tools
```bash
# Linting and formatting
ruff check .                      # Fast Python linter
black .                          # Code formatting (120 char line length)

# Testing
pytest                           # Run all tests
pytest tests/test_csv_analyzer.py # Single test file
pytest -v --tb=short            # Verbose with short traceback

# Dependency management
uv add package-name              # Add new dependency
uv remove package-name           # Remove dependency
uv pip compile requirements.txt  # Update lock file
```

## Architecture Overview

### Core System Design
The application follows a **three-layer service architecture**:

1. **Data Layer**: CSV analysis (`CSVAnalyzer`) for structured financial data
2. **Knowledge Layer**: RAG engine (`RAGEngine`) for unstructured document processing  
3. **Intelligence Layer**: LLM service (`LLMService`) for AI-powered insights generation

### Service Integration Flow
```
CSV Data → CSVAnalyzer → Financial Metrics
                              ↓
PDF/DOCX → RAGEngine → Document Context → LLMService → AI Insights
                              ↓
                         Streamlit UI (app.py)
```

### Key Components

**`services/csv_analyzer.py`**: 
- Handles CSV loading with automatic type detection (dates, currencies, numbers)
- Calculates financial KPIs (YoY growth, ratios, anomaly detection)
- Supports Italian/English column names (`fatturato`/`revenue`, `anno`/`year`)

**`services/rag_engine.py`**:
- Uses LlamaIndex + Qdrant for semantic document search
- Supports PDF, DOCX, TXT, MD formats with metadata preservation
- Implements context-aware querying (combines CSV analysis with document retrieval)

**`services/llm_service.py`**:
- OpenAI GPT-4 integration for business intelligence generation
- Specialized prompts for executive reports, recommendations, anomaly explanations
- Structured output generation (JSON for action items)

**`config/settings.py`**:
- Pydantic-based configuration with environment variable loading
- Auto-creates data directories on initialization
- Centralized settings for OpenAI, Qdrant, and application parameters

### Environment Configuration
Copy `.env.example` to `.env` and configure:
```env
OPENAI_API_KEY=your_key_here           # Required
QDRANT_HOST=localhost                  # Qdrant connection
LLM_MODEL=gpt-4-turbo-preview         # OpenAI model
CHUNK_SIZE=512                        # Document chunking
```

### Data Flow and State Management
- **Streamlit session state** maintains analysis results across UI interactions
- **Qdrant vector store** persists indexed documents between sessions  
- **CSV analysis cache** in `CSVAnalyzer` prevents redundant calculations
- **Temporary file handling** for uploaded documents with automatic cleanup

### Vector Database (Qdrant)
- Collection: `business_documents` (configurable via `QDRANT_COLLECTION_NAME`)
- Embedding model: `text-embedding-3-small` (1536 dimensions)
- Distance metric: Cosine similarity
- Automatic collection creation and management

### UI Architecture (Streamlit)
Multi-page application with cached service initialization:
- **Data Analysis**: CSV upload, financial analysis, visualizations
- **Document RAG**: PDF/DOCX indexing, semantic search
- **AI Insights**: Business intelligence generation, executive reports  
- **Dashboard**: KPI monitoring, trend visualization
- **Settings**: Configuration management, data cleanup

### Error Handling Patterns
- Services use try/catch with detailed error messages
- Streamlit displays user-friendly error notifications
- Automatic retry logic for Qdrant connection issues
- Graceful degradation when services are unavailable