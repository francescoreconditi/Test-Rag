"""Document domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class DocumentType(Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "md"
    CSV = "csv"
    EXCEL = "xlsx"


class DocumentStatus(Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class DocumentMetadata:
    """Document metadata."""
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    language: str = "it"
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """Document entity representing a file in the system."""

    id: Optional[str] = None
    file_path: Path = field(default_factory=Path)
    document_type: Optional[DocumentType] = None
    content: str = ""
    chunks: List[str] = field(default_factory=list)
    embeddings: List[List[float]] = field(default_factory=list)
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    indexed_at: Optional[datetime] = None

    def __post_init__(self):
        """Initialize document type from file path if not provided."""
        if self.file_path and not self.document_type:
            self._detect_document_type()

    def _detect_document_type(self) -> None:
        """Detect document type from file extension."""
        extension = self.file_path.suffix.lower().strip('.')
        try:
            self.document_type = DocumentType(extension)
        except ValueError:
            self.document_type = None

    @property
    def is_indexed(self) -> bool:
        """Check if document is indexed."""
        return self.status == DocumentStatus.INDEXED

    @property
    def has_content(self) -> bool:
        """Check if document has content."""
        return bool(self.content)

    @property
    def chunk_count(self) -> int:
        """Get number of chunks."""
        return len(self.chunks)

    def add_chunk(self, text: str, embedding: Optional[List[float]] = None) -> None:
        """Add a text chunk with optional embedding."""
        self.chunks.append(text)
        if embedding:
            self.embeddings.append(embedding)
        self.updated_at = datetime.now()

    def mark_as_indexed(self) -> None:
        """Mark document as successfully indexed."""
        self.status = DocumentStatus.INDEXED
        self.indexed_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_as_failed(self, error: str) -> None:
        """Mark document as failed with error message."""
        self.status = DocumentStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.now()

    def extract_summary(self, max_length: int = 500) -> str:
        """Extract a summary from document content."""
        if not self.content:
            return ""

        summary = self.content[:max_length]
        if len(self.content) > max_length:
            last_period = summary.rfind('.')
            if last_period > 0:
                summary = summary[:last_period + 1]
            else:
                summary += "..."

        return summary

    def search_content(self, query: str, case_sensitive: bool = False) -> List[str]:
        """Search for query in document chunks."""
        results = []
        search_query = query if case_sensitive else query.lower()

        for chunk in self.chunks:
            search_text = chunk if case_sensitive else chunk.lower()
            if search_query in search_text:
                results.append(chunk)

        return results

    def validate(self) -> List[str]:
        """Validate document integrity."""
        errors = []

        if not self.file_path:
            errors.append("File path is required")

        if self.file_path and not self.file_path.exists():
            errors.append(f"File does not exist: {self.file_path}")

        if not self.document_type:
            errors.append("Document type could not be determined")

        if self.embeddings and len(self.embeddings) != len(self.chunks):
            errors.append("Mismatch between chunks and embeddings count")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'file_path': str(self.file_path),
            'document_type': self.document_type.value if self.document_type else None,
            'content_length': len(self.content),
            'chunk_count': self.chunk_count,
            'metadata': {
                'author': self.metadata.author,
                'title': self.metadata.title,
                'subject': self.metadata.subject,
                'keywords': self.metadata.keywords,
                'language': self.metadata.language,
                'page_count': self.metadata.page_count,
                'word_count': self.metadata.word_count
            },
            'status': self.status.value,
            'error_message': self.error_message,
            'processing_time': self.processing_time,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'indexed_at': self.indexed_at.isoformat() if self.indexed_at else None
        }
