# Performance Optimization Guide

## Overview

This document describes the performance optimization features implemented in the RAG system, including connection pooling, distributed caching, background job processing, and horizontal scaling.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer (Nginx)                   │
└─────────────┬───────────────────────────────────┬───────────┘
              │                                   │
    ┌─────────▼─────────┐               ┌────────▼─────────┐
    │   App Instance 1   │               │  App Instance 2   │
    └─────────┬─────────┘               └────────┬─────────┘
              │                                   │
    ┌─────────▼───────────────────────────────────▼─────────┐
    │              Connection Pool Manager                   │
    └─────────┬───────────────────────────────────┬─────────┘
              │                                   │
    ┌─────────▼─────────┐               ┌────────▼─────────┐
    │   Redis Cache     │               │  Qdrant Vector DB │
    └───────────────────┘               └──────────────────┘
              │
    ┌─────────▼─────────────────────────────────────────────┐
    │            Celery Background Job Queue                 │
    └─────────────────────────────────────────────────────────┘
```

## 1. Connection Pooling

### Features
- **Automatic connection management**: Reuses database connections
- **Configurable pool size**: Min/max connections per pool
- **Health monitoring**: Automatic invalid connection detection
- **Thread-safe**: Safe for concurrent access

### Configuration

```python
from src.infrastructure.performance.connection_pool import get_qdrant_pool

# Get singleton pool instance
pool = get_qdrant_pool()

# Use connection from pool
with pool.get_connection() as conn:
    # Perform operations
    results = conn.search(...)
```

### Pool Statistics

```python
stats = pool.get_stats()
# {
#     'created': 10,
#     'reused': 150,
#     'timeout': 0,
#     'errors': 2,
#     'pool_size': 5,
#     'in_use': 2
# }
```

## 2. Redis Distributed Cache

### Features
- **Session management**: User session storage with TTL
- **Query result caching**: Cache expensive query results
- **Distributed cache**: Share cache across instances
- **Automatic expiration**: TTL-based cache invalidation

### Setup

1. Start Redis server:
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

2. Configure environment:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Usage

```python
from src.infrastructure.performance.redis_cache import get_redis_cache

cache = get_redis_cache()

# Cache operations
cache.set("key", "value", ttl=300)  # 5 minutes TTL
value = cache.get("key")
cache.delete("key")

# Session management
from src.infrastructure.performance.redis_cache import get_session_cache

session_cache = get_session_cache()
session_cache.create_session("session-123", {"user_id": 1})
session_data = session_cache.get_session("session-123")
```

### Cache Decorator

```python
from src.infrastructure.performance.redis_cache import cache_decorator, get_redis_cache

@cache_decorator(
    cache=get_redis_cache(),
    namespace="functions",
    ttl=600
)
def expensive_function(param1, param2):
    # Expensive computation
    return result
```

## 3. Celery Background Jobs

### Features
- **Async document indexing**: Process documents in background
- **Batch processing**: Handle multiple queries efficiently
- **Scheduled tasks**: Periodic maintenance and optimization
- **Task monitoring**: Track task progress and status

### Setup

1. Start Celery worker:
```bash
celery -A src.infrastructure.performance.celery_tasks worker --loglevel=info
```

2. Start Celery beat (for scheduled tasks):
```bash
celery -A src.infrastructure.performance.celery_tasks beat --loglevel=info
```

3. Start Flower (monitoring UI):
```bash
celery -A src.infrastructure.performance.celery_tasks flower --port=5555
```

### Task Submission

```python
from src.infrastructure.performance.celery_tasks import get_task_manager

manager = get_task_manager()

# Submit indexing task
task_id = manager.submit_task(
    "tasks.indexing.index_documents",
    args=(["/path/to/doc1.pdf", "/path/to/doc2.pdf"],),
    kwargs={"collection_name": "business_documents"}
)

# Check task status
status = manager.get_task_status(task_id)
print(f"Task {task_id}: {status['state']}")
```

### Available Tasks

- **Document Indexing**: `tasks.indexing.index_documents`
- **Collection Reindexing**: `tasks.indexing.reindex_collection`
- **Document Analysis**: `tasks.analysis.analyze_documents`
- **Batch Queries**: `tasks.analysis.batch_query`
- **PDF Export**: `tasks.export.export_to_pdf`
- **Excel Export**: `tasks.export.export_to_excel`

## 4. Horizontal Scaling

### Features
- **Multiple app instances**: Run multiple application servers
- **Load balancing strategies**: Round-robin, least connections, weighted
- **Health checking**: Automatic unhealthy instance detection
- **Session affinity**: Sticky sessions for stateful operations

### Deployment

1. Using Docker Compose:
```bash
docker-compose -f docker-compose.scaling.yml up -d
```

2. Scale specific services:
```bash
docker-compose -f docker-compose.scaling.yml up -d --scale app=5 --scale api=3
```

### Load Balancing Strategies

```python
from src.infrastructure.performance.load_balancer import (
    LoadBalancer, ServerInstance, LoadBalancingStrategy
)

