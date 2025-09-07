"""Document router for structured vs unstructured processing."""

from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import mimetypes
try:
    import magic  # python-magic for better file type detection
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
from dataclasses import dataclass


class ProcessingMode(Enum):
    """Document processing modes."""
    STRUCTURED = "structured"      # Excel, CSV, JSON - tabular data
    UNSTRUCTURED = "unstructured"  # PDF text, Word docs - narrative content
    HYBRID = "hybrid"              # PDFs with tables + text
    UNKNOWN = "unknown"            # Cannot determine or unsupported


@dataclass
class DocumentClassification:
    """Result of document classification."""
    file_path: str
    processing_mode: ProcessingMode
    confidence: float  # 0.0 - 1.0
    detected_format: str
    has_tables: bool = False
    has_text: bool = False 
    page_count: Optional[int] = None
    sheet_count: Optional[int] = None
    structured_data_ratio: Optional[float] = None  # % of content that is structured
    
    # Routing recommendations
    recommended_parser: str = ""
    extraction_strategy: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_path': self.file_path,
            'processing_mode': self.processing_mode.value,
            'confidence': self.confidence,
            'detected_format': self.detected_format,
            'has_tables': self.has_tables,
            'has_text': self.has_text,
            'page_count': self.page_count,
            'sheet_count': self.sheet_count,
            'structured_data_ratio': self.structured_data_ratio,
            'recommended_parser': self.recommended_parser,
            'extraction_strategy': self.extraction_strategy
        }


