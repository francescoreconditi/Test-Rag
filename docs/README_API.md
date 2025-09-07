# Business Intelligence RAG API

## Overview

A comprehensive FastAPI application that provides REST APIs for document analysis, CSV processing, and business intelligence insights with multiple output formats.

## Features

- **PDF Analysis**: Upload and analyze PDF documents with OCR and table extraction
- **CSV Analysis**: Process CSV data with actionable business recommendations
- **Multi-format Output**: Get results in JSON, Text, or PDF format
- **Health Monitoring**: Comprehensive health checks and system status
- **API Documentation**: Swagger UI and Scalar documentation
- **Enterprise Features**: Advanced calculations with lineage tracking
- **Docker Ready**: Production and development Docker configurations

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API Key
- Docker (optional)

### Local Development

1. **Install Dependencies**:
   ```bash
   # Using UV (recommended)
   uv pip install -r requirements.txt
   uv pip install -r requirements-enterprise.txt
   
   # Or using pip
   pip install -r requirements.txt
   pip install -r requirements-enterprise.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export OPENAI_API_KEY=your_openai_api_key
   export QDRANT_HOST=localhost
   export QDRANT_PORT=6333
   ```

3. **Start Qdrant** (if not running):
   ```bash
   docker run -p 6333:6333 qdrant/qdrant:v1.7.0
   ```

4. **Run the API**:
   ```bash
   python -m uvicorn api_main:app --reload --port 8000
   ```

5. **Access Documentation**:
   - Swagger UI: http://localhost:8000/docs
   - Scalar UI: http://localhost:8000/scalar
   - ReDoc: http://localhost:8000/redoc

### Docker Deployment

1. **Production Deployment**:
   ```bash
   # Set your OpenAI API key in .env file
   echo "OPENAI_API_KEY=your_key_here" > .env
   
   # Start all services
   docker-compose -f docker-compose.api.yml up -d
   ```

2. **Development Mode**:
   ```bash
   docker-compose -f docker-compose.api.yml -f docker-compose.dev.yml up
   ```

3. **Access Services**:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Angular Frontend: http://localhost:4200
   - Qdrant: http://localhost:6333

## API Endpoints

### Health & Monitoring

- `GET /health` - Comprehensive health check
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/live` - Kubernetes liveness probe

### Document Analysis

- `POST /analyze/pdf` - Analyze PDF documents
  - Parameters: `output_format` (json|pdf|text), `enterprise_mode` (bool)
  - Returns: Analysis with FAQs in chosen format

- `POST /analyze/csv` - Analyze CSV data
  - Parameters: `analysis_type` (general|financial|sales|operational)
  - Returns: Analysis with actionable recommendations

### Knowledge Base

- `POST /query` - Query indexed documents
- `GET /documents` - List indexed documents
- `POST /documents/index` - Index new documents
- `DELETE /documents/clear` - Clear knowledge base

## API Usage Examples

### PDF Analysis

```python
import requests

# Analyze PDF and get JSON response
with open('financial_report.pdf', 'rb') as f:
    files = {'file': f}
    params = {'output_format': 'json', 'enterprise_mode': True}
    
    response = requests.post(
        'http://localhost:8000/analyze/pdf',
        files=files,
        params=params
    )
    
    result = response.json()
    print(f"Analysis: {result['analysis']['analysis']}")
    print(f"FAQs: {len(result['faqs'])}")
```

```bash
# Using curl
curl -X POST "http://localhost:8000/analyze/pdf?output_format=json&enterprise_mode=true" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@financial_report.pdf"
```

### CSV Analysis

```python
import requests

with open('sales_data.csv', 'rb') as f:
    files = {'file': f}
    params = {'analysis_type': 'sales'}
    
    response = requests.post(
        'http://localhost:8000/analyze/csv',
        files=files,
        params=params
    )
    
    result = response.json()
    print(f"Summary: {result['summary']}")
    for action in result['actions']:
        print(f"Action: {action['action']} (Priority: {action['priority']})")
```

### Query Knowledge Base

```python
import requests

query_data = {
    "question": "What is the company's EBITDA?",
    "enterprise_mode": True
}

