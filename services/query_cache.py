"""Simple in-memory cache for RAG query results to improve performance."""

import hashlib
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class QueryCache:
    """In-memory cache for query results with TTL support."""

    def __init__(self, ttl_seconds: int = 3600):
        """Initialize cache with time-to-live in seconds (default 1 hour)."""
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0

    def _generate_key(self, query: str, top_k: int, analysis_type: Optional[str] = None) -> str:
        """Generate a unique cache key for the query parameters."""
        cache_string = f"{query.lower().strip()}_{top_k}_{analysis_type or 'standard'}"
        return hashlib.md5(cache_string.encode()).hexdigest()

    def get(self, query: str, top_k: int, analysis_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve cached result if exists and not expired."""
        key = self._generate_key(query, top_k, analysis_type)

        if key in self.cache:
            cached_item = self.cache[key]
            # Check if expired
            if time.time() - cached_item['timestamp'] < self.ttl_seconds:
                self.hits += 1
                logger.debug(f"Cache hit for query: {query[:50]}... (hits: {self.hits}, misses: {self.misses})")
                return cached_item['result']
            else:
                # Remove expired item
                del self.cache[key]
                logger.debug(f"Cache expired for query: {query[:50]}...")

        self.misses += 1
        logger.debug(f"Cache miss for query: {query[:50]}... (hits: {self.hits}, misses: {self.misses})")
        return None

    def set(self, query: str, top_k: int, result: Dict[str, Any], analysis_type: Optional[str] = None):
        """Store query result in cache."""
        key = self._generate_key(query, top_k, analysis_type)
        self.cache[key] = {
            'result': result,
            'timestamp': time.time(),
            'query': query,
            'top_k': top_k,
            'analysis_type': analysis_type
        }
        logger.debug(f"Cached result for query: {query[:50]}... (cache size: {len(self.cache)})")

    def clear(self):
        """Clear all cached results."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Query cache cleared")

    def cleanup_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, item in self.cache.items()
            if current_time - item['timestamp'] >= self.ttl_seconds
        ]
        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'cache_size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'ttl_seconds': self.ttl_seconds
        }
