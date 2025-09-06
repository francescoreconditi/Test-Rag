"""RAG Engine interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domain.entities import Document


class IRAGEngine(ABC):
    """Interface for RAG (Retrieval-Augmented Generation) engine."""

    @abstractmethod
    def index_document(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> Document:
        """Index a document for retrieval."""
        pass

    @abstractmethod
    def index_documents(self, file_paths: List[Path], metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Index multiple documents."""
        pass

    @abstractmethod
    def query(self, query_text: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query indexed documents."""
        pass

    @abstractmethod
    def query_with_context(self, query_text: str, context: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        """Query with additional context."""
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the index."""
        pass

    @abstractmethod
    def update_document(self, document_id: str, new_content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update an existing document."""
        pass

    @abstractmethod
    def clear_index(self) -> bool:
        """Clear all documents from the index."""
        pass

    @abstractmethod
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index."""
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a specific document."""
        pass

    @abstractmethod
    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """List all indexed documents."""
        pass

    @abstractmethod
    def search_similar(self, document_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Find similar documents to a given document."""
        pass

    @abstractmethod
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text."""
        pass

    @abstractmethod
    def summarize_document(self, document_id: str, max_length: int = 500) -> str:
        """Generate a summary of a document."""
        pass

    @abstractmethod
    def get_document_chunks(self, document_id: str) -> List[str]:
        """Get all chunks of a document."""
        pass

    @abstractmethod
    def reindex_document(self, document_id: str) -> bool:
        """Reindex an existing document."""
        pass

    @abstractmethod
    def export_index(self, output_path: Path) -> bool:
        """Export the entire index to a file."""
        pass

    @abstractmethod
    def import_index(self, input_path: Path) -> bool:
        """Import an index from a file."""
        pass

    @abstractmethod
    def optimize_index(self) -> bool:
        """Optimize the index for better performance."""
        pass
