# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-05
# Scopo: Debug del formatter per capire dove fallisce
# ============================================

"""Debug del formatter per identificare il problema."""

from services.format_helper import format_analysis_result

# Il tuo esempio di input problematico
problematic_input = """[Analisi tipo: BILANCIO]

<KPI_JSON> { "periodi_coperti": [ {"anno": "2025", "mese": "Aprile", "tipo": "consuntivo"}, {"anno": "2025", "mese": "Aprile", "tipo": "budget"}, {"anno": "2024", "mese": "Aprile", "tipo": "consuntivo"} ], "conto_economico": { "ricavi": [ {"periodo":"Aprile 2025 Consuntivo", "valore":"5.214.095", "unita":"€", "fonte_pagina":"1"}, {"periodo":"Aprile 2025 Budget", "valore":"4.855.765", "unita":"€", "fonte_pagina":"1"}, {"periodo":"Aprile 2024 Consuntivo", "valore":"4.464.428", "unita":"€", "fonte_pagina":"1"} ], "ebitda": [ {"periodo":"Aprile 2025 Consuntivo", "valore":"547.643", "unita":"€", "fonte_pagina":"1"}, {"periodo":"Aprile 2025 Budget", "valore":"485.737", "unita":"€", "fonte_pagina":"1"}, {"periodo":"Aprile 2024 Consuntivo", "valore":"489.705", "unita":"€", "fonte_pagina":"1"} ], "ebit": [ {"periodo":"Aprile 2025 Consuntivo", "valore":"400.843", "unita":"€", "fonte_pagina":"1"}, {"periodo":"Aprile 2025 Budget", "valore":"325.454", "unita":"€", "fonte_pagina":"1"}, {"periodo":"Aprile 2024 Consuntivo", "valore":"347.069", "unita":"€", "fonte_pagina":"1"} ], "utile_netto": [] }, "stato_patrimoniale": { "cassa_e_equivalenti": [], "debito_finanziario_totale": [], "patrimonio_netto": [] }, "cash_flow": { "cfo": [], "cfi": [], "cff": [], "capex": [] }, "margini_e_ratios": [ {"nome":"margine EBITDA","periodo":"Aprile 2025 Consuntivo","valore":"10,5","unita":"%","fonte_pagina":"1"}, {"nome":"margine EBITDA","periodo":"Aprile 2025 Budget","valore":"10,0","unita":"%","fonte_pagina":"1"}, {"nome":"margine EBITDA","periodo":"Aprile 2024 Consuntivo","valore":"11,0","unita":"%","fonte_pagina":"1"} ], "guidance_o_outlook": [], "eventi_straordinari": [], "rischi": [], "note": "" } </KPI_JSON>

<SINTESI> Il documento evidenzia una crescita dei ricavi per la Software Division nel mese di Aprile 2025 rispetto sia al budget che all'anno precedente, con un incremento del 7,4% rispetto al budget e del 16,8% rispetto all'anno precedente (p. 1). Questa crescita è guidata principalmente dai ricavi da servizio, che hanno visto un aumento significativo del 23,4% rispetto al budget e del 36,9% rispetto all'anno precedente (p. 1). Nonostante un aumento dei costi del lavoro e degli Opex, il margine EBITDA si è attestato al 10,5% nel consuntivo di Aprile 2025, leggermente superiore al 10,0% previsto nel budget e vicino all'11,0% dell'anno precedente (p. 1). L'EBIT ha registrato un'importante crescita del 23,2% rispetto al budget e del 15,5% rispetto all'anno precedente (p. 1), indicando una gestione efficace dei costi operativi e una buona leva operativa. Non sono stati identificati rischi finanziari specifici, eventi straordinari o guidance futura nel documento. L'analisi suggerisce che la divisione sta performando bene, con un'efficace gestione dei costi e una crescita sostenuta dei ricavi. </SINTESI>"""

def debug_formatter():
    """Debug del formatter step by step."""
    print("=" * 80)
    print("DEBUG FORMATTER")
    print("=" * 80)
    
    print("1. Input ricevuto:")
    print("Primi 200 caratteri:", problematic_input[:200])
    
    print("\n2. Tentativo di formattazione...")
    try:
        result = format_analysis_result(problematic_input)
        print("OK - Formattazione riuscita!")
        print("\n3. Output formattato:")
        print(result[:500] + "..." if len(result) > 500 else result)
    except Exception as e:
        print(f"ERRORE: {str(e)}")
        
        # Proviamo a debuggare step by step
        print("\n4. Debug step by step:")
        
        import re
        import json
        
        try:
            # Step 1: Extract analysis type
            analysis_type_match = re.search(r"\[Analisi tipo: (\w+)\]", problematic_input)
            analysis_type = analysis_type_match.group(1) if analysis_type_match else "GENERALE"
            print(f"   - Tipo analisi estratto: {analysis_type}")
            
            # Step 2: Extract JSON
            json_match = re.search(r"<(?:KPI_)?JSON>(.*?)</(?:KPI_)?JSON>", problematic_input, re.DOTALL)
            if json_match:
                print("   - JSON trovato, tentativo parsing...")
                json_str = json_match.group(1).strip()
                json_data = json.loads(json_str)
                print(f"   - JSON parsato con successo: {len(json_data)} chiavi")
            else:
                print("   - JSON non trovato")
                
            # Step 3: Extract summary
            summary_match = re.search(r"<SINTESI>(.*?)</SINTESI>", problematic_input, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()
                print(f"   - Sintesi estratta: {len(summary)} caratteri")
            else:
                print("   - Sintesi non trovata")
                
        except Exception as debug_e:
            print(f"   - Errore nel debug: {str(debug_e)}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    debug_formatter()