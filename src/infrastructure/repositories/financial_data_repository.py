"""Financial data repository implementation."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.application.interfaces.repository_interfaces import IFinancialDataRepository
from src.domain.entities import FinancialData, FinancialPeriod
from src.domain.value_objects import DateRange

from .base_repository import BaseRepository


class FinancialDataRepository(BaseRepository, IFinancialDataRepository):
    """SQLite implementation of financial data repository."""

    def __init__(self, db_path: Path = Path("data/repositories/financial.db")):
        """Initialize financial data repository."""
        super().__init__(db_path, "financial_data", FinancialData)
        self._create_additional_indexes()

    def _create_additional_indexes(self):
        """Create additional indexes specific to financial data."""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            # Add company index
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_financial_data_company
                ON financial_data (id)
            """)
            conn.commit()

    def find_by_company(self, company_name: str) -> List[FinancialData]:
        """Find financial data by company name."""
        return self.find_by_criteria({'company_name': company_name})

    def find_by_period(self, date_range: DateRange) -> List[FinancialData]:
        """Find financial data within a date range."""
        all_data = self.find_all(limit=10000)  # Get all data

        results = []
        for data in all_data:
            if data.period:
                # Check if period overlaps with date range
                period_start = data.period.start_date
                period_end = data.period.end_date

                if date_range.contains(period_start) or date_range.contains(period_end):
                    results.append(data)
                elif period_start <= date_range.start and period_end >= date_range.end:
                    # Period contains the entire date range
                    results.append(data)

        return results

    def find_by_company_and_period(
        self,
        company_name: str,
        date_range: DateRange
    ) -> List[FinancialData]:
        """Find financial data by company and period."""
        company_data = self.find_by_company(company_name)

        results = []
        for data in company_data:
            if data.period:
                period_start = data.period.start_date
                period_end = data.period.end_date

                if date_range.contains(period_start) or date_range.contains(period_end) or period_start <= date_range.start and period_end >= date_range.end:
                    results.append(data)

        return results

    def get_latest_by_company(self, company_name: str) -> Optional[FinancialData]:
        """Get the latest financial data for a company."""
        company_data = self.find_by_company(company_name)

        if not company_data:
            return None

        # Sort by period end date
        sorted_data = sorted(
            company_data,
            key=lambda x: x.period.end_date if x.period else datetime.min.date(),
            reverse=True
        )

        return sorted_data[0] if sorted_data else None

    def get_companies(self) -> List[str]:
        """Get list of all companies."""
        all_data = self.find_all(limit=10000)
        companies = set(data.company_name for data in all_data if data.company_name)
        return sorted(list(companies))

    def find_by_metric_threshold(
        self,
        metric_name: str,
        threshold: float,
        operator: str = "gte"
    ) -> List[FinancialData]:
        """Find financial data by metric threshold."""
        from decimal import Decimal

        all_data = self.find_all(limit=10000)
        results = []

        threshold_decimal = Decimal(str(threshold))

        for data in all_data:
            metric_value = data.get_metric(metric_name)

            if metric_value is not None:
                if operator == "gte" and metric_value >= threshold_decimal or operator == "lte" and metric_value <= threshold_decimal or operator == "gt" and metric_value > threshold_decimal or operator == "lt" and metric_value < threshold_decimal or operator == "eq" and metric_value == threshold_decimal:
                    results.append(data)

        return results

    def aggregate_by_period(
        self,
        company_name: str,
        aggregation_period: str
    ) -> List[FinancialData]:
        """Aggregate financial data by period."""
        from collections import defaultdict

        company_data = self.find_by_company(company_name)

        if not company_data:
            return []

        # Group data by aggregation period
        grouped_data = defaultdict(list)

        for data in company_data:
            if not data.period:
                continue

            if aggregation_period == 'yearly':
                key = data.period.start_date.year
            elif aggregation_period == 'quarterly':
                quarter = (data.period.start_date.month - 1) // 3 + 1
                key = (data.period.start_date.year, quarter)
            elif aggregation_period == 'monthly':
                key = (data.period.start_date.year, data.period.start_date.month)
            else:
                continue

            grouped_data[key].append(data)

        # Aggregate each group
        aggregated = []

        for period_key, data_list in grouped_data.items():
            if not data_list:
                continue

            # Create aggregated financial data
            first_data = data_list[0]

            # Determine period for aggregated data
            if aggregation_period == 'yearly':
                year = period_key
                period = FinancialPeriod(
                    start_date=datetime(year, 1, 1),
                    end_date=datetime(year, 12, 31),
                    period_type='yearly'
                )
            elif aggregation_period == 'quarterly':
                year, quarter = period_key
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                period = FinancialPeriod(
                    start_date=datetime(year, start_month, 1),
                    end_date=datetime(year, end_month, 28),  # Simplified
                    period_type='quarterly'
                )
            else:  # monthly
                year, month = period_key
                period = FinancialPeriod(
                    start_date=datetime(year, month, 1),
                    end_date=datetime(year, month, 28),  # Simplified
                    period_type='monthly'
                )

            # Aggregate metrics
            aggregated_metrics = {}
            metric_names = set()

            for data in data_list:
                metric_names.update(data.metrics.keys())

            for metric_name in metric_names:
                values = [
                    data.metrics[metric_name]
                    for data in data_list
                    if metric_name in data.metrics
                ]

                if values:
                    # Sum for most metrics
                    aggregated_metrics[metric_name] = sum(values)

            aggregated_data = FinancialData(
                company_name=company_name,
                period=period,
                currency=first_data.currency,
                metrics=aggregated_metrics,
                metadata={'aggregation': aggregation_period}
            )

            aggregated.append(aggregated_data)

        return sorted(aggregated, key=lambda x: x.period.start_date if x.period else datetime.min)