response = requests.post(
    'http://localhost:8000/query',
    json=query_data
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']}")
```

## Response Models

### PDF Analysis Response

```json
{
  "analysis": {
    "analysis": "Comprehensive analysis text...",
    "confidence": 0.87,
    "sources": [...],
    "metadata": {...}
  },
  "faqs": [
    {
      "question": "What is the revenue?",
      "answer": "The revenue is 5.2 million EUR",
      "confidence": 0.92
    }
  ],
  "processing_time": 15.2,
  "file_info": {
    "filename": "report.pdf",
    "size_bytes": 1048576,
    "pages": 15,
    "has_tables": true,
    "has_ocr": false
  }
}
```

### CSV Analysis Response

```json
{
  "summary": "Analysis summary text...",
  "actions": [
    {
      "priority": "HIGH",
      "category": "FINANCIAL",
      "action": "Review cost structure",
      "description": "Detailed description...",
      "impact": "10-15% improvement",
      "timeline": "Within 30 days"
    }
  ],
  "metrics": {
    "total_revenue": 1250000,
    "growth_rate": -8.5,
    "risk_score": 0.73
  },
  "processing_time": 3.2
}
```

## Configuration

### Environment Variables

```bash
# API Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=business_documents

# OpenAI Configuration
OPENAI_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
TEMPERATURE=0.1
MAX_TOKENS=4096

# RAG Configuration
RAG_RESPONSE_MODE=compact
RAG_SIMILARITY_TOP_K=3
RAG_ENABLE_CACHING=true
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200
```

### Docker Configuration

The application uses multi-stage Docker builds with separate configurations for development and production:

- **Production**: Optimized image with security best practices
- **Development**: Volume mounts for hot reloading
- **Health Checks**: Built-in health checks for all services
- **Resource Limits**: Configurable memory and CPU limits

## Monitoring & Logging

### Health Checks

- **Application Health**: `/health` endpoint provides detailed component status
- **Readiness**: `/health/ready` for load balancer health checks
- **Liveness**: `/health/live` for container orchestration

### Logging

- **Structured Logging**: JSON formatted logs with correlation IDs
- **Log Levels**: Configurable logging levels (DEBUG, INFO, WARN, ERROR)
- **Request Tracing**: Full request/response logging with timing

### Metrics

- **Processing Time**: Track analysis processing times
- **Success Rates**: Monitor API success/failure rates
- **Resource Usage**: Memory and CPU utilization monitoring

## Security

### Authentication

- **API Keys**: Support for API key authentication
- **CORS**: Configurable CORS policies
- **Rate Limiting**: Built-in rate limiting (configurable)

### Data Protection

- **Input Validation**: Comprehensive input validation and sanitization
- **File Type Validation**: Strict file type and size validation
- **Error Handling**: Secure error handling without information leakage

### Container Security

- **Non-root User**: Containers run as non-root user
- **Minimal Images**: Based on slim Python images
- **Security Headers**: Standard security headers configured

## Development

### Code Structure

```
api_main.py              # Main FastAPI application
scalar_docs.py           # Scalar documentation configuration
src/                     # Application source code
├── application/         # Application layer
├── domain/             # Domain models and logic
├── infrastructure/     # External integrations
└── presentation/       # API presentation layer
services/               # Business services
tests/                  # Test suites
```

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_api.py -v
```

### Adding New Endpoints

1. **Define Pydantic Models**: Add request/response models
2. **Implement Endpoint**: Add endpoint function with proper documentation
3. **Add Tests**: Write comprehensive tests
4. **Update Documentation**: Update API documentation

## Troubleshooting

### Common Issues

1. **Qdrant Connection Failed**:
   ```bash
   # Check if Qdrant is running
   curl http://localhost:6333/health
   
   # Restart Qdrant
   docker restart qdrant
   ```

2. **OpenAI API Errors**:
   ```bash
   # Verify API key
   echo $OPENAI_API_KEY
   
   # Test API key
   curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
   ```

3. **Memory Issues**:
   ```bash
   # Increase Docker memory limits
   docker-compose -f docker-compose.api.yml up --scale rag_api=1
   ```

### Logs and Debugging

```bash
# View API logs
docker-compose logs rag_api

# Follow logs in real-time
docker-compose logs -f rag_api

# Debug mode
export LOG_LEVEL=DEBUG
python -m uvicorn api_main:app --reload --log-level debug
```

## Performance Tuning

### Optimization Settings

```bash
# Faster response mode
export RAG_RESPONSE_MODE=compact

# Reduced similarity search
export RAG_SIMILARITY_TOP_K=3

# Enable caching
export RAG_ENABLE_CACHING=true
```

### Scaling

- **Horizontal Scaling**: Multiple API instances behind load balancer
- **Caching**: Redis caching for frequent queries
- **Database**: Separate Qdrant instances for different document types

## Support

For issues, questions, or contributions:

- **GitHub Issues**: [Report issues](https://github.com/zcscompany/rag-api/issues)
- **Documentation**: [Full documentation](https://docs.zcscompany.com/rag-api)
- **Email**: api@zcscompany.com

## License

Proprietary - ZCS Company