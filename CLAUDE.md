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
# Streamlit Web Interface
streamlit run app.py              # Local development (localhost:8501)
streamlit run app.py --server.port 8502  # Alternative port

# FastAPI REST API
uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload  # API server (localhost:8000)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload         # Alternative without uv

# Docker deployment
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

# Enterprise components testing
python -c "from src.application.services.enterprise_orchestrator import EnterpriseOrchestrator; print('✅ Enterprise components OK')"
```

## Enterprise Architecture Overview

### Enterprise System Design
The application now follows a **six-layer enterprise architecture**:

1. **Presentation Layer**: Streamlit UI with Enterprise mode toggle
2. **Application Layer**: Enterprise orchestrator coordinating all services  
3. **Domain Layer**: Source references, guardrails, and financial validation
4. **Knowledge Layer**: Hybrid retrieval (BM25 + embeddings + reranking)
5. **Intelligence Layer**: Ontology mapping and data normalization
6. **Infrastructure Layer**: Dimensional fact table with full provenance

### Enterprise Service Integration Flow
```
Documents → Document Router → [Structured|Unstructured|Hybrid]
                ↓
         Hybrid Retrieval (BM25 + Embeddings + CrossEncoder)
                ↓
         Data Normalization (Italian formats, periods, scales)
                ↓
         Ontology Mapping (31 metrics, 219+ synonyms)
                ↓
         Financial Validation (Balance sheet, PFN coherence)
                ↓
         Fact Table Storage (Dimensional model with provenance)
                ↓
         Enterprise Response (with statistics & warnings)
```

### Key Enterprise Components

**`src/application/services/enterprise_orchestrator.py`**:
- Main coordinator for 6-step enterprise pipeline
- Async processing with comprehensive error handling
- Performance statistics and confidence scoring
- Health check system for all components

**`src/application/services/document_router.py`**:
- Intelligent document classification (structured/unstructured/hybrid)
- Content analysis with extensibility patterns
- Graceful fallback when optional libraries missing

**`src/application/services/hybrid_retrieval.py`**:
- BM25Okapi for keyword-based search
- SentenceTransformers for semantic embeddings
- CrossEncoder for result reranking
- Configurable weighting and optimization

**`src/application/services/ontology_mapper.py`**:
- YAML-based financial metrics ontology
- Fuzzy string matching with RapidFuzz
- 31 canonical metrics with Italian/English synonyms
- Batch processing and suggestion system

**`src/application/services/data_normalizer.py`**:
- Multi-locale number parsing (Italian: 1.234,56)
- Scale detection (thousands, millions, billions)
- Period normalization (FY, quarters, YTD)
- Currency extraction and conversion

**`src/domain/value_objects/source_reference.py`**:
- Complete data provenance tracking
- File hashing and timestamping
- Source type classification
- Immutable value objects for data integrity

**`src/domain/value_objects/guardrails.py`**:
- Financial validation rules
- Balance sheet coherence checks (Attivo = Passivo)
- PFN validation (PFN = Debito Lordo - Cassa)
- Configurable tolerance levels

**`src/infrastructure/repositories/fact_table_repository.py`**:
- Dimensional data warehouse (star schema)
- DuckDB/SQLite backend support
- Full provenance tracking per fact
- Entity, metric, period, scenario dimensions

**Enhanced `services/rag_engine.py`**:
- Integrated enterprise orchestrator
- New `enterprise_query()` method
- Fallback to standard mode when enterprise unavailable
- Performance optimizations (compact mode, caching)

### Enterprise Configuration
Enhanced `.env` with enterprise features:
```env
# Performance optimizations
RAG_RESPONSE_MODE=compact            # Faster than tree_summarize
RAG_SIMILARITY_TOP_K=3              # Reduced from 5 for speed
RAG_ENABLE_CACHING=True             # Query result caching

# Enterprise features
HF_HUB_DISABLE_SYMLINKS_WARNING=1   # Suppress HuggingFace warnings

# Optional ML dependencies (graceful degradation if missing):
# - rank_bm25 (BM25 search)
# - sentence-transformers (embeddings)
# - rapidfuzz (fuzzy matching)
# - babel (locale support)
# - python-magic (file type detection)
```

### Enterprise Data Flow and State Management
- **Enterprise Toggle** in Streamlit sidebar activates advanced features
- **Async Processing** with comprehensive error handling
- **Source Provenance** tracked throughout entire pipeline
- **Dimensional Storage** with fact table for audit trails
- **Graceful Degradation** when optional dependencies missing
- **Performance Monitoring** with processing time and confidence scores

### Enterprise Vector Database (Qdrant)
- Collection: `business_documents` (configurable via `QDRANT_COLLECTION_NAME`)
- Embedding model: `text-embedding-3-small` (1536 dimensions)
- Reranker model: `cross-encoder/ms-marco-MiniLM-L-2-v2`
- Distance metric: Cosine similarity
- Enhanced metadata with source references and document classification

### Enterprise UI Architecture (Streamlit)
Enhanced multi-page application:
- **🚀 Enterprise Mode Toggle**: Activate advanced features
- **Enterprise Statistics**: Real-time processing metrics in sidebar
- **Source References**: Complete data provenance in results
- **Validation Warnings**: Financial coherence alerts
- **Professional PDF Export**: ZCS Company styling
- **Error Recovery**: Automatic fallback to standard mode

### Enterprise Error Handling Patterns
- **Graceful Degradation**: Missing ML libraries don't break system
- **Comprehensive Logging**: Structured logging with performance metrics
- **Health Checks**: Component-wise system health monitoring
- **Fallback Mechanisms**: Enterprise → Standard mode on errors
- **User Feedback**: Clear error messages with suggested solutions

### Performance Optimizations
- **Query Caching**: TTL-based result caching
- **Compact Response Mode**: Faster than tree_summarize
- **Reduced Top-K**: From 5 to 3 for better performance
- **Async Processing**: Non-blocking enterprise pipeline
- **Lazy Loading**: Optional components loaded only when needed