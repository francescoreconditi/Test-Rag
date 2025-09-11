"""Document repository implementation."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from src.application.interfaces.repository_interfaces import IDocumentRepository
from src.domain.entities import Document, DocumentStatus, DocumentType

from .base_repository import BaseRepository


class DocumentRepository(BaseRepository, IDocumentRepository):
    """SQLite implementation of document repository."""

    def __init__(self, db_path: Path = Path("data/repositories/documents.db")):
        """Initialize document repository."""
        super().__init__(db_path, "documents", Document)
        self._create_additional_indexes()

    def _create_additional_indexes(self):
        """Create additional indexes specific to documents."""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            # Add status and type indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_status
                ON documents (id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_type
                ON documents (id)
            """)
            conn.commit()

    def find_by_type(self, document_type: str) -> list[Document]:
        """Find documents by type."""
        all_docs = self.find_all(limit=10000)

        # Convert string to DocumentType enum if needed
        try:
            doc_type_enum = DocumentType(document_type.lower())
        except ValueError:
            return []

        return [
            doc for doc in all_docs
            if doc.document_type == doc_type_enum
        ]

    def find_by_status(self, status: str) -> list[Document]:
        """Find documents by processing status."""
        all_docs = self.find_all(limit=10000)

        # Convert string to DocumentStatus enum if needed
        try:
            status_enum = DocumentStatus(status.lower())
        except ValueError:
            return []

        return [
            doc for doc in all_docs
            if doc.status == status_enum
        ]

    def find_indexed(self) -> list[Document]:
        """Find all indexed documents."""
        return self.find_by_status(DocumentStatus.INDEXED.value)

    def find_by_metadata(self, metadata_key: str, metadata_value: Any) -> list[Document]:
        """Find documents by metadata."""
        all_docs = self.find_all(limit=10000)

        results = []
        for doc in all_docs:
            # Check in custom_fields of metadata
            if doc.metadata and doc.metadata.custom_fields.get(metadata_key) == metadata_value or hasattr(doc.metadata, metadata_key) and getattr(doc.metadata, metadata_key) == metadata_value:
                results.append(doc)

        return results

    def search_content(self, query: str, limit: int = 10) -> list[Document]:
        """Search documents by content."""
        all_docs = self.find_all(limit=10000)
        query_lower = query.lower()

        # Score documents based on content match
        scored_docs = []

        for doc in all_docs:
            score = 0

            # Check main content
            if doc.content and query_lower in doc.content.lower():
                score += doc.content.lower().count(query_lower) * 2

            # Check chunks
            for chunk in doc.chunks:
                if query_lower in chunk.lower():
                    score += chunk.lower().count(query_lower)

            # Check metadata
            if doc.metadata:
                if doc.metadata.title and query_lower in doc.metadata.title.lower():
                    score += 5
                if doc.metadata.keywords:
                    for keyword in doc.metadata.keywords:
                        if query_lower in keyword.lower():
                            score += 3

            if score > 0:
                scored_docs.append((score, doc))

        # Sort by score and return top results
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs[:limit]]

    def find_similar(self, document_id: str, limit: int = 5) -> list[Document]:
        """Find similar documents."""
        source_doc = self.find_by_id(document_id)

        if not source_doc:
            return []

        all_docs = self.find_all(limit=10000)

        # Simple similarity based on shared keywords and document type
        scored_docs = []

        for doc in all_docs:
            if doc.id == document_id:
                continue

            score = 0

            # Same document type
            if doc.document_type == source_doc.document_type:
                score += 10

            # Shared keywords
            if source_doc.metadata and doc.metadata:
                if source_doc.metadata.keywords and doc.metadata.keywords:
                    shared_keywords = set(source_doc.metadata.keywords) & set(doc.metadata.keywords)
                    score += len(shared_keywords) * 5

                # Same author
                if source_doc.metadata.author and doc.metadata.author == source_doc.metadata.author:
                    score += 8

                # Same language
                if doc.metadata.language == source_doc.metadata.language:
                    score += 3

            # Similar size
            if source_doc.chunk_count > 0 and doc.chunk_count > 0:
                size_ratio = min(source_doc.chunk_count, doc.chunk_count) / max(source_doc.chunk_count, doc.chunk_count)
                score += int(size_ratio * 5)

            if score > 0:
                scored_docs.append((score, doc))

        # Sort by score and return top results
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs[:limit]]

    def get_by_path(self, file_path: str) -> Optional[Document]:
        """Get document by file path."""
        all_docs = self.find_all(limit=10000)

        file_path_obj = Path(file_path)

        for doc in all_docs:
            if doc.file_path == file_path_obj:
                return doc

        return None

    def find_recent(self, days: int = 7) -> list[Document]:
        """Find recently added documents."""
        cutoff_date = datetime.now() - timedelta(days=days)
        all_docs = self.find_all(limit=10000)

        return [
            doc for doc in all_docs
            if doc.created_at >= cutoff_date
        ]

    def cleanup_old(self, days: int = 90) -> int:
        """Clean up old documents and return count deleted."""
        cutoff_date = datetime.now() - timedelta(days=days)
        all_docs = self.find_all(limit=10000)

        deleted_count = 0

        for doc in all_docs:
            # Only cleanup failed or archived documents
            if doc.status in [DocumentStatus.FAILED, DocumentStatus.ARCHIVED]:
                if doc.created_at < cutoff_date and self.delete(doc.id):
                    deleted_count += 1

        return deleted_count

    def get_statistics(self) -> dict[str, Any]:
        """Get repository statistics."""
        all_docs = self.find_all(limit=10000)

        stats = {
            'total_documents': len(all_docs),
            'by_status': {},
            'by_type': {},
            'total_chunks': 0,
            'average_chunks_per_doc': 0,
            'indexed_documents': 0,
            'failed_documents': 0
        }

        # Count by status
        for status in DocumentStatus:
            count = len([d for d in all_docs if d.status == status])
            stats['by_status'][status.value] = count

            if status == DocumentStatus.INDEXED:
                stats['indexed_documents'] = count
            elif status == DocumentStatus.FAILED:
                stats['failed_documents'] = count

        # Count by type
        for doc_type in DocumentType:
            count = len([d for d in all_docs if d.document_type == doc_type])
            stats['by_type'][doc_type.value] = count

        # Calculate chunk statistics
        if all_docs:
            total_chunks = sum(doc.chunk_count for doc in all_docs)
            stats['total_chunks'] = total_chunks
            stats['average_chunks_per_doc'] = total_chunks / len(all_docs)

        return stats