# Configure servers
servers = [
    ServerInstance("app1", "localhost", 8501, weight=2),
    ServerInstance("app2", "localhost", 8502, weight=1),
    ServerInstance("app3", "localhost", 8503, weight=1)
]

# Create load balancer
lb = LoadBalancer(
    servers=servers,
    strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
    enable_health_checks=True,
    enable_sticky_sessions=True
)

# Get next server
server = lb.get_server(client_id="user-123")
```

### Nginx Configuration

The system includes a pre-configured Nginx setup for:
- WebSocket support for Streamlit
- Rate limiting
- Response caching
- Gzip compression
- Health monitoring

## 5. Performance Monitoring

### Metrics Collection

```python
# Connection Pool Metrics
pool_stats = get_qdrant_pool().get_stats()

# Cache Metrics
cache_stats = get_redis_cache().get_stats()

# Load Balancer Metrics
lb_stats = load_balancer.get_stats()

# Celery Task Metrics
active_tasks = task_manager.get_active_tasks()
scheduled_tasks = task_manager.get_scheduled_tasks()
```

### Monitoring Dashboard

Access monitoring dashboards:
- **Flower (Celery)**: http://localhost:5555
- **Nginx Status**: http://localhost/nginx-status

## 6. Configuration Examples

### Development Setup

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  app:
    build: .
    environment:
      - REDIS_HOST=redis
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
```

### Production Setup

```yaml
# docker-compose.scaling.yml
services:
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app1
      - app2
      - app3
  
  app1:
    build: .
    environment:
      - INSTANCE_ID=app1
  
  app2:
    build: .
    environment:
      - INSTANCE_ID=app2
  
  app3:
    build: .
    environment:
      - INSTANCE_ID=app3
```

## 7. Performance Tuning

### Connection Pool Tuning

```python
# Adjust pool size based on load
pool = QdrantConnectionPool(
    min_size=5,      # Minimum connections
    max_size=20,     # Maximum connections
    idle_timeout=300,  # Connection idle timeout
    max_lifetime=3600  # Connection max lifetime
)
```

### Cache Tuning

```python
# Configure cache TTL
cache = QueryResultCache(
    ttl=600  # 10 minutes default TTL
)

# Set specific TTL per key
cache.set("key", value, ttl=1800)  # 30 minutes
```

### Celery Tuning

```python
# Worker configuration
CELERY_CONFIG = {
    'worker_prefetch_multiplier': 4,
    'worker_max_tasks_per_child': 1000,
    'task_time_limit': 3600,
    'task_soft_time_limit': 3000
}
```

## 8. Testing

Run performance tests:

```bash
# Unit tests
python -m pytest tests/test_performance.py

# Load testing
locust -f tests/load_test.py --host=http://localhost

# Benchmark queries
python tests/benchmark.py
```

## 9. Troubleshooting

### Common Issues

1. **Connection Pool Exhaustion**
   - Increase max_size
   - Check for connection leaks
   - Monitor pool statistics

2. **Cache Misses**
   - Verify Redis connectivity
   - Check TTL settings
   - Monitor cache hit rate

3. **Task Queue Backlog**
   - Scale Celery workers
   - Optimize task processing
   - Check resource limits

4. **Load Balancer Issues**
   - Verify health checks
   - Check server weights
   - Monitor error rates

## 10. Best Practices

1. **Connection Management**
   - Always use connection pools
   - Set appropriate timeouts
   - Monitor connection health

2. **Caching Strategy**
   - Cache expensive queries
   - Use appropriate TTLs
   - Implement cache warming

3. **Background Jobs**
   - Use for long-running tasks
   - Implement proper error handling
   - Monitor task queues

4. **Scaling**
   - Start with vertical scaling
   - Add horizontal scaling as needed
   - Monitor resource usage

## Dependencies

Add to requirements.txt:
```
redis>=4.5.0
celery>=5.3.0
flower>=2.0.0
kombu>=5.3.0
```

## Conclusion

These performance optimizations transform the RAG system from a single-instance application to an enterprise-ready, scalable solution capable of handling thousands of concurrent users with optimal response times.