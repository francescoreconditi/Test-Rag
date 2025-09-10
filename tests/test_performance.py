# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-10
# Scopo: Test delle ottimizzazioni di performance
# ============================================

import unittest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.performance.connection_pool import (
    ConnectionPool, QdrantConnectionPool, DuckDBConnectionPool, QueryOptimizer
)
from src.infrastructure.performance.load_balancer import (
    LoadBalancer, ServerInstance, LoadBalancingStrategy, HealthChecker
)


class TestConnectionPool(unittest.TestCase):
    """Test connection pooling functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_factory = Mock(return_value=Mock())
        self.pool = ConnectionPool(
            factory=self.mock_factory,
            min_size=2,
            max_size=5,
            idle_timeout=10,
            max_lifetime=60
        )
    
    def test_initial_pool_creation(self):
        """Test that minimum connections are created on init."""
        self.assertEqual(self.mock_factory.call_count, 2)
        self.assertEqual(self.pool._created, 2)
    
    def test_get_connection(self):
        """Test getting connection from pool."""
        with self.pool.get_connection() as conn:
            self.assertIsNotNone(conn)
            self.assertEqual(self.pool.get_stats()['reused'], 1)
    
    def test_connection_reuse(self):
        """Test that connections are reused."""
        # Get and release connection
        with self.pool.get_connection() as conn1:
            conn1_id = id(conn1)
        
        # Get again - should reuse
        with self.pool.get_connection() as conn2:
            self.assertEqual(id(conn2), conn1_id)
            self.assertEqual(self.pool.get_stats()['reused'], 2)
    
    def test_max_connections(self):
        """Test that pool respects max connections."""
        connections = []
        
        # Get max connections
        for _ in range(5):
            conn = self.pool.get_connection().__enter__()
            connections.append(conn)
        
        # Pool should be at max
        self.assertEqual(self.pool._created, 5)
        
        # Clean up
        for conn in connections:
            self.pool.get_connection().__exit__(None, None, None)
    
    def test_connection_timeout(self):
        """Test timeout when no connections available."""
        connections = []
        
        # Get all available connections
        for _ in range(5):
            conn = self.pool.get_connection().__enter__()
            connections.append(conn)
        
        # Try to get another - should timeout
        with self.assertRaises(TimeoutError):
            with self.pool.get_connection(timeout=0.1):
                pass


class TestQueryOptimizer(unittest.TestCase):
    """Test query optimization functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.optimizer = QueryOptimizer()
    
    def test_batch_query_optimization(self):
        """Test batch query optimization."""
        queries = [
            "SELECT * FROM table1",
            "SELECT * FROM table2",
            "INSERT INTO table3 VALUES (1)",
            "INSERT INTO table3 VALUES (2)"
        ]
        
        optimized = self.optimizer.optimize_batch_query(queries)
        
        # Should group by query type
        self.assertTrue(any("UNION" in q for q in optimized))
    
    def test_query_caching(self):
        """Test query result caching."""
        query = "SELECT * FROM test"
        result = [{"id": 1, "name": "test"}]
        
        # Cache result
        self.optimizer.cache_query_result(query, result)
        
        # Retrieve from cache
        cached = self.optimizer.get_cached_result(query)
        self.assertEqual(cached, result)
    
    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        self.optimizer.cache_ttl = 0.1  # 100ms TTL
        
        query = "SELECT * FROM test"
        result = [{"id": 1}]
        
        self.optimizer.cache_query_result(query, result)
        
        # Should be in cache
        self.assertIsNotNone(self.optimizer.get_cached_result(query))
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired
        self.assertIsNone(self.optimizer.get_cached_result(query))


