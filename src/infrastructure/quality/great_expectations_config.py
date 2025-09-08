"""Great Expectations configuration for data quality validation."""

import great_expectations as gx
from great_expectations.checkpoint import Checkpoint
from great_expectations.core.batch import BatchRequest
from great_expectations.core.expectation_configuration import ExpectationConfiguration
from great_expectations.core.expectation_suite import ExpectationSuite
from typing import Dict, List, Any, Optional
import pandas as pd
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """Data quality validation using Great Expectations."""
    
    def __init__(self, data_dir: str = "data/great_expectations"):
        """Initialize Great Expectations context."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize context
        self.context = gx.get_context()
        
        # Create expectation suites
        self._create_expectation_suites()
        
        logger.info("Great Expectations validator initialized")
    
    def _create_expectation_suites(self):
        """Create expectation suites for different data types."""
        
        # Financial Metrics Suite
        self._create_financial_metrics_suite()
        
        # Balance Sheet Suite
        self._create_balance_sheet_suite()
        
        # Income Statement Suite
        self._create_income_statement_suite()
        
        # Data Completeness Suite
        self._create_completeness_suite()
    
    def _create_financial_metrics_suite(self):
        """Create expectations for financial metrics."""
        
        suite_name = "financial_metrics_suite"
        
        try:
            suite = self.context.get_expectation_suite(suite_name)
        except:
            suite = self.context.add_expectation_suite(suite_name)
        
        # Revenue expectations
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_not_be_null",
                kwargs={"column": "ricavi"}
            )
        )
        
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_between",
                kwargs={
                    "column": "ricavi",
                    "min_value": 0,
                    "max_value": 1e12,  # 1 trillion max
                    "mostly": 0.99  # Allow 1% outliers
                }
            )
        )
        
        # EBITDA Margin expectations
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_between",
                kwargs={
                    "column": "margine_ebitda_pct",
                    "min_value": -50,
                    "max_value": 50,
                    "mostly": 0.95
                }
            )
        )
        
        # Debt ratios
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_between",
                kwargs={
                    "column": "leverage_ratio",
                    "min_value": 0,
                    "max_value": 10,
                    "mostly": 0.95
                }
            )
        )
        
        # DSO expectations
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_between",
                kwargs={
                    "column": "dso",
                    "min_value": 0,
                    "max_value": 365,
                    "mostly": 0.99
                }
            )
        )
        
        self.context.save_expectation_suite(suite)
        logger.info(f"Created suite: {suite_name}")
    
    def _create_balance_sheet_suite(self):
        """Create expectations for balance sheet validation."""
        
        suite_name = "balance_sheet_suite"
        
        try:
            suite = self.context.get_expectation_suite(suite_name)
        except:
            suite = self.context.add_expectation_suite(suite_name)
        
        # Assets = Liabilities + Equity
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_pair_values_A_to_be_greater_than_B",
                kwargs={
                    "column_A": "attivo_totale",
                    "column_B": "passivo_totale",
                    "or_equal": True,
                    "mostly": 0.99
                }
            )
        )
        
        # Working capital coherence
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_not_be_null",
                kwargs={"column": "capitale_circolante_netto"}
            )
        )
        
        # Equity should be positive (mostly)
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_between",
                kwargs={
                    "column": "patrimonio_netto",
                    "min_value": 0,
                    "max_value": None,
                    "mostly": 0.95
                }
            )
        )
        
        # Cash should be non-negative
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_between",
                kwargs={
                    "column": "cassa",
                    "min_value": 0,
                    "max_value": None
                }
            )
        )
        
        self.context.save_expectation_suite(suite)
        logger.info(f"Created suite: {suite_name}")
    
    def _create_income_statement_suite(self):
        """Create expectations for income statement validation."""
        
        suite_name = "income_statement_suite"
        
        try:
            suite = self.context.get_expectation_suite(suite_name)
        except:
            suite = self.context.add_expectation_suite(suite_name)
        
        # Gross margin = Revenue - COGS
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_not_be_null",
                kwargs={"column": "margine_lordo"}
            )
        )
        
        # EBITDA <= Gross Margin
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_pair_values_A_to_be_greater_than_B",
                kwargs={
                    "column_A": "margine_lordo",
                    "column_B": "ebitda",
                    "or_equal": True,
                    "mostly": 0.99
                }
            )
        )
        
        # EBIT <= EBITDA
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_pair_values_A_to_be_greater_than_B",
                kwargs={
                    "column_A": "ebitda",
                    "column_B": "ebit",
                    "or_equal": True,
                    "mostly": 0.99
                }
            )
        )
        
        # Tax rate reasonable
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_between",
                kwargs={
                    "column": "tax_rate",
                    "min_value": 0,
                    "max_value": 50,
                    "mostly": 0.95
                }
            )
        )
        
        self.context.save_expectation_suite(suite)
        logger.info(f"Created suite: {suite_name}")
    
    def _create_completeness_suite(self):
        """Create expectations for data completeness."""
        
        suite_name = "data_completeness_suite"
        
        try:
            suite = self.context.get_expectation_suite(suite_name)
        except:
            suite = self.context.add_expectation_suite(suite_name)
        
        # Critical fields should not be null
        critical_fields = [
            "entity_id", "period_year", "period_type", 
            "metric_name", "value", "source_file"
        ]
        
        for field in critical_fields:
            suite.add_expectation(
                ExpectationConfiguration(
                    expectation_type="expect_column_values_to_not_be_null",
                    kwargs={"column": field}
                )
            )
        
        # Period year should be reasonable
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_between",
                kwargs={
                    "column": "period_year",
                    "min_value": 2000,
                    "max_value": 2030
                }
            )
        )
        
        # Confidence score
        suite.add_expectation(
            ExpectationConfiguration(
                expectation_type="expect_column_values_to_be_between",
                kwargs={
                    "column": "confidence_score",
                    "min_value": 0,
                    "max_value": 1
                }
            )
        )
        
        self.context.save_expectation_suite(suite)
        logger.info(f"Created suite: {suite_name}")
    
    def validate_dataframe(self, 
                          df: pd.DataFrame, 
                          suite_name: str,
                          save_results: bool = True) -> Dict[str, Any]:
        """Validate a dataframe against an expectation suite."""
        
        # Create a batch from the dataframe
        batch_request = BatchRequest(
            datasource_name="pandas_datasource",
            data_connector_name="default_runtime_data_connector",
            data_asset_name="validation_data",
            runtime_parameters={"batch_data": df},
            batch_identifiers={"default_identifier": "default_identifier"}
        )
        
        # Get the suite
        suite = self.context.get_expectation_suite(suite_name)
        
        # Create validator
        validator = self.context.get_validator(
            batch_request=batch_request,
            expectation_suite=suite
        )
        
        # Run validation
        results = validator.validate()
        
        # Process results
        validation_summary = {
            "success": results.success,
            "total_expectations": len(results.results),
            "successful_expectations": sum(1 for r in results.results if r.success),
            "failed_expectations": sum(1 for r in results.results if not r.success),
            "failures": []
        }
        
        # Collect failures
        for result in results.results:
            if not result.success:
                validation_summary["failures"].append({
                    "expectation": result.expectation_config.expectation_type,
                    "kwargs": result.expectation_config.kwargs,
                    "result": result.result
                })
        
        # Save results if requested
        if save_results:
            results_path = self.data_dir / f"validation_results_{suite_name}.json"
            with open(results_path, 'w') as f:
                json.dump(validation_summary, f, indent=2, default=str)
            
            # Generate HTML report
            self._generate_html_report(results, suite_name)
        
        logger.info(f"Validation complete: {validation_summary['successful_expectations']}/{validation_summary['total_expectations']} passed")
        
        return validation_summary
    
    def _generate_html_report(self, results, suite_name: str):
        """Generate HTML validation report."""
        try:
            # Build data docs
            self.context.build_data_docs()
            
            # Get the URL to the validation results
            validation_result_identifier = results.meta.get("active_batch_definition", {}).get("batch_identifiers", {})
            
            logger.info(f"HTML report generated for {suite_name}")
        except Exception as e:
            logger.warning(f"Could not generate HTML report: {e}")
    
    def validate_financial_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate financial data using appropriate suites."""
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        all_results = {}
        
        # Determine which suites to run based on available columns
        if 'ricavi' in df.columns:
            all_results['financial_metrics'] = self.validate_dataframe(
                df, 'financial_metrics_suite'
            )
        
        if 'attivo_totale' in df.columns and 'passivo_totale' in df.columns:
            all_results['balance_sheet'] = self.validate_dataframe(
                df, 'balance_sheet_suite'
            )
        
        if 'margine_lordo' in df.columns:
            all_results['income_statement'] = self.validate_dataframe(
                df, 'income_statement_suite'
            )
        
        # Always run completeness
        all_results['completeness'] = self.validate_dataframe(
            df, 'data_completeness_suite'
        )
        
        # Aggregate results
        total_success = all(r.get('success', False) for r in all_results.values())
        
        return {
            'overall_success': total_success,
            'suite_results': all_results,
            'summary': {
                'total_suites_run': len(all_results),
                'successful_suites': sum(1 for r in all_results.values() if r.get('success')),
                'total_expectations': sum(r.get('total_expectations', 0) for r in all_results.values()),
                'successful_expectations': sum(r.get('successful_expectations', 0) for r in all_results.values())
            }
        }
    
    def create_checkpoint(self, name: str, suite_name: str) -> Checkpoint:
        """Create a checkpoint for automated validation."""
        
        checkpoint_config = {
            "name": name,
            "config_version": 1,
            "class_name": "Checkpoint",
            "expectation_suite_name": suite_name,
            "action_list": [
                {
                    "name": "store_validation_result",
                    "action": {
                        "class_name": "StoreValidationResultAction"
                    }
                },
                {
                    "name": "store_evaluation_params",
                    "action": {
                        "class_name": "StoreEvaluationParametersAction"
                    }
                },
                {
                    "name": "update_data_docs",
                    "action": {
                        "class_name": "UpdateDataDocsAction"
                    }
                }
            ]
        }
        
        checkpoint = self.context.add_checkpoint(**checkpoint_config)
        logger.info(f"Created checkpoint: {name}")
        
        return checkpoint


# Example usage
if __name__ == "__main__":
    # Initialize validator
    validator = DataQualityValidator()
    
    # Sample data
    sample_data = [
        {
            "entity_id": "company_001",
            "period_year": 2024,
            "period_type": "FY",
            "metric_name": "ricavi",
            "value": 10000000,
            "margine_ebitda_pct": 15.5,
            "leverage_ratio": 2.1,
            "dso": 45,
            "source_file": "bilancio_2024.pdf",
            "confidence_score": 0.95
        },
        {
            "entity_id": "company_001",
            "period_year": 2024,
            "period_type": "FY",
            "metric_name": "ebitda",
            "value": 1550000,
            "source_file": "bilancio_2024.pdf",
            "confidence_score": 0.92
        }
    ]
    
    # Validate
    results = validator.validate_financial_data(sample_data)
    
    print(f"Validation Results:")
    print(f"Overall Success: {results['overall_success']}")
    print(f"Summary: {json.dumps(results['summary'], indent=2)}")
    
    # Show any failures
    for suite_name, suite_results in results['suite_results'].items():
        if suite_results['failures']:
            print(f"\nFailures in {suite_name}:")
            for failure in suite_results['failures']:
                print(f"  - {failure['expectation']}: {failure['kwargs']}")