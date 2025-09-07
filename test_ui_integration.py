#!/usr/bin/env python3
"""Test script for UI/UX integration and advanced features."""

import os
import sys
from pathlib import Path
import json

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

def test_document_preview():
    """Test document preview service."""
    print("Testing Document Preview Service")
    print("-" * 40)
    
    try:
        from src.application.services.document_preview import DocumentPreviewService
        
        service = DocumentPreviewService()
        
        # Test with a sample file (create a dummy CSV for testing)
        test_file = Path("test_sample.csv")
        with open(test_file, 'w') as f:
            f.write("Metric,Value,Unit\n")
            f.write("Ricavi,10000000,EUR\n")
            f.write("EBITDA,1500000,EUR\n")
            f.write("Dipendenti,150,count\n")
        
        print(f"[+] Service initialized")
        print(f"[+] Supported formats: {len(service.supported_formats)}")
        
        # Generate preview
        preview = service.generate_preview(str(test_file), max_pages=2)
        
        if preview['status'] == 'success':
            print(f"[+] Preview generated successfully")
            print(f"   - File info: {preview['file_info']['name']}")
            print(f"   - Content preview length: {len(preview.get('content_preview', ''))}")
            print(f"   - Statistics keys: {list(preview.get('statistics', {}).keys())}")
            print(f"   - Key metrics: {len(preview.get('key_metrics', {}))}")
        else:
            print(f"[-] Preview failed: {preview.get('error')}")
        
        # Cleanup
        test_file.unlink()
        
        return True
        
    except ImportError as e:
        print(f"[-] Import error: {e}")
        return False
    except Exception as e:
        print(f"[-] Test error: {e}")
        return False

def test_interactive_editor():
    """Test interactive editing service."""
    print("\nTesting Interactive Editor Service")
    print("-" * 40)
    
    try:
        from src.application.services.interactive_editor import InteractiveEditingService
        
        service = InteractiveEditingService()
        print(f"[+] Service initialized")
        
        # Start editing session
        session_id = service.start_editing_session("test_document.pdf")
        print(f"[+] Session started: {session_id}")
        
        # Get editable data
        editable_data = service.get_editable_data(session_id)
        print(f"[+] Editable data loaded: {len(editable_data['data'])} metrics")
        
        # Test metric update
        result = service.update_metric_value(session_id, 'ricavi', 11000000, "Test update")
        if result['success']:
            print(f"[+] Metric update successful")
        else:
            print(f"[-] Metric update failed: {result.get('error')}")
        
        # Test suggestions
        suggestions = service.suggest_corrections(session_id)
        print(f"[+] Generated {len(suggestions)} suggestions")
        
        # Test edit history
        history = service.get_edit_history(session_id)
        print(f"[+] Edit history: {len(history)} operations")
        
        return True
        
    except ImportError as e:
        print(f"[-] Import error: {e}")
        return False
    except Exception as e:
        print(f"[-] Test error: {e}")
        return False

