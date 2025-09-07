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
    PERIMETER_CHECK = "perimeter_check"           # Perimeter consistency validation
    PERIOD_CHECK = "period_check"                 # Period consistency validation
    DOMAIN_VALIDATION = "domain_validation"       # Domain-specific validations


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
            condition = ">= 0"
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

    # ============================================================================
    # ADVANCED VALIDATIONS - Range Constraints
    # ============================================================================
    
    def validate_ar_ap_metrics(self, financial_data: Dict[str, Optional[float]]) -> List[ValidationResult]:
        """Validate AR/AP domain-specific metrics."""
        results = []
        
        # DSO range check (typical 30-90 days)
        if 'dso' in financial_data and financial_data['dso'] is not None:
            dso = financial_data['dso']
            passed = 15 <= dso <= 180  # Reasonable range for DSO
            level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
            
            results.append(ValidationResult(
                rule_name="dso_range_check",
                category=ValidationCategory.RANGE_CHECK,
                level=level,
                passed=passed,
                message=f"DSO: {dso:.0f} giorni (range atteso: 15-180 giorni)",
                expected_value="15-180 giorni",
                actual_value=f"{dso:.0f} giorni"
            ))
        
        # DPO range check (typical 30-60 days)
        if 'dpo' in financial_data and financial_data['dpo'] is not None:
            dpo = financial_data['dpo']
            passed = 15 <= dpo <= 120
            level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
            
            results.append(ValidationResult(
                rule_name="dpo_range_check",
                category=ValidationCategory.RANGE_CHECK,
                level=level,
                passed=passed,
                message=f"DPO: {dpo:.0f} giorni (range atteso: 15-120 giorni)",
                expected_value="15-120 giorni",
                actual_value=f"{dpo:.0f} giorni"
            ))
        
        return results
    
    def validate_sales_metrics(self, financial_data: Dict[str, Optional[float]]) -> List[ValidationResult]:
        """Validate sales domain metrics."""
        results = []
        
        # Churn rate should be reasonable (0-50%)
        if 'tasso_churn_pct' in financial_data and financial_data['tasso_churn_pct'] is not None:
            churn = financial_data['tasso_churn_pct']
            passed = 0 <= churn <= 50
            level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
            
            results.append(ValidationResult(
                rule_name="churn_rate_range_check",
                category=ValidationCategory.RANGE_CHECK,
                level=level,
                passed=passed,
                message=f"Tasso Churn: {churn:.1f}% (range atteso: 0-50%)",
                expected_value="0-50%",
                actual_value=f"{churn:.1f}%"
            ))
        
        # Conversion rate should be reasonable (0.1-50%)
        if 'conversion_rate_pct' in financial_data and financial_data['conversion_rate_pct'] is not None:
            conversion = financial_data['conversion_rate_pct']
            passed = 0.1 <= conversion <= 50
            level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
            
            results.append(ValidationResult(
                rule_name="conversion_rate_range_check", 
                category=ValidationCategory.RANGE_CHECK,
                level=level,
                passed=passed,
                message=f"Tasso Conversione: {conversion:.1f}% (range atteso: 0.1-50%)",
                expected_value="0.1-50%",
                actual_value=f"{conversion:.1f}%"
            ))
        
        return results
    
    def validate_inventory_metrics(self, financial_data: Dict[str, Optional[float]]) -> List[ValidationResult]:
        """Validate inventory domain metrics."""
        results = []
        
        # Inventory turnover should be positive and reasonable (0.5-50x per year)
        if 'rotazione_magazzino' in financial_data and financial_data['rotazione_magazzino'] is not None:
            turnover = financial_data['rotazione_magazzino']
            passed = 0.5 <= turnover <= 50
            level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
            
            results.append(ValidationResult(
                rule_name="inventory_turnover_range_check",
                category=ValidationCategory.RANGE_CHECK,
                level=level,
                passed=passed,
                message=f"Rotazione Magazzino: {turnover:.1f}x (range atteso: 0.5-50x)",
                expected_value="0.5-50x",
                actual_value=f"{turnover:.1f}x"
            ))
        
        # Days in inventory (7-730 days reasonable)
        if 'giorni_magazzino' in financial_data and financial_data['giorni_magazzino'] is not None:
            days = financial_data['giorni_magazzino']
            passed = 7 <= days <= 730
            level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
            
            results.append(ValidationResult(
                rule_name="inventory_days_range_check",
                category=ValidationCategory.RANGE_CHECK,
                level=level,
                passed=passed,
                message=f"Giorni Magazzino: {days:.0f} giorni (range atteso: 7-730 giorni)",
                expected_value="7-730 giorni",
                actual_value=f"{days:.0f} giorni"
            ))
        
        return results
    
    def validate_hr_metrics(self, financial_data: Dict[str, Optional[float]]) -> List[ValidationResult]:
        """Validate HR domain metrics."""
        results = []
        
        # Employee turnover should be reasonable (0-100%)
        if 'turnover_personale_pct' in financial_data and financial_data['turnover_personale_pct'] is not None:
            turnover = financial_data['turnover_personale_pct']
            passed = 0 <= turnover <= 100
            level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
            
            results.append(ValidationResult(
                rule_name="employee_turnover_range_check",
                category=ValidationCategory.RANGE_CHECK,
                level=level,
                passed=passed,
                message=f"Turnover Personale: {turnover:.1f}% (range atteso: 0-100%)",
                expected_value="0-100%",
                actual_value=f"{turnover:.1f}%"
            ))
        
        # Absenteeism rate should be reasonable (0-30%)
        if 'assenteismo_pct' in financial_data and financial_data['assenteismo_pct'] is not None:
            absenteeism = financial_data['assenteismo_pct']
            passed = 0 <= absenteeism <= 30
            level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
            
            results.append(ValidationResult(
                rule_name="absenteeism_rate_range_check",
                category=ValidationCategory.RANGE_CHECK,
                level=level,
                passed=passed,
                message=f"Tasso Assenteismo: {absenteeism:.1f}% (range atteso: 0-30%)",
                expected_value="0-30%",
                actual_value=f"{absenteeism:.1f}%"
            ))
        
        return results

    # ============================================================================
    # PERIMETER AND PERIOD CONSISTENCY VALIDATIONS
    # ============================================================================
    
    def validate_perimeter_consistency(self, 
                                     perimeter_data: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Validate consistency across different perimeters (Consolidated/Standalone)."""
        results = []
        
        if len(perimeter_data) < 2:
            return results
        
        # Group by period to compare perimeters
        period_groups = {}
        for data in perimeter_data:
            period = data.get('period', 'unknown')
            perimeter = data.get('perimeter', 'unknown')
            
            if period not in period_groups:
                period_groups[period] = {}
            period_groups[period][perimeter] = data
        
        # Check consolidated >= standalone for key metrics
        for period, perimeters in period_groups.items():
            if 'Consolidated' in perimeters and 'Standalone' in perimeters:
                cons_data = perimeters['Consolidated']
                stand_data = perimeters['Standalone']
                
                # Revenue should be Consolidated >= Standalone
                cons_revenue = cons_data.get('ricavi')
                stand_revenue = stand_data.get('ricavi')
                
                if cons_revenue is not None and stand_revenue is not None:
                    passed = cons_revenue >= stand_revenue * 0.95  # Small tolerance for rounding
                    level = ValidationLevel.ERROR if not passed else ValidationLevel.INFO
                    
                    results.append(ValidationResult(
                        rule_name="perimeter_revenue_consistency",
                        category=ValidationCategory.PERIMETER_CHECK,
                        level=level,
                        passed=passed,
                        message=f"Ricavi {period}: Consolidato ({cons_revenue:,.0f}) vs Standalone ({stand_revenue:,.0f})",
                        expected_value=f">= {stand_revenue:,.0f}",
                        actual_value=cons_revenue
                    ))
        
        return results
    
    def validate_period_consistency(self, 
                                  period_data: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Validate consistency across different periods."""
        results = []
        
        if len(period_data) < 2:
            return results
        
        # Sort by period for chronological comparison
        sorted_data = sorted(period_data, key=lambda x: x.get('period', ''))
        
        # Check for reasonable growth rates YoY
        for i in range(1, len(sorted_data)):
            prev_data = sorted_data[i-1]
            curr_data = sorted_data[i]
            
            prev_period = prev_data.get('period', 'unknown')
            curr_period = curr_data.get('period', 'unknown')
            
            # Revenue growth rate check
            prev_revenue = prev_data.get('ricavi')
            curr_revenue = curr_data.get('ricavi')
            
            if prev_revenue is not None and curr_revenue is not None and prev_revenue != 0:
                growth_rate = (curr_revenue - prev_revenue) / abs(prev_revenue) * 100
                
                # Reasonable growth rate: -50% to +200%
                passed = -50 <= growth_rate <= 200
                level = ValidationLevel.WARNING if not passed else ValidationLevel.INFO
                
                results.append(ValidationResult(
                    rule_name="period_revenue_growth_check",
                    category=ValidationCategory.PERIOD_CHECK,
                    level=level,
                    passed=passed,
                    message=f"Crescita Ricavi {prev_period} -> {curr_period}: {growth_rate:.1f}% (range atteso: -50% / +200%)",
                    expected_value="-50% / +200%",
                    actual_value=f"{growth_rate:.1f}%"
                ))
        
        return results
    
    # ============================================================================
    # COMPREHENSIVE VALIDATION ENGINE
    # ============================================================================
    
    def validate_comprehensive(self, 
                             financial_data: Dict[str, Optional[float]], 
                             perimeter_data: Optional[List[Dict[str, Any]]] = None,
                             period_data: Optional[List[Dict[str, Any]]] = None) -> List[ValidationResult]:
        """Run comprehensive validation including advanced checks."""
        results = []
        
        # Standard validations
        results.extend(self.validate_financial_ratios(financial_data))
        
        # Domain-specific validations
        results.extend(self.validate_ar_ap_metrics(financial_data))
        results.extend(self.validate_sales_metrics(financial_data))
        results.extend(self.validate_inventory_metrics(financial_data))
        results.extend(self.validate_hr_metrics(financial_data))
        
        # Perimeter consistency
        if perimeter_data:
            results.extend(self.validate_perimeter_consistency(perimeter_data))
        
        # Period consistency
        if period_data:
            results.extend(self.validate_period_consistency(period_data))
        
        return results
    
    def get_advanced_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Enhanced summary including category breakdown."""
        base_summary = self.get_validation_summary(results)
        
        # Category breakdown
        categories = {}
        for result in results:
            cat = result.category.value
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0, 'errors': 0, 'warnings': 0}
            
            categories[cat]['total'] += 1
            if result.passed:
                categories[cat]['passed'] += 1
            if result.level == ValidationLevel.ERROR:
                categories[cat]['errors'] += 1
            elif result.level == ValidationLevel.WARNING:
                categories[cat]['warnings'] += 1
        
        # Calculate pass rates per category
        for cat_data in categories.values():
            total = cat_data['total']
            cat_data['pass_rate'] = (cat_data['passed'] / total * 100) if total > 0 else 0
        
        base_summary['categories'] = categories
        base_summary['validation_scope'] = list(categories.keys())
        
        return base_summary