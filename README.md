# Business Intelligence RAG System 🏢

A **next-generation Enterprise Business Intelligence platform** that combines structured data analysis with advanced RAG (Retrieval-Augmented Generation) capabilities. Built with **Clean Architecture**, **Domain-Driven Design**, and **enterprise-grade patterns** for scalable financial analysis and document intelligence.

## 🎯 Core Features

### 🚀 **NEW: Enterprise Mode**
- **🔧 Enterprise Toggle**: One-click activation in Streamlit sidebar
- **📊 Source References**: Complete data provenance tracking
- **✅ Financial Guardrails**: Automated balance sheet and PFN validation
- **🤖 Hybrid Retrieval**: BM25 + Embeddings + Cross-encoder reranking
- **🧠 Ontology Mapping**: 31 canonical metrics with 219+ synonyms (Italian/English)
- **🗄️ Dimensional Fact Table**: Star schema with DuckDB/SQLite persistence
- **⚡ Enterprise Orchestration**: Integrated workflow with 6-step processing pipeline

### 📊 Advanced Financial Analytics
- **Smart CSV Processing** with Italian number format support (`1.234,56`)
- **Automated Financial Modeling** (YoY growth, ratios, KPIs)
- **Anomaly Detection** with statistical algorithms
- **Multi-Currency Support** with conversion tracking
- **Interactive Dashboards** with real-time visualizations
- **Comparative Analysis** across multiple periods and entities

### 🧠 RAG-Powered Document Intelligence  
- **Multi-Format Support** (PDF, DOCX, TXT, Markdown, Excel)
- **Semantic Search** with Qdrant vector database
- **Context-Aware Queries** combining structured and unstructured data
- **Metadata Extraction** with provenance tracking
- **Professional PDF Export** with ZCS Company styling
- **Intelligent Chunking** with overlap optimization

### 🤖 AI-Driven Business Intelligence
- **Executive Reporting** with strategic insights
- **Predictive Analytics** using historical patterns
- **Risk Assessment** with confidence scoring
- **Natural Language Queries** in Italian and English
- **Automated Recommendations** with priority levels
- **Trend Analysis** with statistical significance

### 💼 Enterprise-Ready Architecture
- **Clean Architecture** with domain separation
- **Repository Pattern** with SQLite/DuckDB persistence
- **Dependency Injection** container
- **Comprehensive Logging** with sensitive data filtering
- **Type Safety** with full MyPy compliance
- **Error Handling** with structured exceptions
- **Graceful Degradation** for optional enterprise components

## 🏗️ Architecture Overview

### System Design
The application follows **Clean Architecture** principles with clear layer separation:

```mermaid
graph TD
    UI[Streamlit UI] --> APP[Application Layer]
    APP --> DOMAIN[Domain Layer] 
    APP --> INFRA[Infrastructure Layer]
    
    subgraph "Domain Layer"
        ENT[Entities]
        VO[Value Objects]
        EXC[Exceptions]
    end
    
    subgraph "Application Layer"  
        INT[Interfaces]
        UC[Use Cases]
        DTO[DTOs]
    end
    
    subgraph "Infrastructure Layer"
        REPO[Repositories]
        EXT[External Services]
        PERS[Persistence]
    end
```

### Enterprise Technology Stack

| Layer | Component | Technology | Purpose |
|-------|-----------|------------|---------|
| **Presentation** | UI Framework | Streamlit 1.29+ | Web interface with Enterprise mode |
| **Application** | Business Logic | Python 3.10+ | Use cases & interfaces |
| | **Enterprise Orchestrator** | **Custom Pipeline** | **6-step processing workflow** |
| | **Document Router** | **Content Classification** | **Structured/Unstructured routing** |
| | **Hybrid Retrieval** | **BM25 + Embeddings** | **Advanced search with reranking** |
| **Domain** | Core Models | Pydantic 2.0+ | Entities & value objects |
| | **Source References** | **Provenance Tracking** | **Complete data lineage** |
| | **Financial Guardrails** | **Validation Rules** | **Balance sheet coherence checks** |
| **Infrastructure** | Vector DB | Qdrant 1.7+ | Semantic search |
| | **Fact Table** | **DuckDB/SQLite** | **Dimensional data warehouse** |
| | LLM Service | OpenAI GPT-4 | AI reasoning |
| | **Ontology Mapping** | **YAML + RapidFuzz** | **31 metrics, 219+ synonyms** |
| | **Data Normalization** | **Multi-locale Support** | **Italian formats & periods** |
| | Data Processing | Pandas 2.1+ | CSV analysis |
| | Visualization | Plotly 5.18+ | Interactive charts |
| **ML/AI** | **Embeddings** | **SentenceTransformers** | **All-MiniLM-L6-v2 model** |
| | **Reranker** | **CrossEncoder** | **MS-MARCO-MiniLM-L-2-v2** |
| | **Search** | **BM25Okapi** | **Keyword-based retrieval** |
| **DevOps** | Package Manager | uv | Fast dependencies |
| | Linting | Ruff + Black | Code quality |
| | Type Checking | MyPy | Type safety |
| | Testing | Pytest | Quality assurance |

