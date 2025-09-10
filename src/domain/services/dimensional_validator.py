# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Validazione coerenza dimensionale metriche finanziarie
# ============================================

"""
Dimensional Coherence Validator for financial metrics.
Ensures calculations use consistent periods, perimeters, and business contexts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Severity levels for validation violations."""
    ERROR = "error"        # Must fix - calculation is wrong
    WARNING = "warning"    # Should fix - potential issue
    INFO = "info"         # Good to know - informational

class PeriodType(Enum):
    """Types of financial periods."""
    FISCAL_YEAR = "FY"
    QUARTER = "Q"
    MONTH = "M"
    YEAR_TO_DATE = "YTD"
    ROLLING_12M = "R12"

class PerimeterType(Enum):
    """Types of financial perimeters."""
    CONSOLIDATED = "consolidato"
    STANDALONE = "civilistico"
    MANAGEMENT = "gestionale"
    STATUTORY = "statutario"

@dataclass
class DimensionalContext:
    """Dimensional context for a financial metric."""
    period: str
    period_type: PeriodType
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    perimeter: PerimeterType = PerimeterType.CONSOLIDATED
    scenario: str = "actual"  # actual, budget, forecast
    currency: str = "EUR"
    entity: str = ""
    business_unit: str = ""

@dataclass
class CoherenceRule:
    """Rule for dimensional coherence validation."""
    name: str
    description: str
    affected_metrics: list[str]
    validation_function: str  # Method name to call
    severity: ValidationSeverity
    tolerance_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'affected_metrics': self.affected_metrics,
            'severity': self.severity.value,
            'tolerance_config': self.tolerance_config
        }

@dataclass
class ValidationViolation:
    """Violation of dimensional coherence."""
    rule_name: str
    severity: ValidationSeverity
    description: str
    affected_metrics: list[str]
    violation_details: dict[str, Any]
    suggested_fix: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'rule_name': self.rule_name,
            'severity': self.severity.value,
            'description': self.description,
            'affected_metrics': self.affected_metrics,
            'violation_details': self.violation_details,
            'suggested_fix': self.suggested_fix
        }

@dataclass
class ValidationResult:
    """Result of dimensional coherence validation."""
    is_valid: bool
    violations: list[ValidationViolation]
    warnings: list[ValidationViolation]
    info_messages: list[ValidationViolation]
    total_checks: int

    @property
    def has_errors(self) -> bool:
        return any(v.severity == ValidationSeverity.ERROR for v in self.violations)

    @property
    def has_warnings(self) -> bool:
        return any(v.severity == ValidationSeverity.WARNING for v in self.violations)

    def to_dict(self) -> dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'has_errors': self.has_errors,
            'has_warnings': self.has_warnings,
            'total_checks': self.total_checks,
            'violations': [v.to_dict() for v in self.violations],
            'warnings': [v.to_dict() for v in self.warnings],
            'info_messages': [v.to_dict() for v in self.info_messages]
        }

