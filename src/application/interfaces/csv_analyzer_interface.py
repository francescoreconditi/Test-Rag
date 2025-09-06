"""CSV Analyzer interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.domain.entities import FinancialData


class ICSVAnalyzer(ABC):
    """Interface for CSV analysis service."""

    @abstractmethod
    def load_csv(self, file_path: Path, encoding: str = 'utf-8') -> pd.DataFrame:
        """Load CSV file and return DataFrame."""
        pass

    @abstractmethod
    def load_comparison_csv(self, file_path: Path, encoding: str = 'utf-8') -> pd.DataFrame:
        """Load comparison CSV file."""
        pass

    @abstractmethod
    def analyze_financial_data(self, df: pd.DataFrame) -> FinancialData:
        """Analyze financial data from DataFrame."""
        pass

    @abstractmethod
    def calculate_metrics(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Calculate financial metrics."""
        pass

    @abstractmethod
    def calculate_growth_rates(self, value_column: str, time_column: str = 'anno') -> pd.DataFrame:
        """Calculate growth rates for a value column over time."""
        pass

    @abstractmethod
    def calculate_financial_ratios(self) -> Dict[str, float]:
        """Calculate common financial ratios."""
        pass

    @abstractmethod
    def detect_anomalies(self, column: str, threshold: float = 2.0) -> pd.DataFrame:
        """Detect anomalies in a column using statistical methods."""
        pass

    @abstractmethod
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for numeric columns."""
        pass

    @abstractmethod
    def compare_datasets(self, value_column: str, comparison_column: str = None) -> Dict[str, Any]:
        """Compare main dataset with comparison dataset."""
        pass

    @abstractmethod
    def generate_insights(self) -> List[str]:
        """Generate automatic insights from the data."""
        pass

    @abstractmethod
    def export_analysis(self, output_path: Path, format: str = 'json') -> None:
        """Export analysis results to file."""
        pass

    @abstractmethod
    def get_time_series_analysis(self, value_column: str, time_column: str = 'anno') -> Dict[str, Any]:
        """Perform time series analysis on a column."""
        pass

    @abstractmethod
    def calculate_correlations(self) -> pd.DataFrame:
        """Calculate correlation matrix for numeric columns."""
        pass

    @abstractmethod
    def segment_analysis(self, segment_column: str, value_column: str) -> Dict[str, Any]:
        """Analyze data by segments."""
        pass

    @abstractmethod
    def forecast_values(self, value_column: str, periods: int = 3) -> pd.DataFrame:
        """Simple forecast using linear regression."""
        pass

    @abstractmethod
    def validate_data_quality(self) -> Dict[str, List[str]]:
        """Validate data quality and return issues."""
        pass

    @abstractmethod
    def get_parsed_values_report(self) -> Dict[str, Any]:
        """Get report of all parsed values with their provenance."""
        pass
