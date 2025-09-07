"""Advanced document preview service with content extraction and thumbnails."""

import os
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime
import hashlib
import json

# PDF handling
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Image handling
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Excel handling
import pandas as pd
import openpyxl

logger = logging.getLogger(__name__)


class DocumentPreviewService:
    """Service for generating document previews and extracting key information."""
    
    def __init__(self, cache_dir: str = "cache/previews"):
        """Initialize preview service with caching."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported formats
        self.supported_formats = {
            'pdf': self._preview_pdf,
            'xlsx': self._preview_excel,
            'xls': self._preview_excel,
            'csv': self._preview_csv,
            'txt': self._preview_text,
            'md': self._preview_text,
            'json': self._preview_json,
            'png': self._preview_image,
            'jpg': self._preview_image,
            'jpeg': self._preview_image
        }
    
    def generate_preview(self, 
                        file_path: str,
                        max_pages: int = 3,
                        thumbnail_size: Tuple[int, int] = (200, 200)) -> Dict[str, Any]:
        """
        Generate comprehensive preview of a document.
        
        Returns:
            Dict with preview data including:
            - file_info: Basic file metadata
            - content_preview: Text/data preview
            - thumbnails: Page/sheet thumbnails (base64)
            - statistics: Document statistics
            - key_metrics: Extracted financial metrics
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                'error': f'File not found: {file_path}',
                'status': 'error'
            }
        
        # Basic file info
        file_info = self._get_file_info(file_path)
        
        # Get file extension
        ext = file_path.suffix.lower().strip('.')
        
        # Generate preview based on file type
        if ext in self.supported_formats:
            preview_func = self.supported_formats[ext]
            preview_data = preview_func(file_path, max_pages, thumbnail_size)
        else:
            preview_data = {
                'content_preview': 'Unsupported file format',
                'thumbnails': [],
                'statistics': {}
            }
        
        # Combine all preview data
        result = {
            'file_info': file_info,
            'status': 'success',
            **preview_data
        }
        
        # Cache the preview
        self._cache_preview(file_path, result)
        
        return result
    
    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get basic file information."""
        stat = file_path.stat()
        
        return {
            'name': file_path.name,
            'path': str(file_path),
            'size': stat.st_size,
            'size_formatted': self._format_size(stat.st_size),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'extension': file_path.suffix.lower(),
            'hash': self._calculate_file_hash(file_path)
        }
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash for caching."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()[:16]
    
    def _preview_pdf(self, file_path: Path, max_pages: int, thumbnail_size: Tuple[int, int]) -> Dict[str, Any]:
        """Generate preview for PDF files."""
        if not PYMUPDF_AVAILABLE:
            return {
                'content_preview': 'PDF preview requires PyMuPDF (install with: pip install pymupdf)',
                'thumbnails': [],
                'statistics': {'error': 'PyMuPDF not available'}
            }
        
        try:
            doc = fitz.open(str(file_path))
            
            # Extract text from first few pages
            content_preview = []
            thumbnails = []
            
            for page_num in range(min(max_pages, len(doc))):
                page = doc[page_num]
                
                # Extract text
                text = page.get_text()
                if text.strip():
                    content_preview.append(f"Page {page_num + 1}:\n{text[:500]}...")
                
                # Generate thumbnail if PIL available
                if PIL_AVAILABLE:
                    pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))  # Scale down
                    img_data = pix.pil_tobytes(format="PNG")
                    img = Image.open(io.BytesIO(img_data))
                    img.thumbnail(thumbnail_size)
                    
                    # Convert to base64
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode()
                    
                    thumbnails.append({
                        'page': page_num + 1,
                        'thumbnail': f"data:image/png;base64,{img_base64}"
                    })
            
            # Document statistics
            statistics = {
                'total_pages': len(doc),
                'previewed_pages': min(max_pages, len(doc)),
                'has_text': bool(content_preview),
                'metadata': dict(doc.metadata) if doc.metadata else {}
            }
            
            # Look for financial metrics in text
            key_metrics = self._extract_key_metrics('\n'.join(content_preview))
            
            doc.close()
            
            return {
                'content_preview': '\n\n'.join(content_preview) if content_preview else 'No text content found',
                'thumbnails': thumbnails,
                'statistics': statistics,
                'key_metrics': key_metrics
            }
            
        except Exception as e:
            logger.error(f"Error previewing PDF: {e}")
            return {
                'content_preview': f'Error reading PDF: {str(e)}',
                'thumbnails': [],
                'statistics': {'error': str(e)}
            }
    
    def _preview_excel(self, file_path: Path, max_pages: int, thumbnail_size: Tuple[int, int]) -> Dict[str, Any]:
        """Generate preview for Excel files."""
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            
            content_preview = []
            statistics = {
                'total_sheets': len(excel_file.sheet_names),
                'sheet_names': excel_file.sheet_names[:10]  # First 10 sheets
            }
            
            # Preview first few sheets
            for sheet_name in excel_file.sheet_names[:max_pages]:
                df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=10)
                
                preview_text = f"Sheet: {sheet_name}\n"
                preview_text += f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n"
                preview_text += f"Columns: {', '.join(df.columns[:10])}\n"
                preview_text += "\nFirst 5 rows:\n"
                preview_text += df.head(5).to_string(max_cols=5)
                
                content_preview.append(preview_text)
                
                # Add sheet statistics
                statistics[f'sheet_{sheet_name}'] = {
                    'rows': df.shape[0],
                    'columns': df.shape[1],
                    'numeric_columns': len(df.select_dtypes(include=['number']).columns),
                    'text_columns': len(df.select_dtypes(include=['object']).columns)
                }
            
            # Extract key metrics from numeric columns
            key_metrics = self._extract_excel_metrics(excel_file)
            
            return {
                'content_preview': '\n\n'.join(content_preview),
                'thumbnails': [],  # Excel doesn't have visual thumbnails
                'statistics': statistics,
                'key_metrics': key_metrics
            }
            
        except Exception as e:
            logger.error(f"Error previewing Excel: {e}")
            return {
                'content_preview': f'Error reading Excel: {str(e)}',
                'thumbnails': [],
                'statistics': {'error': str(e)}
            }
    
    def _preview_csv(self, file_path: Path, max_pages: int, thumbnail_size: Tuple[int, int]) -> Dict[str, Any]:
        """Generate preview for CSV files."""
        try:
            # Try to detect encoding
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, nrows=100)
                    break
                except:
                    continue
            
            if df is None:
                raise ValueError("Could not decode CSV with common encodings")
            
            # Generate preview
            preview_text = f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n"
            preview_text += f"Columns: {', '.join(df.columns)}\n\n"
            preview_text += "First 10 rows:\n"
            preview_text += df.head(10).to_string(max_cols=8)
            
            # Statistics
            statistics = {
                'total_rows': len(pd.read_csv(file_path, encoding=encoding)),
                'total_columns': len(df.columns),
                'numeric_columns': len(df.select_dtypes(include=['number']).columns),
                'text_columns': len(df.select_dtypes(include=['object']).columns),
                'null_values': df.isnull().sum().to_dict()
            }
            
            # Extract key metrics
            key_metrics = self._extract_dataframe_metrics(df)
            
            return {
                'content_preview': preview_text,
                'thumbnails': [],
                'statistics': statistics,
                'key_metrics': key_metrics
            }
            
        except Exception as e:
            logger.error(f"Error previewing CSV: {e}")
            return {
                'content_preview': f'Error reading CSV: {str(e)}',
                'thumbnails': [],
                'statistics': {'error': str(e)}
            }
    
    def _preview_text(self, file_path: Path, max_pages: int, thumbnail_size: Tuple[int, int]) -> Dict[str, Any]:
        """Generate preview for text files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(5000)  # First 5000 chars
            
            lines = content.split('\n')
            
            statistics = {
                'total_lines': len(lines),
                'total_chars': len(content),
                'preview_chars': min(5000, len(content))
            }
            
            # Extract any structured data or metrics
            key_metrics = self._extract_key_metrics(content)
            
            return {
                'content_preview': content[:2000] + ('...' if len(content) > 2000 else ''),
                'thumbnails': [],
                'statistics': statistics,
                'key_metrics': key_metrics
            }
            
        except Exception as e:
            logger.error(f"Error previewing text file: {e}")
            return {
                'content_preview': f'Error reading file: {str(e)}',
                'thumbnails': [],
                'statistics': {'error': str(e)}
            }
    
    def _preview_json(self, file_path: Path, max_pages: int, thumbnail_size: Tuple[int, int]) -> Dict[str, Any]:
        """Generate preview for JSON files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Pretty print with indentation
            preview = json.dumps(data, indent=2, ensure_ascii=False)[:2000]
            
            # Extract structure info
            statistics = self._analyze_json_structure(data)
            
            # Extract metrics if present
            key_metrics = self._extract_json_metrics(data)
            
            return {
                'content_preview': preview + ('...' if len(preview) >= 2000 else ''),
                'thumbnails': [],
                'statistics': statistics,
                'key_metrics': key_metrics
            }
            
        except Exception as e:
            logger.error(f"Error previewing JSON: {e}")
            return {
                'content_preview': f'Error reading JSON: {str(e)}',
                'thumbnails': [],
                'statistics': {'error': str(e)}
            }
    
    def _preview_image(self, file_path: Path, max_pages: int, thumbnail_size: Tuple[int, int]) -> Dict[str, Any]:
        """Generate preview for image files."""
        if not PIL_AVAILABLE:
            return {
                'content_preview': 'Image preview requires Pillow (install with: pip install pillow)',
                'thumbnails': [],
                'statistics': {'error': 'Pillow not available'}
            }
        
        try:
            img = Image.open(file_path)
            
            # Get image info
            statistics = {
                'format': img.format,
                'mode': img.mode,
                'size': f"{img.width}×{img.height}",
                'width': img.width,
                'height': img.height
            }
            
            # Create thumbnail
            img_copy = img.copy()
            img_copy.thumbnail(thumbnail_size)
            
            buffered = io.BytesIO()
            img_copy.save(buffered, format=img.format or "PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            thumbnails = [{
                'page': 1,
                'thumbnail': f"data:image/{img.format.lower()};base64,{img_base64}"
            }]
            
            return {
                'content_preview': f"Image: {img.width}×{img.height} pixels, {img.format} format",
                'thumbnails': thumbnails,
                'statistics': statistics,
                'key_metrics': {}
            }
            
        except Exception as e:
            logger.error(f"Error previewing image: {e}")
            return {
                'content_preview': f'Error reading image: {str(e)}',
                'thumbnails': [],
                'statistics': {'error': str(e)}
            }
    
    def _extract_key_metrics(self, text: str) -> Dict[str, Any]:
        """Extract key financial metrics from text."""
        import re
        
        metrics = {}
        
        # Common financial patterns
        patterns = {
            'revenue': r'(?:ricavi|fatturato|revenue)[:\s]+([€$]?[\d.,]+\s*(?:mil|mln|billion|k)?)',
            'ebitda': r'(?:ebitda|mol)[:\s]+([€$]?[\d.,]+\s*(?:mil|mln|billion|k)?)',
            'net_income': r'(?:utile netto|net income)[:\s]+([€$]?[\d.,]+\s*(?:mil|mln|billion|k)?)',
            'employees': r'(?:dipendenti|employees)[:\s]+(\d+)',
            'year': r'(?:anno|year|fy)[:\s]+(20\d{2})'
        }
        
        for metric, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metrics[metric] = match.group(1)
        
        return metrics
    
    def _extract_excel_metrics(self, excel_file: pd.ExcelFile) -> Dict[str, Any]:
        """Extract metrics from Excel file."""
        metrics = {}
        
        # Check first sheet for common metric names
        try:
            df = pd.read_excel(excel_file, sheet_name=0)
            
            # Look for columns with financial keywords
            financial_keywords = ['ricavi', 'fatturato', 'ebitda', 'utile', 'revenue', 'profit', 'sales']
            
            for col in df.columns:
                col_lower = str(col).lower()
                for keyword in financial_keywords:
                    if keyword in col_lower:
                        # Get non-null numeric values
                        numeric_vals = pd.to_numeric(df[col], errors='coerce').dropna()
                        if len(numeric_vals) > 0:
                            metrics[col] = {
                                'min': float(numeric_vals.min()),
                                'max': float(numeric_vals.max()),
                                'mean': float(numeric_vals.mean()),
                                'count': len(numeric_vals)
                            }
                        break
        except:
            pass
        
        return metrics
    
    def _extract_dataframe_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract metrics from DataFrame."""
        metrics = {}
        
        # Numeric columns summary
        numeric_df = df.select_dtypes(include=['number'])
        
        for col in numeric_df.columns[:10]:  # First 10 numeric columns
            metrics[col] = {
                'min': float(numeric_df[col].min()) if not pd.isna(numeric_df[col].min()) else None,
                'max': float(numeric_df[col].max()) if not pd.isna(numeric_df[col].max()) else None,
                'mean': float(numeric_df[col].mean()) if not pd.isna(numeric_df[col].mean()) else None,
                'std': float(numeric_df[col].std()) if not pd.isna(numeric_df[col].std()) else None
            }
        
        return metrics
    
    def _extract_json_metrics(self, data: Any) -> Dict[str, Any]:
        """Extract metrics from JSON data."""
        metrics = {}
        
        def extract_numbers(obj, prefix=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_prefix = f"{prefix}.{key}" if prefix else key
                    extract_numbers(value, new_prefix)
            elif isinstance(obj, (int, float)):
                metrics[prefix] = obj
            elif isinstance(obj, list) and obj and isinstance(obj[0], (int, float)):
                metrics[prefix] = {
                    'count': len(obj),
                    'min': min(obj),
                    'max': max(obj),
                    'mean': sum(obj) / len(obj)
                }
        
        extract_numbers(data)
        
        # Keep only first 20 metrics
        return dict(list(metrics.items())[:20])
    
    def _analyze_json_structure(self, data: Any) -> Dict[str, Any]:
        """Analyze JSON structure."""
        def analyze(obj, depth=0):
            if depth > 5:  # Limit recursion
                return {'type': 'deep_nested'}
            
            if isinstance(obj, dict):
                return {
                    'type': 'object',
                    'keys': len(obj),
                    'sample_keys': list(obj.keys())[:10]
                }
            elif isinstance(obj, list):
                if not obj:
                    return {'type': 'array', 'length': 0}
                return {
                    'type': 'array',
                    'length': len(obj),
                    'item_type': analyze(obj[0], depth + 1)
                }
            else:
                return {'type': type(obj).__name__}
        
        return analyze(data)
    
    def _cache_preview(self, file_path: Path, preview_data: Dict[str, Any]) -> None:
        """Cache preview data."""
        cache_file = self.cache_dir / f"{preview_data['file_info']['hash']}.json"
        
        try:
            # Don't cache thumbnails (too large)
            cache_data = {**preview_data}
            cache_data['thumbnails'] = []
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, default=str)
        except Exception as e:
            logger.error(f"Error caching preview: {e}")
    
    def get_cached_preview(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get cached preview if available."""
        file_hash = self._calculate_file_hash(file_path)
        cache_file = self.cache_dir / f"{file_hash}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return None