## Prerequisites

- **Python 3.10+**
- **OpenAI API Key** (required for LLM and embeddings)
- **Docker + Docker Compose** (optional, for containerized deployment)
- **8GB+ RAM** (recommended for vector operations)

## Installation

### Option 1: Quick Start (Recommended)

```bash
# 1. Clone repository
git clone <repository-url>
cd RAG

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Automatic startup (installs uv if missing)
start.bat      # Windows  
./start.sh     # Linux/Mac

# 4. Open browser: http://localhost:8501
```

### Option 2: Manual Setup with uv

```bash
# Install uv (if not present)
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/Mac
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Setup environment
uv venv                              # Create virtual environment
source .venv/bin/activate           # Linux/Mac
.venv\Scripts\activate              # Windows

# Install dependencies (10-100x faster than pip)
uv pip install -r requirements.txt

# Start Qdrant
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Start application
streamlit run app.py
```

### Option 3: Docker Deployment

```bash
# Complete setup with one command
cp .env.example .env  # Add OPENAI_API_KEY
docker-compose up -d

# Access app: http://localhost:8501
# Qdrant UI: http://localhost:6333/dashboard
```

## Configuration

### Environment Variables (.env)

```env
# OpenAI (Required)
OPENAI_API_KEY=sk-...your-key-here...

# Qdrant Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=business_documents

# AI Configuration
LLM_MODEL=gpt-4-turbo-preview
EMBEDDING_MODEL=text-embedding-3-small
TEMPERATURE=0.1
MAX_TOKENS=2000

# Document Processing
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# RAG Performance (NEW)
RAG_RESPONSE_MODE=compact
RAG_SIMILARITY_TOP_K=3
RAG_ENABLE_CACHING=True

# Enterprise Features (NEW)
HF_HUB_DISABLE_SYMLINKS_WARNING=1

# Application
DEBUG_MODE=false
APP_NAME=Business Intelligence RAG System
```

## 📁 Enterprise Project Structure

```
src/
├── domain/                    # Core business logic (entities, value objects)
│   ├── entities/             # Business entities (FinancialData, Document, AnalysisResult)
│   ├── value_objects/        # NEW: Source references, guardrails, validation
│   │   ├── source_reference.py    # Complete data provenance tracking
│   │   └── guardrails.py          # Financial validation rules
│   └── exceptions/           # Domain-specific exceptions
├── application/              # Use cases and interfaces  
│   ├── interfaces/           # Contracts for external dependencies
│   └── services/             # NEW: Enterprise application services
│       ├── enterprise_orchestrator.py  # Main workflow coordinator
│       ├── document_router.py          # Document classification
│       ├── hybrid_retrieval.py         # BM25 + Embeddings search
│       ├── ontology_mapper.py          # Metric synonyms mapping
│       └── data_normalizer.py          # Multi-locale normalization
├── infrastructure/           # External concerns (databases, APIs)
│   └── repositories/         # Data persistence implementations
│       └── fact_table_repository.py   # NEW: Dimensional data warehouse
├── core/                     # Cross-cutting concerns
│   ├── config.py            # Configuration management
│   ├── logging_config.py    # Structured logging
│   └── dependency_injection.py # DI container
├── presentation/             # UI layer (Streamlit)
│   └── streamlit/
│       └── pdf_exporter.py   # NEW: Professional PDF export (ZCS styling)
└── services/                 # Legacy services (being migrated)
    ├── rag_engine.py        # Enhanced with enterprise orchestrator
    └── query_cache.py       # Performance optimization

config/
└── ontology/                 # NEW: Financial metrics ontology
    └── financial_metrics.yaml     # 31 metrics, 219+ synonyms

tests/
├── unit/                     # Unit tests for domain logic
├── integration/              # Integration tests for repositories
└── e2e/                     # End-to-end workflow tests
```

## 🚀 Usage Guide

