# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-01-16
# Scopo: Servizio di contextual chunks retrieval per migliorare qualità RAG
# ============================================

"""
Contextual Chunks Retrieval Service per migliorare la qualità delle risposte RAG.
Estende i risultati di ricerca includendo chunks adiacenti per maggiore contesto.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class ChunkContext:
    """Rappresenta un chunk con il suo contesto."""

    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    context_type: str  # 'original', 'before', 'after', 'expanded'
    source_file: str
    chunk_index: int


class ContextualRetrievalService:
    """Servizio per il recupero di chunks con contesto esteso."""

    def __init__(self, window_size: int = 1, max_context_chunks: int = 5, similarity_threshold: float = 0.3):
        """Initialize contextual retrieval service.

        Args:
            window_size: Numero di chunks adiacenti da includere (prima e dopo)
            max_context_chunks: Massimo numero di chunks di contesto per documento originale
            similarity_threshold: Soglia minima di similarity per chunks originali
        """
        self.window_size = window_size
        self.max_context_chunks = max_context_chunks
        self.similarity_threshold = similarity_threshold

    def enhance_retrieval_results(
        self, original_results: List[Dict], vector_store, include_metadata: bool = True
    ) -> List[ChunkContext]:
        """Arricchisce i risultati di ricerca con chunks di contesto.

        Args:
            original_results: Risultati originali dalla ricerca vettoriale
            vector_store: Store vettoriale per recuperare chunks aggiuntivi
            include_metadata: Se includere metadata dettagliati

        Returns:
            Lista di ChunkContext con chunks originali e di contesto
        """
        if not original_results:
            return []

        try:
            start_time = time.time()
            enhanced_results = []
            processed_chunks = set()

            # Filtra risultati originali per similarity threshold
            filtered_results = [
                result for result in original_results if result.get("score", 0) >= self.similarity_threshold
            ]

            logger.info(
                f"Filtered {len(original_results)} to {len(filtered_results)} results above threshold {self.similarity_threshold}"
            )

            for result in filtered_results:
                # Aggiungi chunk originale
                original_chunk = self._create_chunk_context(result, "original", result.get("score", 0))

                if original_chunk.chunk_id not in processed_chunks:
                    enhanced_results.append(original_chunk)
                    processed_chunks.add(original_chunk.chunk_id)

                # Recupera chunks di contesto
                context_chunks = self._get_contextual_chunks(result, vector_store, processed_chunks)

                enhanced_results.extend(context_chunks)
                processed_chunks.update(chunk.chunk_id for chunk in context_chunks)

            # Riordina per rilevanza mantenendo vicinanza contestuale
            enhanced_results = self._reorder_with_context_awareness(enhanced_results)

            processing_time = time.time() - start_time
            logger.info(
                f"Enhanced {len(filtered_results)} results to {len(enhanced_results)} chunks in {processing_time:.3f}s"
            )

            return enhanced_results

        except Exception as e:
            logger.error(f"Error enhancing retrieval results: {e}")
            # Fallback ai risultati originali
            return [
                self._create_chunk_context(result, "original", result.get("score", 0)) for result in filtered_results
            ]

    def _create_chunk_context(self, result: Dict, context_type: str, score: float) -> ChunkContext:
        """Crea un ChunkContext da un risultato di ricerca."""
        metadata = result.get("metadata", {})

        return ChunkContext(
            chunk_id=result.get("id", f"chunk_{hash(result.get('content', ''))}"),
            content=result.get("content", result.get("text", "")),
            metadata=metadata,
            score=score,
            context_type=context_type,
            source_file=metadata.get("source", metadata.get("file_name", "unknown")),
            chunk_index=metadata.get("chunk_index", 0),
        )

    def _get_contextual_chunks(
        self, original_result: Dict, vector_store, processed_chunks: Set[str]
    ) -> List[ChunkContext]:
        """Recupera chunks di contesto per un risultato originale."""
        context_chunks = []

        try:
            metadata = original_result.get("metadata", {})
            source_file = metadata.get("source", metadata.get("file_name"))
            chunk_index = metadata.get("chunk_index", 0)

            if not source_file:
                return context_chunks

            # Recupera chunks adiacenti
            for offset in range(-self.window_size, self.window_size + 1):
                if offset == 0:  # Skip original chunk
                    continue

                adjacent_index = chunk_index + offset
                if adjacent_index < 0:
                    continue

                # Cerca chunk adiacente nello store
                adjacent_chunk = self._find_chunk_by_index(vector_store, source_file, adjacent_index)

                if adjacent_chunk and adjacent_chunk["id"] not in processed_chunks:
                    context_type = "before" if offset < 0 else "after"
                    # Score più basso per chunks di contesto
                    context_score = original_result.get("score", 0) * 0.7

                    chunk_context = self._create_chunk_context(adjacent_chunk, context_type, context_score)
                    context_chunks.append(chunk_context)

                    if len(context_chunks) >= self.max_context_chunks:
                        break

            return context_chunks

        except Exception as e:
            logger.warning(f"Error getting contextual chunks: {e}")
            return []

    def _find_chunk_by_index(self, vector_store, source_file: str, chunk_index: int) -> Optional[Dict]:
        """Trova un chunk specifico per source e indice."""
        try:
            # Implementazione dipende dal tipo di vector store
            if hasattr(vector_store, "query_with_filter"):
                # Qdrant o store con filtri
                filter_conditions = {"source": source_file, "chunk_index": chunk_index}
                results = vector_store.query_with_filter(
                    query_vector=None,  # Non usiamo query vettoriale
                    filter_dict=filter_conditions,
                    top_k=1,
                )
                return results[0] if results else None

            elif hasattr(vector_store, "_collection"):
                # Per Qdrant diretto
                from qdrant_client.http import models as rest

                search_result = vector_store._client.scroll(
                    collection_name=vector_store._collection_name,
                    scroll_filter=rest.Filter(
                        must=[
                            rest.FieldCondition(key="source", match=rest.MatchValue(value=source_file)),
                            rest.FieldCondition(key="chunk_index", match=rest.MatchValue(value=chunk_index)),
                        ]
                    ),
                    limit=1,
                    with_payload=True,
                    with_vectors=False,
                )

                if search_result[0]:  # points, next_page_offset
                    point = search_result[0][0]
                    return {"id": point.id, "content": point.payload.get("text", ""), "metadata": point.payload}

            return None

        except Exception as e:
            logger.warning(f"Error finding chunk by index: {e}")
            return None

    def _reorder_with_context_awareness(self, chunks: List[ChunkContext]) -> List[ChunkContext]:
        """Riordina chunks mantenendo consapevolezza del contesto."""
        try:
            # Raggruppa per documento sorgente
            source_groups = {}
            for chunk in chunks:
                source = chunk.source_file
                if source not in source_groups:
                    source_groups[source] = []
                source_groups[source].append(chunk)

            # Ordina ogni gruppo per chunk_index mantenendo chunk originali in testa
            reordered = []
            for source, group in source_groups.items():
                # Separa chunks originali da contesto
                original_chunks = [c for c in group if c.context_type == "original"]
                context_chunks = [c for c in group if c.context_type != "original"]

                # Ordina originali per score
                original_chunks.sort(key=lambda x: x.score, reverse=True)

                # Per ogni chunk originale, aggiungi i suoi chunks di contesto
                for orig_chunk in original_chunks:
                    reordered.append(orig_chunk)

                    # Aggiungi chunks di contesto vicini
                    related_context = [
                        c for c in context_chunks if abs(c.chunk_index - orig_chunk.chunk_index) <= self.window_size
                    ]
                    related_context.sort(key=lambda x: x.chunk_index)
                    reordered.extend(related_context)

            return reordered

        except Exception as e:
            logger.warning(f"Error reordering chunks: {e}")
            # Fallback: ordina solo per score
            return sorted(chunks, key=lambda x: x.score, reverse=True)

    def create_contextual_text(self, chunks: List[ChunkContext], max_length: int = 4000) -> str:
        """Crea testo contestuale unificato dai chunks."""
        if not chunks:
            return ""

        try:
            # Raggruppa per documento e ordina per posizione
            contextual_sections = []
            current_length = 0

            source_groups = {}
            for chunk in chunks:
                source = chunk.source_file
                if source not in source_groups:
                    source_groups[source] = []
                source_groups[source].append(chunk)

            for source, group in source_groups.items():
                if current_length >= max_length:
                    break

                # Ordina per chunk_index
                group.sort(key=lambda x: x.chunk_index)

                section_text = f"\n--- Da {source} ---\n"

                for chunk in group:
                    chunk_text = f"\n[{chunk.context_type.upper()}] {chunk.content}\n"

                    if current_length + len(section_text) + len(chunk_text) > max_length:
                        break

                    section_text += chunk_text
                    current_length += len(chunk_text)

                contextual_sections.append(section_text)

            return "\n".join(contextual_sections)

        except Exception as e:
            logger.error(f"Error creating contextual text: {e}")
            # Fallback: concatena solo i contenuti
            return "\n\n".join(chunk.content for chunk in chunks[:5])

    def get_context_statistics(self, chunks: List[ChunkContext]) -> Dict[str, Any]:
        """Restituisce statistiche sui chunks recuperati."""
        if not chunks:
            return {}

        try:
            stats = {
                "total_chunks": len(chunks),
                "original_chunks": len([c for c in chunks if c.context_type == "original"]),
                "context_chunks": len([c for c in chunks if c.context_type != "original"]),
                "sources_count": len(set(c.source_file for c in chunks)),
                "avg_score": sum(c.score for c in chunks) / len(chunks),
                "context_types": {},
                "source_distribution": {},
            }

            # Distribuzione per tipo di contesto
            for chunk in chunks:
                context_type = chunk.context_type
                stats["context_types"][context_type] = stats["context_types"].get(context_type, 0) + 1

            # Distribuzione per sorgente
            for chunk in chunks:
                source = chunk.source_file
                stats["source_distribution"][source] = stats["source_distribution"].get(source, 0) + 1

            return stats

        except Exception as e:
            logger.error(f"Error computing context statistics: {e}")
            return {"error": str(e)}


# Global contextual retrieval service instance
_contextual_service = None


def get_contextual_retrieval_service(window_size: int = 1) -> ContextualRetrievalService:
    """Get or create global contextual retrieval service instance.

    Args:
        window_size: Window size for contextual chunks

    Returns:
        ContextualRetrievalService instance
    """
    global _contextual_service

    if _contextual_service is None or _contextual_service.window_size != window_size:
        _contextual_service = ContextualRetrievalService(window_size=window_size)

    return _contextual_service
