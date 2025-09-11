"""LLM Service interface."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from src.domain.entities import AnalysisResult, FinancialData


class ILLMService(ABC):
    """Interface for Large Language Model service."""

    @abstractmethod
    def generate_analysis(
        self,
        financial_data: FinancialData,
        context: Optional[dict[str, Any]] = None,
        analysis_type: str = "comprehensive"
    ) -> AnalysisResult:
        """Generate analysis from financial data."""
        pass

    @abstractmethod
    def generate_insights(
        self,
        data: dict[str, Any],
        focus_areas: Optional[list[str]] = None
    ) -> list[str]:
        """Generate business insights from data."""
        pass

    @abstractmethod
    def generate_recommendations(
        self,
        analysis: AnalysisResult,
        business_context: Optional[dict[str, Any]] = None
    ) -> list[str]:
        """Generate actionable recommendations."""
        pass

    @abstractmethod
    def answer_question(
        self,
        question: str,
        context: dict[str, Any],
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
        schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract structured information from text."""
        pass

    @abstractmethod
    def classify_text(
        self,
        text: str,
        categories: list[str]
    ) -> dict[str, float]:
        """Classify text into categories with confidence scores."""
        pass

    @abstractmethod
    def generate_report(
        self,
        data: dict[str, Any],
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
        aspects: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Compare two documents."""
        pass

    @abstractmethod
    def detect_anomalies_with_explanation(
        self,
        data: list[dict[str, Any]],
        context: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Detect and explain anomalies in data."""
        pass

    @abstractmethod
    def forecast_with_reasoning(
        self,
        historical_data: list[dict[str, Any]],
        periods: int,
        factors: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Generate forecast with reasoning."""
        pass

    @abstractmethod
    def validate_analysis(
        self,
        analysis: AnalysisResult,
        validation_rules: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Validate analysis results."""
        pass

    @abstractmethod
    def generate_executive_summary(
        self,
        analysis_results: list[AnalysisResult],
        key_metrics: Optional[list[str]] = None
    ) -> str:
        """Generate executive summary from multiple analyses."""
        pass

    @abstractmethod
    def identify_trends(
        self,
        time_series_data: list[dict[str, Any]],
        confidence_threshold: float = 0.7
    ) -> list[dict[str, Any]]:
        """Identify trends in time series data."""
        pass
