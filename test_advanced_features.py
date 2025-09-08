# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Test delle funzionalità avanzate enterprise
# ============================================

"""
Test script for advanced enterprise features:
- Great Expectations data quality
- Automatic calculations with lineage
- Granular provenance tracking
"""

import asyncio
import pandas as pd
from datetime import datetime
import json
from pathlib import Path

# Import new services
from src.domain.services.data_quality_service import DataQualityService, ValidationResult
from src.domain.services.calculation_engine import CalculationEngine
from src.domain.services.granular_provenance_service import (
    GranularProvenanceService,
    ExtractionContext,
    CellLocation,
    PageLocation
)
from src.domain.value_objects.source_reference import SourceReference, SourceReferenceBuilder

def test_data_quality_service():
    """Test Great Expectations data quality validation."""
    print("\n=== Testing Data Quality Service ===")
    
    # Initialize service
    dq_service = DataQualityService()
    
    # Create test financial data
    test_data = pd.DataFrame({
        'attivo_totale': [1000000, 2000000, 1500000],
        'passivo_totale': [1000000, 2000000, 1500000],  # Should match for balance
        'debito_lordo': [600000, 800000, 700000],
        'cassa': [100000, 200000, 150000],
        'pfn': [500000, 600000, 550000],  # Should equal debito_lordo - cassa
        'ricavi': [5000000, 8000000, 6500000],
        'ebitda': [800000, 1200000, 950000],
        'margine_ebitda_percent': [16.0, 15.0, 14.6]  # Should be reasonable
    })
    
    # Test balance sheet validation
    balance_result = dq_service.validate_balance_sheet_coherence(test_data)
    print(f"Balance Sheet Validation: {'PASSED' if balance_result.is_valid else 'FAILED'}")
    print(f"  Success: {balance_result.success_count}, Failed: {balance_result.failed_count}")
    if balance_result.warnings:
        print(f"  Warnings: {balance_result.warnings}")
    if balance_result.errors:
        print(f"  Errors: {balance_result.errors}")
    
    # Test income statement validation
    income_result = dq_service.validate_income_statement(test_data)
    print(f"Income Statement Validation: {'PASSED' if income_result.is_valid else 'FAILED'}")
    
    # Test range validation
    range_result = dq_service.validate_metric_ranges(test_data)
    print(f"Range Validation: {'PASSED' if range_result.is_valid else 'FAILED'}")
    
    # Calculate quality metrics
    quality_metrics = dq_service.calculate_quality_metrics(test_data)
    print(f"Quality Metrics:")
    print(f"  Completeness: {quality_metrics.completeness:.2f}")
    print(f"  Accuracy: {quality_metrics.accuracy:.2f}")
    print(f"  Consistency: {quality_metrics.consistency:.2f}")
    print(f"  Validity: {quality_metrics.validity:.2f}")
    
    return True

def test_calculation_engine():
    """Test automatic calculations with lineage tracking."""
    print("\n=== Testing Calculation Engine ===")
    
    # Initialize engine
    calc_engine = CalculationEngine()
    
    # Test data
    available_data = {
        'ricavi': 5000000,
        'cogs': 3000000,
        'ebitda': 800000,
        'utile_operativo': 600000,
        'debito_lordo': 800000,
        'cassa': 200000,
        'patrimonio_netto': 2000000,
        'utile_netto': 400000,
        'crediti_commerciali': 500000,
        'rimanenze': 300000,
        'debiti_commerciali': 400000
    }
    
    source_refs = {metric: f"test_file.xlsx|sheet:CE|row:{metric}" for metric in available_data.keys()}
    
    # Test individual calculation
    pfn_calc = calc_engine.calculate_metric('pfn', available_data, source_refs)
    if pfn_calc:
        print(f"PFN Calculation: {pfn_calc.metric_name} = {pfn_calc.value} {pfn_calc.unit}")
        print(f"  Formula: {pfn_calc.lineage.formula}")
        print(f"  Confidence: {pfn_calc.lineage.confidence_score:.2f}")
        print(f"  Status: {pfn_calc.lineage.status.value}")
        print(f"  Inputs: {[inp.metric_name for inp in pfn_calc.lineage.inputs]}")
    
    # Test all possible calculations
    all_calculations = calc_engine.calculate_all_possible(available_data, source_refs)
    print(f"\nCalculated {len(all_calculations)} metrics:")
    
    for calc in all_calculations:
        print(f"  {calc.metric_name}: {calc.value:.2f} {calc.unit} (conf: {calc.lineage.confidence_score:.2f})")
    
    # Test calculable metrics listing
    calculable = calc_engine.list_calculable_metrics(available_data)
    print(f"\nCalculable metrics with current data: {calculable}")
    
    return True

