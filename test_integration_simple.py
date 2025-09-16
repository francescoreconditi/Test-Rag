# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-01-16
# Scopo: Test semplice di integrazione senza download modelli
# ============================================

"""Test di integrazione semplice per verificare che i servizi siano stati integrati correttamente."""

import sys


def test_imports():
    """Test di importazione dei moduli."""
    print("Testing imports...")

    try:
        from services.reranking_service import get_reranking_service
        print("SUCCESS: Reranking service imported")
    except Exception as e:
        print(f"ERROR: Cannot import reranking service: {e}")
        return False

    try:
        from services.contextual_retrieval_service import get_contextual_retrieval_service
        print("SUCCESS: Contextual retrieval service imported")
    except Exception as e:
        print(f"ERROR: Cannot import contextual service: {e}")
        return False

    return True


def test_rag_integration():
    """Test di integrazione con RAG engine."""
    print("\nTesting RAG integration...")

    try:
        from services.rag_engine import RAGEngine
        print("SUCCESS: RAG engine imported")

        # Test initialization without actually loading models
        rag = RAGEngine()

        # Check if quality services are initialized (may be None if dependencies missing)
        has_reranking = hasattr(rag, 'reranking_service')
        has_contextual = hasattr(rag, 'contextual_service')
        has_enhanced_query = hasattr(rag, 'query_enhanced')

        print(f"Has reranking service attribute: {has_reranking}")
        print(f"Has contextual service attribute: {has_contextual}")
        print(f"Has enhanced query method: {has_enhanced_query}")

        if has_enhanced_query:
            print("SUCCESS: Enhanced query method integrated")
        else:
            print("ERROR: Enhanced query method missing")
            return False

        return True

    except Exception as e:
        print(f"ERROR: RAG integration test failed: {e}")
        return False


def test_configuration():
    """Test della configurazione delle funzionalità di qualità."""
    print("\nTesting configuration...")

    try:
        from services import rag_engine

        # Check if quality features flag exists
        quality_available = hasattr(rag_engine, 'QUALITY_FEATURES_AVAILABLE')
        print(f"Quality features flag exists: {quality_available}")

        if quality_available:
            print(f"Quality features available: {rag_engine.QUALITY_FEATURES_AVAILABLE}")

        return True

    except Exception as e:
        print(f"ERROR: Configuration test failed: {e}")
        return False


def main():
    """Esegue tutti i test."""
    print("Simple Integration Test for Quality Enhancements")
    print("=" * 50)

    tests = [
        ("Import Test", test_imports),
        ("RAG Integration Test", test_rag_integration),
        ("Configuration Test", test_configuration),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"ERROR: {test_name} crashed: {e}")
            results[test_name] = False

    print("\n" + "=" * 50)
    print("Test Results:")

    for test_name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"  {test_name}: {status}")

    passed = sum(results.values())
    total = len(results)

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("All integration tests passed!")
        return True
    else:
        print("Some tests failed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)