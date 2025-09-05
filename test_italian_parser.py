#!/usr/bin/env python3
"""
Test del parser italiano per numeri finanziari
"""

import logging
from services.italian_parser import ItalianNumberParser, FinancialValidator, ProvenancedValue
from services.csv_analyzer import CSVAnalyzer
import pandas as pd
import json

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_number_parsing():
    """Test parsing numeri italiani"""
    parser = ItalianNumberParser()
    
    print("="*80)
    print("TEST PARSING NUMERI ITALIANI")
    print("="*80)
    
    test_cases = [
        # Formato italiano standard
        ("1.234,56", 1234.56),
        ("5.214.095", 5214095.0),
        ("1.234.567,89", 1234567.89),
        
        # Negativi tra parentesi
        ("(123,45)", -123.45),
        ("(1.500)", -1500.0),
        
        # Percentuali
        ("7,4%", 0.074),
        ("16,8%", 0.168),
        ("5,2%", 0.052),
        
        # Con valute
        ("€ 5.214.095", 5214095.0),
        ("1.000.000 €", 1000000.0),
        ("$ 1.234,56", 1234.56),
        
        # Scale
        ("valori in migliaia: 1.234", 1234000.0),  # 1.234 * 1000
        ("5.214 (in migliaia)", 5214000.0),
        
        # Casi edge
        ("547", 547.0),
        ("10,5", 10.5),
        ("0,0", 0.0),
    ]
    
    print(f"{'Input':<30} {'Atteso':<15} {'Ottenuto':<15} {'Status'}")
    print("-" * 70)
    
    for input_text, expected in test_cases:
        result = parser.parse_number(input_text)
        
        if result:
            obtained = result.value
            status = "OK" if abs(obtained - expected) < 0.01 else "FAIL"
            print(f"{input_text:<30} {expected:<15} {obtained:<15} {status}")
        else:
            print(f"{input_text:<30} {expected:<15} {'FAILED':<15} FAIL")

def test_document_parsing():
    """Test parsing documento completo"""
    parser = ItalianNumberParser()
    
    print("\n" + "="*80)
    print("TEST PARSING DOCUMENTO")
    print("="*80)
    
    # Documento di esempio simile al Report SWD
    sample_doc = """
    REPORT SWD - Aprile 2025 (valori in migliaia di Euro)
    
    YTD Consuntivo vs P.Y. vs Budget
    
    A. Ricavi                    5.214.095  100,0%   4.855.765  100,0%    358.329   7,4%
    A.01 Ricavi da vendite         683.926   13,1%     691.809   14,2%     (7.883) -1,1%
    A.02 Ricavi da servizio      1.205.342   23,1%     976.736   20,1%    228.606  23,4%
    A.03 Ricavi Assistenze       3.289.555   63,1%   3.120.424   64,3%    169.131   5,4%
    
    C. Consumi                   1.349.351   25,9%   1.191.833   24,5%    157.518  13,2%
    
    Gross Margin                 3.864.743   74,1%   3.663.932   75,5%    200.811   5,5%
    
    D. Costo del Lavoro          2.527.127   48,5%   2.538.367   52,3%    (11.240) -0,4%
    
    E. OPEX                        776.640   14,9%     626.495   12,9%    150.145  24,0%
    E.01 Industriali               442.238    8,5%     382.646    7,9%     59.593  15,6%
    E.02 Commerciali               211.434    4,1%     144.204    3,0%     67.231  46,7%
    
    EBITDA                         547.643   10,5%     485.737   10,0%     61.906  12,7%
    
    G. Ammortamenti                146.800    2,8%     160.283    3,3%    (13.483) -8,4%
    
    EBIT                           400.843    7,7%     325.454    6,7%     75.389  23,2%
    
    H. Oneri Finanziari             6.045    0,1%       1.666    0,0%      4.379  262,8%
    
    EBT                            394.798    7,6%     323.788    6,7%     71.011  21,9%
    
    PFN: 1.200 (migliaia)
    Cassa e banche: 300 (migliaia)  
    Debito finanziario: 1.500 (migliaia)
    """
    
    parsed_doc = parser.parse_financial_document("test_report.pdf", sample_doc)
    
    print(f"Documento parsato: {parsed_doc.file_path}")
    print(f"Valuta rilevata: {parsed_doc.detected_currency}")
    print(f"Scala rilevata: {parsed_doc.detected_scale}x")
    print(f"Periodo rilevato: {parsed_doc.detected_period}")
    print(f"Valori estratti: {len(parsed_doc.values)}")
    
    # Mostra alcuni valori estratti
    print(f"\nPrimi 10 valori estratti:")
    for i, value in enumerate(parsed_doc.values[:10]):
        print(f"  {i+1}. {value.raw_text} -> {value.value} {value.unit} [{value.source_ref}]")
    
    return parsed_doc