class DocumentRouter:
    """Routes documents to appropriate processing pipelines."""
    
    def __init__(self):
        """Initialize document router."""
        # File type mappings
        self.structured_extensions = {
            '.xlsx', '.xls', '.xlsm',  # Excel
            '.csv', '.tsv',            # CSV variants
            '.json', '.jsonl',         # JSON data
            '.xml',                    # Structured XML
            '.parquet', '.feather'     # Binary data formats
        }
        
        self.unstructured_extensions = {
            '.txt', '.md', '.rst',     # Plain text
            '.docx', '.doc',           # Word documents
            '.rtf',                    # Rich text
            '.html', '.htm'            # Web pages (mostly text)
        }
        
        self.hybrid_extensions = {
            '.pdf'  # PDFs can contain both tables and text
        }
        
        # MIME type fallbacks
        self.structured_mimes = {
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv',
            'application/json',
            'application/xml', 'text/xml'
        }
        
        self.unstructured_mimes = {
            'text/plain',
            'text/markdown', 
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/html'
        }
    
    def classify_document(self, file_path: str) -> DocumentClassification:
        """Classify document and determine processing mode."""
        path = Path(file_path)
        
        if not path.exists():
            return DocumentClassification(
                file_path=file_path,
                processing_mode=ProcessingMode.UNKNOWN,
                confidence=0.0,
                detected_format="file_not_found"
            )
        
        # Get file extension and MIME type
        extension = path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Try to get more accurate MIME type with python-magic
        if MAGIC_AVAILABLE:
            try:
                detected_mime = magic.from_file(file_path, mime=True)
                if detected_mime and detected_mime != 'application/octet-stream':
                    mime_type = detected_mime
            except Exception:
                pass  # Fall back to mimetypes guess
        
        # Initial classification based on extension
        if extension in self.structured_extensions:
            return self._classify_structured(file_path, extension, mime_type)
        elif extension in self.unstructured_extensions:
            return self._classify_unstructured(file_path, extension, mime_type)
        elif extension in self.hybrid_extensions:
            return self._classify_hybrid(file_path, extension, mime_type)
        else:
            # Fall back to MIME type
            return self._classify_by_mime(file_path, mime_type)
    
    def _classify_structured(self, file_path: str, extension: str, mime_type: Optional[str]) -> DocumentClassification:
        """Classify structured document."""
        path = Path(file_path)
        
        # Determine specific parser and strategy
        if extension in {'.xlsx', '.xls', '.xlsm'}:
            parser = "pandas_excel"
            strategy = "multi_sheet_extraction"
            sheet_count = self._count_excel_sheets(file_path)
        elif extension in {'.csv', '.tsv'}:
            parser = "pandas_csv" 
            strategy = "delimiter_detection"
            sheet_count = 1
        elif extension == '.json':
            parser = "json_parser"
            strategy = "nested_object_flattening"
            sheet_count = 1
        elif extension == '.xml':
            parser = "xml_parser"
            strategy = "hierarchical_extraction"
            sheet_count = 1
        else:
            parser = "generic_structured"
            strategy = "auto_detect"
            sheet_count = None
        
        return DocumentClassification(
            file_path=file_path,
            processing_mode=ProcessingMode.STRUCTURED,
            confidence=0.95,
            detected_format=extension[1:].upper(),
            has_tables=True,
            has_text=False,
            sheet_count=sheet_count,
            structured_data_ratio=1.0,
            recommended_parser=parser,
            extraction_strategy=strategy
        )
    
    def _classify_unstructured(self, file_path: str, extension: str, mime_type: Optional[str]) -> DocumentClassification:
        """Classify unstructured document."""
        if extension in {'.docx', '.doc'}:
            parser = "python_docx"
            strategy = "paragraph_and_table_extraction"
            has_tables = True  # Word docs often have tables
        elif extension == '.txt':
            parser = "plain_text"
            strategy = "line_based_extraction"
            has_tables = False
        elif extension == '.md':
            parser = "markdown"
            strategy = "structured_markdown_parsing"
            has_tables = True  # Markdown can have tables
        else:
            parser = "generic_text"
            strategy = "text_extraction"
            has_tables = False
        
        return DocumentClassification(
            file_path=file_path,
            processing_mode=ProcessingMode.UNSTRUCTURED,
            confidence=0.90,
            detected_format=extension[1:].upper(),
            has_tables=has_tables,
            has_text=True,
            structured_data_ratio=0.1 if has_tables else 0.0,
            recommended_parser=parser,
            extraction_strategy=strategy
        )
    
    def _classify_hybrid(self, file_path: str, extension: str, mime_type: Optional[str]) -> DocumentClassification:
        """Classify hybrid document (mainly PDFs)."""
        if extension == '.pdf':
            # Analyze PDF content to determine structure/text ratio
            analysis = self._analyze_pdf_content(file_path)
            
            if analysis['table_ratio'] > 0.7:
                # Mostly tables - treat as structured
                mode = ProcessingMode.STRUCTURED
                parser = "pdf_processor"
                strategy = "table_extraction_priority"
                confidence = 0.8
            elif analysis['text_ratio'] > 0.8:
                # Mostly text - treat as unstructured  
                mode = ProcessingMode.UNSTRUCTURED
                parser = "pdf_processor"
                strategy = "text_extraction_priority"
                confidence = 0.8
            else:
                # Mixed content - hybrid approach
                mode = ProcessingMode.HYBRID
                parser = "pdf_processor"
                strategy = "table_and_text_extraction"
                confidence = 0.9
            
            return DocumentClassification(
                file_path=file_path,
                processing_mode=mode,
                confidence=confidence,
                detected_format="PDF",
                has_tables=analysis['has_tables'],
                has_text=analysis['has_text'],
                page_count=analysis['page_count'],
                structured_data_ratio=analysis['table_ratio'],
                recommended_parser=parser,
                extraction_strategy=strategy
            )
        
        return DocumentClassification(
            file_path=file_path,
            processing_mode=ProcessingMode.UNKNOWN,
            confidence=0.5,
            detected_format="HYBRID_UNKNOWN"
        )
    
    def _classify_by_mime(self, file_path: str, mime_type: Optional[str]) -> DocumentClassification:
        """Fallback classification by MIME type."""
        if not mime_type:
            return DocumentClassification(
                file_path=file_path,
                processing_mode=ProcessingMode.UNKNOWN,
                confidence=0.0,
                detected_format="unknown"
            )
        
        if mime_type in self.structured_mimes:
            return DocumentClassification(
                file_path=file_path,
                processing_mode=ProcessingMode.STRUCTURED,
                confidence=0.7,
                detected_format=mime_type,
                has_tables=True,
                recommended_parser="generic_structured",
                extraction_strategy="auto_detect"
            )
        elif mime_type in self.unstructured_mimes:
            return DocumentClassification(
                file_path=file_path,
                processing_mode=ProcessingMode.UNSTRUCTURED,
                confidence=0.7,
                detected_format=mime_type,
                has_text=True,
                recommended_parser="generic_text",
                extraction_strategy="text_extraction"
            )
        else:
            return DocumentClassification(
                file_path=file_path,
                processing_mode=ProcessingMode.UNKNOWN,
                confidence=0.3,
                detected_format=mime_type
            )
    
    def _count_excel_sheets(self, file_path: str) -> Optional[int]:
        """Count sheets in Excel file."""
        try:
            import pandas as pd
            excel_file = pd.ExcelFile(file_path)
            return len(excel_file.sheet_names)
        except Exception:
            return None
    
    def _analyze_pdf_content(self, file_path: str) -> Dict[str, Any]:
        """Analyze PDF to determine content structure."""
        try:
            import fitz  # pymupdf
            
            doc = fitz.open(file_path)
            page_count = len(doc)
            
            total_text_chars = 0
            total_table_cells = 0
            has_tables = False
            has_text = False
            
            for page in doc:
                # Count text characters
                text = page.get_text()
                total_text_chars += len(text.strip())
                if len(text.strip()) > 50:  # Significant text content
                    has_text = True
                
                # Try to detect tables (very basic heuristic)
                # Look for table-like structures (lines, grids)
                try:
                    tables = page.find_tables()
                    if tables:
                        has_tables = True
                        for table in tables:
                            total_table_cells += table.row_count * table.col_count
                except:
                    # Fallback: look for regular patterns in text
                    lines = text.split('\n')
                    tabular_lines = sum(1 for line in lines if '\t' in line or line.count(' ') > 10)
                    if tabular_lines > len(lines) * 0.3:  # 30% of lines seem tabular
                        has_tables = True
                        total_table_cells += tabular_lines * 5  # Estimate
            
            doc.close()
            
            # Calculate ratios
            total_content = total_text_chars + (total_table_cells * 10)  # Weight table cells more
            if total_content == 0:
                text_ratio = 0
                table_ratio = 0
            else:
                text_ratio = total_text_chars / total_content
                table_ratio = (total_table_cells * 10) / total_content
            
            return {
                'page_count': page_count,
                'has_text': has_text,
                'has_tables': has_tables,
                'text_ratio': text_ratio,
                'table_ratio': table_ratio,
                'total_text_chars': total_text_chars,
                'estimated_table_cells': total_table_cells
            }
            
        except Exception as e:
            # Fallback analysis
            return {
                'page_count': 1,
                'has_text': True,
                'has_tables': False,
                'text_ratio': 1.0,
                'table_ratio': 0.0,
                'error': str(e)
            }
    
    def get_processing_pipeline(self, classification: DocumentClassification) -> Dict[str, Any]:
        """Get recommended processing pipeline for classified document."""
        if classification.processing_mode == ProcessingMode.STRUCTURED:
            return {
                'pipeline': 'structured',
                'use_llm': False,
                'parsers': [classification.recommended_parser],
                'extractors': ['tabular_data', 'metadata'],
                'post_processors': ['table_analyzer', 'synonym_mapping', 'validation', 'calculation_engine'],
                'indexing': 'structured_facts'
            }
        
        elif classification.processing_mode == ProcessingMode.UNSTRUCTURED:
            return {
                'pipeline': 'unstructured',
                'use_llm': True,
                'parsers': [classification.recommended_parser],
                'extractors': ['text_content', 'semantic_chunks'],
                'post_processors': ['entity_extraction', 'summarization'],
                'indexing': 'vector_embeddings'
            }
        
        elif classification.processing_mode == ProcessingMode.HYBRID:
            return {
                'pipeline': 'hybrid',
                'use_llm': True,
                'parsers': ['pdf_processor', 'camelot', 'pdfplumber'],
                'extractors': ['tables', 'text_content', 'semantic_chunks'],
                'post_processors': ['table_analysis', 'text_summarization', 'cross_reference', 'calculation_engine'],
                'indexing': 'both'
            }
        
        else:
            return {
                'pipeline': 'fallback',
                'use_llm': False,
                'parsers': ['generic'],
                'extractors': ['raw_content'],
                'post_processors': [],
                'indexing': 'basic'
            }
    
    def batch_classify(self, file_paths: List[str]) -> List[DocumentClassification]:
        """Classify multiple documents."""
        return [self.classify_document(path) for path in file_paths]
    
    def get_classification_summary(self, classifications: List[DocumentClassification]) -> Dict[str, Any]:
        """Get summary of batch classification."""
        if not classifications:
            return {'total': 0}
        
        modes = [c.processing_mode for c in classifications]
        confidence_scores = [c.confidence for c in classifications]
        
        return {
            'total': len(classifications),
            'structured': sum(1 for m in modes if m == ProcessingMode.STRUCTURED),
            'unstructured': sum(1 for m in modes if m == ProcessingMode.UNSTRUCTURED), 
            'hybrid': sum(1 for m in modes if m == ProcessingMode.HYBRID),
            'unknown': sum(1 for m in modes if m == ProcessingMode.UNKNOWN),
            'average_confidence': sum(confidence_scores) / len(confidence_scores),
            'formats': list(set(c.detected_format for c in classifications))
        }