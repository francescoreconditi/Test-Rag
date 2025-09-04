"""Script per testare la pulizia del database vettoriale."""

from services.rag_engine import RAGEngine
import logging

# Configura logging per vedere i dettagli
logging.basicConfig(level=logging.INFO)

def test_database_cleanup():
    """Testa la funzionalità di pulizia del database."""
    
    print("🧪 Test Pulizia Database Vettoriale\n")
    
    try:
        # Inizializza RAG Engine
        print("1. Inizializzando RAG Engine...")
        rag_engine = RAGEngine()
        
        # Controlla stato iniziale
        print("2. Controlliamo lo stato iniziale...")
        initial_stats = rag_engine.get_index_stats()
        print(f"   📊 Vettori iniziali: {initial_stats.get('total_vectors', 0)}")
        
        if initial_stats.get('total_vectors', 0) > 0:
            print("3. Database contiene documenti. Testo pulizia...")
            
            # Testa pulizia
            success = rag_engine.delete_documents("*")
            
            if success:
                print("   ✅ Pulizia completata con successo!")
                
                # Verifica stato finale
                print("4. Verificiamo il risultato...")
                final_stats = rag_engine.get_index_stats()
                final_vectors = final_stats.get('total_vectors', 0)
                print(f"   📊 Vettori finali: {final_vectors}")
                
                if final_vectors == 0:
                    print("   🎉 SUCCESS: Database completamente pulito!")
                    return True
                else:
                    print("   ❌ ERRORE: Database non completamente pulito!")
                    return False
            else:
                print("   ❌ ERRORE: Pulizia fallita!")
                return False
        else:
            print("3. Database già vuoto - testo creazione/eliminazione...")
            
            # Testa che la collezione venga gestita correttamente
            success = rag_engine.delete_documents("*")
            if success:
                stats = rag_engine.get_index_stats()
                print(f"   ✅ Collezione ricreata: {stats.get('total_vectors', 0)} vettori")
                return True
            else:
                print("   ❌ ERRORE nella gestione collezione")
                return False
                
    except Exception as e:
        print(f"❌ ERRORE durante il test: {str(e)}")
        return False

def show_cleanup_instructions():
    """Mostra le istruzioni per la pulizia."""
    
    print("\n📋 ISTRUZIONI PER LA PULIZIA:")
    print("=" * 35)
    
    print("\n🔧 METODO 1 - Via interfaccia (Raccomandato):")
    print("   1. Avvia: streamlit run app.py")
    print("   2. Vai su ⚙️ Impostazioni")
    print("   3. Clicca 'Pulisci Database Vettoriale'")
    print("   4. Riavvia l'app")
    print("   5. ✅ Dovrebbe mostrare 0 vettori")
    
    print("\n🧪 METODO 2 - Test automatico:")
    print("   1. Esegui: python test_database_cleanup.py")
    print("   2. ✅ Vedi il risultato del test")
    
    print("\n🔍 COSA VERIFICARE:")
    print("   • Log deve mostrare 'Collection business_documents deleted successfully'")
    print("   • Log deve mostrare 'Created fresh collection: business_documents'")
    print("   • Statistiche finali devono mostrare 0 vettori")
    print("   • Riavvio app deve mostrare 'Created new empty index'")

def main():
    """Esegui test completo."""
    success = test_database_cleanup()
    show_cleanup_instructions()
    
    print(f"\n📊 RISULTATO TEST: {'✅ SUCCESSO' if success else '❌ FALLITO'}")
    
    if not success:
        print("\n💡 SE IL TEST FALLISCE:")
        print("   • Controlla che Qdrant sia in esecuzione")
        print("   • Verifica la connessione in config/settings.py")  
        print("   • Guarda i log per errori specifici")

if __name__ == "__main__":
    main()