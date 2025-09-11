"""Unit tests for repository implementations."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.domain.entities import (
    AnalysisResult,
    AnalysisType,
    Document,
    DocumentStatus,
    DocumentType,
    FinancialData,
    FinancialPeriod,
)
from src.domain.value_objects import DateRange
from src.infrastructure.repositories import AnalysisResultRepository, DocumentRepository, FinancialDataRepository


class TestFinancialDataRepository:
    """Test cases for FinancialDataRepository."""

    @pytest.fixture
    def temp_repo(self, temp_dir):
        """Create a temporary repository."""
        db_path = temp_dir / "test_financial.db"
        return FinancialDataRepository(db_path)

    def test_save_and_find_by_id(self, temp_repo, sample_financial_data):
        """Test saving and retrieving financial data."""
        entity_id = temp_repo.save(sample_financial_data)

        retrieved = temp_repo.find_by_id(entity_id)
        assert retrieved is not None
        assert retrieved.company_name == sample_financial_data.company_name
        assert retrieved.currency == sample_financial_data.currency

    def test_find_by_company(self, temp_repo, sample_financial_data):
        """Test finding data by company name."""
        temp_repo.save(sample_financial_data)

        # Add another company's data
        other_data = FinancialData(
            company_name="Other Company",
            currency="EUR"
        )
        temp_repo.save(other_data)

        test_company_data = temp_repo.find_by_company("Test Company")
        assert len(test_company_data) == 1
        assert test_company_data[0].company_name == "Test Company"

    def test_find_by_period(self, temp_repo, sample_financial_data):
        """Test finding data by period."""
        temp_repo.save(sample_financial_data)

        # Test with overlapping date range
        date_range = DateRange(
            start=date(2023, 6, 1),
            end=date(2023, 12, 31)
        )

        results = temp_repo.find_by_period(date_range)
        assert len(results) >= 1

    def test_get_latest_by_company(self, temp_repo):
        """Test getting latest financial data for a company."""
        # Create data for different periods
        older_period = FinancialPeriod(
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 31),
            period_type="yearly"
        )

        newer_period = FinancialPeriod(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            period_type="yearly"
        )

        older_data = FinancialData(
            company_name="Test Company",
            period=older_period,
            currency="EUR"
        )

        newer_data = FinancialData(
            company_name="Test Company",
            period=newer_period,
            currency="EUR"
        )

        temp_repo.save(older_data)
        temp_repo.save(newer_data)

        latest = temp_repo.get_latest_by_company("Test Company")
        assert latest is not None
        assert latest.period.end_date == date(2023, 12, 31)

    def test_get_companies(self, temp_repo, sample_financial_data):
        """Test getting list of companies."""
        # Save data for multiple companies
        temp_repo.save(sample_financial_data)

        other_data = FinancialData(
            company_name="Company B",
            currency="EUR"
        )
        temp_repo.save(other_data)

        companies = temp_repo.get_companies()
        assert len(companies) == 2
        assert "Test Company" in companies
        assert "Company B" in companies
        assert companies == sorted(companies)  # Should be sorted

    def test_find_by_metric_threshold(self, temp_repo, sample_financial_data):
        """Test finding data by metric threshold."""
        temp_repo.save(sample_financial_data)

        # Test greater than or equal
        high_revenue = temp_repo.find_by_metric_threshold("revenue", 500000, "gte")
        assert len(high_revenue) == 1

        # Test less than
        low_revenue = temp_repo.find_by_metric_threshold("revenue", 500000, "lt")
        assert len(low_revenue) == 0


class TestDocumentRepository:
    """Test cases for DocumentRepository."""

    @pytest.fixture
    def temp_repo(self, temp_dir):
        """Create a temporary document repository."""
        db_path = temp_dir / "test_documents.db"
        return DocumentRepository(db_path)

    def test_save_and_find_by_id(self, temp_repo, sample_document):
        """Test saving and retrieving documents."""
        entity_id = temp_repo.save(sample_document)

        retrieved = temp_repo.find_by_id(entity_id)
        assert retrieved is not None
        assert retrieved.file_path == sample_document.file_path
        assert retrieved.document_type == sample_document.document_type

    def test_find_by_type(self, temp_repo, sample_document):
        """Test finding documents by type."""
        temp_repo.save(sample_document)

        # Add different document type
        txt_doc = Document(
            file_path=Path("test.txt"),
            document_type=DocumentType.TXT
        )
        temp_repo.save(txt_doc)

        pdf_docs = temp_repo.find_by_type("pdf")
        assert len(pdf_docs) == 1
        assert pdf_docs[0].document_type == DocumentType.PDF

        txt_docs = temp_repo.find_by_type("txt")
        assert len(txt_docs) == 1
        assert txt_docs[0].document_type == DocumentType.TXT

    def test_find_by_status(self, temp_repo, sample_document):
        """Test finding documents by status."""
        temp_repo.save(sample_document)

        # Mark as indexed
        sample_document.mark_as_indexed()
        temp_repo.update(sample_document.id, sample_document)

        indexed_docs = temp_repo.find_by_status("indexed")
        assert len(indexed_docs) == 1
        assert indexed_docs[0].status == DocumentStatus.INDEXED

    def test_find_indexed(self, temp_repo, sample_document):
        """Test finding all indexed documents."""
        sample_document.mark_as_indexed()
        temp_repo.save(sample_document)

        indexed_docs = temp_repo.find_indexed()
        assert len(indexed_docs) == 1
        assert indexed_docs[0].is_indexed

    def test_search_content(self, temp_repo):
        """Test content searching."""
        doc1 = Document(
            file_path=Path("doc1.txt"),
            content="This document contains important financial data"
        )

        doc2 = Document(
            file_path=Path("doc2.txt"),
            content="This is about marketing strategies"
        )

        temp_repo.save(doc1)
        temp_repo.save(doc2)

        results = temp_repo.search_content("financial", limit=10)
        assert len(results) == 1
        assert "financial" in results[0].content

    def test_find_by_metadata(self, temp_repo, sample_document):
        """Test finding documents by metadata."""
        temp_repo.save(sample_document)

        results = temp_repo.find_by_metadata("title", "Test Document")
        assert len(results) == 1
        assert results[0].metadata.title == "Test Document"

    def test_get_by_path(self, temp_repo, sample_document):
        """Test getting document by file path."""
        temp_repo.save(sample_document)

        result = temp_repo.get_by_path("test_document.pdf")
        assert result is not None
        assert result.file_path == Path("test_document.pdf")

    def test_find_recent(self, temp_repo, sample_document):
        """Test finding recent documents."""
        temp_repo.save(sample_document)

        recent_docs = temp_repo.find_recent(days=7)
        assert len(recent_docs) == 1

    def test_cleanup_old(self, temp_repo):
        """Test cleanup of old documents."""
        # Create an old failed document
        old_doc = Document(
            file_path=Path("old_doc.pdf"),
            status=DocumentStatus.FAILED,
            created_at=datetime.now() - timedelta(days=100)
        )
        temp_repo.save(old_doc)

        # Create a recent document (should not be cleaned up)
        recent_doc = Document(
            file_path=Path("recent_doc.pdf"),
            status=DocumentStatus.FAILED
        )
        temp_repo.save(recent_doc)

        cleaned_count = temp_repo.cleanup_old(days=90)
        assert cleaned_count == 1

    def test_get_statistics(self, temp_repo, sample_document):
        """Test repository statistics."""
        sample_document.mark_as_indexed()
        temp_repo.save(sample_document)

        # Add failed document
        failed_doc = Document(
            file_path=Path("failed.pdf"),
            status=DocumentStatus.FAILED
        )
        temp_repo.save(failed_doc)

        stats = temp_repo.get_statistics()

        assert stats['total_documents'] == 2
        assert stats['indexed_documents'] == 1
        assert stats['failed_documents'] == 1
        assert 'by_status' in stats
        assert 'by_type' in stats


class TestAnalysisResultRepository:
    """Test cases for AnalysisResultRepository."""

    @pytest.fixture
    def temp_repo(self, temp_dir):
        """Create a temporary analysis result repository."""
        db_path = temp_dir / "test_analysis.db"
        return AnalysisResultRepository(db_path)

    def test_save_and_find_by_id(self, temp_repo, sample_analysis_result):
        """Test saving and retrieving analysis results."""
        entity_id = temp_repo.save(sample_analysis_result)

        retrieved = temp_repo.find_by_id(entity_id)
        assert retrieved is not None
        assert retrieved.analysis_type == sample_analysis_result.analysis_type
        assert retrieved.source_data_id == sample_analysis_result.source_data_id

    def test_find_by_type(self, temp_repo, sample_analysis_result):
        """Test finding analysis results by type."""
        temp_repo.save(sample_analysis_result)

        # Add different type
        trend_analysis = AnalysisResult(
            analysis_type=AnalysisType.TREND,
            source_data_id="test-data-2"
        )
        temp_repo.save(trend_analysis)

        financial_results = temp_repo.find_by_type("financial")
        assert len(financial_results) == 1
        assert financial_results[0].analysis_type == AnalysisType.FINANCIAL

        trend_results = temp_repo.find_by_type("trend")
        assert len(trend_results) == 1
        assert trend_results[0].analysis_type == AnalysisType.TREND

    def test_find_by_source(self, temp_repo, sample_analysis_result):
        """Test finding analysis results by source data ID."""
        temp_repo.save(sample_analysis_result)

        results = temp_repo.find_by_source("test-financial-1")
        assert len(results) == 1
        assert results[0].source_data_id == "test-financial-1"

    def test_find_recent(self, temp_repo, sample_analysis_result):
        """Test finding recent analysis results."""
        temp_repo.save(sample_analysis_result)

        recent_results = temp_repo.find_recent(hours=24)
        assert len(recent_results) == 1

    def test_find_high_confidence(self, temp_repo, sample_analysis_result):
        """Test finding high confidence results."""
        sample_analysis_result.confidence_score = 0.9
        temp_repo.save(sample_analysis_result)

        # Add low confidence result
        low_confidence = AnalysisResult(
            analysis_type=AnalysisType.FINANCIAL,
            confidence_score=0.5
        )
        temp_repo.save(low_confidence)

        high_conf_results = temp_repo.find_high_confidence(min_confidence=0.8)
        assert len(high_conf_results) == 1
        assert high_conf_results[0].confidence_score >= 0.8

    def test_find_with_anomalies(self, temp_repo, sample_analysis_result):
        """Test finding results with anomalies."""
        # sample_analysis_result already has an anomalous metric from conftest
        from src.domain.entities import MetricResult

        anomaly_metric = MetricResult(
            name="anomalous_value",
            value=Decimal("999999"),
            is_anomaly=True
        )
        sample_analysis_result.add_metric(anomaly_metric)
        temp_repo.save(sample_analysis_result)

        # Add result without anomalies
        normal_result = AnalysisResult(
            analysis_type=AnalysisType.FINANCIAL
        )
        temp_repo.save(normal_result)

        anomaly_results = temp_repo.find_with_anomalies()
        assert len(anomaly_results) == 1

    def test_get_latest_by_type(self, temp_repo):
        """Test getting latest analysis result by type."""
        # Create older result
        older_result = AnalysisResult(
            analysis_type=AnalysisType.FINANCIAL,
            created_at=datetime.now() - timedelta(hours=2)
        )
        temp_repo.save(older_result)

        # Create newer result
        newer_result = AnalysisResult(
            analysis_type=AnalysisType.FINANCIAL,
            created_at=datetime.now()
        )
        temp_repo.save(newer_result)

        latest = temp_repo.get_latest_by_type("financial")
        assert latest is not None
        # Should be the newer one (approximately)
        assert latest.created_at >= older_result.created_at

    def test_find_by_date_range(self, temp_repo, sample_analysis_result):
        """Test finding analysis results by date range."""
        temp_repo.save(sample_analysis_result)

        start_date = datetime.now() - timedelta(hours=1)
        end_date = datetime.now() + timedelta(hours=1)

        results = temp_repo.find_by_date_range(start_date, end_date)
        assert len(results) == 1

    def test_get_statistics(self, temp_repo, sample_analysis_result):
        """Test repository statistics."""
        sample_analysis_result.confidence_score = 0.9
        temp_repo.save(sample_analysis_result)

        # Add another result
        other_result = AnalysisResult(
            analysis_type=AnalysisType.TREND,
            confidence_score=0.7
        )
        temp_repo.save(other_result)

        stats = temp_repo.get_statistics()

        assert stats['total_analyses'] == 2
        assert stats['by_type']['financial'] == 1
        assert stats['by_type']['trend'] == 1
        assert stats['high_confidence_count'] == 1
        assert stats['average_confidence'] == 0.8  # (0.9 + 0.7) / 2
