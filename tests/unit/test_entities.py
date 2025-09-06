"""Unit tests for domain entities."""

import pytest
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

from src.domain.entities import (
    FinancialData, FinancialPeriod, Currency, MetricType,
    Document, DocumentType, DocumentStatus, DocumentMetadata,
    AnalysisResult, AnalysisType, MetricResult, Insight, InsightPriority, ConfidenceLevel
)


class TestFinancialPeriod:
    """Test cases for FinancialPeriod entity."""
    
    def test_financial_period_creation(self, sample_financial_period):
        """Test financial period creation."""
        assert sample_financial_period.start_date == date(2023, 1, 1)
        assert sample_financial_period.end_date == date(2023, 12, 31)
        assert sample_financial_period.period_type == "yearly"
    
    def test_financial_period_invalid_dates_raises_error(self):
        """Test that invalid date order raises error."""
        with pytest.raises(ValueError, match="Start date must be before end date"):
            FinancialPeriod(
                start_date=date(2023, 12, 31),
                end_date=date(2023, 1, 1),
                period_type="yearly"
            )
    
    def test_financial_period_duration(self, sample_financial_period):
        """Test duration calculation."""
        duration = sample_financial_period.duration_days
        assert duration == 364  # 2023 is not a leap year
    
    def test_financial_period_overlaps(self, sample_financial_period):
        """Test overlap detection."""
        overlapping = FinancialPeriod(
            start_date=date(2023, 6, 1),
            end_date=date(2024, 5, 31),
            period_type="yearly"
        )
        
        non_overlapping = FinancialPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            period_type="yearly"
        )
        
        assert sample_financial_period.overlaps_with(overlapping)
        assert not sample_financial_period.overlaps_with(non_overlapping)


class TestFinancialData:
    """Test cases for FinancialData entity."""
    
    def test_financial_data_creation(self, sample_financial_data):
        """Test financial data creation."""
        assert sample_financial_data.company_name == "Test Company"
        assert sample_financial_data.currency == Currency.EUR
        assert len(sample_financial_data.metrics) == 3
    
    def test_add_metric(self, sample_financial_data):
        """Test adding a metric."""
        sample_financial_data.add_metric("growth_rate", Decimal("15.5"), MetricType.GROWTH_RATE)
        
        assert sample_financial_data.get_metric("growth_rate") == Decimal("15.5")
        assert sample_financial_data.metadata["growth_rate_type"] == MetricType.GROWTH_RATE.value
    
    def test_get_metric(self, sample_financial_data):
        """Test getting a metric."""
        revenue = sample_financial_data.get_metric("revenue")
        assert revenue == Decimal("1000000")
        
        non_existent = sample_financial_data.get_metric("non_existent")
        assert non_existent is None
    
    def test_calculate_margin(self, sample_financial_data):
        """Test margin calculation."""
        # Add cost metric with different name
        sample_financial_data.metrics["cost"] = Decimal("850000")
        
        margin = sample_financial_data.calculate_margin()
        expected_margin = ((Decimal("1000000") - Decimal("850000")) / Decimal("1000000")) * 100
        
        assert margin == expected_margin
    
    def test_calculate_growth_rate(self, sample_financial_data):
        """Test growth rate calculation."""
        previous_data = FinancialData(
            company_name="Test Company",
            currency=Currency.EUR
        )
        previous_data.metrics["revenue"] = Decimal("800000")
        
        growth_rate = sample_financial_data.calculate_growth_rate(previous_data, "revenue")
        expected_rate = ((Decimal("1000000") - Decimal("800000")) / Decimal("800000")) * 100
        
        assert growth_rate == expected_rate
    
    def test_validate_valid_data(self, sample_financial_data):
        """Test validation of valid data."""
        errors = sample_financial_data.validate()
        assert errors == []
    
    def test_validate_invalid_data(self):
        """Test validation of invalid data."""
        invalid_data = FinancialData()
        errors = invalid_data.validate()
        
        assert "Company name is required" in errors
        assert "Financial period is required" in errors
        assert "At least one metric is required" in errors
    
    def test_to_dict(self, sample_financial_data):
        """Test conversion to dictionary."""
        data_dict = sample_financial_data.to_dict()
        
        assert data_dict["company_name"] == "Test Company"
        assert data_dict["currency"] == "EUR"
        assert "revenue" in data_dict["metrics"]
        assert data_dict["metrics"]["revenue"] == "1000000"