class DimensionalValidator:
    """
    Enterprise validator for dimensional coherence of financial metrics.
    Ensures calculations use consistent temporal, spatial, and business contexts.
    """

    def __init__(self):
        self.coherence_rules = self._initialize_coherence_rules()
        self.period_parser = PeriodParser()
        self.calculation_dependencies = self._initialize_calculation_dependencies()

    def _initialize_coherence_rules(self) -> list[CoherenceRule]:
        """Initialize standard coherence rules."""
        return [
            # Period coherence rules
            CoherenceRule(
                name="same_period_calculation",
                description="Calculated metrics must use inputs from the same period",
                affected_metrics=["margine_lordo", "margine_ebitda_percent", "ros_percent", "roe_percent"],
                validation_function="validate_same_period",
                severity=ValidationSeverity.ERROR
            ),

            CoherenceRule(
                name="compatible_period_aggregation",
                description="Period aggregations must be mathematically compatible",
                affected_metrics=["ricavi_ytd", "ebitda_ytd", "quarterly_totals"],
                validation_function="validate_period_compatibility",
                severity=ValidationSeverity.ERROR
            ),

            # Perimeter coherence rules
            CoherenceRule(
                name="same_perimeter_calculation",
                description="Financial ratios must use same consolidation perimeter",
                affected_metrics=["roe_percent", "roa_percent", "debt_equity_ratio"],
                validation_function="validate_same_perimeter",
                severity=ValidationSeverity.ERROR
            ),

            CoherenceRule(
                name="perimeter_consistency",
                description="Related metrics should use consistent perimeter",
                affected_metrics=["ricavi", "ebitda", "utile_netto"],
                validation_function="validate_perimeter_consistency",
                severity=ValidationSeverity.WARNING
            ),

            # Scenario coherence rules
            CoherenceRule(
                name="same_scenario_calculation",
                description="Calculations should not mix actual/budget/forecast data",
                affected_metrics=["variance_analysis", "budget_vs_actual"],
                validation_function="validate_same_scenario",
                severity=ValidationSeverity.WARNING
            ),

            # Currency coherence rules
            CoherenceRule(
                name="currency_consistency",
                description="Financial calculations must use consistent currency",
                affected_metrics=["all_financial_metrics"],
                validation_function="validate_currency_consistency",
                severity=ValidationSeverity.ERROR,
                tolerance_config={"allow_fx_converted": True}
            ),

            # Temporal alignment rules
            CoherenceRule(
                name="balance_sheet_point_in_time",
                description="Balance sheet metrics must be from same point in time",
                affected_metrics=["attivo_totale", "passivo_totale", "patrimonio_netto"],
                validation_function="validate_balance_sheet_timing",
                severity=ValidationSeverity.ERROR
            ),

            CoherenceRule(
                name="flow_vs_stock_alignment",
                description="Flow metrics (P&L) and Stock metrics (BS) must be temporally aligned",
                affected_metrics=["roe_calculation", "roa_calculation"],
                validation_function="validate_flow_stock_alignment",
                severity=ValidationSeverity.WARNING
            )
        ]

    def _initialize_calculation_dependencies(self) -> dict[str, dict[str, Any]]:
        """Initialize calculation dependencies and requirements."""
        return {
            "margine_lordo": {
                "inputs": ["ricavi", "cogs"],
                "formula": "ricavi - cogs",
                "coherence_requirements": {
                    "same_period": True,
                    "same_perimeter": True,
                    "same_scenario": True,
                    "same_currency": True
                }
            },
            "margine_ebitda_percent": {
                "inputs": ["ebitda", "ricavi"],
                "formula": "(ebitda / ricavi) * 100",
                "coherence_requirements": {
                    "same_period": True,
                    "same_perimeter": True,
                    "same_scenario": True
                }
            },
            "roe_percent": {
                "inputs": ["utile_netto", "patrimonio_netto"],
                "formula": "(utile_netto / patrimonio_netto) * 100",
                "coherence_requirements": {
                    "same_perimeter": True,
                    "period_alignment": "end_of_period",  # PN a fine periodo
                    "flow_stock_alignment": True
                }
            },
            "debt_equity_ratio": {
                "inputs": ["debito_lordo", "patrimonio_netto"],
                "formula": "debito_lordo / patrimonio_netto",
                "coherence_requirements": {
                    "same_period": True,
                    "same_perimeter": True,
                    "balance_sheet_timing": True
                }
            },
            "pfn": {
                "inputs": ["debito_lordo", "cassa"],
                "formula": "debito_lordo - cassa",
                "coherence_requirements": {
                    "same_period": True,
                    "same_perimeter": True,
                    "balance_sheet_timing": True
                }
            },
            "current_ratio": {
                "inputs": ["attivo_corrente", "passivo_corrente"],
                "formula": "attivo_corrente / passivo_corrente",
                "coherence_requirements": {
                    "same_period": True,
                    "same_perimeter": True,
                    "balance_sheet_timing": True
                }
            }
        }

    def validate_dimensional_coherence(self, facts: list[dict[str, Any]]) -> ValidationResult:
        """
        Main method to validate dimensional coherence across financial facts.

        Args:
            facts: List of financial fact dictionaries

        Returns:
            ValidationResult with violations and warnings
        """
        violations = []
        warnings = []
        info_messages = []
        total_checks = 0

        try:
            # Parse dimensional contexts for all facts
            fact_contexts = self._parse_fact_contexts(facts)

            # Group facts by calculation
            calculation_groups = self._group_facts_by_calculation(facts)

            # Run coherence rules
            for rule in self.coherence_rules:
                total_checks += 1

                try:
                    rule_violations = self._apply_rule(rule, facts, fact_contexts, calculation_groups)

                    for violation in rule_violations:
                        if violation.severity == ValidationSeverity.ERROR:
                            violations.append(violation)
                        elif violation.severity == ValidationSeverity.WARNING:
                            warnings.append(violation)
                        else:
                            info_messages.append(violation)

                except Exception as e:
                    logger.error(f"Failed to apply rule {rule.name}: {e}")
                    violations.append(ValidationViolation(
                        rule_name=rule.name,
                        severity=ValidationSeverity.ERROR,
                        description=f"Rule validation failed: {str(e)}",
                        affected_metrics=rule.affected_metrics,
                        violation_details={"error": str(e)}
                    ))

            # Determine overall validity
            is_valid = len(violations) == 0

            return ValidationResult(
                is_valid=is_valid,
                violations=violations,
                warnings=warnings,
                info_messages=info_messages,
                total_checks=total_checks
            )

        except Exception as e:
            logger.error(f"Dimensional coherence validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                violations=[ValidationViolation(
                    rule_name="validation_system",
                    severity=ValidationSeverity.ERROR,
                    description=f"Validation system error: {str(e)}",
                    affected_metrics=[],
                    violation_details={"system_error": str(e)}
                )],
                warnings=[],
                info_messages=[],
                total_checks=0
            )

    def _parse_fact_contexts(self, facts: list[dict[str, Any]]) -> dict[str, DimensionalContext]:
        """Parse dimensional context for each fact."""
        contexts = {}

        for fact in facts:
            fact_id = fact.get('id', f"{fact.get('metric_name', 'unknown')}_{fact.get('period', 'unknown')}")

            period_str = fact.get('period', '')
            period_type = self.period_parser.parse_period_type(period_str)

            perimeter_str = fact.get('perimeter', 'consolidato')
            perimeter = self._parse_perimeter(perimeter_str)

            contexts[fact_id] = DimensionalContext(
                period=period_str,
                period_type=period_type,
                perimeter=perimeter,
                scenario=fact.get('scenario', 'actual'),
                currency=fact.get('currency', 'EUR'),
                entity=fact.get('entity', ''),
                business_unit=fact.get('business_unit', '')
            )

        return contexts

    def _group_facts_by_calculation(self, facts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Group facts by the calculations they're used in."""
        groups = {}

        # Find calculated metrics and their inputs
        for calculation_name, calc_info in self.calculation_dependencies.items():
            input_metrics = calc_info["inputs"]
            related_facts = []

            for fact in facts:
                metric_name = fact.get('metric_name', '')
                if metric_name in input_metrics or metric_name == calculation_name:
                    related_facts.append(fact)

            if len(related_facts) > 1:  # Only group if we have multiple related facts
                groups[calculation_name] = related_facts

        return groups

    def _apply_rule(self, rule: CoherenceRule, facts: list[dict[str, Any]],
                   contexts: dict[str, DimensionalContext],
                   calculation_groups: dict[str, list[dict[str, Any]]]) -> list[ValidationViolation]:
        """Apply a specific coherence rule."""
        method_name = f"_{rule.validation_function}"

        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(rule, facts, contexts, calculation_groups)
        else:
            logger.warning(f"Validation method not found: {method_name}")
            return []

    def _validate_same_period(self, rule: CoherenceRule, facts: list[dict[str, Any]],
                            contexts: dict[str, DimensionalContext],
                            calculation_groups: dict[str, list[dict[str, Any]]]) -> list[ValidationViolation]:
        """Validate that related metrics use the same period."""
        violations = []

        for calc_name, calc_facts in calculation_groups.items():
            if calc_name in rule.affected_metrics:
                periods = set()
                metric_periods = {}

                for fact in calc_facts:
                    period = fact.get('period', '')
                    metric = fact.get('metric_name', '')
                    periods.add(period)
                    metric_periods[metric] = period

                if len(periods) > 1:
                    violations.append(ValidationViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        description=f"Inconsistent periods in {calc_name} calculation",
                        affected_metrics=list(metric_periods.keys()),
                        violation_details={
                            'calculation': calc_name,
                            'periods_found': list(periods),
                            'metric_periods': metric_periods
                        },
                        suggested_fix=f"Use same period for all inputs in {calc_name} calculation"
                    ))

        return violations

    def _validate_period_compatibility(self, rule: CoherenceRule, facts: list[dict[str, Any]],
                                     contexts: dict[str, DimensionalContext],
                                     calculation_groups: dict[str, list[dict[str, Any]]]) -> list[ValidationViolation]:
        """Validate that periods are mathematically compatible."""
        violations = []

        for fact in facts:
            metric_name = fact.get('metric_name', '')
            period = fact.get('period', '')

            # Check for incompatible period aggregations
            if 'ytd' in metric_name.lower() and not period.startswith('YTD'):
                violations.append(ValidationViolation(
                    rule_name=rule.name,
                    severity=ValidationSeverity.WARNING,
                    description=f"YTD metric {metric_name} should have YTD period, found {period}",
                    affected_metrics=[metric_name],
                    violation_details={
                        'metric': metric_name,
                        'expected_period_type': 'YTD',
                        'actual_period': period
                    }
                ))

        return violations

    def _validate_same_perimeter(self, rule: CoherenceRule, facts: list[dict[str, Any]],
                               contexts: dict[str, DimensionalContext],
                               calculation_groups: dict[str, list[dict[str, Any]]]) -> list[ValidationViolation]:
        """Validate that related metrics use the same perimeter."""
        violations = []

        for calc_name, calc_facts in calculation_groups.items():
            if calc_name in rule.affected_metrics:
                perimeters = set()
                metric_perimeters = {}

                for fact in calc_facts:
                    perimeter = fact.get('perimeter', 'consolidato')
                    metric = fact.get('metric_name', '')
                    perimeters.add(perimeter)
                    metric_perimeters[metric] = perimeter

                if len(perimeters) > 1:
                    violations.append(ValidationViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        description=f"Inconsistent perimeters in {calc_name} calculation",
                        affected_metrics=list(metric_perimeters.keys()),
                        violation_details={
                            'calculation': calc_name,
                            'perimeters_found': list(perimeters),
                            'metric_perimeters': metric_perimeters
                        },
                        suggested_fix=f"Use same perimeter for all inputs in {calc_name} calculation"
                    ))

        return violations

    def _validate_same_scenario(self, rule: CoherenceRule, facts: list[dict[str, Any]],
                              contexts: dict[str, DimensionalContext],
                              calculation_groups: dict[str, list[dict[str, Any]]]) -> list[ValidationViolation]:
        """Validate that calculations don't mix scenarios (actual/budget/forecast)."""
        violations = []

        for calc_name, calc_facts in calculation_groups.items():
            scenarios = set()
            metric_scenarios = {}

            for fact in calc_facts:
                scenario = fact.get('scenario', 'actual')
                metric = fact.get('metric_name', '')
                scenarios.add(scenario)
                metric_scenarios[metric] = scenario

            if len(scenarios) > 1:
                violations.append(ValidationViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    description=f"Mixed scenarios in {calc_name} calculation",
                    affected_metrics=list(metric_scenarios.keys()),
                    violation_details={
                        'calculation': calc_name,
                        'scenarios_found': list(scenarios),
                        'metric_scenarios': metric_scenarios
                    },
                    suggested_fix=f"Use consistent scenario (actual/budget/forecast) for {calc_name}"
                ))

        return violations

    def _validate_currency_consistency(self, rule: CoherenceRule, facts: list[dict[str, Any]],
                                     contexts: dict[str, DimensionalContext],
                                     calculation_groups: dict[str, list[dict[str, Any]]]) -> list[ValidationViolation]:
        """Validate currency consistency in calculations."""
        violations = []

        for calc_name, calc_facts in calculation_groups.items():
            currencies = set()
            metric_currencies = {}

            for fact in calc_facts:
                currency = fact.get('currency', 'EUR')
                metric = fact.get('metric_name', '')
                currencies.add(currency)
                metric_currencies[metric] = currency

            if len(currencies) > 1:
                # Check if FX conversion is allowed
                allow_fx = rule.tolerance_config.get("allow_fx_converted", False)

                if not allow_fx:
                    violations.append(ValidationViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        description=f"Currency mismatch in {calc_name} calculation",
                        affected_metrics=list(metric_currencies.keys()),
                        violation_details={
                            'calculation': calc_name,
                            'currencies_found': list(currencies),
                            'metric_currencies': metric_currencies
                        },
                        suggested_fix=f"Convert all metrics to same currency for {calc_name}"
                    ))

        return violations

    def _validate_balance_sheet_timing(self, rule: CoherenceRule, facts: list[dict[str, Any]],
                                     contexts: dict[str, DimensionalContext],
                                     calculation_groups: dict[str, list[dict[str, Any]]]) -> list[ValidationViolation]:
        """Validate that balance sheet metrics are from same point in time."""
        violations = []

        balance_sheet_metrics = ["attivo_totale", "passivo_totale", "patrimonio_netto", "debito_lordo", "cassa"]
        bs_facts = [f for f in facts if f.get('metric_name') in balance_sheet_metrics]

        if len(bs_facts) > 1:
            periods = {f.get('period', '') for f in bs_facts}

            if len(periods) > 1:
                # Check if periods represent same point in time
                compatible_periods = self._check_balance_sheet_period_compatibility(list(periods))

                if not compatible_periods:
                    metric_periods = {f.get('metric_name', ''): f.get('period', '') for f in bs_facts}
                    violations.append(ValidationViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        description="Balance sheet metrics from different time points",
                        affected_metrics=list(metric_periods.keys()),
                        violation_details={
                            'periods_found': list(periods),
                            'metric_periods': metric_periods
                        },
                        suggested_fix="Use balance sheet metrics from same reporting date"
                    ))

        return violations

    def _validate_flow_stock_alignment(self, rule: CoherenceRule, facts: list[dict[str, Any]],
                                     contexts: dict[str, DimensionalContext],
                                     calculation_groups: dict[str, list[dict[str, Any]]]) -> list[ValidationViolation]:
        """Validate alignment between flow (P&L) and stock (Balance Sheet) metrics."""
        violations = []

        # ROE calculation: utile_netto (flow) vs patrimonio_netto (stock)
        if "roe_calculation" in calculation_groups:
            roe_facts = calculation_groups["roe_calculation"]

            flow_facts = [f for f in roe_facts if f.get('metric_name') in ['utile_netto', 'ricavi', 'ebitda']]
            stock_facts = [f for f in roe_facts if f.get('metric_name') in ['patrimonio_netto', 'attivo_totale']]

            if flow_facts and stock_facts:
                flow_periods = [f.get('period', '') for f in flow_facts]
                stock_periods = [f.get('period', '') for f in stock_facts]

                # Flow should be for period, stock should be end-of-period
                alignment_issues = self._check_flow_stock_period_alignment(flow_periods, stock_periods)

                if alignment_issues:
                    violations.append(ValidationViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        description="Flow and stock metrics not properly aligned",
                        affected_metrics=[f.get('metric_name', '') for f in roe_facts],
                        violation_details=alignment_issues,
                        suggested_fix="Use period-end balance sheet values with period flow metrics"
                    ))

        return violations

    def _parse_perimeter(self, perimeter_str: str) -> PerimeterType:
        """Parse perimeter string to enum."""
        perimeter_lower = perimeter_str.lower()

        if 'consolidato' in perimeter_lower or 'consolidated' in perimeter_lower:
            return PerimeterType.CONSOLIDATED
        elif 'civilistico' in perimeter_lower or 'standalone' in perimeter_lower:
            return PerimeterType.STANDALONE
        elif 'gestionale' in perimeter_lower or 'management' in perimeter_lower:
            return PerimeterType.MANAGEMENT
        elif 'statutario' in perimeter_lower or 'statutory' in perimeter_lower:
            return PerimeterType.STATUTORY
        else:
            return PerimeterType.CONSOLIDATED  # Default

    def _check_balance_sheet_period_compatibility(self, periods: list[str]) -> bool:
        """Check if balance sheet periods represent compatible time points."""
        # Simplified logic - in practice would be more sophisticated
        # All periods should end at same date
        normalized_periods = [self.period_parser.normalize_period_end(p) for p in periods]
        return len(set(normalized_periods)) <= 1

    def _check_flow_stock_period_alignment(self, flow_periods: list[str], stock_periods: list[str]) -> dict[str, Any]:
        """Check alignment between flow and stock periods."""
        issues = {}

        # Simplified check - flow should be period, stock should be end-of-period
        for flow_period in flow_periods:
            expected_stock_period = self.period_parser.get_period_end(flow_period)

            if expected_stock_period not in stock_periods:
                issues['misaligned_periods'] = {
                    'flow_period': flow_period,
                    'expected_stock_period': expected_stock_period,
                    'actual_stock_periods': stock_periods
                }

        return issues

    def get_rule_info(self, rule_name: str) -> Optional[dict[str, Any]]:
        """Get information about a specific rule."""
        for rule in self.coherence_rules:
            if rule.name == rule_name:
                return rule.to_dict()
        return None

    def list_available_rules(self) -> list[dict[str, Any]]:
        """List all available coherence rules."""
        return [rule.to_dict() for rule in self.coherence_rules]