def test_granular_provenance_service():
    """Test granular provenance tracking."""
    print("\n=== Testing Granular Provenance Service ===")
    
    # Initialize service
    prov_service = GranularProvenanceService()
    
    # Test Excel provenance
    cell_loc = CellLocation(
        sheet_name="Conto Economico",
        cell_address="B12",
        row_header="Ricavi",
        column_header="2024"
    )
    
    extraction_ctx = ExtractionContext(
        extraction_method="pandas",
        extraction_engine="openpyxl_1.0",
        confidence_score=0.95
    )
    
    excel_ref = prov_service.create_excel_provenance(
        "test_bilancio.xlsx", "abc123", "Conto Economico", cell_loc, extraction_ctx
    )
    
    print(f"Excel Provenance: {excel_ref.to_string()}")
    print(f"  Confidence: {excel_ref.confidence_score}")
    print(f"  Method: {excel_ref.extraction_method}")
    
    # Test PDF provenance
    page_loc = PageLocation(
        page_number=5,
        table_index=2,
        table_coordinates=(100.0, 200.0, 500.0, 400.0),
        line_number=3
    )
    
    pdf_ref = prov_service.create_pdf_provenance(
        "test_report.pdf", "def456", page_loc, extraction_ctx,
        row_label="EBITDA", column_label="FY2024"
    )
    
    print(f"PDF Provenance: {pdf_ref.to_string()}")
    
    # Test calculated value provenance
    input_sources = [excel_ref, pdf_ref]
    calc_ref = prov_service.create_calculated_value_provenance(
        123.45, "ricavi - cogs", input_sources, "margine_lordo"
    )
    
    print(f"Calculated Provenance: {calc_ref.to_string()}")
    
    # Test provenance summary
    all_refs = [excel_ref, pdf_ref, calc_ref]
    summary = prov_service.get_provenance_summary(all_refs)
    print(f"Provenance Summary:")
    print(f"  Total sources: {summary.get('total_sources', 0)}")
    print(f"  Source types: {summary.get('source_types', {})}")
    print(f"  Files: {summary.get('files', [])}")
    
    # Test provenance validation
    validation = prov_service.validate_provenance_chain(all_refs)
    print(f"Provenance Validation: {'VALID' if validation['is_valid'] else 'INVALID'}")
    if validation['warnings']:
        print(f"  Warnings: {validation['warnings']}")
    
    return True

async def test_advanced_orchestrator():
    """Test the advanced enterprise orchestrator integration."""
    print("\n=== Testing Advanced Enterprise Orchestrator ===")
    
    try:
        # Import the advanced orchestrator
        from src.application.services.advanced_enterprise_orchestrator import AdvancedEnterpriseOrchestrator
        
        # Initialize orchestrator
        orchestrator = AdvancedEnterpriseOrchestrator()
        
        print("Advanced Enterprise Orchestrator initialized successfully")
        
        # Test performance statistics (should be empty initially)
        perf_stats = orchestrator.get_performance_statistics()
        print(f"Performance Stats: {perf_stats}")
        
        return True
        
    except Exception as e:
        print(f"Advanced orchestrator test failed: {e}")
        return False

def run_all_tests():
    """Run all advanced feature tests."""
    print("Running Advanced Enterprise Features Tests")
    print("=" * 60)
    
    tests = [
        test_data_quality_service,
        test_calculation_engine,
        test_granular_provenance_service,
    ]
    
    results = []
    
    for test in tests:
        try:
            result = test()
            results.append(result)
            print(f"{'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            results.append(False)
    
    # Test async orchestrator
    try:
        async_result = asyncio.run(test_advanced_orchestrator())
        results.append(async_result)
    except Exception as e:
        print(f"❌ Async test FAILED: {e}")
        results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All advanced features working correctly!")
    else:
        print("⚠️  Some tests failed - check implementations")
    
    return all(results)

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)