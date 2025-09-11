"""
Redis-based distributed caching system for sessions and query results.
Provides high-performance caching with TTL support and clustering capabilities.
"""

from datetime import datetime
from functools import wraps
import hashlib
import json
import logging
import pickle
from typing import Any, Optional

try:
    import redis
    from redis.asyncio import Redis as AsyncRedis
    from redis.sentinel import Sentinel
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    AsyncRedis = None
    Sentinel = None

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-based distributed cache implementation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: int = 5,
        connection_timeout: int = 5,
        retry_on_timeout: bool = True,
        decode_responses: bool = False,
        use_sentinel: bool = False,
        sentinel_hosts: Optional[list[tuple]] = None,
        sentinel_service_name: str = "mymaster"
    ):
        """Initialize Redis cache with connection pooling."""
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not installed. Install with: pip install redis")

        self.host = host
        self.port = port
        self.db = db
        self.decode_responses = decode_responses

        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }

        if use_sentinel and sentinel_hosts:
            # Use Redis Sentinel for high availability
            self.sentinel = Sentinel(
                sentinel_hosts,
                socket_timeout=socket_timeout,
                socket_connect_timeout=connection_timeout
            )
            self.client = self.sentinel.master_for(
                sentinel_service_name,
                socket_timeout=socket_timeout,
                password=password,
                db=db,
                decode_responses=decode_responses
            )
        else:
            # Create connection pool
            self.pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=connection_timeout,
                retry_on_timeout=retry_on_timeout,
                decode_responses=decode_responses
            )

            # Create Redis client
            self.client = redis.Redis(connection_pool=self.pool)

        # Test connection
        try:
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _generate_key(self, namespace: str, key: str) -> str:
        """Generate namespaced cache key."""
        return f"{namespace}:{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if isinstance(value, (str, int, float)):
            return str(value).encode('utf-8')
        return pickle.dumps(value)

    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from storage."""
        if value is None:
            return None

        # Try to decode as string first
        try:
            return value.decode('utf-8')
        except:
            # Fall back to pickle
            try:
                return pickle.loads(value)
            except:
                return value

    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get value from cache."""
        try:
            full_key = self._generate_key(namespace, key)
            value = self.client.get(full_key)

            if value is not None:
                self.stats['hits'] += 1
                if not self.decode_responses:
                    value = self._deserialize(value)
                return value
            else:
                self.stats['misses'] += 1
                return None

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Redis GET error: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default"
    ) -> bool:
        """Set value in cache with optional TTL."""
        try:
            full_key = self._generate_key(namespace, key)

            if not self.decode_responses:
                value = self._serialize(value)

            result = self.client.setex(full_key, ttl, value) if ttl else self.client.set(full_key, value)

            self.stats['sets'] += 1
            return bool(result)

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Redis SET error: {e}")
            return False

    def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete value from cache."""
        try:
            full_key = self._generate_key(namespace, key)
            result = self.client.delete(full_key)
            self.stats['deletes'] += 1
            return bool(result)

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Redis DELETE error: {e}")
            return False

    def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache."""
        try:
            full_key = self._generate_key(namespace, key)
            return bool(self.client.exists(full_key))

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Redis EXISTS error: {e}")
            return False

    def clear_namespace(self, namespace: str = "default") -> int:
        """Clear all keys in a namespace."""
        try:
            pattern = self._generate_key(namespace, "*")
            keys = self.client.keys(pattern)

            if keys:
                return self.client.delete(*keys)
            return 0

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Redis CLEAR error: {e}")
            return 0

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        hit_rate = 0
        total_requests = self.stats['hits'] + self.stats['misses']

        if total_requests > 0:
            hit_rate = (self.stats['hits'] / total_requests) * 100

        return {
            **self.stats,
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests
        }

    def close(self):
        """Close Redis connection."""
        try:
            self.client.close()
            if hasattr(self, 'pool'):
                self.pool.disconnect()
        except:
            pass