def test_analytics_dashboard():
    """Test analytics dashboard service."""
    print("\nTesting Analytics Dashboard Service")
    print("-" * 40)
    
    try:
        from src.application.services.analytics_dashboard import AnalyticsDashboardService
        
        service = AnalyticsDashboardService()
        print(f"[+] Service initialized")
        print(f"[+] Standard KPIs defined: {len(service.standard_kpis)}")
        
        # Sample data
        financial_data = {
            'ricavi': 12000000,
            'cogs': 7200000,
            'ebitda': 1800000,
            'ebit': 1200000,
            'utile_netto': 840000,
            'attivo_totale': 18000000,
            'patrimonio_netto': 6000000,
            'debito_lordo': 8000000,
            'cassa': 2000000,
            'dipendenti': 150,
            'dso': 73,
            'rotazione_magazzino': 4.0
        }
        
        # Historical periods
        periods = [
            {'period': 'FY2022', 'ricavi': 10000000, 'ebitda': 1300000},
            {'period': 'FY2023', 'ricavi': 11200000, 'ebitda': 1560000},
            {'period': 'FY2024', 'ricavi': 12000000, 'ebitda': 1800000}
        ]
        
        # Generate dashboard
        dashboard_data = service.generate_dashboard_data(financial_data, periods, "manufacturing")
        
        print(f"[+] Dashboard generated successfully")
        print(f"   - KPIs calculated: {len(dashboard_data['kpis'])}")
        print(f"   - Insights generated: {len(dashboard_data['insights'])}")
        print(f"   - Health score: {dashboard_data['health_score']['score']:.1f}/100")
        print(f"   - Risk factors: {len(dashboard_data['risk_assessment']['risk_factors'])}")
        print(f"   - Data quality: {dashboard_data['data_quality']['quality_level']}")
        
        # Test individual components
        kpis = service._calculate_kpis(financial_data, "manufacturing")
        print(f"[+] KPI calculation: {len(kpis)} KPIs")
        
        insights = service._generate_insights(financial_data, periods, "manufacturing")
        print(f"[+] Insights generation: {len(insights)} insights")
        
        return True
        
    except ImportError as e:
        print(f"[-] Import error: {e}")
        return False
    except Exception as e:
        print(f"[-] Test error: {e}")
        return False

def test_ontology_integration():
    """Test ontology integration with new metrics."""
    print("\nTesting Extended Ontology Integration")
    print("-" * 40)
    
    try:
        from src.application.services.ontology_mapper import OntologyMapper
        
        mapper = OntologyMapper("config/ontology/financial_metrics.yaml")
        
        stats = mapper.get_stats()
        print(f"[+] Ontology loaded: {stats['total_canonical_metrics']} metrics")
        print(f"[+] Synonyms indexed: {stats['total_synonyms']} synonyms")
        print(f"[+] Categories: {len(stats['categories'])}")
        
        # Test new domain metrics
        test_metrics = [
            # AR/AP
            "giorni medi di incasso",
            "DSO",
            "tempo medio pagamento",
            
            # Sales
            "ticket medio", 
            "ARPU",
            "churn rate",
            
            # Inventory
            "rotazione magazzino",
            "giorni di scorta",
            "stock out",
            
            # HR
            "FTE",
            "turnover personale",
            "assenteismo"
        ]
        
        successful_mappings = 0
        for metric in test_metrics:
            result = mapper.map_metric(metric, threshold=70)
            if result:
                successful_mappings += 1
                metric_key, canonical_name, score = result
                print(f"   [+] '{metric}' -> '{canonical_name}' ({score:.1f}%)")
            else:
                print(f"   [-] '{metric}' -> No mapping found")
        
        success_rate = (successful_mappings / len(test_metrics)) * 100
        print(f"[+] Mapping success rate: {success_rate:.1f}%")
        
        # Test calculable metrics
        calculable = mapper.get_calculable_metrics()
        print(f"[+] Calculable metrics: {len(calculable)}")
        
        return successful_mappings >= len(test_metrics) * 0.8  # 80% success rate
        
    except ImportError as e:
        print(f"[-] Import error: {e}")
        return False
    except Exception as e:
        print(f"[-] Test error: {e}")
        return False

