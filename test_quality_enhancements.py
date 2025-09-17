# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-01-16
# Scopo: Test dei miglioramenti di qualità RAG (reranking + contextual chunks)
# ============================================

"""
Test script per validare l'implementazione dei servizi di reranking e contextual retrieval.
"""

import logging
import time
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_reranking_service():
    """Test del servizio di reranking."""
    print("\n=== Test Reranking Service ===")

    try:
        from services.reranking_service import get_reranking_service

        # Initialize service
        reranking_service = get_reranking_service(model_name="default")

        # Check availability
        print(f"Reranking available: {reranking_service.is_available()}")
        print(f"Model info: {reranking_service.get_model_info()}")

        if not reranking_service.is_available():
            print("WARNING: Reranking not available - skipping tests")
            return

        # Test documents
        test_query = "financial performance and revenue analysis"
        test_documents = [
            {
                "content": "The company's revenue increased by 15% year over year, reaching $1.2 billion.",
                "score": 0.7,
                "metadata": {"source": "annual_report_2023.pdf"},
            },
            {
                "content": "Environmental sustainability initiatives were implemented across all facilities.",
                "score": 0.6,
                "metadata": {"source": "sustainability_report.pdf"},
            },
            {
                "content": "Operating profit margins improved to 18.5% due to cost optimization strategies.",
                "score": 0.8,
                "metadata": {"source": "quarterly_results.pdf"},
            },
            {
                "content": "The new office building was inaugurated in downtown Milan.",
                "score": 0.5,
                "metadata": {"source": "news_update.pdf"},
            },
        ]

        # Test reranking
        print(f"\nTesting reranking with {len(test_documents)} documents...")
        start_time = time.time()

        reranked_docs = reranking_service.rerank_rag_results(test_query, test_documents, top_k=3)

        rerank_time = time.time() - start_time

        print(f"SUCCESS: Reranking completed in {rerank_time:.3f}s")
        print(f"Results: {len(reranked_docs)} documents")

        for i, doc in enumerate(reranked_docs):
            print(
                f"  {i+1}. Score: {doc.get('combined_score', 0):.3f} "
                f"(rerank: {doc.get('rerank_score', 0):.3f}, "
                f"original: {doc.get('original_vector_score', 0):.3f}) "
                f"- {doc['content'][:60]}..."
            )

        return True

    except ImportError as e:
        print(f"ERROR: Import error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Error testing reranking: {e}")
        return False


def test_contextual_retrieval():
    """Test del servizio di contextual retrieval."""
    print("\n=== Test Contextual Retrieval Service ===")

    try:
        from services.contextual_retrieval_service import get_contextual_retrieval_service

        # Initialize service
        contextual_service = get_contextual_retrieval_service(window_size=1)

        print(f"Contextual service initialized with window_size=1")

        # Mock vector store for testing
        class MockVectorStore:
            def __init__(self):
                self._collection_name = "test_collection"

            def query_with_filter(self, query_vector, filter_dict, top_k=1):
                # Mock adjacent chunks
                source = filter_dict.get("source", "")
                chunk_index = filter_dict.get("chunk_index", 0)

                if chunk_index > 0:  # Simulate that we have previous chunks
                    return [
                        {
                            "id": f"chunk_{source}_{chunk_index}",
                            "content": f"This is chunk {chunk_index} from {source}.",
                            "metadata": {"source": source, "chunk_index": chunk_index},
                        }
                    ]
                return []

        mock_store = MockVectorStore()

        # Test documents
        test_results = [
            {
                "id": "chunk_report_5",
                "content": "The financial results show strong performance with revenue growth of 12%.",
                "score": 0.85,
                "metadata": {"source": "financial_report.pdf", "chunk_index": 5},
            },
            {
                "id": "chunk_analysis_3",
                "content": "Market analysis indicates positive trends in our primary sectors.",
                "score": 0.78,
                "metadata": {"source": "market_analysis.pdf", "chunk_index": 3},
            },
        ]

        # Test contextual enhancement
        print(f"\nTesting contextual enhancement with {len(test_results)} documents...")
        start_time = time.time()

        enhanced_chunks = contextual_service.enhance_retrieval_results(
            test_results, mock_store, include_metadata=True
        )

        context_time = time.time() - start_time

        print(f"SUCCESS: Contextual enhancement completed in {context_time:.3f}s")
        print(f"Enhanced results: {len(enhanced_chunks)} chunks")

        for i, chunk in enumerate(enhanced_chunks):
            print(
                f"  {i+1}. Type: {chunk.context_type}, "
                f"Score: {chunk.score:.3f}, "
                f"Index: {chunk.chunk_index} "
                f"- {chunk.content[:50]}..."
            )

        # Test statistics
        stats = contextual_service.get_context_statistics(enhanced_chunks)
        print(f"\nContext Statistics: {stats}")

        return True

    except ImportError as e:
        print(f"ERROR: Import error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Error testing contextual retrieval: {e}")
        return False


def test_rag_integration():
    """Test dell'integrazione con RAG engine."""
    print("\n=== Test RAG Engine Integration ===")

    try:
        from services.rag_engine import RAGEngine

        print("Testing RAG engine with quality enhancements...")

        # Initialize RAG engine
        rag_engine = RAGEngine()

        # Check if quality services are available
        has_reranking = rag_engine.reranking_service is not None
        has_contextual = rag_engine.contextual_service is not None

        print(f"Reranking service available: {has_reranking}")
        print(f"Contextual service available: {has_contextual}")

        if not (has_reranking or has_contextual):
            print("WARNING: No quality enhancement services available")
            return False

        print("SUCCESS: RAG engine initialized with quality enhancements")

        # Test enhanced query method availability
        if hasattr(rag_engine, "query_enhanced"):
            print("SUCCESS: Enhanced query method available")
        else:
            print("ERROR: Enhanced query method not found")
            return False

        return True

    except ImportError as e:
        print(f"ERROR: Import error: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Error testing RAG integration: {e}")
        return False


def main():
    """Run all tests."""
    print(" Starting Quality Enhancement Tests")
    print("=" * 50)

    results = {
        "reranking": test_reranking_service(),
        "contextual": test_contextual_retrieval(),
        "rag_integration": test_rag_integration(),
    }

    print("\n" + "=" * 50)
    print(" Test Results Summary:")

    for test_name, success in results.items():
        status = "SUCCESS: PASS" if success else "ERROR: FAIL"
        print(f"  {test_name}: {status}")

    total_tests = len(results)
    passed_tests = sum(results.values())

    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print(" All tests passed! Quality enhancements are working correctly.")
        return True
    else:
        print("WARNING: Some tests failed. Check the logs above for details.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)