class TestDocument:
    """Test cases for Document entity."""
    
    def test_document_creation(self, sample_document):
        """Test document creation."""
        assert sample_document.file_path == Path("test_document.pdf")
        assert sample_document.document_type == DocumentType.PDF
        assert sample_document.status == DocumentStatus.PENDING
        assert sample_document.metadata.title == "Test Document"
    
    def test_document_type_detection(self):
        """Test automatic document type detection."""
        doc = Document(file_path=Path("test.docx"))
        assert doc.document_type == DocumentType.DOCX
        
        doc2 = Document(file_path=Path("test.txt"))
        assert doc2.document_type == DocumentType.TXT
    
    def test_document_properties(self, sample_document):
        """Test document properties."""
        assert not sample_document.is_indexed
        assert sample_document.has_content
        assert sample_document.chunk_count == 0
    
    def test_add_chunk(self, sample_document):
        """Test adding chunks."""
        sample_document.add_chunk("First chunk")
        sample_document.add_chunk("Second chunk", [0.1, 0.2, 0.3])
        
        assert sample_document.chunk_count == 2
        assert len(sample_document.embeddings) == 1  # Only second chunk has embedding
    
    def test_mark_as_indexed(self, sample_document):
        """Test marking document as indexed."""
        sample_document.mark_as_indexed()
        
        assert sample_document.is_indexed
        assert sample_document.status == DocumentStatus.INDEXED
        assert sample_document.indexed_at is not None
    
    def test_mark_as_failed(self, sample_document):
        """Test marking document as failed."""
        error_msg = "Processing failed"
        sample_document.mark_as_failed(error_msg)
        
        assert sample_document.status == DocumentStatus.FAILED
        assert sample_document.error_message == error_msg
    
    def test_extract_summary(self, sample_document):
        """Test summary extraction."""
        long_content = "A" * 1000
        sample_document.content = long_content
        
        summary = sample_document.extract_summary(100)
        assert len(summary) <= 103  # 100 + "..."
        
        # Test with period
        content_with_period = "Short content with period. More content after."
        sample_document.content = content_with_period
        summary = sample_document.extract_summary(25)
        assert summary == "Short content with period."
    
    def test_search_content(self, sample_document):
        """Test content searching."""
        sample_document.add_chunk("This contains keyword test")
        sample_document.add_chunk("Another chunk without the word")
        sample_document.add_chunk("TEST in uppercase")
        
        results = sample_document.search_content("test")
        assert len(results) == 2  # Case insensitive by default
        
        results_case_sensitive = sample_document.search_content("test", case_sensitive=True)
        assert len(results_case_sensitive) == 1
    
    def test_validate_valid_document(self, sample_document):
        """Test validation of valid document."""
        # Create actual file for validation
        sample_document.file_path = Path(__file__)  # Use this test file
        errors = sample_document.validate()
        assert errors == []
    
    def test_validate_invalid_document(self):
        """Test validation of invalid document."""
        invalid_doc = Document()
        errors = invalid_doc.validate()
        
        assert "File path is required" in errors
        assert "Document type could not be determined" in errors
    
    def test_to_dict(self, sample_document):
        """Test conversion to dictionary."""
        doc_dict = sample_document.to_dict()
        
        assert doc_dict["file_path"] == "test_document.pdf"
        assert doc_dict["document_type"] == "pdf"
        assert doc_dict["status"] == "pending"
        assert doc_dict["content_length"] > 0


