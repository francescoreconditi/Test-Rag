"""
Load balancing and horizontal scaling configuration.
Manages multiple application instances and distributes load efficiently.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import logging
import random
import threading
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    LEAST_RESPONSE_TIME = "least_response_time"


@dataclass
class ServerInstance:
    """Represents a server instance."""
    id: str
    host: str
    port: int
    weight: int = 1
    max_connections: int = 100
    health_check_url: str = "/health"
    is_healthy: bool = True
    last_health_check: Optional[datetime] = None
    current_connections: int = 0
    total_requests: int = 0
    total_errors: int = 0
    average_response_time: float = 0.0
    response_times: deque = None

    def __post_init__(self):
        if self.response_times is None:
            self.response_times = deque(maxlen=100)

    @property
    def url(self) -> str:
        """Get full server URL."""
        return f"http://{self.host}:{self.port}"

    def update_response_time(self, response_time: float):
        """Update response time metrics."""
        self.response_times.append(response_time)
        self.average_response_time = sum(self.response_times) / len(self.response_times)


class HealthChecker:
    """Health checker for server instances."""

    def __init__(
        self,
        check_interval: int = 30,
        timeout: int = 5,
        unhealthy_threshold: int = 3,
        healthy_threshold: int = 2
    ):
        self.check_interval = check_interval
        self.timeout = timeout
        self.unhealthy_threshold = unhealthy_threshold
        self.healthy_threshold = healthy_threshold
        self.failure_counts = {}
        self.success_counts = {}
        self._stop_event = threading.Event()
        self._check_thread = None

    def start(self, servers: list[ServerInstance]):
        """Start health checking."""
        self._check_thread = threading.Thread(
            target=self._health_check_loop,
            args=(servers,),
            daemon=True
        )
        self._check_thread.start()

    def stop(self):
        """Stop health checking."""
        self._stop_event.set()
        if self._check_thread:
            self._check_thread.join(timeout=5)

    def _health_check_loop(self, servers: list[ServerInstance]):
        """Main health check loop."""
        while not self._stop_event.is_set():
            for server in servers:
                self._check_server_health(server)

            self._stop_event.wait(self.check_interval)

    def _check_server_health(self, server: ServerInstance):
        """Check health of a single server."""
        try:
            response = requests.get(
                f"{server.url}{server.health_check_url}",
                timeout=self.timeout
            )

            if response.status_code == 200:
                self._handle_success(server)
            else:
                self._handle_failure(server)

        except Exception as e:
            logger.warning(f"Health check failed for {server.id}: {e}")
            self._handle_failure(server)

        server.last_health_check = datetime.now()

    def _handle_success(self, server: ServerInstance):
        """Handle successful health check."""
        server_id = server.id

        # Reset failure count
        self.failure_counts[server_id] = 0

        # Increment success count
        if server_id not in self.success_counts:
            self.success_counts[server_id] = 0
        self.success_counts[server_id] += 1

        # Mark as healthy after threshold
        if not server.is_healthy and self.success_counts[server_id] >= self.healthy_threshold:
            server.is_healthy = True
            logger.info(f"Server {server_id} is now healthy")

    def _handle_failure(self, server: ServerInstance):
        """Handle failed health check."""
        server_id = server.id

        # Reset success count
        self.success_counts[server_id] = 0

        # Increment failure count
        if server_id not in self.failure_counts:
            self.failure_counts[server_id] = 0
        self.failure_counts[server_id] += 1

        # Mark as unhealthy after threshold
        if server.is_healthy and self.failure_counts[server_id] >= self.unhealthy_threshold:
            server.is_healthy = False
            logger.warning(f"Server {server_id} is now unhealthy")


class LoadBalancer:
    """Load balancer for distributing requests across server instances."""

    def __init__(
        self,
        servers: list[ServerInstance],
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        enable_health_checks: bool = True,
        enable_sticky_sessions: bool = False,
        session_timeout: int = 3600
    ):
        self.servers = servers
        self.strategy = strategy
        self.enable_sticky_sessions = enable_sticky_sessions
        self.session_timeout = session_timeout

        # Round-robin counter
        self._rr_counter = 0
        self._lock = threading.Lock()

        # Session affinity
        self._sessions = {}
        self._session_lock = threading.Lock()

        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'lb_errors': 0
        }

        # Health checker
        self.health_checker = None
        if enable_health_checks:
            self.health_checker = HealthChecker()
            self.health_checker.start(servers)

    def get_server(self, client_id: Optional[str] = None) -> Optional[ServerInstance]:
        """Get next server based on load balancing strategy."""
        # Check sticky sessions
        if self.enable_sticky_sessions and client_id:
            server = self._get_sticky_server(client_id)
            if server and server.is_healthy:
                return server

        # Get healthy servers
        healthy_servers = [s for s in self.servers if s.is_healthy]

        if not healthy_servers:
            logger.error("No healthy servers available")
            self.stats['lb_errors'] += 1
            return None

        # Select server based on strategy
        server = None

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            server = self._round_robin(healthy_servers)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            server = self._least_connections(healthy_servers)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            server = self._weighted_round_robin(healthy_servers)
        elif self.strategy == LoadBalancingStrategy.IP_HASH:
            server = self._ip_hash(healthy_servers, client_id)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            server = self._random(healthy_servers)
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            server = self._least_response_time(healthy_servers)

        # Update sticky session
        if self.enable_sticky_sessions and client_id and server:
            self._update_sticky_session(client_id, server)

        return server

    def _round_robin(self, servers: list[ServerInstance]) -> ServerInstance:
        """Round-robin selection."""
        with self._lock:
            server = servers[self._rr_counter % len(servers)]
            self._rr_counter += 1
            return server

    def _least_connections(self, servers: list[ServerInstance]) -> ServerInstance:
        """Select server with least connections."""
        return min(servers, key=lambda s: s.current_connections)

    def _weighted_round_robin(self, servers: list[ServerInstance]) -> ServerInstance:
        """Weighted round-robin selection."""
        total_weight = sum(s.weight for s in servers)

        with self._lock:
            target = self._rr_counter % total_weight
            self._rr_counter += 1

        current = 0
        for server in servers:
            current += server.weight
            if current > target:
                return server

        return servers[-1]

    def _ip_hash(self, servers: list[ServerInstance], client_id: Optional[str]) -> ServerInstance:
        """IP hash-based selection."""
        if not client_id:
            return self._random(servers)

        hash_value = int(hashlib.md5(client_id.encode()).hexdigest(), 16)
        return servers[hash_value % len(servers)]

    def _random(self, servers: list[ServerInstance]) -> ServerInstance:
        """Random selection."""
        return random.choice(servers)

    def _least_response_time(self, servers: list[ServerInstance]) -> ServerInstance:
        """Select server with least average response time."""
        return min(servers, key=lambda s: s.average_response_time)

    def _get_sticky_server(self, client_id: str) -> Optional[ServerInstance]:
        """Get server from sticky session."""
        with self._session_lock:
            if client_id in self._sessions:
                session = self._sessions[client_id]

                # Check if session expired
                if datetime.now() - session['timestamp'] > timedelta(seconds=self.session_timeout):
                    del self._sessions[client_id]
                    return None

                # Update timestamp
                session['timestamp'] = datetime.now()
                return session['server']

        return None

    def _update_sticky_session(self, client_id: str, server: ServerInstance):
        """Update sticky session."""
        with self._session_lock:
            self._sessions[client_id] = {
                'server': server,
                'timestamp': datetime.now()
            }

    def execute_request(
        self,
        request_func,
        client_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Any:
        """Execute request with load balancing and retry logic."""
        last_error = None

        for _attempt in range(max_retries):
            server = self.get_server(client_id)

            if not server:
                self.stats['failed_requests'] += 1
                raise Exception("No available servers")

            try:
                # Track connection
                server.current_connections += 1
                self.stats['total_requests'] += 1

                # Execute request
                start_time = time.time()
                result = request_func(server.url)
                response_time = time.time() - start_time

                # Update metrics
                server.update_response_time(response_time)
                server.total_requests += 1
                self.stats['successful_requests'] += 1

                return result

            except Exception as e:
                last_error = e
                server.total_errors += 1
                self.stats['failed_requests'] += 1
                logger.warning(f"Request failed on {server.id}: {e}")

                # Mark server as unhealthy if too many errors
                if server.total_errors > 10:
                    server.is_healthy = False

            finally:
                server.current_connections -= 1

        raise last_error or Exception("All retry attempts failed")

    async def execute_async_request(
        self,
        request_func,
        client_id: Optional[str] = None,
        max_retries: int = 3
    ) -> Any:
        """Execute async request with load balancing."""
        last_error = None

        for _attempt in range(max_retries):
            server = self.get_server(client_id)

            if not server:
                self.stats['failed_requests'] += 1
                raise Exception("No available servers")

            try:
                # Track connection
                server.current_connections += 1
                self.stats['total_requests'] += 1

                # Execute request
                start_time = time.time()
                result = await request_func(server.url)
                response_time = time.time() - start_time

                # Update metrics
                server.update_response_time(response_time)
                server.total_requests += 1
                self.stats['successful_requests'] += 1

                return result

            except Exception as e:
                last_error = e
                server.total_errors += 1
                self.stats['failed_requests'] += 1
                logger.warning(f"Async request failed on {server.id}: {e}")

            finally:
                server.current_connections -= 1

        raise last_error or Exception("All retry attempts failed")

    def get_stats(self) -> dict[str, Any]:
        """Get load balancer statistics."""
        server_stats = []

        for server in self.servers:
            server_stats.append({
                'id': server.id,
                'url': server.url,
                'is_healthy': server.is_healthy,
                'current_connections': server.current_connections,
                'total_requests': server.total_requests,
                'total_errors': server.total_errors,
                'average_response_time': round(server.average_response_time, 3),
                'last_health_check': server.last_health_check.isoformat() if server.last_health_check else None
            })

        return {
            'strategy': self.strategy.value,
            'total_servers': len(self.servers),
            'healthy_servers': sum(1 for s in self.servers if s.is_healthy),
            'stats': self.stats,
            'servers': server_stats,
            'active_sessions': len(self._sessions) if self.enable_sticky_sessions else 0
        }

    def shutdown(self):
        """Shutdown load balancer."""
        if self.health_checker:
            self.health_checker.stop()


class ApplicationCluster:
    """Manages a cluster of application instances."""

    def __init__(self, config_file: Optional[str] = None):
        self.servers = []
        self.load_balancer = None

        if config_file:
            self._load_config(config_file)
        else:
            self._load_default_config()

    def _load_default_config(self):
        """Load default cluster configuration."""
        # Default configuration for local development
        self.servers = [
            ServerInstance(
                id="app-1",
                host="localhost",
                port=8501,
                weight=1
            ),
            ServerInstance(
                id="app-2",
                host="localhost",
                port=8502,
                weight=1
            ),
            ServerInstance(
                id="app-3",
                host="localhost",
                port=8503,
                weight=1
            )
        ]

        self.load_balancer = LoadBalancer(
            servers=self.servers,
            strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
            enable_health_checks=True,
            enable_sticky_sessions=True
        )

    def _load_config(self, config_file: str):
        """Load cluster configuration from file."""
        import json

        with open(config_file) as f:
            config = json.load(f)

        # Create server instances
        for server_config in config['servers']:
            self.servers.append(ServerInstance(**server_config))

        # Create load balancer
        lb_config = config.get('load_balancer', {})
        self.load_balancer = LoadBalancer(
            servers=self.servers,
            strategy=LoadBalancingStrategy(lb_config.get('strategy', 'round_robin')),
            enable_health_checks=lb_config.get('enable_health_checks', True),
            enable_sticky_sessions=lb_config.get('enable_sticky_sessions', False)
        )

    def scale_up(self, num_instances: int = 1):
        """Add new instances to the cluster."""
        for _i in range(num_instances):
            new_port = 8510 + len(self.servers)
            new_server = ServerInstance(
                id=f"app-{len(self.servers) + 1}",
                host="localhost",
                port=new_port,
                weight=1
            )

            self.servers.append(new_server)
            logger.info(f"Added new server instance: {new_server.id}")

    def scale_down(self, num_instances: int = 1):
        """Remove instances from the cluster."""
        for _ in range(min(num_instances, len(self.servers) - 1)):
            if len(self.servers) > 1:
                removed = self.servers.pop()
                logger.info(f"Removed server instance: {removed.id}")

    def get_metrics(self) -> dict[str, Any]:
        """Get cluster metrics."""
        return {
            'cluster_size': len(self.servers),
            'load_balancer': self.load_balancer.get_stats() if self.load_balancer else None,
            'timestamp': datetime.now().isoformat()
        }


# Singleton instance
_cluster = None


def get_application_cluster() -> ApplicationCluster:
    """Get singleton application cluster."""
    global _cluster

    if _cluster is None:
        _cluster = ApplicationCluster()

    return _cluster
