#!/usr/bin/env python3
"""Test script for advanced financial validations."""

from src.domain.value_objects.guardrails import FinancialGuardrails, ValidationLevel
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_advanced_validations():
    """Test the enhanced validation system."""
    
    guardrails = FinancialGuardrails()
    
    print("Testing Advanced Financial Validations")
    print("=" * 50)
    
    # Test data with various metrics
    financial_data = {
        # Basic metrics
        'ricavi': 10000000,
        'cogs': 6000000,
        'margine_lordo': 4000000,
        'ebitda': 1500000,
        'attivo_totale': 15000000,
        'passivo_totale': 15000000,
        'pfn': 2000000,
        'debito_lordo': 5000000,
        'cassa': 3000000,
        
        # AR/AP metrics
        'dso': 45,  # Good range
        'dpo': 35,  # Good range
        
        # Sales metrics
        'tasso_churn_pct': 15,  # Good range
        'conversion_rate_pct': 2.5,  # Good range
        
        # Inventory metrics
        'rotazione_magazzino': 6,  # Good range
        'giorni_magazzino': 60,  # Good range
        
        # HR metrics
        'turnover_personale_pct': 12,  # Good range
        'assenteismo_pct': 4,  # Good range
    }
    
    # Run comprehensive validation
    results = guardrails.validate_comprehensive(financial_data)
    
    # Display results
    print(f"Total validation checks: {len(results)}")
    print()
    
    # Group by category
    categories = {}
    for result in results:
        cat = result.category.value
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(result)
    
    for category, cat_results in categories.items():
        print(f"{category.upper().replace('_', ' ')}:")
        for result in cat_results:
            status = "PASS" if result.passed else "FAIL"
            level = result.level.value.upper()
            print(f"  [{status}] [{level}] {result.message}")
        print()
    
    # Test with problematic values
    print("Testing with OUT-OF-RANGE values:")
    print("-" * 40)
    
    problematic_data = {
        'dso': 250,  # Too high
        'dpo': 10,   # Too low
        'tasso_churn_pct': 75,  # Too high
        'conversion_rate_pct': 0.01,  # Too low
        'rotazione_magazzino': 0.2,  # Too low
        'giorni_magazzino': 1000,  # Too high
        'turnover_personale_pct': 150,  # Too high
        'assenteismo_pct': 40,  # Too high
    }
    
    problem_results = guardrails.validate_comprehensive(problematic_data)
    
    for result in problem_results:
        if not result.passed:
            level = result.level.value.upper()
            print(f"  [FAIL] [{level}] {result.message}")
    
    print()
    
    # Test perimeter consistency
    print("Testing PERIMETER consistency:")
    print("-" * 40)
    
    perimeter_data = [
        {
            'period': 'FY2024',
            'perimeter': 'Standalone',
            'ricavi': 8000000,
            'ebitda': 1000000
        },
        {
            'period': 'FY2024', 
            'perimeter': 'Consolidated',
            'ricavi': 10000000,  # Should be >= Standalone
            'ebitda': 1500000
        }
    ]
    
    perimeter_results = guardrails.validate_perimeter_consistency(perimeter_data)
    for result in perimeter_results:
        status = "PASS" if result.passed else "FAIL"
        level = result.level.value.upper()
        print(f"  [{status}] [{level}] {result.message}")
    
    print()
    
    # Test period consistency (growth rates)
    print("Testing PERIOD consistency:")
    print("-" * 40)
    
    period_data = [
        {
            'period': 'FY2023',
            'ricavi': 8000000,
            'ebitda': 800000
        },
        {
            'period': 'FY2024',
            'ricavi': 10000000,  # 25% growth - reasonable
            'ebitda': 1500000    # 87.5% growth - high but acceptable
        }
    ]
    
    period_results = guardrails.validate_period_consistency(period_data)
    for result in period_results:
        status = "PASS" if result.passed else "FAIL"
        level = result.level.value.upper()
        print(f"  [{status}] [{level}] {result.message}")
    
    print()
    
    # Test with extreme growth
    print("Testing EXTREME growth rates:")
    print("-" * 40)
    
    extreme_period_data = [
        {
            'period': 'FY2023',
            'ricavi': 5000000
        },
        {
            'period': 'FY2024',
            'ricavi': 20000000  # 300% growth - too extreme
        }
    ]
    
    extreme_results = guardrails.validate_period_consistency(extreme_period_data)
    for result in extreme_results:
        status = "PASS" if result.passed else "FAIL"
        level = result.level.value.upper()
        print(f"  [{status}] [{level}] {result.message}")
    
    print()
    
    # Test advanced summary
    print("ADVANCED VALIDATION SUMMARY:")
    print("-" * 40)
    
    all_results = results + problem_results + perimeter_results + period_results + extreme_results
    summary = guardrails.get_advanced_validation_summary(all_results)
    
    print(f"Overall Status: {summary['overall_status']}")
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Pass Rate: {summary['pass_rate']:.1f}%")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}")
    print()
    
    print("Category Breakdown:")
    for category, stats in summary['categories'].items():
        print(f"  {category.replace('_', ' ').title()}:")
        print(f"    Total: {stats['total']}")
        print(f"    Pass Rate: {stats['pass_rate']:.1f}%")
        print(f"    Errors: {stats['errors']}")
        print(f"    Warnings: {stats['warnings']}")
    
    print()
    print("Advanced Validation Test Complete!")
    return True

if __name__ == "__main__":
    test_advanced_validations()