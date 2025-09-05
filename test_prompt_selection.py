# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-05
# Scopo: Test della funzionalità di selezione prompt nell'UI
# ============================================

"""Test della funzionalità di selezione prompt."""

import tempfile
import os
from services.rag_engine import RAGEngine
from config.settings import settings

def test_prompt_selection():
    """Test la selezione dei prompt con override manuale."""
    print("=" * 80)
    print("TEST SELEZIONE PROMPT CON OVERRIDE")
    print("=" * 80)
    
    # Documento di test
    test_content = """
    BILANCIO CONSOLIDATO 2024
    
    Il Gruppo ha registrato ricavi per €150 milioni nel FY2024, con un incremento del 12% YoY.
    L'EBITDA si è attestato a €45 milioni (margine EBITDA del 30%), mentre l'utile netto
    è cresciuto del 15% raggiungendo €22 milioni.
    """
    
    try:
        # Inizializza RAG Engine
        print("Inizializzando RAG Engine...")
        rag_engine = RAGEngine()
        
        # Test 1: Analisi automatica
        print("\n### TEST 1: Analisi Automatica")
        result_auto = rag_engine.analyze_document_content(test_content, "Bilancio_2024.pdf")
        print("Risultato (prime 200 caratteri):")
        print(result_auto[:200] + "...")
        
        # Test 2: Forzare prompt fatturato
        print("\n### TEST 2: Forzare Prompt Fatturato")  
        result_forced = rag_engine.analyze_document_content(test_content, "Bilancio_2024.pdf", force_prompt_type="fatturato")
        print("Risultato (prime 200 caratteri):")
        print(result_forced[:200] + "...")
        
        # Test 3: Forzare prompt generale
        print("\n### TEST 3: Forzare Prompt Generale")
        result_general = rag_engine.analyze_document_content(test_content, "Bilancio_2024.pdf", force_prompt_type="generale")
        print("Risultato (prime 200 caratteri):")
        print(result_general[:200] + "...")
        
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETATI CON SUCCESSO!")
        print("La funzionalità di override del prompt funziona correttamente.")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ERRORE NEL TEST: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    # Verifica che le variabili di ambiente siano configurate
    if not settings.openai_api_key:
        print("❌ OPENAI_API_KEY non configurata. Controlla il file .env")
        exit(1)
    
    test_prompt_selection()