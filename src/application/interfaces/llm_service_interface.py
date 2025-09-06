"""LLM Service interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.domain.entities import AnalysisResult, FinancialData


class ILLMService(ABC):
    """Interface for Large Language Model service."""

    @abstractmethod
    def generate_analysis(
        self,
        financial_data: FinancialData,
        context: Optional[Dict[str, Any]] = None,
        analysis_type: str = "comprehensive"
    ) -> AnalysisResult:
        """Generate analysis from financial data."""
        pass

    @abstractmethod
    def generate_insights(
        self,
        data: Dict[str, Any],
        focus_areas: Optional[List[str]] = None
    ) -> List[str]:
        """Generate business insights from data."""
        pass

    @abstractmethod
    def generate_recommendations(
        self,
        analysis: AnalysisResult,
        business_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generate actionable recommendations."""
        pass

    @abstractmethod
    def answer_question(
        self,
        question: str,
        context: Dict[str, Any],
        max_tokens: int = 500
    ) -> str:
        """Answer a specific question based on context."""
        pass

    @abstractmethod
    def summarize_text(
        self,
        text: str,
        max_length: int = 500,
        style: str = "executive"
    ) -> str:
        """Summarize text in specified style."""
        pass

    @abstractmethod
    def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> str:
        """Translate text to target language."""
        pass

    @abstractmethod
    def extract_information(
        self,
        text: str,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract structured information from text."""
        pass

    @abstractmethod
    def classify_text(
        self,
        text: str,
        categories: List[str]
    ) -> Dict[str, float]:
        """Classify text into categories with confidence scores."""
        pass

    @abstractmethod
    def generate_report(
        self,
        data: Dict[str, Any],
        template: Optional[str] = None,
        format: str = "markdown"
    ) -> str:
        """Generate a formatted report."""
        pass

    @abstractmethod
    def compare_documents(
        self,
        doc1: str,
        doc2: str,
        aspects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Compare two documents."""
        pass

    @abstractmethod
    def detect_anomalies_with_explanation(
        self,
        data: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Detect and explain anomalies in data."""
        pass

    @abstractmethod
    def forecast_with_reasoning(
        self,
        historical_data: List[Dict[str, Any]],
        periods: int,
        factors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate forecast with reasoning."""
        pass

    @abstractmethod
    def validate_analysis(
        self,
        analysis: AnalysisResult,
        validation_rules: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Validate analysis results."""
        pass

    @abstractmethod
    def generate_executive_summary(
        self,
        analysis_results: List[AnalysisResult],
        key_metrics: Optional[List[str]] = None
    ) -> str:
        """Generate executive summary from multiple analyses."""
        pass

    @abstractmethod
    def identify_trends(
        self,
        time_series_data: List[Dict[str, Any]],
        confidence_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Identify trends in time series data."""
        pass