class TestAnalysisResult:
    """Test cases for AnalysisResult entity."""
    
    def test_analysis_result_creation(self, sample_analysis_result):
        """Test analysis result creation."""
        assert sample_analysis_result.analysis_type == AnalysisType.FINANCIAL
        assert sample_analysis_result.source_data_id == "test-financial-1"
        assert len(sample_analysis_result.metrics) == 1
        assert len(sample_analysis_result.insights) == 1
    
    def test_add_metric_updates_confidence(self, sample_analysis_result):
        """Test that adding metrics updates confidence score."""
        initial_confidence = sample_analysis_result.confidence_score
        
        new_metric = MetricResult(
            name="profit_margin",
            value=Decimal("15.0"),
            confidence=0.9
        )
        sample_analysis_result.add_metric(new_metric)
        
        assert sample_analysis_result.confidence_score != initial_confidence
        assert len(sample_analysis_result.metrics) == 2
    
    def test_get_high_priority_insights(self, sample_analysis_result):
        """Test getting high priority insights."""
        high_priority = sample_analysis_result.get_high_priority_insights()
        assert len(high_priority) == 1
        assert high_priority[0].priority in [InsightPriority.HIGH, InsightPriority.CRITICAL]
    
    def test_get_anomalies(self, sample_analysis_result):
        """Test getting anomalies."""
        # Add anomalous metric
        anomaly_metric = MetricResult(
            name="anomalous_expense",
            value=Decimal("999999"),
            is_anomaly=True
        )
        sample_analysis_result.add_metric(anomaly_metric)
        
        anomalies = sample_analysis_result.get_anomalies()
        assert len(anomalies) == 1
        assert anomalies[0].name == "anomalous_expense"
    
    def test_get_metrics_by_trend(self, sample_analysis_result):
        """Test getting metrics by trend."""
        up_trend_metrics = sample_analysis_result.get_metrics_by_trend("up")
        assert len(up_trend_metrics) == 1
        assert up_trend_metrics[0].trend == "up"
    
    def test_generate_executive_report(self, sample_analysis_result):
        """Test executive report generation."""
        report = sample_analysis_result.generate_executive_report()
        
        assert "Rapporto di Analisi" in report
        assert "Test analysis summary" in report
        assert "revenue_growth" in report
        assert "Strong Revenue Growth" in report
    
    def test_to_dict(self, sample_analysis_result):
        """Test conversion to dictionary."""
        result_dict = sample_analysis_result.to_dict()
        
        assert result_dict["analysis_type"] == "financial"
        assert result_dict["source_data_id"] == "test-financial-1"
        assert len(result_dict["metrics"]) == 1
        assert len(result_dict["insights"]) == 1
        assert "confidence_score" in result_dict


class TestMetricResult:
    """Test cases for MetricResult entity."""
    
    def test_metric_result_creation(self):
        """Test metric result creation."""
        metric = MetricResult(
            name="revenue",
            value=Decimal("1000000"),
            unit="EUR",
            change_percentage=Decimal("15.5"),
            trend="up"
        )
        
        assert metric.name == "revenue"
        assert metric.value == Decimal("1000000")
        assert metric.is_positive_change
    
    def test_format_value_with_unit(self):
        """Test value formatting with unit."""
        metric = MetricResult(
            name="revenue",
            value=Decimal("1000000.50"),
            unit="EUR"
        )
        
        formatted = metric.format_value()
        assert formatted == "1,000,000.50 EUR"
    
    def test_format_value_without_unit(self):
        """Test value formatting without unit."""
        metric = MetricResult(
            name="count",
            value=Decimal("1500")
        )
        
        formatted = metric.format_value()
        assert formatted == "1,500.00"


class TestInsight:
    """Test cases for Insight entity."""
    
    def test_insight_creation(self):
        """Test insight creation."""
        insight = Insight(
            title="Revenue Growth",
            description="Strong revenue growth observed",
            priority=InsightPriority.HIGH,
            confidence=ConfidenceLevel.HIGH,
            recommendations=["Continue strategy"],
            risks=["Market volatility"]
        )
        
        assert insight.title == "Revenue Growth"
        assert insight.priority == InsightPriority.HIGH
        assert len(insight.recommendations) == 1
        assert len(insight.risks) == 1
    
    def test_to_executive_summary(self):
        """Test executive summary generation."""
        insight = Insight(
            title="Test Insight",
            description="Test description",
            recommendations=["Rec 1", "Rec 2"],
            risks=["Risk 1"]
        )
        
        summary = insight.to_executive_summary()
        
        assert "**Test Insight**" in summary
        assert "Test description" in summary
        assert "**Raccomandazioni:**" in summary
        assert "Rec 1" in summary
        assert "**Rischi:**" in summary
        assert "Risk 1" in summary