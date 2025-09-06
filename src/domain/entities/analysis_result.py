"""Analysis result domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class AnalysisType(Enum):
    """Types of analysis."""
    FINANCIAL = "financial"
    TREND = "trend"
    ANOMALY = "anomaly"
    COMPARISON = "comparison"
    FORECAST = "forecast"
    SENTIMENT = "sentiment"


class ConfidenceLevel(Enum):
    """Confidence levels for analysis results."""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


class InsightPriority(Enum):
    """Priority levels for insights."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MetricResult:
    """Individual metric analysis result."""
    name: str
    value: Decimal
    unit: Optional[str] = None
    change_percentage: Optional[Decimal] = None
    trend: Optional[str] = None  # 'up', 'down', 'stable'
    benchmark_value: Optional[Decimal] = None
    is_anomaly: bool = False
    confidence: float = 1.0

    @property
    def is_positive_change(self) -> bool:
        """Check if change is positive."""
        return self.change_percentage and self.change_percentage > 0

    def format_value(self) -> str:
        """Format value with unit."""
        if self.unit:
            return f"{self.value:,.2f} {self.unit}"
        return f"{self.value:,.2f}"


@dataclass
class Insight:
    """Business insight from analysis."""
    title: str
    description: str
    priority: InsightPriority = InsightPriority.MEDIUM
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    supporting_metrics: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    def to_executive_summary(self) -> str:
        """Generate executive summary."""
        summary = f"**{self.title}**\n\n{self.description}"

        if self.recommendations:
            summary += "\n\n**Raccomandazioni:**\n"
            for rec in self.recommendations:
                summary += f"• {rec}\n"

        if self.risks:
            summary += "\n\n**Rischi:**\n"
            for risk in self.risks:
                summary += f"• {risk}\n"

        return summary


@dataclass
class AnalysisResult:
    """Complete analysis result entity."""

    id: Optional[str] = None
    analysis_type: AnalysisType = AnalysisType.FINANCIAL
    source_data_id: Optional[str] = None
    metrics: List[MetricResult] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    summary: str = ""
    visualizations: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    processing_time_seconds: Optional[float] = None
    model_used: Optional[str] = None
    confidence_score: float = 0.0

    def add_metric(self, metric: MetricResult) -> None:
        """Add a metric result."""
        self.metrics.append(metric)
        self._update_confidence_score()

    def add_insight(self, insight: Insight) -> None:
        """Add an insight."""
        self.insights.append(insight)

    def _update_confidence_score(self) -> None:
        """Update overall confidence score based on metrics."""
        if not self.metrics:
            self.confidence_score = 0.0
            return

        total_confidence = sum(m.confidence for m in self.metrics)
        self.confidence_score = total_confidence / len(self.metrics)

    def get_high_priority_insights(self) -> List[Insight]:
        """Get high priority insights."""
        return [i for i in self.insights if i.priority in [InsightPriority.HIGH, InsightPriority.CRITICAL]]

    def get_anomalies(self) -> List[MetricResult]:
        """Get detected anomalies."""
        return [m for m in self.metrics if m.is_anomaly]

    def get_metrics_by_trend(self, trend: str) -> List[MetricResult]:
        """Get metrics by trend direction."""
        return [m for m in self.metrics if m.trend == trend]

    def generate_executive_report(self) -> str:
        """Generate executive report."""
        report = f"# Rapporto di Analisi {self.analysis_type.value.title()}\n\n"
        report += f"**Data:** {self.created_at.strftime('%d/%m/%Y %H:%M')}\n"
        report += f"**Confidenza:** {self.confidence_score:.1%}\n\n"

        if self.summary:
            report += f"## Sommario\n{self.summary}\n\n"

        # Key metrics
        if self.metrics:
            report += "## Metriche Chiave\n"
            for metric in self.metrics[:5]:  # Top 5 metrics
                report += f"- **{metric.name}:** {metric.format_value()}"
                if metric.change_percentage:
                    report += f" ({metric.change_percentage:+.1f}%)"
                report += "\n"
            report += "\n"

        # High priority insights
        high_priority = self.get_high_priority_insights()
        if high_priority:
            report += "## Approfondimenti Prioritari\n"
            for insight in high_priority:
                report += insight.to_executive_summary() + "\n\n"

        # Anomalies
        anomalies = self.get_anomalies()
        if anomalies:
            report += "## Anomalie Rilevate\n"
            for anomaly in anomalies:
                report += f"- {anomaly.name}: {anomaly.format_value()}\n"

        return report

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'analysis_type': self.analysis_type.value,
            'source_data_id': self.source_data_id,
            'metrics': [
                {
                    'name': m.name,
                    'value': str(m.value),
                    'unit': m.unit,
                    'change_percentage': str(m.change_percentage) if m.change_percentage else None,
                    'trend': m.trend,
                    'is_anomaly': m.is_anomaly,
                    'confidence': m.confidence
                } for m in self.metrics
            ],
            'insights': [
                {
                    'title': i.title,
                    'description': i.description,
                    'priority': i.priority.name,
                    'confidence': i.confidence.name,
                    'recommendations': i.recommendations,
                    'risks': i.risks
                } for i in self.insights
            ],
            'summary': self.summary,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat(),
            'processing_time_seconds': self.processing_time_seconds,
            'model_used': self.model_used
        }
