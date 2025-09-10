"""Parsers for various document formats (HTML, XML, JSON, Images)."""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any, Optional, Union

from bs4 import BeautifulSoup
from PIL import Image
import pytesseract
import xmltodict

from src.domain.value_objects.source_reference import SourceReference

logger = logging.getLogger(__name__)


@dataclass
class ParsedContent:
    """Represents parsed content from any format."""
    format_type: str
    content_type: str  # 'structured' or 'unstructured'
    data: Union[dict, list, str]  # Parsed data
    tables: Optional[list[dict]] = None
    metadata: Optional[dict[str, Any]] = None
    source_ref: Optional[SourceReference] = None
    extraction_time: float = 0.0
    errors: Optional[list[str]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'format_type': self.format_type,
            'content_type': self.content_type,
            'has_tables': bool(self.tables),
            'table_count': len(self.tables) if self.tables else 0,
            'extraction_time': self.extraction_time,
            'error_count': len(self.errors) if self.errors else 0,
            'metadata': self.metadata
        }


class HTMLParser:
    """Parser for HTML documents."""

    def __init__(self, parser_backend: str = 'lxml'):
        """
        Initialize HTML parser.

        Args:
            parser_backend: 'lxml', 'html.parser', or 'html5lib'
        """
        self.parser_backend = parser_backend

    def parse(self, file_path: str) -> ParsedContent:
        """Parse HTML file."""
        start_time = datetime.now()
        errors = []

        try:
            with open(file_path, encoding='utf-8') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, self.parser_backend)

            # Extract text content
            text_content = soup.get_text(separator='\n', strip=True)

            # Extract tables
            tables = self._extract_tables(soup)

            # Extract metadata
            metadata = self._extract_metadata(soup)

            # Extract structured data (JSON-LD, microdata)
            structured_data = self._extract_structured_data(soup)

            # Determine content type
            content_type = 'structured' if tables or structured_data else 'unstructured'

            # Create source reference
            source_ref = SourceReference(
                file_path=file_path,
                extraction_method=f"beautifulsoup_{self.parser_backend}"
            )

            elapsed_time = (datetime.now() - start_time).total_seconds()

            return ParsedContent(
                format_type='HTML',
                content_type=content_type,
                data={
                    'text': text_content,
                    'structured_data': structured_data
                },
                tables=tables,
                metadata=metadata,
                source_ref=source_ref,
                extraction_time=elapsed_time,
                errors=errors if errors else None
            )

        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            errors.append(str(e))

            return ParsedContent(
                format_type='HTML',
                content_type='unstructured',
                data={'error': str(e)},
                errors=errors
            )

    def _extract_tables(self, soup: BeautifulSoup) -> list[dict]:
        """Extract tables from HTML."""
        tables = []

        for table_idx, table in enumerate(soup.find_all('table')):
            table_data = []
            headers = []

            # Extract headers
            thead = table.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

            # If no thead, check first row
            if not headers:
                first_row = table.find('tr')
                if first_row:
                    potential_headers = first_row.find_all('th')
                    if potential_headers:
                        headers = [th.get_text(strip=True) for th in potential_headers]

            # Extract data rows
            tbody = table.find('tbody') or table
            for row in tbody.find_all('tr'):
                # Skip header rows
                if row.find('th') and not row.find('td'):
                    continue

                row_data = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                if row_data:
                    table_data.append(row_data)

            if table_data:
                tables.append({
                    'index': table_idx,
                    'headers': headers,
                    'data': table_data,
                    'row_count': len(table_data),
                    'column_count': len(table_data[0]) if table_data else 0
                })

        return tables

    def _extract_metadata(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract metadata from HTML."""
        metadata = {}

        # Title
        title = soup.find('title')
        if title:
            metadata['title'] = title.get_text(strip=True)

        # Meta tags
        meta_tags = {}
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                meta_tags[name] = content

        if meta_tags:
            metadata['meta_tags'] = meta_tags

        # Links
        link_count = len(soup.find_all('a'))
        metadata['link_count'] = link_count

        # Forms
        form_count = len(soup.find_all('form'))
        metadata['form_count'] = form_count

        return metadata

    def _extract_structured_data(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract structured data (JSON-LD, microdata) from HTML."""
        structured_data = {}

        # JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        if json_ld_scripts:
            json_ld_data = []
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    json_ld_data.append(data)
                except json.JSONDecodeError:
                    pass

            if json_ld_data:
                structured_data['json_ld'] = json_ld_data

        # Microdata (basic extraction)
        itemscope_elements = soup.find_all(attrs={'itemscope': True})
        if itemscope_elements:
            microdata = []
            for element in itemscope_elements:
                item_type = element.get('itemtype')
                if item_type:
                    microdata.append({'type': item_type})

            if microdata:
                structured_data['microdata'] = microdata

        return structured_data


class XMLParser:
    """Parser for XML documents."""

    def parse(self, file_path: str) -> ParsedContent:
        """Parse XML file."""
        start_time = datetime.now()
        errors = []

        try:
            with open(file_path, encoding='utf-8') as f:
                xml_content = f.read()

            # Parse XML to dictionary
            data = xmltodict.parse(xml_content)

            # Extract financial data patterns
            financial_data = self._extract_financial_patterns(data)

            # Flatten nested structure for easier access
            flattened = self._flatten_dict(data)

            # Create source reference
            source_ref = SourceReference(
                file_path=file_path,
                extraction_method="xmltodict"
            )

            elapsed_time = (datetime.now() - start_time).total_seconds()

            return ParsedContent(
                format_type='XML',
                content_type='structured',
                data={
                    'original': data,
                    'flattened': flattened,
                    'financial_data': financial_data
                },
                metadata={'element_count': len(flattened)},
                source_ref=source_ref,
                extraction_time=elapsed_time,
                errors=errors if errors else None
            )

        except Exception as e:
            logger.error(f"XML parsing failed: {e}")
            errors.append(str(e))

            return ParsedContent(
                format_type='XML',
                content_type='structured',
                data={'error': str(e)},
                errors=errors
            )

    def _extract_financial_patterns(self, data: dict) -> dict[str, Any]:
        """Extract common financial data patterns from XML."""
        financial_data = {}

        # Common financial XML patterns
        patterns = {
            'amount': re.compile(r'amount|value|total|sum', re.IGNORECASE),
            'currency': re.compile(r'currency|curr|ccy', re.IGNORECASE),
            'date': re.compile(r'date|period|year|month', re.IGNORECASE),
            'identifier': re.compile(r'id|code|number|ref', re.IGNORECASE)
        }

        def search_patterns(obj, path=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key

                    for pattern_name, pattern in patterns.items():
                        if pattern.search(key):
                            if pattern_name not in financial_data:
                                financial_data[pattern_name] = []
                            financial_data[pattern_name].append({
                                'path': new_path,
                                'key': key,
                                'value': value
                            })

                    search_patterns(value, new_path)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    search_patterns(item, f"{path}[{idx}]")

        search_patterns(data)
        return financial_data

    def _flatten_dict(self, data: dict, parent_key: str = '', sep: str = '.') -> dict:
        """Flatten nested dictionary."""
        items = []

        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        items.extend(self._flatten_dict(item, f"{new_key}[{i}]", sep=sep).items())
                    else:
                        items.append((f"{new_key}[{i}]", item))
            else:
                items.append((new_key, v))

        return dict(items)


class JSONParser:
    """Enhanced parser for JSON documents."""

    def parse(self, file_path: str) -> ParsedContent:
        """Parse JSON file."""
        start_time = datetime.now()
        errors = []

        try:
            with open(file_path, encoding='utf-8') as f:
                data = json.load(f)

            # Detect if it's tabular JSON (array of objects with same keys)
            is_tabular = self._is_tabular_json(data)

            tables = None
            if is_tabular:
                tables = [self._json_to_table(data)]

            # Extract nested financial data
            financial_data = self._extract_financial_data(data)

            # Create source reference
            source_ref = SourceReference(
                file_path=file_path,
                extraction_method="json_native"
            )

            elapsed_time = (datetime.now() - start_time).total_seconds()

            return ParsedContent(
                format_type='JSON',
                content_type='structured',
                data={
                    'original': data,
                    'financial_data': financial_data,
                    'is_tabular': is_tabular
                },
                tables=tables,
                metadata={
                    'is_array': isinstance(data, list),
                    'item_count': len(data) if isinstance(data, list) else 1
                },
                source_ref=source_ref,
                extraction_time=elapsed_time,
                errors=errors if errors else None
            )

        except Exception as e:
            logger.error(f"JSON parsing failed: {e}")
            errors.append(str(e))

            return ParsedContent(
                format_type='JSON',
                content_type='structured',
                data={'error': str(e)},
                errors=errors
            )

    def _is_tabular_json(self, data: Any) -> bool:
        """Check if JSON represents tabular data."""
        if not isinstance(data, list) or len(data) < 2:
            return False

        # Check if all items are dictionaries with similar keys
        if not all(isinstance(item, dict) for item in data):
            return False

        first_keys = set(data[0].keys())
        return all(set(item.keys()) == first_keys for item in data[1:])

    def _json_to_table(self, data: list[dict]) -> dict:
        """Convert tabular JSON to table format."""
        if not data:
            return {}

        headers = list(data[0].keys())
        rows = []

        for item in data:
            row = [str(item.get(header, '')) for header in headers]
            rows.append(row)

        return {
            'headers': headers,
            'data': rows,
            'row_count': len(rows),
            'column_count': len(headers)
        }

    def _extract_financial_data(self, data: Any) -> dict[str, Any]:
        """Extract financial data from JSON."""
        financial_keywords = {
            'revenue', 'sales', 'profit', 'loss', 'income', 'expense',
            'asset', 'liability', 'equity', 'cash', 'debt', 'ebitda',
            'margin', 'cost', 'price', 'amount', 'total', 'balance'
        }

        financial_data = {}

        def extract(obj, path=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key

                    # Check if key contains financial keywords
                    key_lower = key.lower()
                    for keyword in financial_keywords:
                        if keyword in key_lower:
                            if keyword not in financial_data:
                                financial_data[keyword] = []
                            financial_data[keyword].append({
                                'path': new_path,
                                'key': key,
                                'value': value
                            })
                            break

                    extract(value, new_path)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    extract(item, f"{path}[{idx}]")

        extract(data)
        return financial_data


class ImageParser:
    """Parser for image files with OCR capabilities."""

    def __init__(self, ocr_language: str = 'ita+eng'):
        """
        Initialize image parser.

        Args:
            ocr_language: Languages for OCR
        """
        self.ocr_language = ocr_language

    def parse(self, file_path: str) -> ParsedContent:
        """Parse image file using OCR."""
        start_time = datetime.now()
        errors = []

        try:
            # Open image
            image = Image.open(file_path)

            # Extract text using OCR
            text = pytesseract.image_to_string(image, lang=self.ocr_language)

            # Extract data (tables if possible)
            data = pytesseract.image_to_data(image, lang=self.ocr_language, output_type=pytesseract.Output.DICT)

            # Try to detect tables in OCR output
            tables = self._detect_tables_in_ocr(data)

            # Get image metadata
            metadata = {
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'width': image.width,
                'height': image.height
            }

            # Create source reference
            source_ref = SourceReference(
                file_path=file_path,
                extraction_method=f"tesseract_ocr_{self.ocr_language}"
            )

            elapsed_time = (datetime.now() - start_time).total_seconds()

            return ParsedContent(
                format_type='IMAGE',
                content_type='unstructured',
                data={
                    'text': text,
                    'ocr_data': data
                },
                tables=tables,
                metadata=metadata,
                source_ref=source_ref,
                extraction_time=elapsed_time,
                errors=errors if errors else None
            )

        except Exception as e:
            logger.error(f"Image parsing failed: {e}")
            errors.append(str(e))

            return ParsedContent(
                format_type='IMAGE',
                content_type='unstructured',
                data={'error': str(e)},
                errors=errors
            )

    def _detect_tables_in_ocr(self, ocr_data: dict) -> Optional[list[dict]]:
        """Detect potential tables in OCR output."""
        # Basic table detection based on aligned text blocks
        # This is a simplified approach - more sophisticated methods exist

        tables = []

        # Group text by approximate rows (y-coordinate)
        rows = {}
        threshold = 10  # Pixels threshold for same row

        for i, text in enumerate(ocr_data['text']):
            if text.strip():
                y = ocr_data['top'][i]

                # Find closest row
                row_key = None
                for existing_y in rows:
                    if abs(existing_y - y) < threshold:
                        row_key = existing_y
                        break

                if row_key is None:
                    row_key = y
                    rows[row_key] = []

                rows[row_key].append({
                    'text': text,
                    'x': ocr_data['left'][i],
                    'confidence': ocr_data['conf'][i]
                })

        # Sort rows by y-coordinate
        sorted_rows = sorted(rows.items(), key=lambda x: x[0])

        # Convert to table if we have multiple rows with multiple columns
        if len(sorted_rows) > 1:
            table_data = []
            for _, row_items in sorted_rows:
                # Sort items in row by x-coordinate
                sorted_items = sorted(row_items, key=lambda x: x['x'])
                row_text = [item['text'] for item in sorted_items]
                table_data.append(row_text)

            # Only consider it a table if we have consistent column counts
            col_counts = [len(row) for row in table_data]
            if col_counts and max(col_counts) > 1 and min(col_counts) == max(col_counts):
                tables.append({
                    'data': table_data,
                    'row_count': len(table_data),
                    'column_count': col_counts[0]
                })

        return tables if tables else None


class FormatParserFactory:
    """Factory for creating appropriate parser based on file format."""

    @staticmethod
    def get_parser(file_path: str) -> Optional[Union[HTMLParser, XMLParser, JSONParser, ImageParser]]:
        """Get appropriate parser for file."""
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension in ['.html', '.htm']:
            return HTMLParser()
        elif extension == '.xml':
            return XMLParser()
        elif extension in ['.json', '.jsonl']:
            return JSONParser()
        elif extension in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
            return ImageParser()
        else:
            logger.warning(f"No parser available for extension: {extension}")
            return None

    @staticmethod
    def parse_file(file_path: str) -> Optional[ParsedContent]:
        """Parse file with appropriate parser."""
        parser = FormatParserFactory.get_parser(file_path)

        if parser:
            return parser.parse(file_path)
        else:
            return None
