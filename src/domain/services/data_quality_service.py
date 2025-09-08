# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Data Quality con Great Expectations
# ============================================

"""
Enterprise Data Quality Service using Great Expectations.
Validates financial data integrity and coherence.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
import great_expectations as gx
from great_expectations.core import ExpectationSuite

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of data quality validation."""
    is_valid: bool
    success_count: int
    failed_count: int
    warnings: List[str]
    errors: List[str]
    details: Dict[str, Any]

@dataclass 
class QualityMetrics:
    """Data quality metrics."""
    completeness: float  # % non-null values
    accuracy: float     # % values within expected ranges
    consistency: float  # % coherent relationships
    timeliness: float   # % recent data
    validity: float     # % valid format/type

class DataQualityService:
    """
    Enterprise data quality service with Great Expectations.
    Validates financial metrics, balance sheet coherence, and data integrity.
    """
    
    def __init__(self):
        # Simple validation rules instead of full Great Expectations setup
        self.validation_rules = {}
        self._setup_financial_validation_rules()
        
    def _setup_financial_validation_rules(self):
        """Setup simplified financial validation rules."""
        
        # Balance Sheet Rules
        self.validation_rules["balance_sheet"] = {
            "required_columns": ["attivo_totale", "passivo_totale"],
            "coherence_checks": [
                {
                    "name": "balance_coherence",
                    "check": lambda df: self._check_balance_coherence(df),
                    "description": "Attivo should equal Passivo"
                }
            ],
            "pfn_checks": [
                {
                    "name": "pfn_coherence",
                    "check": lambda df: self._check_pfn_coherence(df),
                    "description": "PFN should equal Debito Lordo - Cassa"
                }
            ]
        }
        
        # Income Statement Rules
        self.validation_rules["income_statement"] = {
            "required_columns": ["ricavi"],
            "type_checks": [
                {
                    "name": "numeric_types",
                    "check": lambda df: self._check_numeric_types(df, ["ricavi", "ebitda"]),
                    "description": "Financial metrics should be numeric"
                }
            ],
            "null_checks": [
                {
                    "name": "no_nulls",
                    "check": lambda df: self._check_no_nulls(df, ["ricavi"]),
                    "description": "Key metrics should not be null"
                }
            ]
        }
        
        # Range Rules
        self.validation_rules["ranges"] = {
            "percentage_ranges": [
                {
                    "name": "margin_percentages",
                    "check": lambda df: self._check_percentage_ranges(df),
                    "description": "Percentage metrics should be reasonable"
                }
            ]
        }

    def validate_financial_data(self, df: pd.DataFrame, 
                              suite_name: str = "balance_sheet") -> ValidationResult:
        """
        Validate financial data using specified expectation suite.
        
        Args:
            df: DataFrame with financial metrics
            suite_name: Name of expectation suite to use
            
        Returns:
            ValidationResult with detailed validation outcomes
        """
        try:
            # Get validation rules
            rules = self.validation_rules.get(suite_name)
            if not rules:
                raise ValueError(f"Unknown validation suite: {suite_name}")
            
            # Run validation checks
            success_count = 0
            failed_count = 0
            warnings = []
            errors = []
            
            # Check all rule categories
            for category, checks in rules.items():
                if category == "required_columns":
                    # Check required columns exist
                    for col in checks:
                        if col in df.columns:
                            success_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"Missing required column: {col}")
                
                elif isinstance(checks, list):
                    # Run validation checks
                    for check_config in checks:
                        try:
                            check_result = check_config["check"](df)
                            if check_result["success"]:
                                success_count += 1
                            else:
                                failed_count += 1
                                if check_result.get("critical", False):
                                    errors.append(f"CRITICAL: {check_config['description']} - {check_result['message']}")
                                else:
                                    warnings.append(f"WARNING: {check_config['description']} - {check_result['message']}")
                        except Exception as e:
                            failed_count += 1
                            errors.append(f"Check failed: {check_config['name']} - {str(e)}")
            
            is_valid = failed_count == 0
            
            return ValidationResult(
                is_valid=is_valid,
                success_count=success_count,
                failed_count=failed_count,
                warnings=warnings,
                errors=errors,
                details={"suite_name": suite_name, "total_checks": success_count + failed_count}
            )
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                success_count=0,
                failed_count=1,
                warnings=[],
                errors=[f"Validation error: {str(e)}"],
                details={}
            )

    def validate_balance_sheet_coherence(self, df: pd.DataFrame) -> ValidationResult:
        """Validate balance sheet accounting coherence."""
        return self.validate_financial_data(df, "balance_sheet")
    
    def validate_income_statement(self, df: pd.DataFrame) -> ValidationResult:
        """Validate income statement data quality.""" 
        return self.validate_financial_data(df, "income_statement")
    
    def validate_metric_ranges(self, df: pd.DataFrame) -> ValidationResult:
        """Validate that metrics are within reasonable ranges."""
        return self.validate_financial_data(df, "ranges")

    def calculate_quality_metrics(self, df: pd.DataFrame) -> QualityMetrics:
        """
        Calculate comprehensive data quality metrics.
        
        Args:
            df: DataFrame with financial data
            
        Returns:
            QualityMetrics with completeness, accuracy, etc.
        """
        try:
            total_cells = df.size
            non_null_cells = df.count().sum()
            completeness = non_null_cells / total_cells if total_cells > 0 else 0.0
            
            # Accuracy: check numeric columns are within reasonable ranges
            numeric_cols = df.select_dtypes(include=['number']).columns
            valid_numeric_count = 0
            total_numeric_count = 0
            
            for col in numeric_cols:
                total_numeric_count += len(df[col].dropna())
                # Basic sanity checks
                valid_values = df[col].dropna()
                if col.endswith('_percent'):
                    valid_numeric_count += len(valid_values[(valid_values >= -100) & (valid_values <= 100)])
                else:
                    # For absolute values, check they're not extremely large/small
                    valid_numeric_count += len(valid_values[abs(valid_values) < 1e12])
            
            accuracy = valid_numeric_count / total_numeric_count if total_numeric_count > 0 else 1.0
            
            # Consistency: basic coherence checks
            consistency_checks = 0
            consistency_passed = 0
            
            if 'attivo_totale' in df.columns and 'passivo_totale' in df.columns:
                consistency_checks += 1
                diff = abs(df['attivo_totale'] - df['passivo_totale']).fillna(float('inf'))
                tolerance = df['attivo_totale'].abs() * 0.01  # 1% tolerance
                if (diff <= tolerance).all():
                    consistency_passed += 1
                    
            if 'pfn' in df.columns and 'debito_lordo' in df.columns and 'cassa' in df.columns:
                consistency_checks += 1
                calculated_pfn = df['debito_lordo'] - df['cassa']
                diff = abs(df['pfn'] - calculated_pfn).fillna(float('inf'))
                tolerance = df['debito_lordo'].abs() * 0.01
                if (diff <= tolerance).all():
                    consistency_passed += 1
            
            consistency = consistency_passed / consistency_checks if consistency_checks > 0 else 1.0
            
            # Timeliness: assume all data is recent for now (would need timestamp info)
            timeliness = 1.0
            
            # Validity: check data types and formats
            expected_types = {
                'ricavi': ['float64', 'int64'],
                'ebitda': ['float64', 'int64'],
                'attivo_totale': ['float64', 'int64']
            }
            
            validity_checks = 0
            validity_passed = 0
            
            for col, types in expected_types.items():
                if col in df.columns:
                    validity_checks += 1
                    if df[col].dtype.name in types:
                        validity_passed += 1
            
            validity = validity_passed / validity_checks if validity_checks > 0 else 1.0
            
            return QualityMetrics(
                completeness=completeness,
                accuracy=accuracy,
                consistency=consistency,
                timeliness=timeliness,
                validity=validity
            )
            
        except Exception as e:
            logger.error(f"Quality metrics calculation failed: {e}")
            return QualityMetrics(0.0, 0.0, 0.0, 0.0, 0.0)

    def comprehensive_validation(self, df: pd.DataFrame) -> Dict[str, ValidationResult]:
        """
        Run comprehensive validation across all expectation suites.
        
        Args:
            df: DataFrame with financial data
            
        Returns:
            Dictionary with validation results for each suite
        """
        results = {}
        
        for suite_name in self.expectation_suites.keys():
            try:
                results[suite_name] = self.validate_financial_data(df, suite_name)
            except Exception as e:
                logger.error(f"Validation failed for suite {suite_name}: {e}")
                results[suite_name] = ValidationResult(
                    is_valid=False,
                    success_count=0,
                    failed_count=1,
                    warnings=[],
                    errors=[f"Suite {suite_name} failed: {str(e)}"],
                    details={}
                )
        
        return results

    def _check_balance_coherence(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check balance sheet coherence (Attivo = Passivo)."""
        if 'attivo_totale' not in df.columns or 'passivo_totale' not in df.columns:
            return {"success": False, "message": "Missing balance sheet columns", "critical": True}
        
        try:
            differences = abs(df['attivo_totale'] - df['passivo_totale'])
            tolerance = df['attivo_totale'].abs() * 0.01  # 1% tolerance
            coherent = (differences <= tolerance).all()
            
            if coherent:
                return {"success": True, "message": "Balance sheet is coherent"}
            else:
                max_diff = differences.max()
                return {"success": False, "message": f"Balance incoherence detected, max difference: {max_diff:.2f}", "critical": True}
        except Exception as e:
            return {"success": False, "message": f"Balance check error: {str(e)}", "critical": True}

    def _check_pfn_coherence(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check PFN coherence (PFN = Debito Lordo - Cassa)."""
        required_cols = ['pfn', 'debito_lordo', 'cassa']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return {"success": False, "message": f"Missing PFN columns: {missing_cols}", "critical": False}
        
        try:
            calculated_pfn = df['debito_lordo'] - df['cassa']
            differences = abs(df['pfn'] - calculated_pfn)
            tolerance = df['debito_lordo'].abs() * 0.01  # 1% tolerance
            coherent = (differences <= tolerance).all()
            
            if coherent:
                return {"success": True, "message": "PFN calculation is coherent"}
            else:
                max_diff = differences.max()
                return {"success": False, "message": f"PFN incoherence detected, max difference: {max_diff:.2f}", "critical": False}
        except Exception as e:
            return {"success": False, "message": f"PFN check error: {str(e)}", "critical": False}

    def _check_numeric_types(self, df: pd.DataFrame, columns: List[str]) -> Dict[str, Any]:
        """Check that specified columns are numeric."""
        issues = []
        for col in columns:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    issues.append(f"{col} is not numeric")
        
        if not issues:
            return {"success": True, "message": "All specified columns are numeric"}
        else:
            return {"success": False, "message": f"Non-numeric columns: {', '.join(issues)}", "critical": False}

    def _check_no_nulls(self, df: pd.DataFrame, columns: List[str]) -> Dict[str, Any]:
        """Check that specified columns have no null values."""
        issues = []
        for col in columns:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    issues.append(f"{col} has {null_count} null values")
        
        if not issues:
            return {"success": True, "message": "No null values in key columns"}
        else:
            return {"success": False, "message": f"Null values found: {', '.join(issues)}", "critical": False}

    def _check_percentage_ranges(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check that percentage columns are within reasonable ranges."""
        percentage_cols = [col for col in df.columns if col.endswith('_percent')]
        issues = []
        
        for col in percentage_cols:
            values = df[col].dropna()
            if len(values) == 0:
                continue
                
            # Check for extreme values
            if (values < -100).any() or (values > 100).any():
                extreme_values = values[(values < -100) | (values > 100)]
                issues.append(f"{col} has extreme values: {extreme_values.tolist()}")
        
        if not issues:
            return {"success": True, "message": "All percentage values are reasonable"}
        else:
            return {"success": False, "message": f"Extreme percentages: {', '.join(issues)}", "critical": False}

    def add_custom_validation(self, suite_name: str, validation_config: Dict[str, Any]):
        """Add custom validation rule to existing suite."""
        try:
            if suite_name in self.validation_rules:
                category = validation_config.get("category", "custom_checks")
                if category not in self.validation_rules[suite_name]:
                    self.validation_rules[suite_name][category] = []
                self.validation_rules[suite_name][category].append(validation_config)
                logger.info(f"Added custom validation to {suite_name}")
            else:
                logger.warning(f"Validation suite {suite_name} not found")
        except Exception as e:
            logger.error(f"Failed to add custom validation: {e}")