class TestLoadBalancer(unittest.TestCase):
    """Test load balancing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.servers = [
            ServerInstance("server1", "localhost", 8001),
            ServerInstance("server2", "localhost", 8002),
            ServerInstance("server3", "localhost", 8003)
        ]
        
        self.lb = LoadBalancer(
            servers=self.servers,
            strategy=LoadBalancingStrategy.ROUND_ROBIN,
            enable_health_checks=False
        )
    
    def test_round_robin(self):
        """Test round-robin load balancing."""
        servers_selected = []
        
        for _ in range(6):
            server = self.lb.get_server()
            servers_selected.append(server.id)
        
        # Should cycle through servers
        self.assertEqual(servers_selected[0], "server1")
        self.assertEqual(servers_selected[1], "server2")
        self.assertEqual(servers_selected[2], "server3")
        self.assertEqual(servers_selected[3], "server1")
    
    def test_least_connections(self):
        """Test least connections strategy."""
        self.lb.strategy = LoadBalancingStrategy.LEAST_CONNECTIONS
        
        # Set different connection counts
        self.servers[0].current_connections = 5
        self.servers[1].current_connections = 2
        self.servers[2].current_connections = 8
        
        # Should select server with least connections
        server = self.lb.get_server()
        self.assertEqual(server.id, "server2")
    
    def test_weighted_round_robin(self):
        """Test weighted round-robin strategy."""
        self.servers[0].weight = 3
        self.servers[1].weight = 2
        self.servers[2].weight = 1
        
        self.lb.strategy = LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
        
        servers_selected = []
        for _ in range(12):  # 2 full cycles
            server = self.lb.get_server()
            servers_selected.append(server.id)
        
        # Count selections
        server1_count = servers_selected.count("server1")
        server2_count = servers_selected.count("server2")
        server3_count = servers_selected.count("server3")
        
        # Should respect weights (approximately)
        self.assertGreater(server1_count, server2_count)
        self.assertGreater(server2_count, server3_count)
    
    def test_unhealthy_server_exclusion(self):
        """Test that unhealthy servers are excluded."""
        # Mark server as unhealthy
        self.servers[1].is_healthy = False
        
        servers_selected = set()
        for _ in range(10):
            server = self.lb.get_server()
            servers_selected.add(server.id)
        
        # Should not select unhealthy server
        self.assertNotIn("server2", servers_selected)
    
    def test_sticky_sessions(self):
        """Test sticky session functionality."""
        self.lb.enable_sticky_sessions = True
        
        # First request creates session
        client_id = "client123"
        server1 = self.lb.get_server(client_id)
        
        # Subsequent requests should get same server
        for _ in range(5):
            server = self.lb.get_server(client_id)
            self.assertEqual(server.id, server1.id)
    
    def test_execute_request_with_retry(self):
        """Test request execution with retry logic."""
        # Mock request function
        request_func = Mock()
        request_func.side_effect = [
            Exception("First attempt failed"),
            Exception("Second attempt failed"),
            "Success"
        ]
        
        result = self.lb.execute_request(request_func, max_retries=3)
        
        self.assertEqual(result, "Success")
        self.assertEqual(request_func.call_count, 3)


class TestHealthChecker(unittest.TestCase):
    """Test health checking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.servers = [
            ServerInstance("server1", "localhost", 8001),
            ServerInstance("server2", "localhost", 8002)
        ]
        
        self.health_checker = HealthChecker(
            check_interval=1,
            timeout=1,
            unhealthy_threshold=2,
            healthy_threshold=2
        )
    
    @patch('requests.get')
    def test_health_check_success(self, mock_get):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Mark server as unhealthy initially
        self.servers[0].is_healthy = False
        
        # Perform health checks
        for _ in range(2):
            self.health_checker._check_server_health(self.servers[0])
        
        # Should be marked healthy after threshold
        self.assertTrue(self.servers[0].is_healthy)
    
    @patch('requests.get')
    def test_health_check_failure(self, mock_get):
        """Test failed health check."""
        mock_get.side_effect = Exception("Connection failed")
        
        # Server starts healthy
        self.servers[0].is_healthy = True
        
        # Perform health checks
        for _ in range(2):
            self.health_checker._check_server_health(self.servers[0])
        
        # Should be marked unhealthy after threshold
        self.assertFalse(self.servers[0].is_healthy)


class TestRedisCache(unittest.TestCase):
    """Test Redis cache functionality."""
    
    @patch('redis.Redis')
    def test_cache_operations(self, mock_redis_class):
        """Test basic cache operations."""
        # Import here to avoid import errors if Redis not installed
        try:
            from src.infrastructure.performance.redis_cache import RedisCache
        except ImportError:
            self.skipTest("Redis not installed")
        
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis
        
        cache = RedisCache()
        
        # Test set
        cache.set("key1", "value1", ttl=60)
        mock_redis.setex.assert_called()
        
        # Test get
        mock_redis.get.return_value = b"value1"
        value = cache.get("key1")
        self.assertEqual(value, "value1")
        
        # Test delete
        cache.delete("key1")
        mock_redis.delete.assert_called()


class TestCeleryTasks(unittest.TestCase):
    """Test Celery task functionality."""
    
    @patch('src.infrastructure.performance.celery_tasks.app')
    def test_task_submission(self, mock_app):
        """Test task submission."""
        try:
            from src.infrastructure.performance.celery_tasks import TaskManager
        except ImportError:
            self.skipTest("Celery not installed")
        
        mock_task = Mock()
        mock_task.id = "task-123"
        mock_app.send_task.return_value = mock_task
        
        manager = TaskManager()
        task_id = manager.submit_task(
            "tasks.indexing.index_documents",
            args=(["/path/to/doc"],),
            kwargs={"collection_name": "test"}
        )
        
        self.assertEqual(task_id, "task-123")
        mock_app.send_task.assert_called_once()


class TestIntegration(unittest.TestCase):
    """Integration tests for performance features."""
    
    def test_connection_pool_with_load_balancer(self):
        """Test connection pool integration with load balancer."""
        # Create mock connection pool
        pool = ConnectionPool(
            factory=lambda: Mock(spec=['execute']),
            min_size=1,
            max_size=3
        )
        
        # Create servers
        servers = [
            ServerInstance("server1", "localhost", 8001),
            ServerInstance("server2", "localhost", 8002)
        ]
        
        # Create load balancer
        lb = LoadBalancer(
            servers=servers,
            strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
            enable_health_checks=False
        )
        
        # Simulate concurrent requests
        def make_request():
            server = lb.get_server()
            with pool.get_connection() as conn:
                time.sleep(0.01)  # Simulate work
                return server.id
        
        # Run concurrent requests
        threads = []
        results = []
        
        for _ in range(10):
            thread = threading.Thread(target=lambda: results.append(make_request()))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have distributed requests
        self.assertEqual(len(results), 10)
        self.assertIn("server1", results)
        self.assertIn("server2", results)


if __name__ == "__main__":
    unittest.main()