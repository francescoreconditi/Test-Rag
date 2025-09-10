"""
Connection pooling and query optimization for database connections.
Manages connection lifecycle and implements query optimization strategies.
"""

import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
import threading
from queue import Queue, Empty
import time

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import duckdb

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Generic connection pool implementation."""
    
    def __init__(
        self,
        factory,
        min_size: int = 2,
        max_size: int = 10,
        idle_timeout: int = 300,
        max_lifetime: int = 3600
    ):
        self.factory = factory
        self.min_size = min_size
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self.max_lifetime = max_lifetime
        
        self._pool = Queue(maxsize=max_size)
        self._in_use = set()
        self._lock = threading.Lock()
        self._created = 0
        self._stats = {
            'created': 0,
            'reused': 0,
            'timeout': 0,
            'errors': 0
        }
        
        # Pre-create minimum connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Pre-create minimum number of connections."""
        for _ in range(self.min_size):
            try:
                conn = self.factory()
                self._pool.put({
                    'connection': conn,
                    'created_at': time.time(),
                    'last_used': time.time()
                })
                self._created += 1
                self._stats['created'] += 1
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
    
    @contextmanager
    def get_connection(self, timeout: float = 5.0):
        """Get a connection from the pool."""
        conn_info = None
        start_time = time.time()
        
        try:
            # Try to get from pool
            while True:
                try:
                    conn_info = self._pool.get(timeout=0.1)
                    
                    # Check if connection is still valid
                    if self._is_valid(conn_info):
                        self._stats['reused'] += 1
                        break
                    else:
                        # Connection expired, create new one
                        conn_info['connection'] = self.factory()
                        conn_info['created_at'] = time.time()
                        self._stats['created'] += 1
                        break
                        
                except Empty:
                    # Pool is empty, create new connection if under limit
                    with self._lock:
                        if self._created < self.max_size:
                            conn_info = {
                                'connection': self.factory(),
                                'created_at': time.time(),
                                'last_used': time.time()
                            }
                            self._created += 1
                            self._stats['created'] += 1
                            break
                    
                    # Check timeout
                    if time.time() - start_time > timeout:
                        self._stats['timeout'] += 1
                        raise TimeoutError(f"Could not acquire connection within {timeout}s")
            
            # Mark connection as in use
            with self._lock:
                self._in_use.add(id(conn_info))
            
            # Update last used time
            conn_info['last_used'] = time.time()
            
            yield conn_info['connection']
            
        except Exception as e:
            self._stats['errors'] += 1
            raise
            
        finally:
            # Return connection to pool
            if conn_info:
                with self._lock:
                    self._in_use.discard(id(conn_info))
                
                if self._is_valid(conn_info):
                    self._pool.put(conn_info)
                else:
                    # Connection invalid, decrease count
                    with self._lock:
                        self._created -= 1
    
    def _is_valid(self, conn_info: Dict) -> bool:
        """Check if connection is still valid."""
        now = time.time()
        
        # Check lifetime
        if now - conn_info['created_at'] > self.max_lifetime:
            return False
        
        # Check idle timeout
        if now - conn_info['last_used'] > self.idle_timeout:
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            **self._stats,
            'pool_size': self._pool.qsize(),
            'in_use': len(self._in_use),
            'total_created': self._created
        }
    
    def close(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn_info = self._pool.get_nowait()
                # Attempt to close connection if it has close method
                if hasattr(conn_info['connection'], 'close'):
                    conn_info['connection'].close()
            except:
                pass


class QdrantConnectionPool(ConnectionPool):
    """Specialized connection pool for Qdrant."""
    
    def __init__(self, url: str = "http://localhost:6333", **kwargs):
        self.url = url
        super().__init__(
            factory=lambda: QdrantClient(url=self.url),
            **kwargs
        )


class DuckDBConnectionPool(ConnectionPool):
    """Specialized connection pool for DuckDB."""
    
    def __init__(self, database: str = ":memory:", **kwargs):
        self.database = database
        super().__init__(
            factory=lambda: duckdb.connect(self.database),
            **kwargs
        )


class QueryOptimizer:
    """Query optimization strategies."""
    
    def __init__(self):
        self.query_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.batch_size = 100
        self.parallel_threshold = 10
    
    def optimize_batch_query(self, queries: List[str]) -> List[str]:
        """Optimize multiple queries for batch execution."""
        optimized = []
        
        # Group similar queries
        query_groups = self._group_similar_queries(queries)
        
        for group in query_groups:
            if len(group) > self.parallel_threshold:
                # Split large groups for parallel execution
                for i in range(0, len(group), self.batch_size):
                    batch = group[i:i + self.batch_size]
                    optimized.append(self._create_batch_query(batch))
            else:
                optimized.extend(group)
        
        return optimized
    
    def _group_similar_queries(self, queries: List[str]) -> List[List[str]]:
        """Group queries by similarity for optimization."""
        groups = {}
        
        for query in queries:
            # Simple grouping by query type
            query_type = self._get_query_type(query)
            if query_type not in groups:
                groups[query_type] = []
            groups[query_type].append(query)
        
        return list(groups.values())
    
    def _get_query_type(self, query: str) -> str:
        """Determine query type for grouping."""
        query_lower = query.lower().strip()
        
        if query_lower.startswith('select'):
            return 'select'
        elif query_lower.startswith('insert'):
            return 'insert'
        elif query_lower.startswith('update'):
            return 'update'
        elif query_lower.startswith('delete'):
            return 'delete'
        else:
            return 'other'
    
    def _create_batch_query(self, queries: List[str]) -> str:
        """Create optimized batch query."""
        # For SELECT queries, try to combine with UNION
        if all(q.lower().startswith('select') for q in queries):
            return ' UNION ALL '.join(queries)
        
        # For other queries, use transaction
        return 'BEGIN TRANSACTION;\n' + ';\n'.join(queries) + ';\nCOMMIT;'
    
    def cache_query_result(self, query: str, result: Any):
        """Cache query result with TTL."""
        self.query_cache[query] = {
            'result': result,
            'timestamp': datetime.now()
        }
    
    def get_cached_result(self, query: str) -> Optional[Any]:
        """Get cached result if still valid."""
        if query in self.query_cache:
            cached = self.query_cache[query]
            age = datetime.now() - cached['timestamp']
            
            if age.total_seconds() < self.cache_ttl:
                return cached['result']
            else:
                # Remove expired cache
                del self.query_cache[query]
        
        return None
    
    def clear_cache(self):
        """Clear all cached results."""
        self.query_cache.clear()


class AsyncQueryExecutor:
    """Asynchronous query executor with optimization."""
    
    def __init__(self, pool: ConnectionPool, optimizer: QueryOptimizer):
        self.pool = pool
        self.optimizer = optimizer
        self.executor = None
    
    async def execute_query(self, query: str, use_cache: bool = True) -> Any:
        """Execute single query with caching."""
        # Check cache first
        if use_cache:
            cached = self.optimizer.get_cached_result(query)
            if cached is not None:
                return cached
        
        # Execute query
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self._execute_sync,
            query
        )
        
        # Cache result
        if use_cache:
            self.optimizer.cache_query_result(query, result)
        
        return result
    
    def _execute_sync(self, query: str) -> Any:
        """Synchronous query execution."""
        with self.pool.get_connection() as conn:
            if hasattr(conn, 'execute'):
                return conn.execute(query).fetchall()
            else:
                # For Qdrant or other clients
                return conn.search(query)
    
    async def execute_batch(self, queries: List[str]) -> List[Any]:
        """Execute multiple queries in parallel."""
        # Optimize queries
        optimized = self.optimizer.optimize_batch_query(queries)
        
        # Execute in parallel
        tasks = [self.execute_query(q, use_cache=False) for q in optimized]
        results = await asyncio.gather(*tasks)
        
        return results


# Singleton instances
_qdrant_pool = None
_duckdb_pool = None
_query_optimizer = None


def get_qdrant_pool() -> QdrantConnectionPool:
    """Get singleton Qdrant connection pool."""
    global _qdrant_pool
    if _qdrant_pool is None:
        _qdrant_pool = QdrantConnectionPool()
    return _qdrant_pool


def get_duckdb_pool() -> DuckDBConnectionPool:
    """Get singleton DuckDB connection pool."""
    global _duckdb_pool
    if _duckdb_pool is None:
        _duckdb_pool = DuckDBConnectionPool()
    return _duckdb_pool


def get_query_optimizer() -> QueryOptimizer:
    """Get singleton query optimizer."""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    return _query_optimizer