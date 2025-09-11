# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Calcoli derivati automatici con lineage
# ============================================

"""
Enterprise Calculation Engine with automatic derivation and lineage tracking.
Computes financial ratios and derived metrics with full provenance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from typing import Any, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

class CalculationStatus(Enum):
    """Status of calculation execution."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Some inputs missing
    SKIPPED = "skipped"  # Dependencies not met

@dataclass
class InputReference:
    """Reference to input metric used in calculation."""
    metric_name: str
    value: Union[float, int]
    source_ref: str
    quality_score: Optional[float] = None

@dataclass
class CalculationLineage:
    """Complete lineage tracking for calculated metrics."""
    formula: str
    inputs: list[InputReference]
    calculation_method: str
    timestamp: datetime
    status: CalculationStatus
    confidence_score: float
    notes: list[str] = field(default_factory=list)

@dataclass
class CalculatedMetric:
    """Result of automatic calculation with full lineage."""
    metric_name: str
    value: Union[float, int]
    unit: str
    lineage: CalculationLineage
    source_ref: str  # Generated reference for calculated value

class CalculationEngine:
    """
    Enterprise calculation engine for automatic financial metric derivation.
    Supports complex formulas with dependency tracking and lineage.
    """

    def __init__(self):
        self.calculation_registry = {}
        self.dependency_graph = {}
        self._register_standard_calculations()

    def _register_standard_calculations(self):
        """Register standard financial calculations."""

        # Margin calculations
        self.register_calculation(
            name="margine_lordo",
            formula="ricavi - cogs",
            inputs=["ricavi", "cogs"],
            description="Gross margin = Revenue - Cost of Goods Sold"
        )

        self.register_calculation(
            name="margine_ebitda_percent",
            formula="(ebitda / ricavi) * 100",
            inputs=["ebitda", "ricavi"],
            description="EBITDA margin percentage"
        )

        self.register_calculation(
            name="ros_percent",
            formula="(utile_operativo / ricavi) * 100",
            inputs=["utile_operativo", "ricavi"],
            description="Return on Sales percentage"
        )

        self.register_calculation(
            name="roe_percent",
            formula="(utile_netto / patrimonio_netto) * 100",
            inputs=["utile_netto", "patrimonio_netto"],
            description="Return on Equity percentage"
        )

        # Financial position
        self.register_calculation(
            name="pfn",
            formula="debito_lordo - cassa",
            inputs=["debito_lordo", "cassa"],
            description="Net Financial Position"
        )

        self.register_calculation(
            name="pfn_ebitda_ratio",
            formula="pfn / ebitda",
            inputs=["pfn", "ebitda"],
            description="Net Debt to EBITDA ratio"
        )

        # Working capital
        self.register_calculation(
            name="ccn",
            formula="crediti_commerciali + rimanenze - debiti_commerciali",
            inputs=["crediti_commerciali", "rimanenze", "debiti_commerciali"],
            description="Net Working Capital"
        )

        # Liquidity ratios
        self.register_calculation(
            name="current_ratio",
            formula="attivo_corrente / passivo_corrente",
            inputs=["attivo_corrente", "passivo_corrente"],
            description="Current ratio for liquidity analysis"
        )

        self.register_calculation(
            name="quick_ratio",
            formula="(cassa + crediti_commerciali) / passivo_corrente",
            inputs=["cassa", "crediti_commerciali", "passivo_corrente"],
            description="Quick ratio (acid test)"
        )

        # Efficiency ratios
        self.register_calculation(
            name="rotazione_magazzino_giorni",
            formula="(rimanenze / cogs) * 365",
            inputs=["rimanenze", "cogs"],
            description="Inventory turnover in days"
        )

        self.register_calculation(
            name="dso_giorni",
            formula="(crediti_commerciali / ricavi) * 365",
            inputs=["crediti_commerciali", "ricavi"],
            description="Days Sales Outstanding"
        )

        # Coverage ratios
        self.register_calculation(
            name="interest_coverage",
            formula="ebit / oneri_finanziari",
            inputs=["ebit", "oneri_finanziari"],
            description="Interest coverage ratio"
        )

        # Advanced calculations with dependencies
        self.register_calculation(
            name="roic_percent",
            formula="(ebit * (1 - tax_rate)) / (patrimonio_netto + pfn) * 100",
            inputs=["ebit", "tax_rate", "patrimonio_netto", "pfn"],
            description="Return on Invested Capital percentage",
            dependencies=["pfn"]  # Depends on calculated PFN
        )

    def register_calculation(self, name: str, formula: str, inputs: list[str],
                           description: str = "", dependencies: list[str] = None):
        """
        Register a new calculation formula.

        Args:
            name: Metric name to calculate
            formula: Mathematical formula (Python expression)
            inputs: List of required input metric names
            description: Human-readable description
            dependencies: List of other calculated metrics this depends on
        """
        self.calculation_registry[name] = {
            'formula': formula,
            'inputs': inputs,
            'description': description,
            'dependencies': dependencies or []
        }

        # Build dependency graph
        self.dependency_graph[name] = dependencies or []

        logger.info(f"Registered calculation: {name} = {formula}")

    def calculate_metric(self, metric_name: str, available_data: dict[str, Any],
                        source_refs: dict[str, str] = None) -> Optional[CalculatedMetric]:
        """
        Calculate a specific metric if inputs are available.

        Args:
            metric_name: Name of metric to calculate
            available_data: Dictionary of available metric values
            source_refs: Dictionary mapping metric names to source references

        Returns:
            CalculatedMetric with lineage or None if cannot calculate
        """
        if metric_name not in self.calculation_registry:
            logger.warning(f"Unknown calculation: {metric_name}")
            return None

        calc_config = self.calculation_registry[metric_name]
        formula = calc_config['formula']
        required_inputs = calc_config['inputs']
        dependencies = calc_config.get('dependencies', [])

        # Check if all dependencies are satisfied first
        for dep in dependencies:
            if dep not in available_data:
                logger.info(f"Cannot calculate {metric_name}: missing dependency {dep}")
                return None

        # Check if all required inputs are available
        missing_inputs = []
        input_refs = []
        calculation_vars = {}

        for input_name in required_inputs:
            if input_name in available_data and available_data[input_name] is not None:
                value = available_data[input_name]
                calculation_vars[input_name] = value

                input_refs.append(InputReference(
                    metric_name=input_name,
                    value=value,
                    source_ref=source_refs.get(input_name, f"data[{input_name}]") if source_refs else f"data[{input_name}]"
                ))
            else:
                missing_inputs.append(input_name)

        if missing_inputs:
            logger.info(f"Cannot calculate {metric_name}: missing inputs {missing_inputs}")
            return None

        # Perform calculation
        try:
            # Safe evaluation of formula
            result = self._safe_eval(formula, calculation_vars)

            if result is None or (isinstance(result, float) and (np.isnan(result) or np.isinf(result))):
                status = CalculationStatus.FAILED
                confidence = 0.0
                notes = ["Calculation resulted in invalid value"]
                result = 0.0
            else:
                status = CalculationStatus.SUCCESS
                confidence = self._calculate_confidence(input_refs)
                notes = []

            # Generate source reference for calculated value
            source_ref = f"calculated|formula:{formula}|timestamp:{datetime.now().isoformat()}"

            # Create lineage
            lineage = CalculationLineage(
                formula=formula,
                inputs=input_refs,
                calculation_method="automatic",
                timestamp=datetime.now(),
                status=status,
                confidence_score=confidence,
                notes=notes
            )

            # Determine unit
            unit = self._infer_unit(metric_name, input_refs)

            return CalculatedMetric(
                metric_name=metric_name,
                value=result,
                unit=unit,
                lineage=lineage,
                source_ref=source_ref
            )

        except Exception as e:
            logger.error(f"Calculation failed for {metric_name}: {e}")

            lineage = CalculationLineage(
                formula=formula,
                inputs=input_refs,
                calculation_method="automatic",
                timestamp=datetime.now(),
                status=CalculationStatus.FAILED,
                confidence_score=0.0,
                notes=[f"Calculation error: {str(e)}"]
            )

            return CalculatedMetric(
                metric_name=metric_name,
                value=0.0,
                unit="unknown",
                lineage=lineage,
                source_ref=f"failed_calculation|{metric_name}|{datetime.now().isoformat()}"
            )

    def calculate_all_possible(self, available_data: dict[str, Any],
                             source_refs: dict[str, str] = None) -> list[CalculatedMetric]:
        """
        Calculate all possible metrics given available data.
        Respects dependency ordering.

        Args:
            available_data: Dictionary of available metric values
            source_refs: Dictionary mapping metric names to source references

        Returns:
            List of successfully calculated metrics
        """
        calculated_metrics = []
        enhanced_data = available_data.copy()
        enhanced_refs = source_refs.copy() if source_refs else {}

        # Get calculation order respecting dependencies
        calculation_order = self._get_calculation_order()

        for metric_name in calculation_order:
            calculated = self.calculate_metric(metric_name, enhanced_data, enhanced_refs)
            if calculated and calculated.lineage.status == CalculationStatus.SUCCESS:
                calculated_metrics.append(calculated)

                # Add calculated value to available data for subsequent calculations
                enhanced_data[metric_name] = calculated.value
                enhanced_refs[metric_name] = calculated.source_ref

                logger.info(f"Successfully calculated {metric_name} = {calculated.value}")

        return calculated_metrics

    def _get_calculation_order(self) -> list[str]:
        """
        Determine calculation order based on dependencies using topological sort.

        Returns:
            List of metric names in dependency order
        """
        # Simple topological sort for dependency resolution
        visited = set()
        temp_visited = set()
        order = []

        def visit(metric):
            if metric in temp_visited:
                raise ValueError(f"Circular dependency detected involving {metric}")
            if metric in visited:
                return

            temp_visited.add(metric)

            # Visit dependencies first
            for dep in self.dependency_graph.get(metric, []):
                if dep in self.calculation_registry:  # Only process registered calculations
                    visit(dep)

            temp_visited.remove(metric)
            visited.add(metric)
            order.append(metric)

        # Process all registered calculations
        for metric in self.calculation_registry:
            if metric not in visited:
                visit(metric)

        return order

    def _safe_eval(self, formula: str, variables: dict[str, Union[float, int]]) -> Optional[float]:
        """
        Safely evaluate mathematical formula with given variables.

        Args:
            formula: Mathematical expression
            variables: Dictionary of variable values

        Returns:
            Calculation result or None if failed
        """
        try:
            # Create safe evaluation context
            safe_dict = {
                '__builtins__': {},
                'abs': abs,
                'min': min,
                'max': max,
                'round': round
            }
            safe_dict.update(variables)

            # Evaluate formula
            result = eval(formula, safe_dict)

            # Convert to float
            if isinstance(result, (int, float)):
                return float(result)
            else:
                logger.warning(f"Formula result is not numeric: {type(result)}")
                return None

        except ZeroDivisionError:
            logger.warning(f"Division by zero in formula: {formula}")
            return None
        except Exception as e:
            logger.error(f"Formula evaluation error: {e}")
            return None

    def _calculate_confidence(self, inputs: list[InputReference]) -> float:
        """
        Calculate confidence score based on input quality.

        Args:
            inputs: List of input references with quality scores

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not inputs:
            return 0.0

        # Simple approach: average of input quality scores
        # If no quality scores available, use medium confidence
        quality_scores = [inp.quality_score for inp in inputs if inp.quality_score is not None]

        if quality_scores:
            return sum(quality_scores) / len(quality_scores)
        else:
            # Default confidence based on number of inputs (more inputs = more reliable)
            base_confidence = 0.7
            input_bonus = min(0.2, len(inputs) * 0.05)  # Up to 20% bonus
            return min(1.0, base_confidence + input_bonus)

    def _infer_unit(self, metric_name: str, inputs: list[InputReference]) -> str:
        """
        Infer appropriate unit for calculated metric.

        Args:
            metric_name: Name of calculated metric
            inputs: Input references

        Returns:
            Inferred unit string
        """
        # Rules for unit inference
        if metric_name.endswith('_percent'):
            return '%'
        elif metric_name.endswith('_giorni'):
            return 'giorni'
        elif metric_name.endswith('_ratio'):
            return 'ratio'
        elif 'margine' in metric_name.lower():
            # Inherit unit from revenue-like inputs
            for inp in inputs:
                if 'ricav' in inp.metric_name.lower():
                    return 'EUR'  # Default to EUR for Italian context
            return 'EUR'
        elif metric_name in ['ccn', 'pfn']:
            return 'EUR'
        else:
            # Try to infer from most common input unit
            return 'number'

    def get_calculation_info(self, metric_name: str) -> Optional[dict[str, Any]]:
        """Get information about a registered calculation."""
        return self.calculation_registry.get(metric_name)

    def list_calculable_metrics(self, available_data: dict[str, Any]) -> list[str]:
        """
        List all metrics that can be calculated given available data.

        Args:
            available_data: Dictionary of available metric values

        Returns:
            List of calculable metric names
        """
        calculable = []
        enhanced_data = available_data.copy()

        calculation_order = self._get_calculation_order()

        for metric_name in calculation_order:
            calc_config = self.calculation_registry[metric_name]
            required_inputs = calc_config['inputs']
            dependencies = calc_config.get('dependencies', [])

            # Check dependencies first
            deps_met = all(dep in enhanced_data for dep in dependencies)
            if not deps_met:
                continue

            # Check required inputs
            inputs_available = all(
                input_name in enhanced_data and enhanced_data[input_name] is not None
                for input_name in required_inputs
            )

            if inputs_available:
                calculable.append(metric_name)
                # Assume we would calculate this for subsequent dependency checks
                enhanced_data[metric_name] = 1.0  # Placeholder

        return calculable
