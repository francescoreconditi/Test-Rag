"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock

from src.domain.entities import FinancialData, Document, AnalysisResult, FinancialPeriod, DocumentMetadata
from src.domain.value_objects import Money, Percentage, DateRange
from src.core.dependency_injection import DependencyContainer


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp(prefix="rag_tests_"))
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_db_path(temp_dir):
    """Get a test database path."""
    return temp_dir / "test.db"


@pytest.fixture
def sample_financial_period():
    """Create a sample financial period."""
    return FinancialPeriod(
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
        period_type="yearly"
    )


@pytest.fixture
def sample_financial_data(sample_financial_period):
    """Create sample financial data."""
    data = FinancialData(
        id="test-financial-1",
        company_name="Test Company",
        period=sample_financial_period,
        currency="EUR"
    )
    
    # Add some metrics
    data.add_metric("revenue", Decimal("1000000"), "revenue")
    data.add_metric("profit", Decimal("150000"), "profit")
    data.add_metric("expenses", Decimal("850000"), "expense")
    
    return data


@pytest.fixture
def sample_document():
    """Create a sample document."""
    metadata = DocumentMetadata(
        author="Test Author",
        title="Test Document",
        language="it",
        keywords=["test", "documento"]
    )
    
    return Document(
        id="test-doc-1",
        file_path=Path("test_document.pdf"),
        content="This is test content for the document.",
        metadata=metadata
    )


@pytest.fixture
def sample_analysis_result():
    """Create a sample analysis result."""
    from src.domain.entities import MetricResult, Insight, InsightPriority, ConfidenceLevel
    
    result = AnalysisResult(
        id="test-analysis-1",
        analysis_type="financial",
        source_data_id="test-financial-1",
        summary="Test analysis summary"
    )
    
    # Add a metric
    metric = MetricResult(
        name="revenue_growth",
        value=Decimal("15.5"),
        unit="%",
        trend="up"
    )
    result.add_metric(metric)
    
    # Add an insight
    insight = Insight(
        title="Strong Revenue Growth",
        description="The company shows strong revenue growth of 15.5%",
        priority=InsightPriority.HIGH,
        confidence=ConfidenceLevel.HIGH,
        recommendations=["Continue current strategy", "Monitor market conditions"]
    )
    result.add_insight(insight)
    
    return result


@pytest.fixture
def sample_money():
    """Create sample money value object."""
    return Money(Decimal("1500.75"), "EUR")


@pytest.fixture
def sample_percentage():
    """Create sample percentage value object."""
    return Percentage(Decimal("15.5"))


@pytest.fixture
def sample_date_range():
    """Create sample date range value object."""
    return DateRange(
        start=date(2023, 1, 1),
        end=date(2023, 12, 31)
    )


@pytest.fixture
def mock_container():
    """Create a mock dependency container."""
    container = DependencyContainer()
    
    # Mock repositories
    mock_financial_repo = Mock()
    mock_document_repo = Mock()
    mock_analysis_repo = Mock()
    
    container.register_instance("IFinancialDataRepository", mock_financial_repo)
    container.register_instance("IDocumentRepository", mock_document_repo)
    container.register_instance("IAnalysisResultRepository", mock_analysis_repo)
    
    return container


@pytest.fixture
def mock_csv_analyzer():
    """Create a mock CSV analyzer."""
    analyzer = Mock()
    analyzer.load_csv.return_value = None
    analyzer.analyze_financial_data.return_value = None
    analyzer.calculate_metrics.return_value = {}
    return analyzer


@pytest.fixture
def mock_rag_engine():
    """Create a mock RAG engine."""
    engine = Mock()
    engine.index_document.return_value = None
    engine.query.return_value = []
    engine.get_index_stats.return_value = {"total_vectors": 0}
    return engine


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    service = Mock()
    service.generate_analysis.return_value = None
    service.generate_insights.return_value = []
    service.answer_question.return_value = "Test answer"
    return service


@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for tests."""
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')


@pytest.fixture
def csv_sample_data():
    """Create sample CSV data for testing."""
    import pandas as pd
    
    data = {
        'anno': [2021, 2022, 2023],
        'fatturato': [1000000, 1150000, 1300000],
        'costi': [850000, 920000, 1050000],
        'margine': [150000, 230000, 250000]
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def document_content_samples():
    """Sample document content for testing."""
    return {
        'pdf_text': """
        Analisi Finanziaria Q4 2023
        
        La società ha registrato un fatturato di €1.3M nel 2023,
        con una crescita del 13% rispetto all'anno precedente.
        
        I costi operativi sono aumentati del 14%, principalmente
        a causa dell'espansione delle attività.
        """,
        
        'markdown_text': """
        # Report Trimestrale
        
        ## Metriche Principali
        - Ricavi: €325,000
        - Margine lordo: 23%
        - Crescita YoY: +8.5%
        
        ## Raccomandazioni
        1. Ottimizzare i costi variabili
        2. Espandere il mercato europeo
        """
    }


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.slow = pytest.mark.slow