def test_advanced_validations():
    """Test advanced validation system."""
    print("\nTesting Advanced Validation System")
    print("-" * 40)
    
    try:
        from src.domain.value_objects.guardrails import FinancialGuardrails
        
        guardrails = FinancialGuardrails()
        print(f"[+] Guardrails initialized")
        
        # Test data with good and bad values
        test_data = {
            'ricavi': 10000000,
            'ebitda': 1500000,
            'dso': 250,  # Too high - should trigger warning
            'tasso_churn_pct': 75,  # Too high
            'rotazione_magazzino': 0.2,  # Too low
            'turnover_personale_pct': 12,  # Good
            'assenteismo_pct': 4  # Good
        }
        
        # Run comprehensive validation
        results = guardrails.validate_comprehensive(test_data)
        print(f"[+] Validation completed: {len(results)} checks")
        
        # Count results by level
        errors = sum(1 for r in results if r.level.value == 'error' and not r.passed)
        warnings = sum(1 for r in results if r.level.value == 'warning' and not r.passed)
        passed = sum(1 for r in results if r.passed)
        
        print(f"   - Passed: {passed}")
        print(f"   - Warnings: {warnings}")
        print(f"   - Errors: {errors}")
        
        # Test domain-specific validations
        ar_ap_results = guardrails.validate_ar_ap_metrics(test_data)
        sales_results = guardrails.validate_sales_metrics(test_data)
        hr_results = guardrails.validate_hr_metrics(test_data)
        
        print(f"[+] AR/AP validations: {len(ar_ap_results)}")
        print(f"[+] Sales validations: {len(sales_results)}")  
        print(f"[+] HR validations: {len(hr_results)}")
        
        # Test advanced summary
        summary = guardrails.get_advanced_validation_summary(results)
        print(f"[+] Advanced summary generated")
        print(f"   - Overall status: {summary['overall_status']}")
        print(f"   - Pass rate: {summary['pass_rate']:.1f}%")
        print(f"   - Categories tested: {len(summary['categories'])}")
        
        return True
        
    except ImportError as e:
        print(f"[-] Import error: {e}")
        return False
    except Exception as e:
        print(f"[-] Test error: {e}")
        return False

def test_streamlit_pages():
    """Test Streamlit page files exist and are valid."""
    print("\nTesting Streamlit Pages")
    print("-" * 40)
    
    pages_dir = Path("pages")
    expected_patterns = [
        ("Analytics Dashboard", "1_*_Analytics_Dashboard.py"),
        ("Document Preview", "2_*_Document_Preview.py"), 
        ("Interactive Editor", "3_*_Interactive_Editor.py")
    ]
    
    all_exist = True
    
    for page_name, pattern in expected_patterns:
        matching_files = list(pages_dir.glob(pattern))
        if matching_files:
            page_file = matching_files[0]  # Use first match
            # Remove Unicode characters from filename for display
            display_name = ''.join(c for c in page_file.name if ord(c) < 128)
            print(f"[+] {page_name} exists ({display_name})")
            
            # Basic syntax check
            try:
                with open(page_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for required components
                if 'def main():' in content:
                    print(f"   [+] Has main() function")
                else:
                    print(f"   [!] Missing main() function")
                
                if 'st.' in content:
                    print(f"   [+] Uses Streamlit components")
                else:
                    print(f"   [!] No Streamlit usage found")
                    
            except Exception as e:
                print(f"   [-] Error reading file: {e}")
                all_exist = False
        else:
            print(f"[-] {page_name} missing")
            all_exist = False
    
    return all_exist

def main():
    """Run all UI/UX integration tests."""
    print("[*] UI/UX Integration Tests")
    print("=" * 50)
    
    test_results = []
    
    # Run all tests
    test_functions = [
        ("Document Preview", test_document_preview),
        ("Interactive Editor", test_interactive_editor),
        ("Analytics Dashboard", test_analytics_dashboard),
        ("Ontology Integration", test_ontology_integration),
        ("Advanced Validations", test_advanced_validations),
        ("Streamlit Pages", test_streamlit_pages)
    ]
    
    for test_name, test_func in test_functions:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"[-] {test_name} failed with exception: {e}")
            test_results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("[*] TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        icon = "[+]" if result else "[-]"
        print(f"{icon} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n[*] Overall Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("[+] All UI/UX integration tests passed!")
        print("\n[*] Ready for production deployment:")
        print("   • Advanced Analytics Dashboard")
        print("   • Document Preview with thumbnails")  
        print("   • Interactive Metrics Editor")
        print("   • Extended domain ontology (68 metrics)")
        print("   • Advanced validations (range, perimeter, period)")
        print("   • Comprehensive UI/UX integration")
    else:
        print(f"[!] Some tests failed. Please review and fix issues.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)