### 🚀 **NEW: Enterprise Mode Usage**

**Activate Enterprise Features:**
1. **Toggle Enterprise Mode** in Streamlit sidebar (🚀 Modalità Enterprise)
2. **Upload Financial Documents** (PDF, Excel, Word)
3. **Ask Questions** - Enterprise pipeline automatically:
   - Routes documents (structured/unstructured/hybrid)
   - Performs hybrid retrieval (BM25 + embeddings + reranking)
   - Extracts and normalizes financial metrics
   - Maps to canonical ontology (Italian ↔ English)
   - Validates balance sheet coherence
   - Stores with full provenance in dimensional fact table

**Enterprise Query Results Include:**
- **📊 Metriche Rilevate**: Normalized values with confidence scores
- **✅ Risultati di Validazione**: Coherence checks (balance sheet, PFN)
- **⚡ Processing Statistics**: Time, confidence, records saved
- **🔍 Source References**: Complete data provenance
- **⚠️ Validation Warnings**: Accounting inconsistencies flagged

### 1. 📊 Financial Data Analysis

**Enterprise-Grade CSV Processing:**
1. **Smart Upload**: Auto-detects Italian formats (`1.234,56`, date formats)
2. **Financial Modeling**: Automatic KPI calculation and trend analysis
3. **Advanced Analytics**:
   - YoY growth with statistical significance
   - Financial ratios and margin analysis
   - Anomaly detection with confidence scores
   - Multi-period comparative analysis
4. **Interactive Visualizations**: Plotly dashboards with drill-down capabilities

### 2. 🔍 RAG Document Intelligence

**Semantic Document Processing:**
1. **Multi-Format Ingestion**: PDF, DOCX, TXT, Markdown with metadata extraction
2. **Intelligent Indexing**: Context-aware chunking with Qdrant vector storage
3. **Natural Language Queries**: Ask complex questions in Italian or English
4. **Context Integration**: Combines financial data insights with document content
5. **Professional PDF Export** - Export Q&A sessions with ZCS Company styling

### 3. 🤖 AI-Powered Business Intelligence

**Strategic Decision Support:**
- **Executive Dashboards**: C-suite ready reports with key insights
- **Predictive Analytics**: Trend forecasting with confidence intervals  
- **Risk Assessment**: Automated risk scoring with mitigation strategies
- **Compliance Reporting**: Audit-ready documentation with provenance tracking
- **Multi-Language Support**: Italian and English query processing

## 🛠️ Development

### Quality Assurance

```bash
# Code Quality
ruff check .                       # Fast linting with 800+ rules
black .                           # Consistent code formatting  
mypy src/                         # Type checking
bandit src/                       # Security scanning

# Testing Suite  
pytest                            # Run all tests (80% coverage target)
pytest -m unit                   # Unit tests only
pytest -m integration            # Integration tests  
pytest -v --tb=short            # Verbose output

# Performance Testing
pytest -m slow                   # Performance benchmarks
pytest --cov=src --cov-report=html  # Coverage report
```

### Dependency Management

```bash
# Fast dependency management with uv (10-100x faster than pip)
uv add package-name               # Add production dependency
uv add --dev package-name         # Add development dependency
uv remove package-name            # Remove dependency
uv pip compile requirements.txt   # Update lockfile
uv sync                          # Sync environment
```

### Architecture Validation

```bash
# Domain Model Validation
python -m src.domain.entities.financial_data  # Test entity integrity
python -m src.domain.value_objects.money     # Test value objects

# Repository Testing  
python -m src.infrastructure.repositories    # Test data persistence

# Dependency Injection Validation
python -m src.core.dependency_injection      # Test DI container
```

## Troubleshooting

### Common Issues

#### OpenAI API Errors
```bash
# Invalid API key
export OPENAI_API_KEY=sk-your-key-here
# Or edit .env file

# Rate limit exceeded  
# Solution: Reduce request frequency or upgrade plan
```

#### Qdrant Connection Issues
```bash
# Check Qdrant status
curl http://localhost:6333/health

# Restart Qdrant
docker restart qdrant
```

#### Memory Issues
```bash
# Reduce chunk size
CHUNK_SIZE=256  # Default: 512

# Increase Docker memory
docker-compose up --memory=4g
```

## Contributing

1. **Fork** the repository
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

## License

This project is released under the **MIT License** - see [LICENSE](LICENSE) for details.

## Support

- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for Q&A
- **Documentation**: Complete wiki on GitHub

---

**Ready to transform your data into business intelligence? Start now with a simple `start.bat`!**