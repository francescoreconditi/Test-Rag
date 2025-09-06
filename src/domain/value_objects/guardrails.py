"""Financial guardrails and validation rules."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union
import math
from decimal import Decimal


class ValidationLevel(Enum):
    """Severity levels for validation failures."""
    ERROR = "error"      # Critical failure, blocks processing
    WARNING = "warning"  # Important issue, allow but flag
    INFO = "info"       # Minor issue, informational only


class ValidationCategory(Enum):
    """Categories of financial validations."""
    ACCOUNTING_COHERENCE = "accounting_coherence"  # Balance sheet coherence
    RANGE_CHECK = "range_check"                   # Value within expected range
    CONSISTENCY_CHECK = "consistency_check"        # Cross-metric consistency
    FORMAT_CHECK = "format_check"                 # Data format validation
    BUSINESS_LOGIC = "business_logic"             # Business rule validation


@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation check."""
    rule_name: str
    category: ValidationCategory
    level: ValidationLevel
    passed: bool
    message: str
    expected_value: Optional[Union[float, str]] = None
    actual_value: Optional[Union[float, str]] = None
    tolerance: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'rule_name': self.rule_name,
            'category': self.category.value,
            'level': self.level.value,
            'passed': self.passed,
            'message': self.message,
            'expected_value': self.expected_value,
            'actual_value': self.actual_value,
            'tolerance': self.tolerance
        }


