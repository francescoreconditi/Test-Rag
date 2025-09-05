# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-05
# Scopo: Test del sistema di routing dei prompt specializzati
# ============================================

"""Test script per verificare il funzionamento del prompt router."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.prompt_router import choose_prompt, get_available_prompts, get_prompt_description

# Test cases con testi di esempio per diversi tipi di documenti
test_cases = [
    {
        "name": "Bilancio_2024.pdf",
        "text": """
        BILANCIO CONSOLIDATO 2024
        
        Il Gruppo ha registrato ricavi per €150 milioni nel FY2024, con un incremento del 12% YoY.
        L'EBITDA si è attestato a €45 milioni (margine EBITDA del 30%), mentre l'utile netto
        è cresciuto del 15% raggiungendo €22 milioni.
        
        Lo stato patrimoniale evidenzia un patrimonio netto di €180 milioni e una PFN di €35 milioni,
        con un rapporto PFN/EBITDA di 0.78x, ben al di sotto dei covenant bancari fissati a 3.0x.
        
        Il cash flow operativo è stato positivo per €38 milioni, con un CAPEX di €12 milioni
        principalmente dedicato all'espansione della capacità produttiva.
        """
    },
    {
        "name": "Analisi_Vendite_Q3.xlsx",
        "text": """
        REPORT VENDITE TERZO TRIMESTRE
        
        Fatturato Q3: €42.5M (+8% vs Q2, +15% YoY)
        
        Breakdown per prodotto:
        - Linea Premium: €18M (42% del totale)
        - Linea Standard: €15M (35%)
        - Servizi: €9.5M (23%)
        
        Top 5 clienti rappresentano il 35% del fatturato totale.
        ASP (Average Selling Price) aumentato del 5% grazie al mix favorevole.
        Order backlog a fine trimestre: €65M
        
        Pipeline commerciale: €120M di opportunità identificate per Q4.
        """
    },
    {
        "name": "Report_Magazzino_Ottobre.pdf",
        "text": """
        ANALISI GIACENZE E LOGISTICA - OTTOBRE 2024
        
        Valore totale giacenze: €8.2M
        Giorni di giacenza media: 45 (target: 30)
        
        KPI Logistici:
        - OTIF (On Time In Full): 92%
        - Indice di rotazione: 8.1x
        - Tasso resi: 2.3%
        
        Analisi SKU:
        - 15 SKU in rottura di stock nel mese
        - €1.2M di scorte obsolete identificate (14.6% del totale)
        - Lead time medio fornitori: 21 giorni
        
        Livello di servizio: 94% (target 95%)
        """
    },
    {
        "name": "Contratto_Fornitura_2024.docx",
        "text": """
        CONTRATTO DI FORNITURA
        
        Art. 1 - PARTI
        Tra la società ALFA SpA (Fornitore) e BETA Srl (Cliente)
        
        Art. 2 - OGGETTO
        Fornitura di componenti industriali secondo specifiche tecniche allegate.
        
        Art. 3 - DURATA
        Il contratto ha durata di 24 mesi con decorrenza dal 01/01/2024 e scadenza 31/12/2025.
        Rinnovo automatico salvo disdetta con preavviso di 90 giorni.
        
        Art. 4 - CORRISPETTIVI
        Importo annuo stimato €500.000 + IVA
        Pagamento a 60 giorni fine mese data fattura
        
        Art. 5 - SLA E PENALI
        Tempo di consegna: max 15 giorni lavorativi
        Penale per ritardo: 0.5% del valore dell'ordine per ogni giorno di ritardo
        
        Art. 6 - LEGGE APPLICABILE E FORO COMPETENTE
        Il presente contratto è regolato dalla legge italiana.
        Foro competente: Tribunale di Milano
        """
    },
    {
        "name": "Presentazione_Strategia_2025.pptx",
        "text": """
        PIANO STRATEGICO 2025
        
        Slide 1: Executive Summary
        - Obiettivo crescita fatturato: +20% YoY
        - Espansione in 3 nuovi mercati
        - Investimento in digitalizzazione: €5M
        
        Slide 5: Roadmap Implementazione
        Q1: Launch nuovo prodotto flagship
        Q2: Apertura filiale Germania
        Q3: Go-live nuovo ERP
        Q4: Consolidamento e pianificazione 2026
        
        Slide 12: KPI e Milestone
        - ROE target: 15%
        - Market share obiettivo: 25%
        - Customer satisfaction: >4.5/5
        
        Company Profile: Leader di mercato nel settore B2B
        """
    },
    {
        "name": "Documento_Generico.txt",
        "text": """
        Questo è un documento di esempio che non rientra in categorie specifiche.
        Contiene informazioni varie sull'azienda e le sue attività.
        
        L'azienda opera nel settore manifatturiero da oltre 20 anni.
        Ha 150 dipendenti distribuiti in 3 sedi.
        
        Mission: Fornire soluzioni innovative per i nostri clienti.
        Vision: Diventare il riferimento del settore entro il 2030.
        """
    }
]

def run_tests():
    """Esegue i test del prompt router."""
    print("=" * 80)
    print("TEST PROMPT ROUTER - ANALISI DEI RISULTATI")
    print("=" * 80)
    print()
    
    # Mostra prompt disponibili
    print("TIPI DI PROMPT DISPONIBILI:")
    for prompt_type in get_available_prompts():
        print(f"  - {prompt_type}: {get_prompt_description(prompt_type)}")
    print()
    print("=" * 80)
    
    # Test ogni documento
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTEST {i}: {test_case['name']}")
        print("-" * 40)
        
        # Analizza con prompt router
        prompt_name, prompt_text, debug_info = choose_prompt(
            test_case["name"],
            test_case["text"]
        )
        
        # Mostra risultati
        print(f"Prompt scelto: {prompt_name.upper()}")
        print(f"Punteggi calcolati:")
        for prompt_type, score in debug_info['scores'].items():
            marker = " [SELEZIONATO]" if prompt_type == prompt_name else ""
            print(f"  - {prompt_type}: {score:.2f}{marker}")
        
        print(f"Lunghezza testo: {debug_info['length_chars']} caratteri")
        
        # Mostra prime righe del prompt generato
        prompt_lines = prompt_text.split('\n')[:5]
        print(f"Inizio del prompt generato:")
        for line in prompt_lines:
            if line.strip():
                print(f"  {line[:80]}...")
                break
    
    print("\n" + "=" * 80)
    print("TEST COMPLETATO CON SUCCESSO!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()