class PeriodParser:
    """Helper class for parsing and normalizing financial periods."""

    def parse_period_type(self, period_str: str) -> PeriodType:
        """Parse period string to determine type."""
        period_lower = period_str.lower()

        if period_lower.startswith('fy') or 'esercizio' in period_lower:
            return PeriodType.FISCAL_YEAR
        elif period_lower.startswith('q') or 'trimestre' in period_lower:
            return PeriodType.QUARTER
        elif period_lower.startswith('m') or 'mese' in period_lower:
            return PeriodType.MONTH
        elif 'ytd' in period_lower:
            return PeriodType.YEAR_TO_DATE
        elif 'r12' in period_lower or 'rolling' in period_lower:
            return PeriodType.ROLLING_12M
        else:
            return PeriodType.FISCAL_YEAR  # Default

    def normalize_period_end(self, period_str: str) -> str:
        """Normalize period to its end date for comparison."""
        # Simplified implementation
        if 'fy2024' in period_str.lower():
            return "2024-12-31"
        elif 'q1_2024' in period_str.lower():
            return "2024-03-31"
        elif 'q2_2024' in period_str.lower():
            return "2024-06-30"
        # ... more period mappings
        return period_str

    def get_period_end(self, period_str: str) -> str:
        """Get the end-of-period representation for a flow period."""
        # Convert flow period to corresponding stock period
        return self.normalize_period_end(period_str)
