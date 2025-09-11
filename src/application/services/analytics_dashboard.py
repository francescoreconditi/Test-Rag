"""Advanced analytics dashboard service with KPIs, trends, and visualizations."""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from typing import Any, Optional

import numpy as np

# Visualization libraries (optional)
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from src.application.services.ontology_mapper import OntologyMapper
from src.domain.value_objects.guardrails import FinancialGuardrails

logger = logging.getLogger(__name__)


@dataclass
class KPIDefinition:
    """Definition of a Key Performance Indicator."""
    name: str
    description: str
    category: str
    formula: Optional[str] = None
    target_value: Optional[float] = None
    unit: str = "numeric"
    trend_direction: str = "higher_better"  # higher_better, lower_better, target_based
    industry_benchmark: Optional[float] = None


@dataclass
class AnalyticsInsight:
    """Represents an analytical insight or finding."""
    title: str
    description: str
    insight_type: str  # trend, anomaly, benchmark, correlation
    severity: str  # high, medium, low
    metrics_involved: list[str]
    confidence: float
    recommendation: Optional[str] = None
    chart_data: Optional[dict] = None


class AnalyticsDashboardService:
    """Service for generating advanced analytics dashboards and insights."""

    def __init__(self):
        """Initialize analytics dashboard service."""
        self.ontology_mapper = OntologyMapper()
        self.guardrails = FinancialGuardrails()

        # Define standard KPIs
        self.standard_kpis = self._define_standard_kpis()

        # Industry benchmarks (sample data)
        self.industry_benchmarks = {
            'margine_ebitda_pct': {'manufacturing': 12.5, 'services': 18.2, 'retail': 8.7},
            'ros_pct': {'manufacturing': 8.3, 'services': 12.1, 'retail': 5.2},
            'roe_pct': {'manufacturing': 14.2, 'services': 16.8, 'retail': 18.5},
            'dso': {'manufacturing': 52, 'services': 35, 'retail': 25},
            'rotazione_magazzino': {'manufacturing': 6.8, 'retail': 8.2, 'services': 15.0}
        }

    def generate_dashboard_data(self,
                               financial_data: dict[str, Any],
                               periods: list[dict[str, Any]] = None,
                               industry: str = "manufacturing") -> dict[str, Any]:
        """
        Generate comprehensive dashboard data.

        Args:
            financial_data: Current period financial metrics
            periods: Historical data for trend analysis
            industry: Industry for benchmarking

        Returns:
            Complete dashboard data structure
        """

        # Calculate KPIs
        kpi_data = self._calculate_kpis(financial_data, industry)

        # Generate insights
        insights = self._generate_insights(financial_data, periods, industry)

        # Create visualizations
        charts = self._create_charts(financial_data, periods) if PLOTLY_AVAILABLE else {}

        # Health score
        health_score = self._calculate_health_score(financial_data, industry)

        # Performance summary
        performance_summary = self._create_performance_summary(financial_data, periods)

        # Risk assessment
        risk_assessment = self._assess_risks(financial_data)

        return {
            'generated_at': datetime.now().isoformat(),
            'kpis': kpi_data,
            'insights': [insight.__dict__ for insight in insights],
            'charts': charts,
            'health_score': health_score,
            'performance_summary': performance_summary,
            'risk_assessment': risk_assessment,
            'data_quality': self._assess_data_quality(financial_data),
            'recommendations': self._generate_recommendations(insights)
        }

    def _define_standard_kpis(self) -> list[KPIDefinition]:
        """Define standard financial KPIs."""
        return [
            # Profitability KPIs
            KPIDefinition(
                name="Margine EBITDA %",
                description="Margine operativo lordo come percentuale dei ricavi",
                category="profitability",
                formula="(ebitda / ricavi) * 100",
                target_value=15.0,
                unit="percentage",
                trend_direction="higher_better"
            ),
            KPIDefinition(
                name="ROS %",
                description="Return on Sales - margine operativo sui ricavi",
                category="profitability",
                formula="(ebit / ricavi) * 100",
                target_value=10.0,
                unit="percentage",
                trend_direction="higher_better"
            ),
            KPIDefinition(
                name="ROE %",
                description="Return on Equity - rendimento del patrimonio",
                category="profitability",
                formula="(utile_netto / patrimonio_netto) * 100",
                target_value=15.0,
                unit="percentage",
                trend_direction="higher_better"
            ),

            # Efficiency KPIs
            KPIDefinition(
                name="DSO",
                description="Days Sales Outstanding - giorni medi di incasso",
                category="efficiency",
                formula="(crediti_commerciali / ricavi) * 365",
                target_value=45.0,
                unit="days",
                trend_direction="lower_better"
            ),
            KPIDefinition(
                name="Rotazione Magazzino",
                description="Velocità di rotazione delle scorte",
                category="efficiency",
                formula="cogs / rimanenze",
                target_value=6.0,
                unit="times",
                trend_direction="higher_better"
            ),
            KPIDefinition(
                name="Ricavi per Dipendente",
                description="Produttività per dipendente",
                category="productivity",
                formula="ricavi / dipendenti",
                target_value=150000,
                unit="currency",
                trend_direction="higher_better"
            ),

            # Growth KPIs
            KPIDefinition(
                name="Crescita Ricavi %",
                description="Crescita year-over-year dei ricavi",
                category="growth",
                target_value=10.0,
                unit="percentage",
                trend_direction="higher_better"
            ),

            # Leverage KPIs
            KPIDefinition(
                name="Leverage",
                description="Rapporto debiti/patrimonio netto",
                category="leverage",
                formula="debito_lordo / patrimonio_netto",
                target_value=1.5,
                unit="ratio",
                trend_direction="target_based"
            )
        ]

    def _calculate_kpis(self, financial_data: dict[str, Any], industry: str) -> list[dict[str, Any]]:
        """Calculate KPI values and performance against targets."""
        kpi_results = []

        for kpi in self.standard_kpis:
            result = {
                'name': kpi.name,
                'description': kpi.description,
                'category': kpi.category,
                'unit': kpi.unit,
                'trend_direction': kpi.trend_direction,
                'target_value': kpi.target_value
            }

            # Calculate actual value
            if kpi.formula:
                actual_value = self._calculate_formula_value(kpi.formula, financial_data)
            else:
                # Direct metric lookup
                metric_key = kpi.name.lower().replace(' ', '_').replace('%', '_pct')
                actual_value = financial_data.get(metric_key)

            result['actual_value'] = actual_value

            # Industry benchmark
            metric_key = kpi.name.lower().replace(' ', '_').replace('%', '_pct')
            benchmark = self.industry_benchmarks.get(metric_key, {}).get(industry)
            result['industry_benchmark'] = benchmark

            # Performance assessment
            if actual_value is not None:
                if kpi.target_value:
                    target_performance = self._assess_target_performance(
                        actual_value, kpi.target_value, kpi.trend_direction
                    )
                    result['target_performance'] = target_performance

                if benchmark:
                    benchmark_performance = self._assess_benchmark_performance(
                        actual_value, benchmark, kpi.trend_direction
                    )
                    result['benchmark_performance'] = benchmark_performance

                # Status color
                result['status'] = self._get_kpi_status(result)

            kpi_results.append(result)

        return kpi_results

    def _calculate_formula_value(self, formula: str, data: dict[str, Any]) -> Optional[float]:
        """Calculate value from formula safely."""
        try:
            # Replace metric names with values
            calc_formula = formula
            for metric, value in data.items():
                if value is not None:
                    calc_formula = calc_formula.replace(metric, str(float(value)))

            # Safe evaluation (basic math only)
            import ast
            import operator

            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.USub: operator.neg,
            }

            def eval_expr(expr):
                return eval_(ast.parse(expr, mode='eval').body)

            def eval_(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.Constant):
                    return node.value
                elif isinstance(node, ast.BinOp):
                    return ops[type(node.op)](eval_(node.left), eval_(node.right))
                elif isinstance(node, ast.UnaryOp):
                    return ops[type(node.op)](eval_(node.operand))
                else:
                    raise TypeError(f"Unsupported node type: {type(node)}")

            return eval_expr(calc_formula)

        except Exception as e:
            logger.debug(f"Error calculating formula '{formula}': {e}")
            return None

    def _assess_target_performance(self, actual: float, target: float, direction: str) -> dict[str, Any]:
        """Assess performance against target."""
        if direction == "higher_better":
            ratio = actual / target
            performance = "above" if ratio >= 1.0 else "below"
        elif direction == "lower_better":
            ratio = target / actual
            performance = "above" if ratio >= 1.0 else "below"
        else:  # target_based
            deviation = abs(actual - target) / target
            ratio = 1 - deviation
            performance = "on_target" if deviation <= 0.1 else "off_target"

        return {
            'performance': performance,
            'ratio': min(ratio, 2.0),  # Cap at 200%
            'deviation_pct': ((actual - target) / target) * 100
        }

    def _assess_benchmark_performance(self, actual: float, benchmark: float, direction: str) -> dict[str, Any]:
        """Assess performance against industry benchmark."""
        return self._assess_target_performance(actual, benchmark, direction)

    def _get_kpi_status(self, kpi_result: dict[str, Any]) -> str:
        """Determine KPI status color based on performance."""
        target_perf = kpi_result.get('target_performance', {})
        benchmark_perf = kpi_result.get('benchmark_performance', {})

        # Prioritize target performance
        if target_perf:
            perf = target_perf['performance']
            ratio = target_perf.get('ratio', 0)

            if perf == "above" and ratio >= 1.0 or perf == "on_target":
                return "green"
            elif ratio >= 0.8:
                return "yellow"
            else:
                return "red"

        # Fallback to benchmark
        elif benchmark_perf:
            perf = benchmark_perf['performance']
            ratio = benchmark_perf.get('ratio', 0)

            if perf == "above" and ratio >= 1.0:
                return "green"
            elif ratio >= 0.9:
                return "yellow"
            else:
                return "red"

        return "gray"  # No comparison available

    def _generate_insights(self,
                          financial_data: dict[str, Any],
                          periods: list[dict[str, Any]] = None,
                          industry: str = "manufacturing") -> list[AnalyticsInsight]:
        """Generate analytical insights from the data."""
        insights = []

        # Profitability insights
        insights.extend(self._analyze_profitability(financial_data, industry))

        # Efficiency insights
        insights.extend(self._analyze_efficiency(financial_data, industry))

        # Trend insights (if historical data available)
        if periods:
            insights.extend(self._analyze_trends(periods))

        # Risk insights
        insights.extend(self._analyze_risks_for_insights(financial_data))

        # Data quality insights
        insights.extend(self._analyze_data_quality_insights(financial_data))

        # Sort by confidence and severity
        insights.sort(key=lambda x: (x.severity == "high", x.confidence), reverse=True)

        return insights[:10]  # Top 10 insights

    def _analyze_profitability(self, data: dict[str, Any], industry: str) -> list[AnalyticsInsight]:
        """Analyze profitability metrics."""
        insights = []

        # EBITDA margin analysis
        ebitda_margin = self._calculate_formula_value("(ebitda / ricavi) * 100", data)
        industry_benchmark = self.industry_benchmarks.get('margine_ebitda_pct', {}).get(industry, 12.0)

        if ebitda_margin is not None:
            if ebitda_margin < industry_benchmark * 0.7:
                insights.append(AnalyticsInsight(
                    title="Margine EBITDA Sotto Benchmark",
                    description=f"Il margine EBITDA del {ebitda_margin:.1f}% è significativamente sotto il benchmark di settore ({industry_benchmark:.1f}%)",
                    insight_type="benchmark",
                    severity="high",
                    metrics_involved=['ebitda', 'ricavi'],
                    confidence=0.85,
                    recommendation="Analizzare i costi operativi e identificare aree di ottimizzazione"
                ))
            elif ebitda_margin > industry_benchmark * 1.2:
                insights.append(AnalyticsInsight(
                    title="Margine EBITDA Eccellente",
                    description=f"Il margine EBITDA del {ebitda_margin:.1f}% supera significativamente il benchmark di settore ({industry_benchmark:.1f}%)",
                    insight_type="benchmark",
                    severity="low",
                    metrics_involved=['ebitda', 'ricavi'],
                    confidence=0.90,
                    recommendation="Mantenere l'efficienza operativa attuale"
                ))

        return insights

    def _analyze_efficiency(self, data: dict[str, Any], industry: str) -> list[AnalyticsInsight]:
        """Analyze operational efficiency."""
        insights = []

        # DSO analysis
        dso = data.get('dso')
        if dso and dso > 60:
            insights.append(AnalyticsInsight(
                title="DSO Elevato",
                description=f"I giorni medi di incasso ({dso:.0f} giorni) sono elevati e potrebbero impattare il cash flow",
                insight_type="efficiency",
                severity="medium",
                metrics_involved=['dso', 'crediti_commerciali'],
                confidence=0.80,
                recommendation="Migliorare i processi di collezione crediti"
            ))

        # Inventory turnover
        inventory_turnover = data.get('rotazione_magazzino')
        if inventory_turnover and inventory_turnover < 4:
            insights.append(AnalyticsInsight(
                title="Rotazione Magazzino Lenta",
                description=f"La rotazione magazzino ({inventory_turnover:.1f}x) è bassa, indicando possibili scorte eccessive",
                insight_type="efficiency",
                severity="medium",
                metrics_involved=['rotazione_magazzino', 'rimanenze'],
                confidence=0.75,
                recommendation="Ottimizzare la gestione delle scorte e ridurre l'inventario obsoleto"
            ))

        return insights

    def _analyze_trends(self, periods: list[dict[str, Any]]) -> list[AnalyticsInsight]:
        """Analyze trends from historical data."""
        insights = []

        if len(periods) < 2:
            return insights

        # Revenue trend
        revenues = [p.get('ricavi') for p in periods[-3:] if p.get('ricavi')]
        if len(revenues) >= 2:
            growth_rates = [(revenues[i] - revenues[i-1]) / revenues[i-1] * 100
                           for i in range(1, len(revenues))]
            avg_growth = np.mean(growth_rates)

            if avg_growth < -5:
                insights.append(AnalyticsInsight(
                    title="Trend Ricavi Decrescente",
                    description=f"I ricavi mostrano un trend negativo con crescita media del {avg_growth:.1f}%",
                    insight_type="trend",
                    severity="high",
                    metrics_involved=['ricavi'],
                    confidence=0.85,
                    recommendation="Analizzare le cause del declino e implementare strategie di rilancio"
                ))
            elif avg_growth > 15:
                insights.append(AnalyticsInsight(
                    title="Crescita Ricavi Accelerata",
                    description=f"I ricavi mostrano una crescita sostenuta del {avg_growth:.1f}%",
                    insight_type="trend",
                    severity="low",
                    metrics_involved=['ricavi'],
                    confidence=0.90,
                    recommendation="Monitorare la sostenibilità della crescita"
                ))

        return insights

    def _analyze_risks_for_insights(self, data: dict[str, Any]) -> list[AnalyticsInsight]:
        """Analyze financial risks."""
        insights = []

        # Liquidity risk
        current_ratio = data.get('current_ratio')
        if current_ratio and current_ratio < 1.2:
            insights.append(AnalyticsInsight(
                title="Rischio Liquidità",
                description=f"Il rapporto di liquidità ({current_ratio:.2f}) è basso, possibile difficoltà nel pagamento debiti a breve",
                insight_type="risk",
                severity="high",
                metrics_involved=['current_ratio'],
                confidence=0.80,
                recommendation="Migliorare la gestione della liquidità"
            ))

        # Leverage risk
        leverage = data.get('leverage')
        if leverage and leverage > 3.0:
            insights.append(AnalyticsInsight(
                title="Leverage Elevato",
                description=f"Il rapporto di indebitamento ({leverage:.1f}x) è elevato",
                insight_type="risk",
                severity="medium",
                metrics_involved=['leverage', 'debito_lordo'],
                confidence=0.75,
                recommendation="Considerare la riduzione del debito o l'aumento del capitale"
            ))

        return insights

    def _analyze_data_quality_insights(self, data: dict[str, Any]) -> list[AnalyticsInsight]:
        """Analyze data quality issues."""
        insights = []

        # Missing critical metrics
        critical_metrics = ['ricavi', 'ebitda', 'utile_netto', 'attivo_totale']
        missing_metrics = [m for m in critical_metrics if data.get(m) is None]

        if missing_metrics:
            insights.append(AnalyticsInsight(
                title="Metriche Critiche Mancanti",
                description=f"Metriche critiche non disponibili: {', '.join(missing_metrics)}",
                insight_type="data_quality",
                severity="medium",
                metrics_involved=missing_metrics,
                confidence=1.0,
                recommendation="Completare l'estrazione delle metriche mancanti"
            ))

        return insights

    def _create_charts(self,
                      financial_data: dict[str, Any],
                      periods: list[dict[str, Any]] = None) -> dict[str, Any]:
        """Create visualization charts."""
        if not PLOTLY_AVAILABLE:
            return {"error": "Plotly not available for charts"}

        charts = {}

        # KPI Overview Chart
        charts['kpi_overview'] = self._create_kpi_overview_chart(financial_data)

        # Profitability Waterfall
        charts['profitability_waterfall'] = self._create_profitability_waterfall(financial_data)

        # Trend Charts (if historical data available)
        if periods:
            charts['revenue_trend'] = self._create_trend_chart(periods, 'ricavi', 'Revenue Trend')
            charts['profitability_trend'] = self._create_profitability_trend(periods)

        # Efficiency Radar Chart
        charts['efficiency_radar'] = self._create_efficiency_radar(financial_data)

        return charts

    def _create_kpi_overview_chart(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create KPI overview gauge charts."""
        kpis = self._calculate_kpis(data, "manufacturing")

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['Margine EBITDA %', 'ROS %', 'DSO', 'ROE %'],
            specs=[[{"type": "indicator"}, {"type": "indicator"}],
                   [{"type": "indicator"}, {"type": "indicator"}]]
        )

        kpi_subset = [k for k in kpis if k['name'] in ['Margine EBITDA %', 'ROS %', 'DSO', 'ROE %']][:4]

        positions = [(1,1), (1,2), (2,1), (2,2)]

        for i, kpi in enumerate(kpi_subset):
            if kpi['actual_value'] is not None:
                row, col = positions[i]

                fig.add_trace(go.Indicator(
                    mode = "gauge+number+delta",
                    value = kpi['actual_value'],
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': kpi['name']},
                    delta = {'reference': kpi.get('target_value', 0)},
                    gauge = {
                        'axis': {'range': [None, kpi.get('target_value', 100) * 1.5]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, (kpi.get('target_value', 100) * 0.7)], 'color': "lightgray"},
                            {'range': [(kpi.get('target_value', 100) * 0.7), kpi.get('target_value', 100)], 'color': "yellow"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': kpi.get('target_value', 100)
                        }
                    }
                ), row=row, col=col)

        return json.loads(fig.to_json())

    def _create_profitability_waterfall(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create profitability waterfall chart."""
        ricavi = data.get('ricavi', 0)
        cogs = data.get('cogs', 0)
        ebitda = data.get('ebitda', 0)
        ebit = data.get('ebit', 0)
        utile_netto = data.get('utile_netto', 0)

        fig = go.Figure(go.Waterfall(
            name = "Profitability",
            orientation = "v",
            measure = ["absolute", "relative", "relative", "relative", "total"],
            x = ["Ricavi", "COGS", "Altri Costi Op.", "Interessi/Tasse", "Utile Netto"],
            text = [f"€{ricavi:,.0f}", f"-€{cogs:,.0f}",
                   f"-€{(ebitda-ebit):,.0f}", f"-€{(ebit-utile_netto):,.0f}", f"€{utile_netto:,.0f}"],
            y = [ricavi, -cogs, -(ebitda-ebit) if (ebitda-ebit) > 0 else 0,
                -(ebit-utile_netto) if (ebit-utile_netto) > 0 else 0, utile_netto],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))

        fig.update_layout(title = "Waterfall Profitability Analysis")

        return json.loads(fig.to_json())

    def _create_trend_chart(self, periods: list[dict[str, Any]], metric: str, title: str) -> dict[str, Any]:
        """Create trend chart for a specific metric."""
        dates = [p.get('period', '') for p in periods if p.get(metric)]
        values = [p.get(metric) for p in periods if p.get(metric)]

        if not values:
            return {"error": f"No data for {metric}"}

        fig = go.Figure(data=go.Scatter(
            x=dates,
            y=values,
            mode='lines+markers',
            name=metric
        ))

        fig.update_layout(title=title)

        return json.loads(fig.to_json())

    def _create_profitability_trend(self, periods: list[dict[str, Any]]) -> dict[str, Any]:
        """Create profitability trend chart."""
        dates = [p.get('period', '') for p in periods]

        fig = go.Figure()

        metrics = ['ricavi', 'ebitda', 'ebit', 'utile_netto']
        colors = ['blue', 'green', 'orange', 'red']

        for metric, color in zip(metrics, colors):
            values = [p.get(metric, 0) for p in periods]
            if any(v for v in values):
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=values,
                    mode='lines+markers',
                    name=metric.replace('_', ' ').title(),
                    line={"color": color}
                ))

        fig.update_layout(title="Profitability Trend Analysis")

        return json.loads(fig.to_json())

    def _create_efficiency_radar(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create efficiency radar chart."""
        # Normalize metrics to 0-100 scale for radar
        metrics = {
            'DSO': min(100, max(0, 100 - (data.get('dso', 45) - 30) * 2)),  # Lower is better
            'Inventory Turnover': min(100, (data.get('rotazione_magazzino', 6) / 10) * 100),
            'Asset Turnover': min(100, (data.get('asset_turnover', 1.5) / 2) * 100),
            'ROA': min(100, (data.get('roa_pct', 8) / 15) * 100),
            'ROE': min(100, (data.get('roe_pct', 15) / 25) * 100)
        }

        fig = go.Figure(data=go.Scatterpolar(
            r=list(metrics.values()),
            theta=list(metrics.keys()),
            fill='toself',
            name='Current Performance'
        ))

        fig.update_layout(
            polar={
                "radialaxis": {
                    "visible": True,
                    "range": [0, 100]
                }
            },
            title="Efficiency Radar Chart"
        )

        return json.loads(fig.to_json())

    def _calculate_health_score(self, data: dict[str, Any], industry: str) -> dict[str, Any]:
        """Calculate overall financial health score."""
        kpis = self._calculate_kpis(data, industry)

        # Weight different categories
        weights = {
            'profitability': 0.4,
            'efficiency': 0.3,
            'leverage': 0.2,
            'growth': 0.1
        }

        category_scores = {}

        for kpi in kpis:
            category = kpi['category']
            status = kpi.get('status', 'gray')

            # Convert status to score
            status_score = {'green': 100, 'yellow': 70, 'red': 30, 'gray': 50}.get(status, 50)

            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(status_score)

        # Calculate weighted average
        weighted_score = 0
        total_weight = 0

        for category, weight in weights.items():
            if category in category_scores:
                category_avg = np.mean(category_scores[category])
                weighted_score += category_avg * weight
                total_weight += weight

        if total_weight > 0:
            health_score = weighted_score / total_weight
        else:
            health_score = 50  # Neutral score if no data

        # Determine health level
        if health_score >= 80:
            health_level = "Excellent"
        elif health_score >= 65:
            health_level = "Good"
        elif health_score >= 50:
            health_level = "Fair"
        else:
            health_level = "Poor"

        return {
            'score': round(health_score, 1),
            'level': health_level,
            'category_scores': {k: round(np.mean(v), 1) for k, v in category_scores.items()},
            'description': f"Overall financial health is {health_level.lower()} with a score of {health_score:.1f}/100"
        }

    def _create_performance_summary(self,
                                   current_data: dict[str, Any],
                                   periods: list[dict[str, Any]] = None) -> dict[str, Any]:
        """Create performance summary."""
        summary = {
            'key_metrics': {},
            'trends': {},
            'alerts': []
        }

        # Key metrics
        key_metrics = ['ricavi', 'ebitda', 'utile_netto', 'dipendenti']
        for metric in key_metrics:
            value = current_data.get(metric)
            if value is not None:
                summary['key_metrics'][metric] = {
                    'value': value,
                    'formatted': f"€{value:,.0f}" if metric != 'dipendenti' else f"{value:,.0f}"
                }

        # Trends (if historical data available)
        if periods and len(periods) >= 2:
            for metric in key_metrics:
                current = current_data.get(metric)
                previous = periods[-2].get(metric) if len(periods) >= 2 else None

                if current is not None and previous is not None and previous != 0:
                    growth = (current - previous) / previous * 100
                    summary['trends'][metric] = {
                        'growth_rate': round(growth, 1),
                        'direction': 'up' if growth > 0 else 'down',
                        'formatted': f"{growth:+.1f}%"
                    }

        # Alerts for significant issues
        if current_data.get('leverage', 0) > 3.0:
            summary['alerts'].append("High leverage ratio detected")

        if current_data.get('dso', 0) > 90:
            summary['alerts'].append("Very high DSO - collection issues")

        return summary

    def _assess_risks(self, data: dict[str, Any]) -> dict[str, Any]:
        """Assess various financial risks."""
        risks = {
            'liquidity_risk': 'low',
            'leverage_risk': 'low',
            'profitability_risk': 'low',
            'operational_risk': 'low',
            'overall_risk': 'low'
        }

        risk_factors = []

        # Liquidity risk
        current_ratio = data.get('current_ratio', 2.0)
        if current_ratio < 1.0:
            risks['liquidity_risk'] = 'high'
            risk_factors.append("Very low current ratio")
        elif current_ratio < 1.5:
            risks['liquidity_risk'] = 'medium'
            risk_factors.append("Low current ratio")

        # Leverage risk
        leverage = data.get('leverage', 1.0)
        if leverage > 4.0:
            risks['leverage_risk'] = 'high'
            risk_factors.append("Very high leverage")
        elif leverage > 2.5:
            risks['leverage_risk'] = 'medium'
            risk_factors.append("High leverage")

        # Profitability risk
        ebitda_margin = self._calculate_formula_value("(ebitda / ricavi) * 100", data)
        if ebitda_margin is not None:
            if ebitda_margin < 0:
                risks['profitability_risk'] = 'high'
                risk_factors.append("Negative EBITDA margin")
            elif ebitda_margin < 5:
                risks['profitability_risk'] = 'medium'
                risk_factors.append("Low EBITDA margin")

        # Operational risk
        dso = data.get('dso', 45)
        if dso > 90:
            risks['operational_risk'] = 'high'
            risk_factors.append("Very high DSO")
        elif dso > 60:
            risks['operational_risk'] = 'medium'
            risk_factors.append("High DSO")

        # Overall risk
        high_risks = sum(1 for risk in risks.values() if risk == 'high')
        medium_risks = sum(1 for risk in risks.values() if risk == 'medium')

        if high_risks > 0:
            risks['overall_risk'] = 'high'
        elif medium_risks > 1:
            risks['overall_risk'] = 'medium'

        return {
            'risks': risks,
            'risk_factors': risk_factors,
            'risk_score': high_risks * 3 + medium_risks * 1  # Simple scoring
        }

    def _assess_data_quality(self, data: dict[str, Any]) -> dict[str, Any]:
        """Assess data quality and completeness."""
        total_expected = 20  # Expected number of key metrics
        available = sum(1 for v in data.values() if v is not None)
        completeness = (available / total_expected) * 100

        quality_issues = []

        # Check for critical missing metrics
        critical_metrics = ['ricavi', 'ebitda', 'attivo_totale', 'patrimonio_netto']
        missing_critical = [m for m in critical_metrics if data.get(m) is None]

        if missing_critical:
            quality_issues.append(f"Missing critical metrics: {', '.join(missing_critical)}")

        # Check for unrealistic values
        if data.get('ricavi', 0) < 0:
            quality_issues.append("Negative revenue detected")

        leverage = data.get('leverage', 0)
        if leverage > 10:
            quality_issues.append("Extremely high leverage ratio - possible data error")

        quality_level = "excellent" if completeness >= 90 and not quality_issues else \
                       "good" if completeness >= 70 and len(quality_issues) <= 1 else \
                       "fair" if completeness >= 50 else "poor"

        return {
            'completeness_pct': round(completeness, 1),
            'available_metrics': available,
            'total_expected': total_expected,
            'quality_level': quality_level,
            'issues': quality_issues
        }

    def _generate_recommendations(self, insights: list[AnalyticsInsight]) -> list[dict[str, Any]]:
        """Generate actionable recommendations based on insights."""
        recommendations = []

        # Collect recommendations from high-severity insights
        for insight in insights:
            if insight.severity == "high" and insight.recommendation:
                recommendations.append({
                    'title': f"Address {insight.title}",
                    'description': insight.recommendation,
                    'priority': 'high',
                    'metrics_involved': insight.metrics_involved,
                    'confidence': insight.confidence
                })

        # Add general recommendations
        recommendations.append({
            'title': 'Implement Regular Monitoring',
            'description': 'Set up automated KPI monitoring with monthly reviews',
            'priority': 'medium',
            'metrics_involved': [],
            'confidence': 0.9
        })

        recommendations.append({
            'title': 'Enhance Data Collection',
            'description': 'Improve data collection processes to increase completeness and accuracy',
            'priority': 'medium',
            'metrics_involved': [],
            'confidence': 0.8
        })

        return recommendations[:5]  # Top 5 recommendations
