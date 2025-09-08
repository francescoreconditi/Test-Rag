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
    
    def get_page_with_highlights(self, 
                                file_path: str, 
                                page_number: int,
                                highlight_regions: List[Dict[str, Any]] = None,
                                dpi: int = 150) -> Optional[str]:
        """
        Get a page image with extraction highlights.
        
        Args:
            file_path: Path to the PDF file
            page_number: Page number (1-indexed)
            highlight_regions: List of regions to highlight
                Format: [{"x": float, "y": float, "width": float, "height": float, 
                         "color": str, "label": str}]
            dpi: Image resolution
        
        Returns:
            Base64-encoded PNG image or None if error
        """
        if not PYMUPDF_AVAILABLE or not PIL_AVAILABLE:
            logger.warning("Page highlighting requires PyMuPDF and Pillow")
            return None
        
        try:
            doc = fitz.open(file_path)
            page = doc[page_number - 1]
            
            # Render page to image
            mat = fitz.Matrix(dpi/72, dpi/72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image
            img_data = pix.pil_tobytes(format="PNG")
            img = Image.open(io.BytesIO(img_data))
            
            # Add highlights if provided
            if highlight_regions:
                img = self._add_highlight_overlays(img, highlight_regions, page.rect, dpi)
            
            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG", optimize=True)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            doc.close()
            
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"Error generating highlighted page: {e}")
            return None
    
    def _add_highlight_overlays(self, 
                               img: Image.Image, 
                               regions: List[Dict], 
                               page_rect: fitz.Rect,
                               dpi: int) -> Image.Image:
        """Add highlight overlays to the image."""
        from PIL import ImageDraw, ImageFont
        
        # Create overlay for drawing
        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay, 'RGBA')
        
        # Scale factor from PDF points to image pixels
        scale = dpi / 72
        
        # Color mapping
        color_map = {
            'yellow': (255, 255, 0, 100),
            'red': (255, 0, 0, 100),
            'green': (0, 255, 0, 100),
            'blue': (0, 0, 255, 100),
            'orange': (255, 165, 0, 100),
            'purple': (128, 0, 128, 100)
        }
        
        for region in regions:
            # Convert PDF coordinates to image pixels
            x = region['x'] * scale
            y = region['y'] * scale
            width = region['width'] * scale
            height = region['height'] * scale
            
            # Get color
            color_name = region.get('color', 'yellow')
            fill_color = color_map.get(color_name, color_map['yellow'])
            
            # Draw filled rectangle
            draw.rectangle(
                [x, y, x + width, y + height],
                fill=fill_color,
                outline=(255, 0, 0, 255),
                width=2
            )
            
            # Add label if provided
            if 'label' in region and region['label']:
                try:
                    font = ImageFont.truetype("arial.ttf", 12)
                except:
                    try:
                        font = ImageFont.load_default()
                    except:
                        continue  # Skip label if no font available
                
                label_text = str(region['label'])
                
                # Get text dimensions
                bbox = draw.textbbox((0, 0), label_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Label position (above the highlight)
                label_x = max(0, x)
                label_y = max(0, y - text_height - 5)
                
                # Draw label background
                draw.rectangle(
                    [label_x, label_y, label_x + text_width + 4, label_y + text_height + 4],
                    fill=(255, 255, 255, 220),
                    outline=(0, 0, 0, 255)
                )
                
                # Draw label text
                draw.text(
                    (label_x + 2, label_y + 2),
                    label_text,
                    fill=(0, 0, 0, 255),
                    font=font
                )
        
        # Composite overlay onto original image
        result = Image.alpha_composite(img.convert('RGBA'), overlay)
        return result.convert('RGB')
    
    def find_text_regions(self, 
                         file_path: str, 
                         page_number: int,
                         search_texts: List[str]) -> List[Dict[str, Any]]:
        """
        Find text regions on a PDF page.
        
        Args:
            file_path: Path to PDF
            page_number: Page number (1-indexed)
            search_texts: List of texts to find
        
        Returns:
            List of found regions with positions
        """
        if not PYMUPDF_AVAILABLE:
            return []
        
        regions = []
        
        try:
            doc = fitz.open(file_path)
            page = doc[page_number - 1]
            
            for search_text in search_texts:
                # Find all instances of the text
                text_instances = page.search_for(search_text)
                
                for i, rect in enumerate(text_instances):
                    regions.append({
                        'text': search_text,
                        'instance': i,
                        'x': rect.x0,
                        'y': rect.y0,
                        'width': rect.width,
                        'height': rect.height,
                        'color': 'yellow',
                        'label': f"'{search_text}'"
                    })
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error finding text regions: {e}")
        
        return regions
    
    def generate_source_preview(self, 
                               source_ref: str, 
                               extracted_value: str = None) -> Optional[str]:
        """
        Generate a preview image with the source reference highlighted.
        
        Args:
            source_ref: Source reference string (e.g., "file.pdf|p.12|row:Ricavi")
            extracted_value: The value that was extracted
        
        Returns:
            Base64-encoded image with highlights
        """
        try:
            # Parse source reference
            parts = source_ref.split('|')
            file_path = None
            page_num = None
            search_text = None
            
            for part in parts:
                if part.endswith('.pdf') or part.endswith('.xlsx'):
                    file_path = part
                elif part.startswith('p.'):
                    try:
                        page_num = int(part[2:])
                    except:
                        continue
                elif part.startswith('row:') or part.startswith('cell:'):
                    search_text = part.split(':', 1)[1]
            
            if not file_path or not page_num:
                logger.warning(f"Invalid source reference: {source_ref}")
                return None
            
            # Handle different file types
            if file_path.endswith('.pdf'):
                return self._generate_pdf_source_preview(
                    file_path, page_num, search_text, extracted_value
                )
            elif file_path.endswith(('.xlsx', '.xls')):
                return self._generate_excel_source_preview(
                    file_path, search_text, extracted_value
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating source preview: {e}")
            return None
    
    def _generate_pdf_source_preview(self, 
                                    file_path: str, 
                                    page_num: int,
                                    search_text: str = None,
                                    extracted_value: str = None) -> Optional[str]:
        """Generate PDF source preview with highlights."""
        
        highlight_regions = []
        
        if search_text:
            # Find the text and create highlight regions
            regions = self.find_text_regions(file_path, page_num, [search_text])
            highlight_regions.extend(regions)
        
        # Add extracted value highlight if different from search text
        if extracted_value and extracted_value != search_text:
            value_regions = self.find_text_regions(file_path, page_num, [extracted_value])
            for region in value_regions:
                region['color'] = 'green'
                region['label'] = f"Extracted: {extracted_value}"
            highlight_regions.extend(value_regions)
        
        return self.get_page_with_highlights(
            file_path, page_num, highlight_regions
        )
    
    def _generate_excel_source_preview(self, 
                                      file_path: str,
                                      cell_ref: str = None,
                                      extracted_value: str = None) -> Optional[str]:
        """Generate Excel source preview (simplified table view)."""
        try:
            # For Excel, we create a text-based preview since visual highlighting is complex
            df = pd.read_excel(file_path, nrows=20, sheet_name=0)
            
            # Create a simple HTML table representation
            html_table = df.to_html(max_rows=20, max_cols=10, classes="excel-preview")
            
            # Convert HTML to image using a simple text representation
            preview_text = f"Excel File: {Path(file_path).name}\n\n"
            preview_text += f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n\n"
            preview_text += "First 10 rows:\n"
            preview_text += df.head(10).to_string(max_cols=8)
            
            if cell_ref:
                preview_text += f"\n\n[HIGHLIGHTED] Cell reference: {cell_ref}"
            if extracted_value:
                preview_text += f"\n[EXTRACTED] Value: {extracted_value}"
            
            # For now, return None - could implement HTML-to-image conversion
            logger.info(f"Excel preview generated (text-based): {len(preview_text)} chars")
            return None
            
        except Exception as e:
            logger.error(f"Error generating Excel preview: {e}")
            return None