class SessionCache(RedisCache):
    """Specialized cache for user sessions."""

    def __init__(self, ttl: int = 3600, **kwargs):
        """Initialize session cache with default TTL."""
        super().__init__(**kwargs)
        self.ttl = ttl
        self.namespace = "sessions"

    def create_session(self, session_id: str, data: dict[str, Any]) -> bool:
        """Create new session."""
        session_data = {
            'id': session_id,
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat(),
            'data': data
        }

        return self.set(session_id, session_data, ttl=self.ttl, namespace=self.namespace)

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Get session data."""
        session = self.get(session_id, namespace=self.namespace)

        if session:
            # Update last accessed time
            session['last_accessed'] = datetime.now().isoformat()
            self.set(session_id, session, ttl=self.ttl, namespace=self.namespace)

        return session

    def update_session(self, session_id: str, data: dict[str, Any]) -> bool:
        """Update session data."""
        session = self.get_session(session_id)

        if session:
            session['data'].update(data)
            session['last_accessed'] = datetime.now().isoformat()
            return self.set(session_id, session, ttl=self.ttl, namespace=self.namespace)

        return False

    def destroy_session(self, session_id: str) -> bool:
        """Destroy session."""
        return self.delete(session_id, namespace=self.namespace)


class QueryResultCache(RedisCache):
    """Specialized cache for query results."""

    def __init__(self, ttl: int = 300, **kwargs):
        """Initialize query result cache."""
        super().__init__(**kwargs)
        self.ttl = ttl
        self.namespace = "query_results"

    def _generate_query_key(self, query: str, params: Optional[dict] = None) -> str:
        """Generate unique key for query."""
        query_str = f"{query}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(query_str.encode()).hexdigest()

    def cache_result(
        self,
        query: str,
        result: Any,
        params: Optional[dict] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache query result."""
        key = self._generate_query_key(query, params)

        cache_entry = {
            'query': query,
            'params': params,
            'result': result,
            'cached_at': datetime.now().isoformat()
        }

        return self.set(key, cache_entry, ttl=ttl or self.ttl, namespace=self.namespace)

    def get_result(self, query: str, params: Optional[dict] = None) -> Optional[Any]:
        """Get cached query result."""
        key = self._generate_query_key(query, params)
        cache_entry = self.get(key, namespace=self.namespace)

        if cache_entry:
            return cache_entry.get('result')

        return None

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cached results matching pattern."""
        try:
            full_pattern = self._generate_key(self.namespace, f"*{pattern}*")
            keys = self.client.keys(full_pattern)

            if keys:
                return self.client.delete(*keys)
            return 0

        except Exception as e:
            logger.error(f"Redis pattern invalidation error: {e}")
            return 0


def cache_decorator(
    cache: RedisCache,
    namespace: str = "functions",
    ttl: int = 300,
    key_prefix: Optional[str] = None
):
    """Decorator for caching function results."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            # Check cache
            result = cache.get(cache_key, namespace=namespace)
            if result is not None:
                return result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result, ttl=ttl, namespace=namespace)

            return result

        return wrapper

    return decorator


class AsyncRedisCache:
    """Asynchronous Redis cache implementation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50
    ):
        """Initialize async Redis cache."""
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not installed. Install with: pip install redis")

        self.host = host
        self.port = port
        self.db = db
        self.client = None
        self.password = password
        self.max_connections = max_connections

    async def connect(self):
        """Connect to Redis asynchronously."""
        self.client = await AsyncRedis.from_url(
            f"redis://{self.host}:{self.port}/{self.db}",
            password=self.password,
            max_connections=self.max_connections
        )

        # Test connection
        await self.client.ping()
        logger.info(f"Async connected to Redis at {self.host}:{self.port}")

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get value from cache asynchronously."""
        if not self.client:
            await self.connect()

        full_key = f"{namespace}:{key}"
        value = await self.client.get(full_key)

        if value:
            return pickle.loads(value)
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default"
    ) -> bool:
        """Set value in cache asynchronously."""
        if not self.client:
            await self.connect()

        full_key = f"{namespace}:{key}"
        serialized = pickle.dumps(value)

        if ttl:
            return await self.client.setex(full_key, ttl, serialized)
        else:
            return await self.client.set(full_key, serialized)

    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete value from cache asynchronously."""
        if not self.client:
            await self.connect()

        full_key = f"{namespace}:{key}"
        return bool(await self.client.delete(full_key))

    async def close(self):
        """Close async Redis connection."""
        if self.client:
            await self.client.close()


# Singleton instances
_redis_cache = None
_session_cache = None
_query_cache = None


def get_redis_cache() -> Optional[RedisCache]:
    """Get singleton Redis cache instance."""
    global _redis_cache

    if not REDIS_AVAILABLE:
        logger.warning("Redis not available, caching disabled")
        return None

    if _redis_cache is None:
        try:
            _redis_cache = RedisCache()
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            return None

    return _redis_cache


def get_session_cache() -> Optional[SessionCache]:
    """Get singleton session cache instance."""
    global _session_cache

    if not REDIS_AVAILABLE:
        return None

    if _session_cache is None:
        try:
            _session_cache = SessionCache()
        except Exception as e:
            logger.error(f"Failed to initialize session cache: {e}")
            return None

    return _session_cache


def get_query_cache() -> Optional[QueryResultCache]:
    """Get singleton query result cache instance."""
    global _query_cache

    if not REDIS_AVAILABLE:
        return None

    if _query_cache is None:
        try:
            _query_cache = QueryResultCache()
        except Exception as e:
            logger.error(f"Failed to initialize query cache: {e}")
            return None

    return _query_cache
