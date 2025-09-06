"""Financial data domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class Currency(Enum):
    """Supported currencies."""
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"


class MetricType(Enum):
    """Types of financial metrics."""
    REVENUE = "revenue"
    PROFIT = "profit"
    EXPENSE = "expense"
    MARGIN = "margin"
    GROWTH_RATE = "growth_rate"
    RATIO = "ratio"


@dataclass(frozen=True)
class FinancialPeriod:
    """Represents a financial period."""
    start_date: datetime
    end_date: datetime
    period_type: str  # 'monthly', 'quarterly', 'yearly'

    def __post_init__(self):
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")

    @property
    def duration_days(self) -> int:
        """Calculate duration in days."""
        return (self.end_date - self.start_date).days

    def overlaps_with(self, other: 'FinancialPeriod') -> bool:
        """Check if this period overlaps with another."""
        return not (self.end_date <= other.start_date or self.start_date >= other.end_date)


@dataclass
class FinancialData:
    """Core financial data entity."""

    id: Optional[str] = None
    company_name: str = ""
    period: Optional[FinancialPeriod] = None
    currency: Currency = Currency.EUR
    metrics: Dict[str, Decimal] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_metric(self, name: str, value: Decimal, metric_type: MetricType) -> None:
        """Add a financial metric."""
        self.metrics[name] = value
        self.metadata[f"{name}_type"] = metric_type.value
        self.updated_at = datetime.now()

    def get_metric(self, name: str) -> Optional[Decimal]:
        """Get a metric value by name."""
        return self.metrics.get(name)

    def calculate_margin(self, revenue_key: str = "revenue", cost_key: str = "cost") -> Optional[Decimal]:
        """Calculate profit margin."""
        revenue = self.metrics.get(revenue_key)
        cost = self.metrics.get(cost_key)

        if revenue and cost and revenue != 0:
            return ((revenue - cost) / revenue) * 100
        return None

    def calculate_growth_rate(self, previous: 'FinancialData', metric_name: str) -> Optional[Decimal]:
        """Calculate growth rate compared to previous period."""
        current_value = self.metrics.get(metric_name)
        previous_value = previous.metrics.get(metric_name)

        if current_value and previous_value and previous_value != 0:
            return ((current_value - previous_value) / previous_value) * 100
        return None

    def validate(self) -> List[str]:
        """Validate financial data integrity."""
        errors = []

        if not self.company_name:
            errors.append("Company name is required")

        if not self.period:
            errors.append("Financial period is required")

        if not self.metrics:
            errors.append("At least one metric is required")

        for name, value in self.metrics.items():
            if value < 0 and name not in ['loss', 'deficit', 'debt']:
                errors.append(f"Metric '{name}' has negative value: {value}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'period': {
                'start': self.period.start_date.isoformat() if self.period else None,
                'end': self.period.end_date.isoformat() if self.period else None,
                'type': self.period.period_type if self.period else None
            },
            'currency': self.currency.value,
            'metrics': {k: str(v) for k, v in self.metrics.items()},
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
