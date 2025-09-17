# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-01-16
# Scopo: Servizio di reranking avanzato per migliorare qualità RAG
# ============================================

"""
Advanced Reranking Service per migliorare la qualità delle risposte RAG.
Utilizza Cross-Encoder models per riordinare i risultati di ricerca.
"""

import logging
from typing import Dict, List, Optional, Tuple
import time

try:
    from sentence_transformers import CrossEncoder

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    CrossEncoder = None

logger = logging.getLogger(__name__)


class RerankingService:
    """Servizio di reranking che utilizza Cross-Encoder per migliorare la rilevanza dei risultati."""

    # Modelli disponibili per il reranking
    MODELS = {
        "default": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "fast": "cross-encoder/ms-marco-MiniLM-L-2-v2",
        "accurate": "cross-encoder/ms-marco-electra-base",
        "multilingual": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    }

    def __init__(self, model_name: str = "default", confidence_threshold: float = 0.5, lazy_load: bool = True):
        """Initialize reranking service.

        Args:
            model_name: Nome del modello da utilizzare (default, fast, accurate, multilingual)
            confidence_threshold: Soglia di confidence per filtrare risultati di bassa qualità
            lazy_load: Se True, carica il modello solo quando necessario
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.model_loaded = False
        self.lazy_load = lazy_load

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers not available. Reranking will be disabled.")
            return

        if not lazy_load:
            self._load_model()

    def _load_model(self):
        """Load the reranking model lazily."""
        if self.model_loaded:
            return

        try:
            model_path = self.MODELS.get(self.model_name, self.MODELS["default"])
            logger.info(f"Loading reranking model: {model_path}")

            start_time = time.time()
            self.model = CrossEncoder(model_path)
            load_time = time.time() - start_time

            logger.info(f"Reranking model loaded in {load_time:.2f}s")
            self.model_loaded = True

        except Exception as e:
            logger.error(f"Failed to load reranking model: {e}")
            self.model = None
            self.model_loaded = False

    def is_available(self) -> bool:
        """Check if reranking service is available.

        Returns:
            True if reranking is available, False otherwise
        """
        return SENTENCE_TRANSFORMERS_AVAILABLE and self.model_loaded

    def rerank_documents(self, query: str, documents: List[Dict], top_k: Optional[int] = None) -> List[Dict]:
        """Rerank documents based on query relevance.

        Args:
            query: User query
            documents: List of document dictionaries with 'content' and optional metadata
            top_k: Number of top documents to return. If None, returns all with scores

        Returns:
            List of reranked documents with added 'rerank_score' field
        """
        # Load model if lazy loading is enabled
        if self.lazy_load and not self.model_loaded and SENTENCE_TRANSFORMERS_AVAILABLE:
            self._load_model()

        if not self.is_available():
            logger.warning("Reranking not available, returning original order")
            return documents[:top_k] if top_k else documents

        if not documents:
            return []

        try:
            start_time = time.time()

            # Prepare query-document pairs for reranking
            pairs = []
            valid_docs = []

            for doc in documents:
                content = doc.get("content", doc.get("text", str(doc)))
                if content and content.strip():
                    pairs.append([query, content])
                    valid_docs.append(doc)

            if not pairs:
                logger.warning("No valid documents for reranking")
                return []

            # Get relevance scores
            scores = self.model.predict(pairs)

            # Add scores to documents and filter by threshold
            scored_docs = []
            for doc, score in zip(valid_docs, scores):
                # Convert numpy float to Python float for JSON serialization
                rerank_score = float(score)

                # Only include documents above confidence threshold
                if rerank_score >= self.confidence_threshold:
                    doc_copy = doc.copy()
                    doc_copy["rerank_score"] = rerank_score
                    scored_docs.append(doc_copy)

            # Sort by rerank score (descending)
            scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)

            # Apply top_k limit
            if top_k:
                scored_docs = scored_docs[:top_k]

            rerank_time = time.time() - start_time
            logger.info(f"Reranked {len(documents)} documents to {len(scored_docs)} in {rerank_time:.3f}s")

            return scored_docs

        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            # Fallback to original order
            return documents[:top_k] if top_k else documents

    def rerank_rag_results(self, query: str, rag_results: List[Dict], top_k: int = 5) -> List[Dict]:
        """Rerank RAG search results.

        Args:
            query: Original user query
            rag_results: Results from RAG vector search with 'content', 'score', 'metadata'
            top_k: Number of top results to return

        Returns:
            Reranked results with combined scoring
        """
        if not rag_results:
            return []

        # Rerank based on content
        reranked = self.rerank_documents(query, rag_results, top_k=None)

        if not reranked:
            return rag_results[:top_k]

        # Combine original vector score with rerank score
        for doc in reranked:
            original_score = doc.get("score", 0.0)
            rerank_score = doc.get("rerank_score", 0.0)

            # Weighted combination: 60% rerank, 40% original vector score
            combined_score = 0.6 * rerank_score + 0.4 * original_score
            doc["combined_score"] = combined_score
            doc["original_vector_score"] = original_score

        # Sort by combined score
        reranked.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

        return reranked[:top_k]

    def get_model_info(self) -> Dict:
        """Get information about the loaded model.

        Returns:
            Dictionary with model information
        """
        return {
            "available": self.is_available(),
            "model_name": self.model_name,
            "model_path": self.MODELS.get(self.model_name, "unknown"),
            "confidence_threshold": self.confidence_threshold,
            "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE,
        }

    def set_confidence_threshold(self, threshold: float):
        """Update confidence threshold.

        Args:
            threshold: New confidence threshold (0.0 to 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
            logger.info(f"Updated confidence threshold to {threshold}")
        else:
            logger.warning(f"Invalid confidence threshold: {threshold}. Must be between 0.0 and 1.0")

    def benchmark_model(self, test_queries: List[str], test_documents: List[str]) -> Dict:
        """Benchmark reranking performance.

        Args:
            test_queries: List of test queries
            test_documents: List of test documents

        Returns:
            Performance metrics
        """
        if not self.is_available():
            return {"error": "Reranking not available"}

        try:
            start_time = time.time()

            # Test with all query-document combinations
            total_pairs = 0
            for query in test_queries:
                docs = [{"content": doc} for doc in test_documents]
                self.rerank_documents(query, docs)
                total_pairs += len(docs)

            total_time = time.time() - start_time

            return {
                "total_queries": len(test_queries),
                "total_documents": len(test_documents),
                "total_pairs_processed": total_pairs,
                "total_time_seconds": total_time,
                "avg_time_per_query": total_time / len(test_queries),
                "pairs_per_second": total_pairs / total_time,
                "model_info": self.get_model_info(),
            }

        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            return {"error": str(e)}


# Global reranking service instance
_reranking_service = None


def get_reranking_service(model_name: str = "default") -> RerankingService:
    """Get or create global reranking service instance.

    Args:
        model_name: Model to use for reranking

    Returns:
        RerankingService instance
    """
    global _reranking_service

    if _reranking_service is None or _reranking_service.model_name != model_name:
        _reranking_service = RerankingService(model_name=model_name)

    return _reranking_service
