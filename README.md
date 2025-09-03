# Business Intelligence RAG System

A comprehensive Business Intelligence system that combines structured data analysis (CSV) with RAG (Retrieval-Augmented Generation) for unstructured document processing, providing intelligent insights through AI.

## Features

### Structured Data Analysis
- **Automatic CSV loading** with type recognition (dates, currencies, numbers)
- **Balance sheet analysis** with YoY variations and trends calculation
- **Automatic KPIs** (growth, margins, financial ratios)
- **Anomaly detection** to identify outlier values
- **Interactive visualizations** with Plotly (charts, dashboards)
- **Multi-language support** (Italian/English columns: fatturato/revenue, anno/year)

### RAG Document System
- **Semantic indexing** of PDF, DOCX, TXT, Markdown files
- **Qdrant vector database** for high-speed search
- **Intelligent chunking** with configurable overlap
- **Metadata preservation** (page, source, file type)
- **Context-aware queries** (combines CSV data with documents)
- **OpenAI embeddings** (text-embedding-3-small)

### AI-Powered Intelligence
- **Business insights** with in-depth strategic analysis
- **Executive reports** customizable for C-suite
- **Natural Q&A** on data and documents
- **Prioritized action items** with timelines and owners
- **Anomaly explanations** with recommendations
- **Comparative analysis** between periods

### Interactive Dashboard
- **Multi-module interface** (Analysis, RAG, AI, Dashboard, Settings)
- **Real-time metrics** with live updates
- **Export functions** (Markdown, CSV, JSON)
- **Session state** for continuous workflows
- **Responsive design** optimized for all screens

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Backend** | Python | 3.10+ | Core logic |
| **RAG Framework** | LlamaIndex | 0.9+ | Document processing |
| **Vector DB** | Qdrant | 1.7+ | Semantic search |
| **LLM** | OpenAI GPT-4 | - | AI insights |
| **UI Framework** | Streamlit | 1.29+ | Web interface |
| **Data Analysis** | Pandas + NumPy | 2.1+ | CSV processing |
| **Visualization** | Plotly | 5.18+ | Interactive charts |
| **Package Manager** | uv | - | Fast dependency management |
| **Containerization** | Docker | - | Deployment |

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
TEMPERATURE=0.7
MAX_TOKENS=2000

# Document Processing
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# Application
DEBUG_MODE=false
APP_NAME=Business Intelligence RAG System
```

## Usage Guide

### 1. CSV Data Analysis

1. **Upload CSV**: Load balance sheets, financial reports, management data
2. **Configure columns**: Select year/revenue columns for automatic analysis
3. **View results**:
   - **Summary**: Key KPIs and metrics
   - **Trends**: YoY growth, historical trends
   - **Visualizations**: Customizable interactive charts
   - **Recommendations**: AI-powered suggestions

### 2. Document Processing (RAG)

1. **Upload documents**: PDF, DOCX, TXT, Markdown
2. **Automatic indexing**: Chunking and embedding generation
3. **Semantic queries**: Ask natural language questions
4. **Context-aware search**: Combines CSV insights with document content

### 3. AI-Powered Insights

- **Complete Business Insights**: Strategic analysis considering financial performance and market context
- **Executive Reports**: Customizable sections for C-suite presentations
- **Intelligent Q&A**: Natural language questions about data and documents
- **Prioritized Action Items**: Structured recommendations with timelines

## Development

### Commands

```bash
# Linting and formatting
ruff check .                        # Fast Python linter
black .                            # Code formatter
ruff check --fix .                 # Auto-fix issues

# Testing
pytest                             # Run all tests
pytest tests/test_csv_analyzer.py  # Single module
pytest -v --tb=short              # Verbose output

# Dependencies
uv add package-name                # Add dependency
uv remove package-name             # Remove dependency  
uv pip compile requirements.txt    # Update lockfile
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