"""Calculation engine with formula tracking and lineage management."""

import ast
from dataclasses import dataclass
from enum import Enum
import logging
import operator
from typing import Any, Optional, Union

from src.application.services.ontology_mapper import OntologyMapper
from src.domain.value_objects.source_reference import ProvenancedValue, SourceReference

logger = logging.getLogger(__name__)


class CalculationType(Enum):
    """Types of calculations supported."""
    DERIVED = "derived"  # Simple arithmetic
    RATIO = "ratio"  # Division-based ratios
    PERCENTAGE = "percentage"  # Percentage calculations
    GROWTH = "growth"  # YoY, QoQ growth rates
    AGGREGATION = "aggregation"  # Sum, average, etc.
    CUSTOM = "custom"  # User-defined formulas


@dataclass
class CalculationDefinition:
    """Definition of a calculation formula."""
    name: str
    formula: str  # e.g., "pfn = debito_lordo - cassa"
    calculation_type: CalculationType
    required_inputs: list[str]  # Required metric names
    unit: str  # Output unit
    description: Optional[str] = None
    validation_rules: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'formula': self.formula,
            'type': self.calculation_type.value,
            'required_inputs': self.required_inputs,
            'unit': self.unit,
            'description': self.description
        }


@dataclass
class CalculationResult:
    """Result of a calculation with full lineage."""
    value: Union[float, int]
    formula_applied: str
    calculation_type: CalculationType
    input_values: list[ProvenancedValue]
    confidence: float
    provenance: ProvenancedValue
    warnings: Optional[list[str]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'value': self.value,
            'formula': self.formula_applied,
            'type': self.calculation_type.value,
            'confidence': self.confidence,
            'input_count': len(self.input_values),
            'warnings': self.warnings,
            'lineage': self.provenance.get_lineage()
        }


