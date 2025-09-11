"""Repository interfaces for data access."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from src.domain.entities import AnalysisResult, Document, FinancialData
from src.domain.value_objects import DateRange


class IRepository(ABC):
    """Base repository interface."""

    @abstractmethod
    def save(self, entity: Any) -> str:
        """Save an entity and return its ID."""
        pass

    @abstractmethod
    def find_by_id(self, entity_id: str) -> Optional[Any]:
        """Find an entity by ID."""
        pass

    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> list[Any]:
        """Find all entities with pagination."""
        pass

    @abstractmethod
    def update(self, entity_id: str, entity: Any) -> bool:
        """Update an entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        pass

    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """Check if an entity exists."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Count total entities."""
        pass


class IFinancialDataRepository(IRepository):
    """Repository interface for financial data."""

    @abstractmethod
    def find_by_company(self, company_name: str) -> list[FinancialData]:
        """Find financial data by company name."""
        pass

    @abstractmethod
    def find_by_period(self, date_range: DateRange) -> list[FinancialData]:
        """Find financial data within a date range."""
        pass

    @abstractmethod
    def find_by_company_and_period(
        self,
        company_name: str,
        date_range: DateRange
    ) -> list[FinancialData]:
        """Find financial data by company and period."""
        pass

    @abstractmethod
    def get_latest_by_company(self, company_name: str) -> Optional[FinancialData]:
        """Get the latest financial data for a company."""
        pass

    @abstractmethod
    def get_companies(self) -> list[str]:
        """Get list of all companies."""
        pass

    @abstractmethod
    def find_by_metric_threshold(
        self,
        metric_name: str,
        threshold: float,
        operator: str = "gte"  # gte, lte, gt, lt, eq
    ) -> list[FinancialData]:
        """Find financial data by metric threshold."""
        pass

    @abstractmethod
    def aggregate_by_period(
        self,
        company_name: str,
        aggregation_period: str  # 'monthly', 'quarterly', 'yearly'
    ) -> list[FinancialData]:
        """Aggregate financial data by period."""
        pass


class IDocumentRepository(IRepository):
    """Repository interface for documents."""

    @abstractmethod
    def find_by_type(self, document_type: str) -> list[Document]:
        """Find documents by type."""
        pass

    @abstractmethod
    def find_by_status(self, status: str) -> list[Document]:
        """Find documents by processing status."""
        pass

    @abstractmethod
    def find_indexed(self) -> list[Document]:
        """Find all indexed documents."""
        pass

    @abstractmethod
    def find_by_metadata(self, metadata_key: str, metadata_value: Any) -> list[Document]:
        """Find documents by metadata."""
        pass

    @abstractmethod
    def search_content(self, query: str, limit: int = 10) -> list[Document]:
        """Search documents by content."""
        pass

    @abstractmethod
    def find_similar(self, document_id: str, limit: int = 5) -> list[Document]:
        """Find similar documents."""
        pass

    @abstractmethod
    def get_by_path(self, file_path: str) -> Optional[Document]:
        """Get document by file path."""
        pass

    @abstractmethod
    def find_recent(self, days: int = 7) -> list[Document]:
        """Find recently added documents."""
        pass

    @abstractmethod
    def cleanup_old(self, days: int = 90) -> int:
        """Clean up old documents and return count deleted."""
        pass


class IAnalysisResultRepository(IRepository):
    """Repository interface for analysis results."""

    @abstractmethod
    def find_by_type(self, analysis_type: str) -> list[AnalysisResult]:
        """Find analysis results by type."""
        pass

    @abstractmethod
    def find_by_source(self, source_data_id: str) -> list[AnalysisResult]:
        """Find analysis results by source data ID."""
        pass

    @abstractmethod
    def find_recent(self, hours: int = 24) -> list[AnalysisResult]:
        """Find recent analysis results."""
        pass

    @abstractmethod
    def find_high_confidence(self, min_confidence: float = 0.8) -> list[AnalysisResult]:
        """Find high confidence analysis results."""
        pass

    @abstractmethod
    def find_with_anomalies(self) -> list[AnalysisResult]:
        """Find analysis results containing anomalies."""
        pass

    @abstractmethod
    def get_latest_by_type(self, analysis_type: str) -> Optional[AnalysisResult]:
        """Get the latest analysis result by type."""
        pass

    @abstractmethod
    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> list[AnalysisResult]:
        """Find analysis results within date range."""
        pass

    @abstractmethod
    def get_statistics(self) -> dict[str, Any]:
        """Get repository statistics."""
        pass