def test_validation():
    """Test validazioni finanziarie"""
    print("\n" + "="*80)
    print("TEST VALIDAZIONI FINANZIARIE")
    print("="*80)
    
    validator = FinancialValidator()
    
    # Crea dati di test
    values = [
        ProvenancedValue(
            value=1500000, raw_text="1.500", unit="", currency="EUR",
            source_ref="test|metric:debito"
        ),
        ProvenancedValue(
            value=300000, raw_text="300", unit="", currency="EUR", 
            source_ref="test|metric:cassa"
        ),
        ProvenancedValue(
            value=1200000, raw_text="1.200", unit="", currency="EUR",
            source_ref="test|metric:pfn"
        ),
        ProvenancedValue(
            value=1.5, raw_text="150%", unit="%", currency="EUR",
            source_ref="test|metric:crescita"  # Percentuale impossibile
        )
    ]
    
    # Test validazioni
    balance_errors = validator.validate_balance_sheet(values)
    range_errors = validator.validate_ranges(values)
    
    print("Errori bilancio:", balance_errors if balance_errors else "Nessuno")
    print("Errori range:", range_errors if range_errors else "Nessuno")
    
    return len(balance_errors) + len(range_errors) == 0

def test_csv_integration():
    """Test integrazione con CSVAnalyzer"""
    print("\n" + "="*80)  
    print("TEST INTEGRAZIONE CSV ANALYZER")
    print("="*80)
    
    # Crea un CSV di test con numeri italiani
    test_data = {
        'Anno': [2023, 2024, 2025],
        'Fatturato': ['1.234.567,89', '1.456.789,12', '1.567.890,23'],
        'EBITDA': ['123.456,78', '145.678,91', '156.789,02'],
        'Margine_EBITDA': ['10,0%', '10,0%', '10,0%'],
        'Crescita_YoY': ['5,2%', '18,0%', '7,6%']
    }
    
    df = pd.DataFrame(test_data)
    df.to_csv('test_italian.csv', index=False)
    
    try:
        # Test CSVAnalyzer migliorato
        analyzer = CSVAnalyzer()
        loaded_df = analyzer.load_csv('test_italian.csv')
        
        print(f"CSV caricato: {len(loaded_df)} righe, {len(loaded_df.columns)} colonne")
        print(f"Valori con provenienza: {len(analyzer.parsed_values)}")
        
        # Verifica che i numeri siano stati parsati correttamente
        print("\nColonne parsate:")
        for col in loaded_df.columns:
            print(f"  {col}: {loaded_df[col].dtype}")
        
        print("\nPrimi valori con provenienza:")
        provenance_data = analyzer.get_parsed_values_with_provenance()
        for pv in provenance_data[:5]:
            print(f"  {pv['raw_text']} -> {pv['value']} ({pv['source_ref']})")
        
        # Test validazioni
        validation_results = analyzer.validate_financial_coherence()
        print(f"\nValidazioni: {'Passed' if validation_results['validation_passed'] else 'Failed'}")
        if not validation_results['validation_passed']:
            print(f"  Errori: {validation_results['total_errors']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test CSV: {str(e)}")
        return False
    finally:
        # Cleanup
        import os
        if os.path.exists('test_italian.csv'):
            os.unlink('test_italian.csv')

def test_prompt_integration():
    """Test integrazione con prompt specializzati"""
    print("\n" + "="*80)
    print("TEST INTEGRAZIONE PROMPT")
    print("="*80)
    
    from services.prompt_router import PROMPT_BILANCIO, PROMPT_REPORT_DETTAGLIATO
    
    sample_text = """
    Ricavi: 5.214.095 €
    EBITDA: 547.643 € (10,5%)
    Crescita YoY: 7,4%
    """
    
    # Test prompt bilancio migliorato
    prompt_bilancio = PROMPT_BILANCIO("test.pdf", sample_text)
    print("Prompt BILANCIO generato con competenze italiane")
    
    # Test prompt report dettagliato
    prompt_report = PROMPT_REPORT_DETTAGLIATO("test_report.pdf", sample_text) 
    print("Prompt REPORT_DETTAGLIATO generato con parsing avanzato")
    
    # Verifica che i prompt contengano le istruzioni italiane
    checks = [
        "numeri italiani" in prompt_bilancio.lower(),
        "1.234,56" in prompt_bilancio,
        "parsing accurato" in prompt_report.lower(),
        "formato italiano" in prompt_report.lower()
    ]
    
    print(f"Controlli prompt: {sum(checks)}/4 OK")
    return all(checks)

def main():
    """Esegue tutti i test"""
    print("AVVIO TEST SUITE PARSER ITALIANO")
    print("=" * 80)
    
    results = {
        'number_parsing': True,
        'document_parsing': True,
        'validation': True,
        'csv_integration': True,
        'prompt_integration': True
    }
    
    try:
        # Test parsing numeri
        test_number_parsing()
        
        # Test parsing documento
        parsed_doc = test_document_parsing()
        results['document_parsing'] = len(parsed_doc.values) > 0
        
        # Test validazioni
        results['validation'] = test_validation()
        
        # Test integrazione CSV
        results['csv_integration'] = test_csv_integration()
        
        # Test integrazione prompt
        results['prompt_integration'] = test_prompt_integration()
        
    except Exception as e:
        print(f"ERRORE DURANTE I TEST: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Report finale
    print("\n" + "="*80)
    print("REPORT FINALE TEST")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{test_name.replace('_', ' ').title():<30} {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nRISULTATO: {total_passed}/{total_tests} test passati")
    
    if total_passed == total_tests:
        print("TUTTI I TEST SUPERATI! Parser italiano pronto per produzione!")
    else:
        print("Alcuni test falliti - verificare implementazione")
    
    return total_passed == total_tests

if __name__ == "__main__":
    main()