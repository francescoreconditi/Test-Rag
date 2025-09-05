# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-05
# Scopo: Test del prompt generale
# ============================================

"""Test del prompt generale per identificare il problema."""

from services.prompt_router import PROMPT_GENERAL

def test_general_prompt():
    """Test del prompt generale."""
    print("=" * 80)
    print("TEST PROMPT GENERALE")
    print("=" * 80)
    
    # Testo di test
    test_text = """
    REPORT DIVISIONE SOFTWARE - APRILE 2025
    
    La divisione software ha registrato ricavi per €5,214,095 nel mese di aprile 2025,
    con una crescita del 7,4% rispetto al budget. L'EBITDA si è attestato a €547,643
    (margine del 10,5%).
    
    I ricavi da servizio hanno mostrato performance particolarmente positive,
    con un incremento del 23,4% rispetto al budget.
    """
    
    file_name = "4.Report_SWD_Aprile 2025.pdf"
    
    print("1. Testo di input:")
    print(f"   Lunghezza: {len(test_text)} caratteri")
    print(f"   Preview: {test_text[:200]}...")
    
    print("\n2. Generazione prompt generale...")
    prompt = PROMPT_GENERAL(file_name, test_text)
    
    print("3. Prompt generato:")
    print(f"   Lunghezza: {len(prompt)} caratteri")
    print(f"   Prime 500 caratteri:")
    print(prompt[:500] + "...")
    
    print("\n4. Verifica che il testo sia incluso nel prompt...")
    if test_text.strip() in prompt:
        print("   ✓ Testo incluso correttamente nel prompt")
    else:
        print("   ✗ PROBLEMA: Testo NON trovato nel prompt!")
        
        # Controlliamo se almeno parte del testo c'è
        if "Report" in prompt.upper():
            print("   - Trovata parola 'Report' nel prompt")
        if "5,214,095" in prompt or "5.214.095" in prompt:
            print("   - Trovati i numeri nel prompt")
        if "software" in prompt.lower():
            print("   - Trovata parola 'software' nel prompt")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETATO")
    print("=" * 80)

if __name__ == "__main__":
    test_general_prompt()