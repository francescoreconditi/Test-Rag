"""Advanced PDF table extraction using Tabula-py and PDFPlumber."""

import tabula
import pdfplumber
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import logging
import re

logger = logging.getLogger(__name__)


class PDFTableExtractor:
    """Advanced PDF table extraction with multiple backends."""
    
    def __init__(self):
        """Initialize PDF table extractor."""
        self.backends = ['tabula', 'pdfplumber']
        logger.info("PDF table extractor initialized with Tabula and PDFPlumber")
    
    def extract_tables(self, 
                      pdf_path: str, 
                      pages: str = 'all',
                      method: str = 'auto') -> List[Dict[str, Any]]:
        """
        Extract tables from PDF using best available method.
        
        Args:
            pdf_path: Path to PDF file
            pages: Page numbers ('all', '1', '1-3', or list)
            method: 'tabula', 'pdfplumber', or 'auto'
            
        Returns:
            List of extracted tables with metadata
        """
        tables = []
        
        if method == 'auto':
            # Try Tabula first (better for bordered tables)
            tables = self._extract_with_tabula(pdf_path, pages)
            
            # If no tables found, try PDFPlumber
            if not tables:
                logger.info("No tables found with Tabula, trying PDFPlumber")
                tables = self._extract_with_pdfplumber(pdf_path, pages)
        elif method == 'tabula':
            tables = self._extract_with_tabula(pdf_path, pages)
        elif method == 'pdfplumber':
            tables = self._extract_with_pdfplumber(pdf_path, pages)
        
        # Post-process tables
        tables = self._post_process_tables(tables)
        
        # Identify financial tables
        for table in tables:
            table['is_financial'] = self._is_financial_table(table)
            if table['is_financial']:
                table['metrics'] = self._extract_financial_metrics(table)
        
        return tables
    
    def _extract_with_tabula(self, pdf_path: str, pages: str) -> List[Dict[str, Any]]:
        """Extract tables using Tabula-py."""
        tables = []
        
        try:
            # Try lattice mode first (for bordered tables)
            dfs = tabula.read_pdf(
                pdf_path,
                pages=pages,
                multiple_tables=True,
                lattice=True,
                pandas_options={'header': None}
            )
            
            if not dfs:
                # Try stream mode (for borderless tables)
                logger.info("Trying stream mode for borderless tables")
                dfs = tabula.read_pdf(
                    pdf_path,
                    pages=pages,
                    multiple_tables=True,
                    stream=True,
                    pandas_options={'header': None}
                )
            
            # Convert DataFrames to our format
            for i, df in enumerate(dfs):
                if not df.empty:
                    table = {
                        'index': i,
                        'method': 'tabula',
                        'dataframe': df,
                        'shape': df.shape,
                        'headers': self._detect_headers(df),
                        'data': df.values.tolist(),
                        'page': self._get_page_from_tabula(pdf_path, df)
                    }
                    tables.append(table)
            
            logger.info(f"Tabula extracted {len(tables)} tables")
            
        except Exception as e:
            logger.error(f"Tabula extraction error: {e}")
        
        return tables
    
    def _extract_with_pdfplumber(self, pdf_path: str, pages: str) -> List[Dict[str, Any]]:
        """Extract tables using PDFPlumber."""
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Parse pages parameter
                if pages == 'all':
                    page_nums = range(len(pdf.pages))
                elif isinstance(pages, str):
                    if '-' in pages:
                        start, end = pages.split('-')
                        page_nums = range(int(start) - 1, int(end))
                    else:
                        page_nums = [int(pages) - 1]
                else:
                    page_nums = [p - 1 for p in pages]
                
                # Extract tables from each page
                for page_num in page_nums:
                    if page_num < len(pdf.pages):
                        page = pdf.pages[page_num]
                        page_tables = page.extract_tables()
                        
                        for i, table_data in enumerate(page_tables):
                            if table_data and self._is_valid_table(table_data):
                                # Convert to DataFrame
                                df = pd.DataFrame(table_data)
                                
                                table = {
                                    'index': len(tables),
                                    'method': 'pdfplumber',
                                    'dataframe': df,
                                    'shape': df.shape,
                                    'headers': self._detect_headers(df),
                                    'data': table_data,
                                    'page': page_num + 1,
                                    'bbox': None  # PDFPlumber doesn't provide bbox easily
                                }
                                
                                # Extract table position if available
                                if hasattr(page, 'find_tables'):
                                    found_tables = page.find_tables()
                                    if i < len(found_tables):
                                        table['bbox'] = found_tables[i].bbox
                                
                                tables.append(table)
            
            logger.info(f"PDFPlumber extracted {len(tables)} tables")
            
        except Exception as e:
            logger.error(f"PDFPlumber extraction error: {e}")
        
        return tables
    
    def _detect_headers(self, df: pd.DataFrame) -> List[str]:
        """Detect and extract table headers."""
        headers = []
        
        if df.empty:
            return headers
        
        # Check first row for header-like content
        first_row = df.iloc[0] if len(df) > 0 else []
        
        # Heuristics for header detection
        is_header = False
        if first_row is not None and len(first_row) > 0:
            # Check if first row contains mostly strings
            non_null = [x for x in first_row if pd.notna(x)]
            if non_null:
                string_count = sum(1 for x in non_null if isinstance(x, str) and not self._is_number(str(x)))
                if string_count > len(non_null) / 2:
                    is_header = True
        
        if is_header:
            headers = [str(x) if pd.notna(x) else '' for x in first_row]
            # Set as DataFrame columns if appropriate
            try:
                df.columns = headers
                df = df.iloc[1:]  # Remove header row from data
            except:
                pass
        
        return headers
    
    def _is_valid_table(self, table_data: List[List]) -> bool:
        """Check if extracted data is a valid table."""
        if not table_data or len(table_data) < 2:
            return False
        
        # Check if rows have consistent column count
        col_counts = [len(row) for row in table_data if row]
        if not col_counts:
            return False
        
        # Allow some variation in column count
        avg_cols = sum(col_counts) / len(col_counts)
        valid_rows = sum(1 for c in col_counts if abs(c - avg_cols) <= 1)
        
        return valid_rows > len(col_counts) * 0.7
    
    def _post_process_tables(self, tables: List[Dict]) -> List[Dict]:
        """Post-process extracted tables."""
        processed = []
        
        for table in tables:
            # Clean data
            if 'dataframe' in table:
                df = table['dataframe']
                
                # Remove empty rows and columns
                df = df.dropna(how='all')
                df = df.dropna(axis=1, how='all')
                
                # Handle merged cells
                df = self._handle_merged_cells(df)
                
                # Normalize numbers
                df = self._normalize_table_numbers(df)
                
                table['dataframe'] = df
                table['shape'] = df.shape
                table['data'] = df.values.tolist()
            
            processed.append(table)
        
        return processed
    
    def _handle_merged_cells(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle merged cells in tables."""
        # Forward fill NaN values in first column (common for merged row headers)
        if len(df.columns) > 0:
            first_col = df.iloc[:, 0]
            if first_col.isna().any():
                df.iloc[:, 0] = first_col.fillna(method='ffill')
        
        # Forward fill NaN values in header row if detected
        if len(df) > 0:
            first_row = df.iloc[0]
            if first_row.isna().any():
                df.iloc[0] = first_row.fillna(method='ffill')
        
        return df
    
    def _normalize_table_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize numbers in table."""
        for col in df.columns:
            # Try to convert to numeric
            try:
                # Handle European number format
                df[col] = df[col].apply(self._parse_number)
            except:
                pass
        
        return df
    
    def _parse_number(self, value: Any) -> Any:
        """Parse various number formats."""
        if pd.isna(value):
            return value
        
        if isinstance(value, (int, float)):
            return value
        
        if not isinstance(value, str):
            return value
        
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[€$£¥\s]', '', str(value))
        
        # Handle parentheses for negative
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        
        # Handle percentage
        if '%' in cleaned:
            try:
                return float(cleaned.replace('%', '')) / 100
            except:
                return value
        
        # Handle different decimal separators
        if ',' in cleaned and '.' in cleaned:
            # Assume comma is thousands separator
            cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Check if comma is decimal separator (European)
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        
        try:
            if '.' in cleaned:
                return float(cleaned)
            else:
                return int(cleaned)
        except:
            return value
    
    def _is_number(self, text: str) -> bool:
        """Check if text represents a number."""
        try:
            self._parse_number(text)
            return isinstance(self._parse_number(text), (int, float))
        except:
            return False
    
    def _is_financial_table(self, table: Dict) -> bool:
        """Identify if table contains financial data."""
        financial_keywords = [
            'revenue', 'ricavi', 'fatturato', 'sales', 'vendite',
            'ebitda', 'ebit', 'mol', 'margine',
            'profit', 'utile', 'income', 'reddito',
            'asset', 'attiv', 'liabilit', 'passiv',
            'equity', 'patrimonio', 'cash', 'cassa',
            'debt', 'debit', 'cost', 'costi'
        ]
        
        # Check headers
        headers_text = ' '.join(table.get('headers', [])).lower()
        for keyword in financial_keywords:
            if keyword in headers_text:
                return True
        
        # Check first column
        if 'dataframe' in table and not table['dataframe'].empty:
            df = table['dataframe']
            if len(df.columns) > 0:
                first_col = df.iloc[:, 0].astype(str).str.lower()
                first_col_text = ' '.join(first_col.dropna().tolist())
                for keyword in financial_keywords:
                    if keyword in first_col_text:
                        return True
        
        return False
    
    def _extract_financial_metrics(self, table: Dict) -> Dict[str, Any]:
        """Extract financial metrics from table."""
        metrics = {}
        
        if 'dataframe' not in table or table['dataframe'].empty:
            return metrics
        
        df = table['dataframe']
        
        # Mapping of keywords to metric names
        metric_mappings = {
            'revenue': ['revenue', 'ricavi', 'fatturato', 'sales', 'vendite', 'turnover'],
            'ebitda': ['ebitda', 'mol', 'margine operativo lordo'],
            'ebit': ['ebit', 'operating income', 'reddito operativo'],
            'net_income': ['net income', 'utile netto', 'net profit', 'risultato netto'],
            'total_assets': ['total assets', 'totale attivo', 'attività totali'],
            'total_liabilities': ['total liabilities', 'totale passivo', 'passività totali'],
            'equity': ['equity', 'patrimonio netto', 'shareholders equity'],
            'cash': ['cash', 'cassa', 'disponibilità liquide'],
            'debt': ['debt', 'debito', 'indebitamento']
        }
        
        # Search in first column for metric names
        if len(df.columns) > 0:
            for i, row in df.iterrows():
                if pd.notna(row.iloc[0]):
                    row_label = str(row.iloc[0]).lower()
                    
                    for metric_name, keywords in metric_mappings.items():
                        if any(kw in row_label for kw in keywords):
                            # Get value from last numeric column
                            for j in range(len(row) - 1, 0, -1):
                                value = row.iloc[j]
                                if pd.notna(value) and isinstance(value, (int, float)):
                                    metrics[metric_name] = value
                                    break
                            break
        
        return metrics
    
    def _get_page_from_tabula(self, pdf_path: str, df: pd.DataFrame) -> Optional[int]:
        """Try to determine which page a table came from."""
        # This is a limitation of tabula-py
        # Would need to track during extraction
        return None
    
    def extract_all_tables_to_excel(self, pdf_path: str, output_path: str):
        """Extract all tables and save to Excel file."""
        tables = self.extract_tables(pdf_path)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for i, table in enumerate(tables):
                if 'dataframe' in table:
                    sheet_name = f"Table_{i+1}_p{table.get('page', 'unknown')}"
                    if table.get('is_financial'):
                        sheet_name = f"Financial_{i+1}"
                    
                    table['dataframe'].to_excel(
                        writer, 
                        sheet_name=sheet_name[:31],  # Excel limit
                        index=False
                    )
        
        logger.info(f"Exported {len(tables)} tables to {output_path}")
        return output_path