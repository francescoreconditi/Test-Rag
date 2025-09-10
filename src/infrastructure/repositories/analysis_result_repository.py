"""Analysis result repository implementation."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from src.application.interfaces.repository_interfaces import IAnalysisResultRepository
from src.domain.entities import AnalysisResult, AnalysisType

from .base_repository import BaseRepository


class AnalysisResultRepository(BaseRepository, IAnalysisResultRepository):
    """SQLite implementation of analysis result repository."""

    def __init__(self, db_path: Path = Path("data/repositories/analysis.db")):
        """Initialize analysis result repository."""
        super().__init__(db_path, "analysis_results", AnalysisResult)
        self._create_additional_indexes()

    def _create_additional_indexes(self):
        """Create additional indexes specific to analysis results."""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            # Add type and confidence indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_results_type
                ON analysis_results (id)
            """)
            conn.commit()

    def find_by_type(self, analysis_type: str) -> list[AnalysisResult]:
        """Find analysis results by type."""
        all_results = self.find_all(limit=10000)

        # Convert string to AnalysisType enum if needed
        try:
            type_enum = AnalysisType(analysis_type.lower())
        except ValueError:
            return []

        return [
            result for result in all_results
            if result.analysis_type == type_enum
        ]

    def find_by_source(self, source_data_id: str) -> list[AnalysisResult]:
        """Find analysis results by source data ID."""
        all_results = self.find_all(limit=10000)

        return [
            result for result in all_results
            if result.source_data_id == source_data_id
        ]

    def find_recent(self, hours: int = 24) -> list[AnalysisResult]:
        """Find recent analysis results."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        all_results = self.find_all(limit=10000)

        return [
            result for result in all_results
            if result.created_at >= cutoff_time
        ]

    def find_high_confidence(self, min_confidence: float = 0.8) -> list[AnalysisResult]:
        """Find high confidence analysis results."""
        all_results = self.find_all(limit=10000)

        return [
            result for result in all_results
            if result.confidence_score >= min_confidence
        ]

    def find_with_anomalies(self) -> list[AnalysisResult]:
        """Find analysis results containing anomalies."""
        all_results = self.find_all(limit=10000)

        results_with_anomalies = []

        for result in all_results:
            # Check if any metrics are marked as anomalies
            if any(metric.is_anomaly for metric in result.metrics):
                results_with_anomalies.append(result)

        return results_with_anomalies

    def get_latest_by_type(self, analysis_type: str) -> Optional[AnalysisResult]:
        """Get the latest analysis result by type."""
        results_of_type = self.find_by_type(analysis_type)

        if not results_of_type:
            return None

        # Sort by creation date
        sorted_results = sorted(
            results_of_type,
            key=lambda x: x.created_at,
            reverse=True
        )

        return sorted_results[0] if sorted_results else None

    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> list[AnalysisResult]:
        """Find analysis results within date range."""
        all_results = self.find_all(limit=10000)

        return [
            result for result in all_results
            if start_date <= result.created_at <= end_date
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Get repository statistics."""
        all_results = self.find_all(limit=10000)

        stats = {
            'total_analyses': len(all_results),
            'by_type': {},
            'average_confidence': 0,
            'high_confidence_count': 0,
            'with_anomalies_count': 0,
            'average_processing_time': 0,
            'total_metrics': 0,
            'total_insights': 0,
            'models_used': {}
        }

        if not all_results:
            return stats

        # Count by type
        for analysis_type in AnalysisType:
            count = len([r for r in all_results if r.analysis_type == analysis_type])
            stats['by_type'][analysis_type.value] = count

        # Calculate averages and counts
        total_confidence = 0
        total_processing_time = 0
        valid_processing_count = 0
        models_count = {}

        for result in all_results:
            # Confidence
            total_confidence += result.confidence_score
            if result.confidence_score >= 0.8:
                stats['high_confidence_count'] += 1

            # Anomalies
            if any(metric.is_anomaly for metric in result.metrics):
                stats['with_anomalies_count'] += 1

            # Processing time
            if result.processing_time_seconds:
                total_processing_time += result.processing_time_seconds
                valid_processing_count += 1

            # Metrics and insights
            stats['total_metrics'] += len(result.metrics)
            stats['total_insights'] += len(result.insights)

            # Models used
            if result.model_used:
                models_count[result.model_used] = models_count.get(result.model_used, 0) + 1

        # Calculate averages
        stats['average_confidence'] = total_confidence / len(all_results)

        if valid_processing_count > 0:
            stats['average_processing_time'] = total_processing_time / valid_processing_count

        stats['models_used'] = models_count

        # Add time-based statistics
        if all_results:
            sorted_by_date = sorted(all_results, key=lambda x: x.created_at)
            stats['oldest_analysis'] = sorted_by_date[0].created_at.isoformat()
            stats['newest_analysis'] = sorted_by_date[-1].created_at.isoformat()

            # Analyses per day (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_analyses = [r for r in all_results if r.created_at >= thirty_days_ago]

            if recent_analyses:
                days_span = (datetime.now() - thirty_days_ago).days
                stats['analyses_per_day_last_30'] = len(recent_analyses) / max(days_span, 1)

        return stats
