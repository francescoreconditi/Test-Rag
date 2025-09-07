"""Advanced PDF processor with OCR and table extraction capabilities."""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime

# PDF processing libraries
import fitz  # PyMuPDF
import pdfplumber
import camelot
import tabula
import ocrmypdf
import pytesseract
from PIL import Image
import io

from src.domain.value_objects.source_reference import SourceReference

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Represents an extracted table from PDF."""
    page_number: int
    table_index: int
    data: List[List[str]]  # 2D array of cell values
    headers: Optional[List[str]] = None
    extraction_method: str = ""
    confidence: float = 0.0
    source_ref: Optional[SourceReference] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'page_number': self.page_number,
            'table_index': self.table_index,
            'rows': len(self.data),
            'columns': len(self.data[0]) if self.data else 0,
            'headers': self.headers,
            'extraction_method': self.extraction_method,
            'confidence': self.confidence
        }


@dataclass
class ExtractedText:
    """Represents extracted text from PDF."""
    page_number: int
    text: str
    extraction_method: str = ""
    is_ocr: bool = False
    source_ref: Optional[SourceReference] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'page_number': self.page_number,
            'text_length': len(self.text),
            'extraction_method': self.extraction_method,
            'is_ocr': self.is_ocr
        }


@dataclass
class PDFExtractionResult:
    """Complete result of PDF extraction."""
    file_path: str
    page_count: int
    tables: List[ExtractedTable]
    texts: List[ExtractedText]
    metadata: Dict[str, Any]
    extraction_time: float
    errors: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_path': self.file_path,
            'page_count': self.page_count,
            'table_count': len(self.tables),
            'text_pages': len(self.texts),
            'has_ocr': any(t.is_ocr for t in self.texts),
            'extraction_time': self.extraction_time,
            'error_count': len(self.errors) if self.errors else 0,
            'metadata': self.metadata
        }


class PDFProcessor:
    """Advanced PDF processor with multiple extraction methods."""
    
    def __init__(self, 
                 enable_ocr: bool = True,
                 ocr_language: str = 'ita+eng',
                 table_extraction_method: str = 'auto'):
        """
        Initialize PDF processor.
        
        Args:
            enable_ocr: Enable OCR for scanned PDFs
            ocr_language: Languages for OCR (ita+eng for Italian and English)
            table_extraction_method: 'camelot', 'tabula', 'pdfplumber', or 'auto'
        """
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language
        self.table_extraction_method = table_extraction_method
        
        # Check Tesseract availability
        if enable_ocr:
            try:
                # Try default path first
                pytesseract.get_tesseract_version()
                logger.info("Tesseract OCR is available")
            except Exception:
                # Try Windows default installation path
                try:
                    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                    pytesseract.get_tesseract_version()
                    logger.info("Tesseract OCR is available at Windows default path")
                except Exception as e:
                    logger.warning(f"Tesseract not available: {e}. OCR will be disabled.")
                    self.enable_ocr = False
    
    def process_pdf(self, file_path: str) -> PDFExtractionResult:
        """
        Process PDF with all available methods.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            PDFExtractionResult with all extracted content
        """
        start_time = datetime.now()
        errors = []
        
        # Check if PDF needs OCR
        needs_ocr = self._check_needs_ocr(file_path)
        ocr_file_path = file_path
        
        if needs_ocr and self.enable_ocr:
            logger.info(f"PDF appears to be scanned, running OCR...")
            ocr_file_path = self._run_ocr(file_path)
            if ocr_file_path is None:
                errors.append("OCR failed")
                ocr_file_path = file_path
        
        # Extract text
        texts = self._extract_text(ocr_file_path, is_ocr=needs_ocr)
        
        # Extract tables
        tables = self._extract_tables(ocr_file_path)
        
        # Extract metadata
        metadata = self._extract_metadata(file_path)
        
        # Clean up OCR file if created
        if ocr_file_path != file_path and os.path.exists(ocr_file_path):
            os.remove(ocr_file_path)
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        return PDFExtractionResult(
            file_path=file_path,
            page_count=metadata.get('page_count', 0),
            tables=tables,
            texts=texts,
            metadata=metadata,
            extraction_time=elapsed_time,
            errors=errors if errors else None
        )
    
    def _check_needs_ocr(self, file_path: str) -> bool:
        """Check if PDF needs OCR (is scanned/image-based)."""
        try:
            doc = fitz.open(file_path)
            
            # Sample first few pages
            sample_pages = min(3, len(doc))
            total_chars = 0
            
            for i in range(sample_pages):
                page = doc[i]
                text = page.get_text()
                total_chars += len(text.strip())
            
            doc.close()
            
            # If very little text extracted, likely needs OCR
            avg_chars_per_page = total_chars / sample_pages if sample_pages > 0 else 0
            needs_ocr = avg_chars_per_page < 100
            
            logger.info(f"PDF OCR check: avg {avg_chars_per_page:.0f} chars/page, needs_ocr={needs_ocr}")
            return needs_ocr
            
        except Exception as e:
            logger.error(f"Error checking OCR need: {e}")
            return False
    
    def _run_ocr(self, file_path: str) -> Optional[str]:
        """Run OCR on PDF and return path to OCR'd file."""
        try:
            # Create temporary file for OCR output
            with tempfile.NamedTemporaryFile(suffix='_ocr.pdf', delete=False) as tmp:
                output_path = tmp.name
            
            # Run OCR
            ocrmypdf.ocr(
                file_path,
                output_path,
                language=self.ocr_language,
                deskew=True,
                clean=True,
                force_ocr=False,  # Only OCR pages that need it
                skip_text=True,   # Skip pages with existing text
                optimize=1        # Optimize file size
            )
            
            logger.info(f"OCR completed: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return None
    
    def _extract_text(self, file_path: str, is_ocr: bool = False) -> List[ExtractedText]:
        """Extract text from PDF using PyMuPDF."""
        texts = []
        
        try:
            doc = fitz.open(file_path)
            
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                
                if text.strip():
                    source_ref = SourceReference(
                        file_path=file_path,
                        page_number=page_num,
                        extraction_method="pymupdf_ocr" if is_ocr else "pymupdf"
                    )
                    
                    texts.append(ExtractedText(
                        page_number=page_num,
                        text=text,
                        extraction_method="pymupdf",
                        is_ocr=is_ocr,
                        source_ref=source_ref
                    ))
            
            doc.close()
            logger.info(f"Extracted text from {len(texts)} pages")
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
        
        return texts
    
    def _extract_tables(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables using multiple methods with fallback."""
        tables = []
        
        if self.table_extraction_method == 'auto':
            # Try methods in order of accuracy
            methods = ['camelot', 'tabula', 'pdfplumber']
        else:
            methods = [self.table_extraction_method]
        
        for method in methods:
            if method == 'camelot':
                tables = self._extract_tables_camelot(file_path)
            elif method == 'tabula':
                tables = self._extract_tables_tabula(file_path)
            elif method == 'pdfplumber':
                tables = self._extract_tables_pdfplumber(file_path)
            
            if tables:
                logger.info(f"Successfully extracted {len(tables)} tables using {method}")
                break
        
        return tables
    
    def _extract_tables_camelot(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables using Camelot."""
        tables = []
        
        try:
            # Try lattice method first (for tables with lines)
            lattice_tables = camelot.read_pdf(
                file_path,
                pages='all',
                flavor='lattice',
                suppress_stdout=True
            )
            
            for idx, table in enumerate(lattice_tables):
                if table.df.empty:
                    continue
                    
                source_ref = SourceReference(
                    file_path=file_path,
                    page_number=table.page,
                    table_index=idx,
                    extraction_method="camelot_lattice"
                )
                
                tables.append(ExtractedTable(
                    page_number=table.page,
                    table_index=idx,
                    data=table.df.values.tolist(),
                    headers=table.df.columns.tolist() if not table.df.columns.empty else None,
                    extraction_method="camelot_lattice",
                    confidence=table.accuracy,
                    source_ref=source_ref
                ))
            
            # Try stream method for tables without lines
            if not tables:
                stream_tables = camelot.read_pdf(
                    file_path,
                    pages='all',
                    flavor='stream',
                    suppress_stdout=True
                )
                
                for idx, table in enumerate(stream_tables):
                    if table.df.empty:
                        continue
                        
                    source_ref = SourceReference(
                        file_path=file_path,
                        page_number=table.page,
                        table_index=idx,
                        extraction_method="camelot_stream"
                    )
                    
                    tables.append(ExtractedTable(
                        page_number=table.page,
                        table_index=idx,
                        data=table.df.values.tolist(),
                        headers=table.df.columns.tolist() if not table.df.columns.empty else None,
                        extraction_method="camelot_stream",
                        confidence=table.accuracy,
                        source_ref=source_ref
                    ))
            
        except Exception as e:
            logger.warning(f"Camelot extraction failed: {e}")
        
        return tables
    
    def _extract_tables_tabula(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables using Tabula."""
        tables = []
        
        try:
            # Read all tables from PDF
            dfs = tabula.read_pdf(
                file_path,
                pages='all',
                multiple_tables=True,
                pandas_options={'header': None},
                silent=True
            )
            
            # Get page numbers for each table
            # Note: Tabula doesn't directly provide page numbers, so we estimate
            for idx, df in enumerate(dfs):
                if df.empty:
                    continue
                
                # Estimate page number (this is approximate)
                page_num = idx + 1
                
                source_ref = SourceReference(
                    file_path=file_path,
                    page_number=page_num,
                    table_index=idx,
                    extraction_method="tabula"
                )
                
                tables.append(ExtractedTable(
                    page_number=page_num,
                    table_index=idx,
                    data=df.values.tolist(),
                    headers=df.columns.tolist() if not df.columns.empty else None,
                    extraction_method="tabula",
                    confidence=0.7,  # Tabula doesn't provide confidence
                    source_ref=source_ref
                ))
            
        except Exception as e:
            logger.warning(f"Tabula extraction failed: {e}")
        
        return tables
    
    def _extract_tables_pdfplumber(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables using pdfplumber as fallback."""
        tables = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    
                    for idx, table_data in enumerate(page_tables):
                        if not table_data:
                            continue
                        
                        source_ref = SourceReference(
                            file_path=file_path,
                            page_number=page_num,
                            table_index=idx,
                            extraction_method="pdfplumber"
                        )
                        
                        # Clean and process table data
                        cleaned_data = []
                        headers = None
                        
                        for row_idx, row in enumerate(table_data):
                            # Clean None values
                            cleaned_row = [cell if cell else "" for cell in row]
                            
                            if row_idx == 0 and any(cleaned_row):
                                headers = cleaned_row
                            else:
                                cleaned_data.append(cleaned_row)
                        
                        if cleaned_data:
                            tables.append(ExtractedTable(
                                page_number=page_num,
                                table_index=idx,
                                data=cleaned_data,
                                headers=headers,
                                extraction_method="pdfplumber",
                                confidence=0.6,  # Lower confidence for fallback
                                source_ref=source_ref
                            ))
            
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
        
        return tables
    
    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract PDF metadata."""
        metadata = {}
        
        try:
            doc = fitz.open(file_path)
            
            metadata = {
                'page_count': len(doc),
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'creator': doc.metadata.get('creator', ''),
                'producer': doc.metadata.get('producer', ''),
                'creation_date': str(doc.metadata.get('creationDate', '')),
                'modification_date': str(doc.metadata.get('modDate', '')),
                'file_size': os.path.getsize(file_path),
                'is_encrypted': doc.is_encrypted,
                'is_form': doc.is_form_pdf
            }
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            metadata = {'error': str(e)}
        
        return metadata
    
    def extract_images(self, file_path: str, output_dir: str = None) -> List[Dict[str, Any]]:
        """Extract images from PDF."""
        images = []
        
        try:
            doc = fitz.open(file_path)
            
            for page_num, page in enumerate(doc, 1):
                image_list = page.get_images()
                
                for img_idx, img in enumerate(image_list):
                    # Extract image
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                    else:  # CMYK
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                        img_data = pix.tobytes("png")
                    
                    # Save or process image
                    if output_dir:
                        output_path = Path(output_dir) / f"page{page_num}_img{img_idx}.png"
                        output_path.write_bytes(img_data)
                        
                        images.append({
                            'page_number': page_num,
                            'image_index': img_idx,
                            'output_path': str(output_path),
                            'size': len(img_data)
                        })
                    else:
                        # Just collect metadata
                        images.append({
                            'page_number': page_num,
                            'image_index': img_idx,
                            'size': len(img_data)
                        })
                    
                    pix = None  # Free memory
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Image extraction failed: {e}")
        
        return images