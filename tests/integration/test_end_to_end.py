"""End-to-end integration tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd

from src.core.dependency_injection import DependencyContainer
from src.infrastructure.repositories import (
    FinancialDataRepository,
    DocumentRepository,
    AnalysisResultRepository
)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for integration tests."""
        temp_path = Path(tempfile.mkdtemp(prefix="e2e_tests_"))
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)
    
    @pytest.fixture
    def integrated_container(self, temp_workspace):
        """Create a fully integrated container with real repositories."""
        container = DependencyContainer()
        
        # Configure repositories with temp database paths
        container.register_instance(
            "IFinancialDataRepository",
            FinancialDataRepository(temp_workspace / "financial.db")
        )
        container.register_instance(
            "IDocumentRepository", 
            DocumentRepository(temp_workspace / "documents.db")
        )
        container.register_instance(
            "IAnalysisResultRepository",
            AnalysisResultRepository(temp_workspace / "analysis.db")
        )
        
        return container
    
    @pytest.fixture
    def sample_csv_file(self, temp_workspace, csv_sample_data):
        """Create a sample CSV file."""
        csv_path = temp_workspace / "sample_data.csv"
        csv_sample_data.to_csv(csv_path, index=False)
        return csv_path
    
    def test_csv_to_analysis_workflow(
        self, 
        integrated_container, 
        sample_csv_file,
        mock_csv_analyzer,
        mock_llm_service
    ):
        """Test complete workflow from CSV loading to analysis generation."""
        # Mock CSV analyzer behavior
        from src.domain.entities import FinancialData, FinancialPeriod
        from datetime import date
        from decimal import Decimal
        
        period = FinancialPeriod(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            period_type="yearly"
        )
        
        financial_data = FinancialData(
            company_name="Test Company",
            period=period,
            currency="EUR"
        )
        financial_data.add_metric("revenue", Decimal("1300000"), "revenue")
        financial_data.add_metric("profit", Decimal("250000"), "profit")
        
        mock_csv_analyzer.analyze_financial_data.return_value = financial_data
        
        # Mock LLM service behavior
        from src.domain.entities import AnalysisResult, AnalysisType, MetricResult
        
        analysis_result = AnalysisResult(
            analysis_type=AnalysisType.FINANCIAL,
            source_data_id=financial_data.id,
            summary="Strong financial performance with 13% revenue growth"
        )
        
        revenue_metric = MetricResult(
            name="revenue_growth", 
            value=Decimal("13.0"),
            unit="%",
            trend="up"
        )
        analysis_result.add_metric(revenue_metric)
        
        mock_llm_service.generate_analysis.return_value = analysis_result
        
        # Execute workflow
        # 1. Load CSV data
        df = pd.read_csv(sample_csv_file)
        assert len(df) == 3
        
        # 2. Analyze financial data
        analyzed_data = mock_csv_analyzer.analyze_financial_data(df)
        assert analyzed_data.company_name == "Test Company"
        
        # 3. Store in repository
        financial_repo = integrated_container.get("IFinancialDataRepository")
        data_id = financial_repo.save(analyzed_data)
        assert data_id is not None
        
        # 4. Generate AI analysis
        ai_analysis = mock_llm_service.generate_analysis(analyzed_data)
        assert ai_analysis.analysis_type == AnalysisType.FINANCIAL
        
        # 5. Store analysis result
        analysis_repo = integrated_container.get("IAnalysisResultRepository")
        analysis_id = analysis_repo.save(ai_analysis)
        assert analysis_id is not None
        
        # 6. Verify data can be retrieved
        retrieved_data = financial_repo.find_by_id(data_id)
        assert retrieved_data is not None
        assert retrieved_data.company_name == "Test Company"
        
        retrieved_analysis = analysis_repo.find_by_id(analysis_id)
        assert retrieved_analysis is not None
        assert "revenue growth" in retrieved_analysis.summary.lower()
    
    def test_document_indexing_and_querying_workflow(
        self, 
        integrated_container,
        temp_workspace,
        document_content_samples,
        mock_rag_engine
    ):
        """Test document indexing and querying workflow."""
        from src.domain.entities import Document, DocumentType, DocumentStatus
        
        # Create test document file
        doc_path = temp_workspace / "test_report.md"
        doc_path.write_text(document_content_samples['markdown_text'])
        
        # Create document entity
        document = Document(
            file_path=doc_path,
            document_type=DocumentType.MARKDOWN,
            content=document_content_samples['markdown_text']
        )
        
        # Mock RAG engine behavior
        mock_rag_engine.index_document.return_value = document
        mock_rag_engine.query.return_value = [
            {
                "content": "Ricavi: €325,000",
                "score": 0.95,
                "metadata": {"chunk_id": "1"}
            }
        ]
        
        # Execute workflow
        # 1. Store document in repository
        doc_repo = integrated_container.get("IDocumentRepository")
        doc_id = doc_repo.save(document)
        assert doc_id is not None
        
        # 2. Index document with RAG engine
        indexed_doc = mock_rag_engine.index_document(doc_path)
        assert indexed_doc is not None
        
        # 3. Mark as indexed and update
        document.mark_as_indexed()
        doc_repo.update(doc_id, document)
        
        # 4. Query the indexed content
        query_results = mock_rag_engine.query("ricavi mensili")
        assert len(query_results) > 0
        assert "€325,000" in query_results[0]["content"]
        
        # 5. Verify document status
        retrieved_doc = doc_repo.find_by_id(doc_id)
        assert retrieved_doc.status == DocumentStatus.INDEXED
    
    def test_multi_source_analysis_workflow(
        self,
        integrated_container,
        sample_csv_file,
        temp_workspace,
        document_content_samples,
        mock_csv_analyzer,
        mock_rag_engine,
        mock_llm_service
    ):
        """Test analysis workflow combining CSV data and documents."""
        # Setup financial data
        from src.domain.entities import FinancialData, FinancialPeriod
        from datetime import date
        from decimal import Decimal
        
        period = FinancialPeriod(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            period_type="yearly"
        )
        
        financial_data = FinancialData(
            company_name="Test Company",
            period=period,
            currency="EUR"
        )
        financial_data.add_metric("revenue", Decimal("1300000"), "revenue")
        
        mock_csv_analyzer.analyze_financial_data.return_value = financial_data
        
        # Setup document
        from src.domain.entities import Document, DocumentType
        
        doc_path = temp_workspace / "context_doc.pdf"
        doc_path.write_text(document_content_samples['pdf_text'])
        
        document = Document(
            file_path=doc_path,
            document_type=DocumentType.PDF,
            content=document_content_samples['pdf_text']
        )
        
        # Mock services
        mock_rag_engine.query_with_context.return_value = [
            {
                "content": "La società ha registrato un fatturato di €1.3M nel 2023",
                "score": 0.9
            }
        ]
        
        from src.domain.entities import AnalysisResult, AnalysisType, Insight, InsightPriority
        
        comprehensive_analysis = AnalysisResult(
            analysis_type=AnalysisType.COMPREHENSIVE,
            source_data_id=financial_data.id,
            summary="Comprehensive analysis combining quantitative and qualitative data"
        )
        
        insight = Insight(
            title="Data Alignment",
            description="CSV data aligns with document narrative",
            priority=InsightPriority.HIGH,
            recommendations=["Continue monitoring alignment"]
        )
        comprehensive_analysis.add_insight(insight)
        
        mock_llm_service.generate_analysis.return_value = comprehensive_analysis
        
        # Execute multi-source workflow
        # 1. Process CSV data
        csv_data = pd.read_csv(sample_csv_file)
        analyzed_financial = mock_csv_analyzer.analyze_financial_data(csv_data)
        
        # 2. Store financial data
        financial_repo = integrated_container.get("IFinancialDataRepository")
        financial_id = financial_repo.save(analyzed_financial)
        
        # 3. Store and index document
        doc_repo = integrated_container.get("IDocumentRepository")
        document.mark_as_indexed()
        doc_id = doc_repo.save(document)
        
        # 4. Query document with financial context
        context = {
            "revenue": str(analyzed_financial.get_metric("revenue")),
            "company": analyzed_financial.company_name
        }
        
        doc_results = mock_rag_engine.query_with_context(
            "financial performance", 
            context
        )
        
        # 5. Generate comprehensive analysis
        comprehensive = mock_llm_service.generate_analysis(
            analyzed_financial,
            context={"document_insights": doc_results}
        )
        
        # 6. Store comprehensive analysis
        analysis_repo = integrated_container.get("IAnalysisResultRepository")
        analysis_id = analysis_repo.save(comprehensive)
        
        # 7. Verify all components are stored and accessible
        assert financial_repo.find_by_id(financial_id) is not None
        assert doc_repo.find_by_id(doc_id) is not None
        assert analysis_repo.find_by_id(analysis_id) is not None
        
        # 8. Verify analysis contains multi-source insights
        retrieved_analysis = analysis_repo.find_by_id(analysis_id)
        assert retrieved_analysis.analysis_type == AnalysisType.COMPREHENSIVE
        assert len(retrieved_analysis.insights) > 0
        assert "alignment" in retrieved_analysis.insights[0].description.lower()
    
    def test_repository_health_and_recovery(self, integrated_container):
        """Test repository health checks and error recovery."""
        # Get all repositories
        financial_repo = integrated_container.get("IFinancialDataRepository")
        doc_repo = integrated_container.get("IDocumentRepository")
        analysis_repo = integrated_container.get("IAnalysisResultRepository")
        
        # Test basic operations work
        assert financial_repo.count() == 0
        assert doc_repo.count() == 0
        assert analysis_repo.count() == 0
        
        # Add some test data
        from src.domain.entities import FinancialData, Document, AnalysisResult
        
        test_financial = FinancialData(company_name="Health Test Co")
        test_doc = Document(file_path=Path("health_test.txt"))
        test_analysis = AnalysisResult(summary="Health test analysis")
        
        financial_id = financial_repo.save(test_financial)
        doc_id = doc_repo.save(test_doc)
        analysis_id = analysis_repo.save(test_analysis)
        
        # Verify data persistence
        assert financial_repo.exists(financial_id)
        assert doc_repo.exists(doc_id)
        assert analysis_repo.exists(analysis_id)
        
        # Test cleanup operations
        assert financial_repo.delete(financial_id)
        assert doc_repo.delete(doc_id) 
        assert analysis_repo.delete(analysis_id)
        
        # Verify cleanup
        assert not financial_repo.exists(financial_id)
        assert not doc_repo.exists(doc_id)
        assert not analysis_repo.exists(analysis_id)
    
    @pytest.mark.slow
    def test_performance_with_large_dataset(self, integrated_container, temp_workspace):
        """Test performance with larger datasets."""
        import time
        
        # Create large CSV dataset
        large_data = pd.DataFrame({
            'anno': list(range(2000, 2024)) * 10,  # 240 rows
            'fatturato': [1000000 + (i * 50000) for i in range(240)],
            'costi': [800000 + (i * 30000) for i in range(240)],
            'margine': [200000 + (i * 20000) for i in range(240)]
        })
        
        csv_path = temp_workspace / "large_dataset.csv"
        large_data.to_csv(csv_path, index=False)
        
        # Time the operations
        start_time = time.time()
        
        # Create multiple financial data entries
        financial_repo = integrated_container.get("IFinancialDataRepository")
        
        from src.domain.entities import FinancialData
        
        for i in range(50):  # Create 50 companies
            financial_data = FinancialData(
                company_name=f"Company_{i:03d}",
                currency="EUR"
            )
            financial_data.add_metric("revenue", 1000000 + (i * 10000), "revenue")
            financial_repo.save(financial_data)
        
        save_time = time.time() - start_time
        
        # Time retrieval operations
        start_time = time.time()
        
        # Test various queries
        all_companies = financial_repo.get_companies()
        high_revenue = financial_repo.find_by_metric_threshold("revenue", 1200000, "gte")
        
        query_time = time.time() - start_time
        
        # Verify results
        assert len(all_companies) == 50
        assert len(high_revenue) > 0
        
        # Performance assertions (adjust thresholds as needed)
        assert save_time < 10.0  # Should save 50 records in under 10 seconds
        assert query_time < 2.0   # Should query in under 2 seconds
        
        print(f"Performance metrics - Save: {save_time:.2f}s, Query: {query_time:.2f}s")