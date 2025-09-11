"""Dependency injection container."""

import logging
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from src.application.interfaces import (
    IAnalysisResultRepository,
    IDocumentRepository,
    IFinancialDataRepository,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DependencyContainer:
    """Simple dependency injection container."""

    def __init__(self):
        """Initialize the container."""
        self._services: dict[type, Any] = {}
        self._factories: dict[type, Callable] = {}
        self._singletons: dict[type, Any] = {}

    def register_singleton(self, interface: type[T], implementation: type[T]) -> None:
        """Register a singleton service."""
        self._services[interface] = implementation
        logger.debug(f"Registered singleton: {interface.__name__} -> {implementation.__name__}")

    def register_factory(self, interface: type[T], factory: Callable[[], T]) -> None:
        """Register a factory function for creating instances."""
        self._factories[interface] = factory
        logger.debug(f"Registered factory for: {interface.__name__}")

    def register_instance(self, interface: type[T], instance: T) -> None:
        """Register an existing instance."""
        self._singletons[interface] = instance
        logger.debug(f"Registered instance: {interface.__name__}")

    def get(self, interface: type[T]) -> T:
        """Get a service instance."""
        # Check for existing singleton instance
        if interface in self._singletons:
            return self._singletons[interface]

        # Check for factory
        if interface in self._factories:
            instance = self._factories[interface]()
            logger.debug(f"Created instance from factory: {interface.__name__}")
            return instance

        # Check for registered service
        if interface in self._services:
            implementation = self._services[interface]

            # Create singleton instance
            instance = implementation() if hasattr(implementation, '__init__') else implementation

            self._singletons[interface] = instance
            logger.debug(f"Created singleton instance: {interface.__name__}")
            return instance

        raise ValueError(f"Service not registered: {interface.__name__}")

    def is_registered(self, interface: type[T]) -> bool:
        """Check if a service is registered."""
        return (interface in self._services or
                interface in self._factories or
                interface in self._singletons)

    def clear(self) -> None:
        """Clear all registrations."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        logger.info("Dependency container cleared")

    def configure_default_services(self, config: Optional[dict[str, Any]] = None) -> None:
        """Configure default services with optional configuration."""
        if config is None:
            config = {}

        # Import implementations
        from src.infrastructure.repositories import (
            AnalysisResultRepository,
            DocumentRepository,
            FinancialDataRepository,
        )

        # Configure repositories
        data_path = Path(config.get('data_path', 'data'))

        self.register_factory(
            IFinancialDataRepository,
            lambda: FinancialDataRepository(data_path / "repositories" / "financial.db")
        )

        self.register_factory(
            IDocumentRepository,
            lambda: DocumentRepository(data_path / "repositories" / "documents.db")
        )

        self.register_factory(
            IAnalysisResultRepository,
            lambda: AnalysisResultRepository(data_path / "repositories" / "analysis.db")
        )

        logger.info("Default services configured")

    def configure_production_services(self, config: dict[str, Any]) -> None:
        """Configure services for production environment."""

        # Configure with production implementations
        self.configure_default_services(config)

        # Add production-specific configurations
        openai_api_key = config.get('openai_api_key')
        if not openai_api_key:
            raise ValueError("OpenAI API key is required for production")

        qdrant_host = config.get('qdrant_host', 'localhost')
        qdrant_port = config.get('qdrant_port', 6333)

        logger.info(f"Production services configured with Qdrant at {qdrant_host}:{qdrant_port}")

    def health_check(self) -> dict[str, bool]:
        """Perform health check on all registered services."""
        health_status = {}

        for interface in self._services:
            try:
                service = self.get(interface)

                # Check if service has health check method
                if hasattr(service, 'health_check'):
                    health_status[interface.__name__] = service.health_check()
                else:
                    # Basic check - service can be instantiated
                    health_status[interface.__name__] = service is not None

            except Exception as e:
                logger.error(f"Health check failed for {interface.__name__}: {e}")
                health_status[interface.__name__] = False

        return health_status


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


def configure_container(config: Optional[dict[str, Any]] = None, production: bool = False) -> DependencyContainer:
    """Configure the global dependency container."""
    container = get_container()

    if production:
        container.configure_production_services(config or {})
    else:
        container.configure_default_services(config)

    return container


def inject(interface: type[T]) -> T:
    """Convenience function to inject a dependency."""
    return get_container().get(interface)
