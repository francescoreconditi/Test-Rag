# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-05
# Scopo: Test della formattazione output analisi
# ============================================

"""Test della formattazione degli output di analisi."""

from services.format_helper import format_analysis_result

# Esempio reale dal tuo output
test_input = """[Analisi tipo: BILANCIO]

<KPI_JSON>
{
  "periodi_coperti": ["Aprile ytd 2025"],
  "conto_economico": {
    "ricavi": [
      {"periodo":"Aprile ytd 2025", "valore":"5.214.095", "unita":"€", "fonte_pagina":""}
    ],
    "ebitda": [
      {"periodo":"Aprile ytd 2025", "valore":"547.643", "unita":"€", "fonte_pagina":""}
    ],
    "ebit": [
      {"periodo":"Aprile ytd 2025", "valore":"400.843", "unita":"€", "fonte_pagina":""}
    ],
    "utile_netto": []
  },
  "stato_patrimoniale": {
    "cassa_e_equivalenti": [],
    "debito_finanziario_totale": [],
    "patrimonio_netto": []
  },
  "cash_flow": {
    "cfo": [],
    "cfi": [],
    "cff": [],
    "capex": []
  },
  "margini_e_ratios": [
    {"nome":"margine EBITDA","periodo":"Aprile ytd 2025","valore":"10,5","unita":"%","fonte_pagina":""}
  ],
  "guidance_o_outlook": [],
  "eventi_straordinari": [],
  "rischi": [],
  "note": ""
}
</KPI_JSON>

<SINTESI>
Il documento presenta un'analisi finanziaria della Software Division per il periodo "Aprile ytd 2025". I ricavi totali hanno mostrato una crescita, attestandosi a €5.214.095, con un incremento del 7,4% rispetto al periodo precedente. La crescita è stata guidata principalmente dai ricavi da servizio, che hanno visto un aumento significativo del 23,4%. Il margine EBITDA si è posizionato al 10,5%, indicando una buona capacità di generare profitto operativo. L'EBIT ha registrato un valore di €400.843, segnando un aumento del 23,2% rispetto al periodo precedente, il che riflette un miglioramento dell'efficienza operativa. Nonostante l'assenza di dati specifici su utile netto, debito finanziario, e cash flow, l'analisi suggerisce una solida performance finanziaria per il periodo in esame. Tuttavia, il documento non fornisce informazioni su rischi finanziari, outlook futuro o covenant, limitando la comprensione completa della situazione finanziaria e delle prospettive future della divisione.
</SINTESI>"""

def test_formatting():
    """Testa la formattazione dell'output."""
    print("=" * 80)
    print("TEST FORMATTAZIONE OUTPUT ANALISI")
    print("=" * 80)
    print("\n### INPUT ORIGINALE (prime 500 caratteri):")
    print(test_input[:500] + "...")
    
    print("\n" + "=" * 80)
    print("### OUTPUT FORMATTATO:")
    print("=" * 80)
    
    formatted = format_analysis_result(test_input)
    print(formatted)
    
    print("\n" + "=" * 80)
    print("TEST COMPLETATO!")
    print("=" * 80)

if __name__ == "__main__":
    test_formatting()