@dataclass
class FinancialGuardrails:
    """Collection of financial validation rules."""
    
    # Tolerance settings
    balance_tolerance: float = 0.01  # 1% tolerance for balance sheet
    ratio_tolerance: float = 0.05   # 5% tolerance for calculated ratios
    
    def validate_balance_sheet_coherence(self, 
                                       attivo_totale: Optional[float], 
                                       passivo_totale: Optional[float]) -> ValidationResult:
        """Validate that total assets equals total liabilities + equity."""
        if attivo_totale is None or passivo_totale is None:
            return ValidationResult(
                rule_name="balance_sheet_coherence",
                category=ValidationCategory.ACCOUNTING_COHERENCE,
                level=ValidationLevel.INFO,
                passed=True,  # Cannot validate without data
                message="Dati insufficienti per validare coerenza bilancio",
                expected_value=None,
                actual_value=None
            )
        
        if attivo_totale == 0 and passivo_totale == 0:
            return ValidationResult(
                rule_name="balance_sheet_coherence", 
                category=ValidationCategory.ACCOUNTING_COHERENCE,
                level=ValidationLevel.WARNING,
                passed=False,
                message="Attivo e Passivo entrambi zero",
                expected_value=None,
                actual_value=0
            )
        
        # Calculate relative difference
        max_value = max(abs(attivo_totale), abs(passivo_totale))
        if max_value == 0:
            difference_pct = 0
        else:
            difference_pct = abs(attivo_totale - passivo_totale) / max_value
        
        passed = difference_pct <= self.balance_tolerance
        level = ValidationLevel.ERROR if not passed else ValidationLevel.INFO
        
        return ValidationResult(
            rule_name="balance_sheet_coherence",
            category=ValidationCategory.ACCOUNTING_COHERENCE,
            level=level,
            passed=passed,
            message=f"Attivo ({attivo_totale:,.0f}) vs Passivo ({passivo_totale:,.0f}) - Differenza: {difference_pct:.1%}",
            expected_value=attivo_totale,
            actual_value=passivo_totale,
            tolerance=self.balance_tolerance
        )
    
    def validate_pfn_coherence(self,
                             pfn: Optional[float],
                             debito_lordo: Optional[float], 
                             cassa: Optional[float]) -> ValidationResult:
        """Validate PFN = Debito Lordo - Cassa."""
        if pfn is None or debito_lordo is None or cassa is None:
            return ValidationResult(
                rule_name="pfn_coherence",
                category=ValidationCategory.ACCOUNTING_COHERENCE,
                level=ValidationLevel.INFO,
                passed=True,
                message="Dati insufficienti per validare PFN = Debito Lordo - Cassa"
            )
        
        expected_pfn = debito_lordo - cassa
        difference = abs(pfn - expected_pfn)
        
        # Use absolute tolerance for small numbers, relative for large ones
        max_value = max(abs(pfn), abs(expected_pfn), 1000)  # Min 1000 for percentage calc
        tolerance_absolute = max(1000, max_value * self.ratio_tolerance)  # Min 1k tolerance
        
        passed = difference <= tolerance_absolute
        level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
        
        return ValidationResult(
            rule_name="pfn_coherence",
            category=ValidationCategory.ACCOUNTING_COHERENCE,
            level=level,
            passed=passed,
            message=f"PFN ({pfn:,.0f}) vs Calcolata ({expected_pfn:,.0f}) - Differenza: {difference:,.0f}",
            expected_value=expected_pfn,
            actual_value=pfn,
            tolerance=tolerance_absolute
        )
    
    def validate_margine_lordo(self,
                              margine_lordo: Optional[float],
                              ricavi: Optional[float],
                              cogs: Optional[float]) -> ValidationResult:
        """Validate Margine Lordo = Ricavi - COGS."""
        if margine_lordo is None or ricavi is None or cogs is None:
            return ValidationResult(
                rule_name="margine_lordo_coherence",
                category=ValidationCategory.ACCOUNTING_COHERENCE,
                level=ValidationLevel.INFO,
                passed=True,
                message="Dati insufficienti per validare Margine Lordo = Ricavi - COGS"
            )
        
        expected_margine = ricavi - cogs
        difference = abs(margine_lordo - expected_margine)
        
        # Tolerance based on revenue
        tolerance_absolute = max(1000, abs(ricavi) * self.ratio_tolerance)
        passed = difference <= tolerance_absolute
        level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
        
        return ValidationResult(
            rule_name="margine_lordo_coherence",
            category=ValidationCategory.ACCOUNTING_COHERENCE,
            level=level,
            passed=passed,
            message=f"Margine Lordo ({margine_lordo:,.0f}) vs Calcolato ({expected_margine:,.0f})",
            expected_value=expected_margine,
            actual_value=margine_lordo,
            tolerance=tolerance_absolute
        )
    
    def validate_percentage_range(self, 
                                 value: Optional[float], 
                                 metric_name: str,
                                 min_pct: float = -100.0,
                                 max_pct: float = 100.0) -> ValidationResult:
        """Validate that percentage values are in reasonable range."""
        if value is None:
            return ValidationResult(
                rule_name=f"{metric_name}_range_check",
                category=ValidationCategory.RANGE_CHECK,
                level=ValidationLevel.INFO,
                passed=True,
                message=f"Nessun valore per {metric_name}"
            )
        
        # Convert to percentage if value seems to be in decimal form (0.15 = 15%)
        display_value = value
        if abs(value) <= 2.0:  # Likely decimal form
            display_value = value * 100
        
        passed = min_pct <= display_value <= max_pct
        level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
        
        return ValidationResult(
            rule_name=f"{metric_name}_range_check",
            category=ValidationCategory.RANGE_CHECK,
            level=level,
            passed=passed,
            message=f"{metric_name}: {display_value:.1f}% (range atteso: {min_pct}% - {max_pct}%)",
            expected_value=f"{min_pct}%-{max_pct}%",
            actual_value=f"{display_value:.1f}%"
        )
    
    def validate_positive_value(self, 
                               value: Optional[float], 
                               metric_name: str,
                               allow_zero: bool = True) -> ValidationResult:
        """Validate that certain metrics should be positive."""
        if value is None:
            return ValidationResult(
                rule_name=f"{metric_name}_positive_check",
                category=ValidationCategory.RANGE_CHECK,
                level=ValidationLevel.INFO,
                passed=True,
                message=f"Nessun valore per {metric_name}"
            )
        
        if allow_zero:
            passed = value >= 0
            condition = "≥ 0"
        else:
            passed = value > 0
            condition = "> 0"
        
        level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
        
        return ValidationResult(
            rule_name=f"{metric_name}_positive_check",
            category=ValidationCategory.RANGE_CHECK,
            level=level,
            passed=passed,
            message=f"{metric_name}: {value:,.0f} (atteso {condition})",
            expected_value=condition,
            actual_value=value
        )
    
    def validate_financial_ratios(self, financial_data: Dict[str, Optional[float]]) -> List[ValidationResult]:
        """Run comprehensive validation on financial data."""
        results = []
        
        # Balance sheet coherence
        if 'attivo_totale' in financial_data and 'passivo_totale' in financial_data:
            results.append(self.validate_balance_sheet_coherence(
                financial_data['attivo_totale'],
                financial_data['passivo_totale']
            ))
        
        # PFN coherence
        if all(k in financial_data for k in ['pfn', 'debito_lordo', 'cassa']):
            results.append(self.validate_pfn_coherence(
                financial_data['pfn'],
                financial_data['debito_lordo'], 
                financial_data['cassa']
            ))
        
        # Margine Lordo coherence
        if all(k in financial_data for k in ['margine_lordo', 'ricavi', 'cogs']):
            results.append(self.validate_margine_lordo(
                financial_data['margine_lordo'],
                financial_data['ricavi'],
                financial_data['cogs']
            ))
        
        # Range checks for percentages
        percentage_metrics = [
            ('margine_ebitda_pct', -50, 100), 
            ('ros_pct', -50, 50),
            ('roe_pct', -100, 100),
            ('crescita_ricavi_pct', -50, 200)
        ]
        
        for metric, min_val, max_val in percentage_metrics:
            if metric in financial_data:
                results.append(self.validate_percentage_range(
                    financial_data[metric], 
                    metric.replace('_pct', '').replace('_', ' ').title(),
                    min_val, 
                    max_val
                ))
        
        # Positive value checks
        positive_metrics = [
            ('ricavi', True), 
            ('patrimonio_netto', False),  # Can be negative in crisis
            ('ebitda', False)  # Can be negative
        ]
        
        for metric, allow_zero in positive_metrics:
            if metric in financial_data:
                results.append(self.validate_positive_value(
                    financial_data[metric],
                    metric.replace('_', ' ').title(),
                    allow_zero
                ))
        
        return results

    def validate_balance_sheet(self, validation_data: Dict[str, Any]) -> ValidationResult:
        """Alias for validate_balance_sheet_coherence to maintain compatibility."""
        attivo = validation_data.get('attivo_totale')
        passivo = validation_data.get('passivo_totale')
        return self.validate_balance_sheet_coherence(attivo, passivo)

    def validate_pfn_coherence_from_data(self, validation_data: Dict[str, Any]) -> ValidationResult:
        """Extract PFN data and validate coherence."""
        pfn = validation_data.get('pfn')
        debito_lordo = validation_data.get('debito_lordo')
        cassa = validation_data.get('cassa')
        return self.validate_pfn_coherence(pfn, debito_lordo, cassa)

    def validate_margin_coherence(self, validation_data: Dict[str, Any]) -> ValidationResult:
        """Extract margin data and validate coherence."""
        margine_lordo = validation_data.get('margine_lordo')
        ricavi = validation_data.get('ricavi')
        cogs = validation_data.get('cogs')
        return self.validate_margine_lordo(margine_lordo, ricavi, cogs)
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Summarize validation results."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        errors = sum(1 for r in results if r.level == ValidationLevel.ERROR)
        warnings = sum(1 for r in results if r.level == ValidationLevel.WARNING)
        
        return {
            'total_checks': total,
            'passed': passed,
            'failed': total - passed,
            'errors': errors,
            'warnings': warnings,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'overall_status': 'PASS' if errors == 0 else 'FAIL' if errors > 0 else 'WARNING'
        }