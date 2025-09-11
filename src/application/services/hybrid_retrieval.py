"""Hybrid retrieval service combining BM25 and embeddings."""

from dataclasses import dataclass
import logging
import os
from typing import Any, Optional

import numpy as np
from openai import OpenAI

try:
    from rank_bm25 import BM25Okapi

    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

try:
    from sentence_transformers import CrossEncoder

    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False

from pathlib import Path
import pickle

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result of hybrid retrieval."""

    content: str
    score: float
    bm25_score: float
    embedding_score: float
    rerank_score: Optional[float]
    metadata: dict[str, Any]
    source_id: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "score": self.score,
            "bm25_score": self.bm25_score,
            "embedding_score": self.embedding_score,
            "rerank_score": self.rerank_score,
            "metadata": self.metadata,
            "source_id": self.source_id,
        }


@dataclass
class IndexedDocument:
    """Document in the hybrid index."""

    content: str
    embedding: np.ndarray
    tokens: list[str]
    metadata: dict[str, Any]
    doc_id: str


class HybridRetriever:
    """Hybrid retrieval combining BM25 keyword search and embedding similarity."""

    def __init__(
        self,
        embedding_model_name: str = "text-embedding-3-small",
        reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-2-v2",
        cache_dir: str = "data/cache",
        openai_api_key: Optional[str] = None,
    ):
        """Initialize hybrid retriever."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Initialize OpenAI client for embeddings
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
            self.embedding_model_name = embedding_model_name
            logger.info(f"Initialized OpenAI embeddings with model: {embedding_model_name}")
        else:
            logger.error("No OpenAI API key provided, embedding functionality disabled")
            self.openai_client = None
            self.embedding_model_name = None

        # Load reranker model
        if RERANKER_AVAILABLE:
            try:
                self.reranker = CrossEncoder(reranker_model_name)
                logger.info(f"Loaded reranker model: {reranker_model_name}")
            except Exception as e:
                logger.warning(f"Failed to load reranker {reranker_model_name}: {e}")
                self.reranker = None
        else:
            logger.warning("CrossEncoder not available, reranker functionality disabled")
            self.reranker = None

        # Index components
        self.documents: list[IndexedDocument] = []
        self.bm25_index: Optional[BM25Okapi] = None
        self.doc_embeddings: Optional[np.ndarray] = None

        # Search parameters
        self.bm25_weight = 0.3  # Weight for BM25 scores
        self.embedding_weight = 0.7  # Weight for embedding scores
        self.use_reranking = True  # Whether to use cross-encoder reranking

    def add_documents(
        self, documents: list[dict[str, Any]], content_field: str = "content", metadata_field: str = "metadata"
    ) -> None:
        """Add documents to the hybrid index."""
        new_docs = []

        for i, doc in enumerate(documents):
            content = doc.get(content_field, "")
            if not content:
                continue

            metadata = doc.get(metadata_field, {})
            doc_id = doc.get("id", f"doc_{len(self.documents) + i}")

            # Tokenize for BM25
            tokens = self._tokenize(content)

            # Generate embedding
            embedding = None
            if self.openai_client:
                try:
                    response = self.openai_client.embeddings.create(
                        model=self.embedding_model_name,
                        input=content[:8191]  # OpenAI max input length
                    )
                    embedding = np.array(response.data[0].embedding)
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for doc {doc_id}: {e}")
                    embedding = np.zeros(1536)  # Fallback empty embedding for text-embedding-3-small

            indexed_doc = IndexedDocument(
                content=content, embedding=embedding, tokens=tokens, metadata=metadata, doc_id=doc_id
            )

            new_docs.append(indexed_doc)

        self.documents.extend(new_docs)
        logger.info(f"Added {len(new_docs)} documents to hybrid index")

        # Rebuild indices
        self._build_bm25_index()
        self._build_embedding_index()

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization for BM25."""
        import re

        # Basic tokenization - can be improved with spaCy/NLTK
        text = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = text.split()
        return [token for token in tokens if len(token) > 2]  # Filter short tokens

    def _build_bm25_index(self) -> None:
        """Build BM25 index from documents."""
        if not self.documents:
            return

        if BM25_AVAILABLE:
            corpus = [doc.tokens for doc in self.documents]
            self.bm25_index = BM25Okapi(corpus)
            logger.info(f"Built BM25 index with {len(corpus)} documents")
        else:
            logger.warning("BM25 not available, BM25 indexing disabled")
            self.bm25_index = None

    def _build_embedding_index(self) -> None:
        """Build embedding index from documents."""
        if not self.documents or not self.openai_client:
            return

        embeddings = []
        for doc in self.documents:
            if doc.embedding is not None:
                embeddings.append(doc.embedding)
            else:
                # Generate embedding if missing
                try:
                    response = self.openai_client.embeddings.create(
                        model=self.embedding_model_name,
                        input=doc.content[:8191]  # OpenAI max input length
                    )
                    emb = np.array(response.data[0].embedding)
                    embeddings.append(emb)
                    doc.embedding = emb
                except Exception as e:
                    logger.warning(f"Failed to generate embedding: {e}")
                    embeddings.append(np.zeros(1536))  # text-embedding-3-small dimensions

        if embeddings:
            self.doc_embeddings = np.vstack(embeddings)
            logger.info(f"Built embedding index with {self.doc_embeddings.shape} shape")

    def search(
        self, query: str, top_k: int = 10, bm25_top_k: int = 50, embedding_top_k: int = 50, final_rerank_k: int = 10
    ) -> list[RetrievalResult]:
        """Perform hybrid search."""
        if not self.documents:
            logger.warning("No documents in hybrid index")
            return []

        # Step 1: BM25 retrieval
        bm25_results = self._bm25_search(query, top_k=bm25_top_k)

        # Step 2: Embedding similarity search
        embedding_results = self._embedding_search(query, top_k=embedding_top_k)

        # Step 3: Combine scores
        combined_results = self._combine_scores(bm25_results, embedding_results, top_k)

        # Step 4: Reranking (optional)
        if self.use_reranking and self.reranker and len(combined_results) > 1:
            combined_results = self._rerank_results(query, combined_results, final_rerank_k)

        return combined_results[:top_k]

    def _bm25_search(self, query: str, top_k: int = 50) -> list[tuple[int, float]]:
        """Search using BM25."""
        if not self.bm25_index:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25_index.get_scores(query_tokens)

        # Get top-k results
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = [(idx, scores[idx]) for idx in top_indices if scores[idx] > 0]

        logger.debug(f"BM25 found {len(results)} results")
        return results

    def _embedding_search(self, query: str, top_k: int = 50) -> list[tuple[int, float]]:
        """Search using embedding similarity."""
        if not self.openai_client or self.doc_embeddings is None:
            return []

        try:
            # Generate query embedding
            response = self.openai_client.embeddings.create(
                model=self.embedding_model_name,
                input=query[:8191]  # OpenAI max input length
            )
            query_embedding = np.array(response.data[0].embedding)

            # Calculate cosine similarities
            similarities = np.dot(self.doc_embeddings, query_embedding) / (
                np.linalg.norm(self.doc_embeddings, axis=1) * np.linalg.norm(query_embedding)
            )

            # Get top-k results
            top_indices = np.argsort(similarities)[::-1][:top_k]
            results = [(idx, similarities[idx]) for idx in top_indices if similarities[idx] > 0]

            logger.debug(f"Embedding search found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Embedding search failed: {e}")
            return []

    def _combine_scores(
        self, bm25_results: list[tuple[int, float]], embedding_results: list[tuple[int, float]], top_k: int
    ) -> list[RetrievalResult]:
        """Combine BM25 and embedding scores."""

        # Normalize scores to [0, 1] range
        bm25_scores = {}
        if bm25_results:
            max_bm25 = max(score for _, score in bm25_results)
            bm25_scores = {idx: score / max_bm25 for idx, score in bm25_results if max_bm25 > 0}

        embedding_scores = {}
        if embedding_results:
            max_embedding = max(score for _, score in embedding_results)
            embedding_scores = {idx: score / max_embedding for idx, score in embedding_results if max_embedding > 0}

        # Combine scores
        combined_scores = {}
        all_indices = set(bm25_scores.keys()) | set(embedding_scores.keys())

        for idx in all_indices:
            bm25_score = bm25_scores.get(idx, 0.0)
            embedding_score = embedding_scores.get(idx, 0.0)

            # Weighted combination
            combined_score = self.bm25_weight * bm25_score + self.embedding_weight * embedding_score

            combined_scores[idx] = (combined_score, bm25_score, embedding_score)

        # Sort by combined score and create results
        sorted_indices = sorted(combined_scores.keys(), key=lambda x: combined_scores[x][0], reverse=True)

        results = []
        for idx in sorted_indices[:top_k]:
            if idx >= len(self.documents):
                continue

            doc = self.documents[idx]
            combined_score, bm25_score, embedding_score = combined_scores[idx]

            result = RetrievalResult(
                content=doc.content,
                score=combined_score,
                bm25_score=bm25_score,
                embedding_score=embedding_score,
                rerank_score=None,
                metadata=doc.metadata,
                source_id=doc.doc_id,
            )
            results.append(result)

        return results

    def _rerank_results(self, query: str, results: list[RetrievalResult], top_k: int) -> list[RetrievalResult]:
        """Rerank results using cross-encoder."""
        if not self.reranker or len(results) <= 1:
            return results

        try:
            # Prepare query-document pairs
            pairs = [(query, result.content) for result in results]

            # Get reranking scores
            rerank_scores = self.reranker.predict(pairs, convert_to_numpy=True)

            # Update results with reranking scores
            for result, rerank_score in zip(results, rerank_scores):
                result.rerank_score = float(rerank_score)
                # Use reranking score as final score
                result.score = float(rerank_score)

            # Sort by reranking score
            results.sort(key=lambda x: x.score, reverse=True)

            logger.debug(f"Reranked {len(results)} results")
            return results[:top_k]

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return results

    def save_index(self, file_path: str) -> None:
        """Save hybrid index to file."""
        try:
            index_data = {
                "documents": self.documents,
                "bm25_weight": self.bm25_weight,
                "embedding_weight": self.embedding_weight,
                "doc_count": len(self.documents),
            }

            with open(file_path, "wb") as f:
                pickle.dump(index_data, f)

            logger.info(f"Saved hybrid index with {len(self.documents)} documents to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def load_index(self, file_path: str) -> bool:
        """Load hybrid index from file."""
        try:
            with open(file_path, "rb") as f:
                index_data = pickle.load(f)

            self.documents = index_data["documents"]
            self.bm25_weight = index_data.get("bm25_weight", 0.3)
            self.embedding_weight = index_data.get("embedding_weight", 0.7)

            # Rebuild indices
            self._build_bm25_index()
            self._build_embedding_index()

            logger.info(f"Loaded hybrid index with {len(self.documents)} documents")
            return True

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    def clear_index(self) -> None:
        """Clear the hybrid index."""
        self.documents.clear()
        self.bm25_index = None
        self.doc_embeddings = None
        logger.info("Cleared hybrid index")

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        return {
            "document_count": len(self.documents),
            "has_bm25_index": self.bm25_index is not None,
            "has_embedding_index": self.doc_embeddings is not None,
            "embedding_dimension": self.doc_embeddings.shape[1] if self.doc_embeddings is not None else 0,
            "bm25_weight": self.bm25_weight,
            "embedding_weight": self.embedding_weight,
            "reranking_enabled": self.use_reranking and self.reranker is not None,
        }

    def optimize_weights(
        self,
        queries: list[str],
        relevance_scores: list[list[float]],
        weight_range: tuple[float, float] = (0.1, 0.9),
        steps: int = 10,
    ) -> tuple[float, float]:
        """Optimize BM25 and embedding weights based on relevance feedback."""
        best_weights = (self.bm25_weight, self.embedding_weight)
        best_score = 0.0

        step_size = (weight_range[1] - weight_range[0]) / steps

        for i in range(steps + 1):
            bm25_w = weight_range[0] + i * step_size
            emb_w = 1.0 - bm25_w

            # Temporarily set weights
            orig_bm25_w, orig_emb_w = self.bm25_weight, self.embedding_weight
            self.bm25_weight, self.embedding_weight = bm25_w, emb_w

            # Evaluate on queries
            total_score = 0.0
            for query, rel_scores in zip(queries, relevance_scores):
                results = self.search(query, top_k=len(rel_scores))
                # Simple NDCG-like scoring
                dcg = sum(rel_score / np.log2(pos + 2) for pos, rel_score in enumerate(rel_scores[: len(results)]))
                total_score += dcg

            if total_score > best_score:
                best_score = total_score
                best_weights = (bm25_w, emb_w)

            # Restore original weights
            self.bm25_weight, self.embedding_weight = orig_bm25_w, orig_emb_w

        # Set optimal weights
        self.bm25_weight, self.embedding_weight = best_weights
        logger.info(f"Optimized weights: BM25={self.bm25_weight:.3f}, Embedding={self.embedding_weight:.3f}")

        return best_weights