class CalculationEngine:
    """Engine for performing calculations with formula tracking."""

    def __init__(self, ontology_mapper: Optional[OntologyMapper] = None):
        """
        Initialize calculation engine.

        Args:
            ontology_mapper: Mapper for metric name normalization
        """
        self.ontology_mapper = ontology_mapper or OntologyMapper()
        self.calculations = self._load_standard_calculations()

        # Safe operators for formula evaluation
        self.safe_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

    def _load_standard_calculations(self) -> dict[str, CalculationDefinition]:
        """Load standard financial calculations."""
        calculations = {
            'pfn': CalculationDefinition(
                name='Posizione Finanziaria Netta',
                formula='debito_lordo - cassa',
                calculation_type=CalculationType.DERIVED,
                required_inputs=['debito_lordo', 'cassa'],
                unit='currency',
                description='Net Financial Position',
                validation_rules={'non_negative': False}  # Can be negative
            ),

            'margine_lordo': CalculationDefinition(
                name='Margine Lordo',
                formula='ricavi - cogs',
                calculation_type=CalculationType.DERIVED,
                required_inputs=['ricavi', 'cogs'],
                unit='currency',
                description='Gross Margin'
            ),

            'capitale_circolante_netto': CalculationDefinition(
                name='Capitale Circolante Netto',
                formula='crediti_commerciali + rimanenze - debiti_commerciali',
                calculation_type=CalculationType.DERIVED,
                required_inputs=['crediti_commerciali', 'rimanenze', 'debiti_commerciali'],
                unit='currency',
                description='Net Working Capital'
            ),

            'free_cash_flow': CalculationDefinition(
                name='Free Cash Flow',
                formula='flussi_operativi - flussi_investimenti',
                calculation_type=CalculationType.DERIVED,
                required_inputs=['flussi_operativi', 'flussi_investimenti'],
                unit='currency',
                description='Free Cash Flow'
            ),

            'margine_ebitda_pct': CalculationDefinition(
                name='Margine EBITDA %',
                formula='(ebitda / ricavi) * 100',
                calculation_type=CalculationType.PERCENTAGE,
                required_inputs=['ebitda', 'ricavi'],
                unit='percentage',
                description='EBITDA Margin',
                validation_rules={'range': (0, 100)}
            ),

            'ros_pct': CalculationDefinition(
                name='ROS %',
                formula='(ebit / ricavi) * 100',
                calculation_type=CalculationType.PERCENTAGE,
                required_inputs=['ebit', 'ricavi'],
                unit='percentage',
                description='Return on Sales'
            ),

            'roe_pct': CalculationDefinition(
                name='ROE %',
                formula='(utile_netto / patrimonio_netto) * 100',
                calculation_type=CalculationType.PERCENTAGE,
                required_inputs=['utile_netto', 'patrimonio_netto'],
                unit='percentage',
                description='Return on Equity'
            ),

            'roa_pct': CalculationDefinition(
                name='ROA %',
                formula='(utile_netto / attivo_totale) * 100',
                calculation_type=CalculationType.PERCENTAGE,
                required_inputs=['utile_netto', 'attivo_totale'],
                unit='percentage',
                description='Return on Assets'
            ),

            'leverage': CalculationDefinition(
                name='Leverage',
                formula='debito_lordo / patrimonio_netto',
                calculation_type=CalculationType.RATIO,
                required_inputs=['debito_lordo', 'patrimonio_netto'],
                unit='ratio',
                description='Debt to Equity Ratio'
            ),

            'pfn_ebitda': CalculationDefinition(
                name='PFN/EBITDA',
                formula='pfn / ebitda',
                calculation_type=CalculationType.RATIO,
                required_inputs=['pfn', 'ebitda'],
                unit='ratio',
                description='Net Debt to EBITDA Ratio'
            ),

            'ricavi_per_dipendente': CalculationDefinition(
                name='Ricavi per Dipendente',
                formula='ricavi / dipendenti',
                calculation_type=CalculationType.RATIO,
                required_inputs=['ricavi', 'dipendenti'],
                unit='currency',
                description='Revenue per Employee'
            )
        }

        return calculations

    def calculate(self,
                  metric_name: str,
                  available_values: dict[str, ProvenancedValue],
                  period: Optional[str] = None,
                  entity: Optional[str] = None) -> Optional[CalculationResult]:
        """
        Calculate a derived metric from available values.

        Args:
            metric_name: Name of the metric to calculate
            available_values: Dictionary of available ProvenancedValues by metric name
            period: Period filter for input values
            entity: Entity filter for input values

        Returns:
            CalculationResult with full lineage or None if calculation not possible
        """
        # Normalize metric name
        mapped = self.ontology_mapper.map_metric(metric_name)
        canonical_name = mapped[0] if mapped else metric_name  # tuple: (key, name, confidence)

        # Find calculation definition
        calc_def = self.calculations.get(canonical_name)
        if not calc_def:
            logger.warning(f"No calculation definition for metric: {canonical_name}")
            return None

        # Check if we have all required inputs
        input_values = []
        missing_inputs = []

        for required_input in calc_def.required_inputs:
            # Check if it's directly available
            if required_input in available_values:
                value = available_values[required_input]

                # Apply filters if specified
                if period and value.period != period:
                    missing_inputs.append(f"{required_input}[period={period}]")
                    continue
                if entity and value.entity != entity:
                    missing_inputs.append(f"{required_input}[entity={entity}]")
                    continue

                input_values.append(value)
            else:
                # Try recursive calculation
                recursive_result = self.calculate(
                    required_input,
                    available_values,
                    period,
                    entity
                )

                if recursive_result:
                    input_values.append(recursive_result.provenance)
                else:
                    missing_inputs.append(required_input)

        if missing_inputs:
            logger.info(f"Cannot calculate {canonical_name}: missing {missing_inputs}")
            return None

        # Perform calculation
        try:
            result_value = self._evaluate_formula(calc_def.formula, input_values)

            # Validate result
            warnings = self._validate_result(result_value, calc_def)

            # Calculate confidence based on input confidences
            confidence = self._calculate_confidence(input_values)

            # Create source reference for calculated value
            source_ref = SourceReference(
                file_path="calculated",
                extraction_method="calculation_engine",
                confidence_score=confidence
            )

            # Create provenance
            provenance = ProvenancedValue(
                value=result_value,
                source_ref=source_ref,
                metric_name=canonical_name,
                unit=calc_def.unit,
                period=period,
                entity=entity,
                is_calculated=True,
                calculation_formula=calc_def.formula,
                calculated_from=input_values,
                calculation_confidence=confidence
            )

            return CalculationResult(
                value=result_value,
                formula_applied=calc_def.formula,
                calculation_type=calc_def.calculation_type,
                input_values=input_values,
                confidence=confidence,
                provenance=provenance,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Calculation failed for {canonical_name}: {e}")
            return None

    def _evaluate_formula(self, formula: str, input_values: list[ProvenancedValue]) -> float:
        """Safely evaluate a formula with input values."""
        # Create variable mapping
        var_map = {}
        for value in input_values:
            if value.metric_name:
                var_map[value.metric_name] = float(value.value)

        # Parse formula
        try:
            # Replace metric names with values
            eval_formula = formula
            for var_name, var_value in var_map.items():
                eval_formula = eval_formula.replace(var_name, str(var_value))

            # Safely evaluate using AST
            return self._safe_eval(eval_formula)

        except Exception as e:
            raise ValueError(f"Formula evaluation failed: {e}")

    def _safe_eval(self, expression: str) -> float:
        """Safely evaluate mathematical expression using AST."""
        try:
            # Parse expression to AST
            node = ast.parse(expression, mode='eval')

            # Evaluate AST
            return self._eval_node(node.body)

        except Exception as e:
            raise ValueError(f"Safe evaluation failed: {e}")

    def _eval_node(self, node):
        """Recursively evaluate AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):  # For Python < 3.8
            return node.n
        elif isinstance(node, ast.BinOp):
            operator_func = self.safe_operators.get(type(node.op))
            if operator_func:
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                return operator_func(left, right)
            else:
                raise ValueError(f"Unsupported operator: {type(node.op)}")
        elif isinstance(node, ast.UnaryOp):
            operator_func = self.safe_operators.get(type(node.op))
            if operator_func:
                operand = self._eval_node(node.operand)
                return operator_func(operand)
            else:
                raise ValueError(f"Unsupported unary operator: {type(node.op)}")
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")

    def _validate_result(self, value: float, calc_def: CalculationDefinition) -> Optional[list[str]]:
        """Validate calculation result against rules."""
        warnings = []

        if not calc_def.validation_rules:
            return None

        # Check range
        if 'range' in calc_def.validation_rules:
            min_val, max_val = calc_def.validation_rules['range']
            if value < min_val or value > max_val:
                warnings.append(f"Value {value} outside expected range [{min_val}, {max_val}]")

        # Check non-negative
        if calc_def.validation_rules.get('non_negative', True) and value < 0:
            warnings.append(f"Unexpected negative value: {value}")

        return warnings if warnings else None

    def _calculate_confidence(self, input_values: list[ProvenancedValue]) -> float:
        """Calculate confidence score based on input confidences."""
        if not input_values:
            return 0.0

        confidences = []
        for value in input_values:
            if value.source_ref and value.source_ref.confidence_score:
                confidences.append(value.source_ref.confidence_score)
            elif hasattr(value, 'calculation_confidence') and value.calculation_confidence:
                confidences.append(value.calculation_confidence)
            else:
                confidences.append(0.8)  # Default confidence

        # Return minimum confidence (weakest link)
        return min(confidences)

    def add_custom_calculation(self, calculation: CalculationDefinition):
        """Add a custom calculation definition."""
        mapped = self.ontology_mapper.map_metric(calculation.name)
        canonical_name = mapped[0] if mapped else calculation.name  # tuple: (key, name, confidence)
        self.calculations[canonical_name] = calculation
        logger.info(f"Added custom calculation: {canonical_name}")

    def get_available_calculations(self, available_metrics: list[str]) -> list[str]:
        """Get list of calculations possible with available metrics."""
        available_set = set(available_metrics)
        possible_calculations = []

        for calc_name, calc_def in self.calculations.items():
            required_set = set(calc_def.required_inputs)
            if required_set.issubset(available_set):
                possible_calculations.append(calc_name)

        return possible_calculations

    def calculate_growth(self,
                        metric_name: str,
                        current_value: ProvenancedValue,
                        previous_value: ProvenancedValue,
                        growth_type: str = 'yoy') -> Optional[CalculationResult]:
        """
        Calculate growth rate between two periods.

        Args:
            metric_name: Name of the metric
            current_value: Current period value
            previous_value: Previous period value
            growth_type: Type of growth ('yoy', 'qoq', 'mom')

        Returns:
            CalculationResult with growth percentage
        """
        if previous_value.value == 0:
            logger.warning(f"Cannot calculate growth for {metric_name}: previous value is zero")
            return None

        try:
            growth_rate = ((current_value.value - previous_value.value) / previous_value.value) * 100

            formula = f"(({current_value.value} - {previous_value.value}) / {previous_value.value}) * 100"

            # Create source reference
            source_ref = SourceReference(
                file_path="calculated",
                extraction_method=f"growth_calculation_{growth_type}",
                confidence_score=min(
                    current_value.source_ref.confidence_score or 0.8,
                    previous_value.source_ref.confidence_score or 0.8
                )
            )

            # Create provenance
            provenance = ProvenancedValue(
                value=growth_rate,
                source_ref=source_ref,
                metric_name=f"{metric_name}_growth_{growth_type}",
                unit='percentage',
                period=current_value.period,
                entity=current_value.entity,
                is_calculated=True,
                calculation_formula=formula,
                calculated_from=[current_value, previous_value],
                calculation_confidence=source_ref.confidence_score
            )

            return CalculationResult(
                value=growth_rate,
                formula_applied=formula,
                calculation_type=CalculationType.GROWTH,
                input_values=[current_value, previous_value],
                confidence=source_ref.confidence_score,
                provenance=provenance
            )

        except Exception as e:
            logger.error(f"Growth calculation failed: {e}")
            return None

    def calculate_aggregation(self,
                            metric_name: str,
                            values: list[ProvenancedValue],
                            aggregation_type: str = 'sum') -> Optional[CalculationResult]:
        """
        Calculate aggregation of multiple values.

        Args:
            metric_name: Name of the output metric
            values: List of values to aggregate
            aggregation_type: Type of aggregation ('sum', 'avg', 'min', 'max')

        Returns:
            CalculationResult with aggregated value
        """
        if not values:
            return None

        try:
            if aggregation_type == 'sum':
                result = sum(v.value for v in values)
                formula = f"sum({[v.value for v in values]})"
            elif aggregation_type == 'avg':
                result = sum(v.value for v in values) / len(values)
                formula = f"avg({[v.value for v in values]})"
            elif aggregation_type == 'min':
                result = min(v.value for v in values)
                formula = f"min({[v.value for v in values]})"
            elif aggregation_type == 'max':
                result = max(v.value for v in values)
                formula = f"max({[v.value for v in values]})"
            else:
                raise ValueError(f"Unknown aggregation type: {aggregation_type}")

            # Calculate confidence
            confidence = min(v.source_ref.confidence_score or 0.8 for v in values)

            # Create source reference
            source_ref = SourceReference(
                file_path="calculated",
                extraction_method=f"aggregation_{aggregation_type}",
                confidence_score=confidence
            )

            # Create provenance
            provenance = ProvenancedValue(
                value=result,
                source_ref=source_ref,
                metric_name=f"{metric_name}_{aggregation_type}",
                unit=values[0].unit if values else None,
                period=values[0].period if values else None,
                entity=values[0].entity if values else None,
                is_calculated=True,
                calculation_formula=formula,
                calculated_from=values,
                calculation_confidence=confidence
            )

            return CalculationResult(
                value=result,
                formula_applied=formula,
                calculation_type=CalculationType.AGGREGATION,
                input_values=values,
                confidence=confidence,
                provenance=provenance
            )

        except Exception as e:
            logger.error(f"Aggregation calculation failed: {e}")
            return None
