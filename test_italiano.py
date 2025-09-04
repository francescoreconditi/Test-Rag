"""Script di test per verificare che l'applicazione funzioni in italiano."""

import pandas as pd
from services.csv_analyzer import CSVAnalyzer
from services.llm_service import LLMService
import os

def test_csv_analysis():
    """Test analisi CSV in italiano."""
    print("🧪 Test Analisi CSV...")
    
    # Carica i dati di esempio
    analyzer = CSVAnalyzer()
    df = analyzer.load_csv("data/esempio_vendite.csv")
    
    # Esegui analisi
    analysis = analyzer.analyze_balance_sheet(df, year_column='anno', revenue_column='fatturato')
    
    print(f"✅ Analisi completata:")
    print(f"   - Summary metriche: {len(analysis.get('summary', {}))}")
    print(f"   - Insights trovate: {len(analysis.get('insights', []))}")
    print(f"   - Trends disponibili: {'yoy_growth' in analysis.get('trends', {})}")
    
    # Mostra insights in italiano
    print("\n📝 Insights generate:")
    for i, insight in enumerate(analysis.get('insights', []), 1):
        print(f"   {i}. {insight}")
    
    return analysis

def test_llm_service():
    """Test servizio LLM in italiano."""
    print("\n🧪 Test Servizio LLM...")
    
    # Dati di esempio per il test
    test_analysis = {
        'summary': {'fatturato_totale': 5500000.0, 'crescita_media': 8.5},
        'trends': {'yoy_growth': [{'year': 2023, 'growth_percentage': 8.5, 'absolute_change': 125000}]},
        'insights': ['Rilevato forte trend di crescita positiva', 'Reddittività migliorata']
    }
    
    try:
        # Inizializza servizio LLM
        llm_service = LLMService()
        
        # Test generazione insights
        print("   Generando insights aziendali...")
        insights = llm_service.generate_business_insights(test_analysis)
        
        # Verifica che la risposta sia in italiano
        italian_terms = ['fatturato', 'crescita', 'raccomandazioni', 'analisi', 'azienda', 'strategico']
        english_terms = ['revenue', 'growth', 'recommendations', 'analysis', 'business', 'strategic']
        
        insights_lower = insights.lower()
        italian_found = sum(1 for term in italian_terms if term in insights_lower)
        english_found = sum(1 for term in english_terms if term in insights_lower)
        
        print(f"   ✅ Insights generate (lunghezza: {len(insights)} caratteri)")
        print(f"   📊 Termini italiani trovati: {italian_found}/{len(italian_terms)}")
        print(f"   📊 Termini inglesi trovati: {english_found}/{len(english_terms)}")
        
        if english_found > 0:
            print("   ⚠️ ATTENZIONE: Trovati termini inglesi!")
            
        # Mostra un estratto
        print(f"\n📄 Estratto risposta:")
        print(f"   {insights[:200]}...")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Errore nel test LLM: {str(e)}")
        return False

def main():
    """Esegui tutti i test."""
    print("🚀 Avvio Test Sistema BI RAG in Italiano\n")
    
    # Test 1: Analisi CSV
    analysis = test_csv_analysis()
    
    # Test 2: LLM Service (solo se disponibile API key)
    if os.getenv('OPENAI_API_KEY'):
        llm_success = test_llm_service()
        print(f"\n📊 Test LLM: {'✅ Successo' if llm_success else '❌ Fallito'}")
    else:
        print("\n⚠️ OPENAI_API_KEY non trovata, saltando test LLM")
    
    print("\n🎉 Test completati! Ora puoi avviare l'app con: streamlit run app.py")

if __name__ == "__main__":
    main()