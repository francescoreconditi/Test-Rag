"""HTML and XML document parser for financial reports."""

from bs4 import BeautifulSoup
import xmltodict
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class HTMLXMLParser:
    """Parser for HTML and XML financial documents."""
    
    def __init__(self):
        """Initialize HTML/XML parser."""
        self.supported_formats = ['.html', '.htm', '.xml', '.xhtml', '.xbrl']
        logger.info("HTML/XML parser initialized")
    
    def parse_html(self, content: Union[str, bytes], encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Parse HTML content and extract financial data.
        
        Args:
            content: HTML content as string or bytes
            encoding: Character encoding
            
        Returns:
            Parsed data with tables and text extracted
        """
        try:
            if isinstance(content, bytes):
                content = content.decode(encoding, errors='ignore')
            
            soup = BeautifulSoup(content, 'lxml')
            
            # Extract metadata
            metadata = self._extract_html_metadata(soup)
            
            # Extract tables
            tables = self._extract_html_tables(soup)
            
            # Extract financial data from text
            financial_data = self._extract_financial_data(soup)
            
            # Extract structured data (if present)
            structured_data = self._extract_structured_data(soup)
            
            return {
                'format': 'html',
                'metadata': metadata,
                'tables': tables,
                'financial_data': financial_data,
                'structured_data': structured_data,
                'raw_text': soup.get_text(separator=' ', strip=True)[:5000]
            }
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return {'error': str(e), 'format': 'html'}
    
    def parse_xml(self, content: Union[str, bytes], encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Parse XML content including XBRL financial reports.
        
        Args:
            content: XML content as string or bytes
            encoding: Character encoding
            
        Returns:
            Parsed XML data as dictionary
        """
        try:
            if isinstance(content, bytes):
                content = content.decode(encoding, errors='ignore')
            
            # Parse XML to dictionary
            xml_dict = xmltodict.parse(content)
            
            # Check if it's XBRL
            if self._is_xbrl(xml_dict):
                return self._parse_xbrl(xml_dict)
            
            # Extract financial metrics from generic XML
            financial_metrics = self._extract_xml_metrics(xml_dict)
            
            return {
                'format': 'xml',
                'data': xml_dict,
                'financial_metrics': financial_metrics,
                'structure': self._analyze_xml_structure(xml_dict)
            }
            
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return {'error': str(e), 'format': 'xml'}
    
    def _extract_html_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract metadata from HTML head."""
        metadata = {}
        
        # Title
        title = soup.find('title')
        if title:
            metadata['title'] = title.get_text(strip=True)
        
        # Meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                metadata[name] = content
        
        return metadata
    
    def _extract_html_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract all tables from HTML."""
        tables = []
        
        for i, table in enumerate(soup.find_all('table')):
            table_data = {
                'index': i,
                'headers': [],
                'rows': [],
                'caption': None
            }
            
            # Get caption if exists
            caption = table.find('caption')
            if caption:
                table_data['caption'] = caption.get_text(strip=True)
            
            # Extract headers
            thead = table.find('thead')
            if thead:
                headers = []
                for th in thead.find_all('th'):
                    headers.append(th.get_text(strip=True))
                table_data['headers'] = headers
            
            # Extract rows
            tbody = table.find('tbody') or table
            for tr in tbody.find_all('tr'):
                row = []
                for td in tr.find_all(['td', 'th']):
                    cell_text = td.get_text(strip=True)
                    # Try to parse numbers
                    cell_value = self._parse_cell_value(cell_text)
                    row.append(cell_value)
                
                if row and any(cell for cell in row):  # Skip empty rows
                    table_data['rows'].append(row)
            
            # Try to identify financial tables
            if self._is_financial_table(table_data):
                table_data['is_financial'] = True
                table_data['metrics'] = self._extract_table_metrics(table_data)
            
            tables.append(table_data)
        
        return tables
    
    def _extract_financial_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract financial data from HTML text using patterns."""
        financial_data = {}
        
        # Common financial patterns
        patterns = {
            'revenue': [
                r'(?:revenues?|sales|fatturato|ricavi)[:\s]+([€$£¥]?[\d,.\s]+(?:million|billion|mln|mld)?)',
                r'total\s+(?:revenues?|sales)[:\s]+([€$£¥]?[\d,.\s]+)'
            ],
            'ebitda': [
                r'ebitda[:\s]+([€$£¥]?[\d,.\s]+(?:million|billion|mln|mld)?)',
                r'mol[:\s]+([€$£¥]?[\d,.\s]+)'
            ],
            'net_income': [
                r'net\s+(?:income|profit)[:\s]+([€$£¥]?[\d,.\s]+)',
                r'utile\s+netto[:\s]+([€$£¥]?[\d,.\s]+)'
            ],
            'total_assets': [
                r'total\s+assets[:\s]+([€$£¥]?[\d,.\s]+)',
                r'(?:attivo|attività)\s+totale[:\s]+([€$£¥]?[\d,.\s]+)'
            ],
            'employees': [
                r'(?:employees|dipendenti|fte)[:\s]+(\d+)',
                r'number\s+of\s+employees[:\s]+(\d+)'
            ]
        }
        
        text = soup.get_text(separator=' ', strip=True).lower()
        
        for metric, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    financial_data[metric] = match.group(1)
                    break
        
        return financial_data
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured data (JSON-LD, microdata)."""
        structured = {}
        
        # Look for JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        if json_ld_scripts:
            structured['json_ld'] = []
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    structured['json_ld'].append(data)
                except:
                    pass
        
        # Look for microdata
        items = soup.find_all(attrs={'itemscope': True})
        if items:
            structured['microdata'] = []
            for item in items:
                item_data = {
                    'type': item.get('itemtype', ''),
                    'properties': {}
                }
                for prop in item.find_all(attrs={'itemprop': True}):
                    prop_name = prop.get('itemprop')
                    prop_value = prop.get('content') or prop.get_text(strip=True)
                    item_data['properties'][prop_name] = prop_value
                structured['microdata'].append(item_data)
        
        return structured
    
    def _parse_cell_value(self, text: str) -> Union[str, float, int]:
        """Parse cell value to appropriate type."""
        if not text:
            return ''
        
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[€$£¥\s]', '', text)
        
        # Handle percentages
        if '%' in text:
            try:
                return float(cleaned.replace('%', '')) / 100
            except:
                pass
        
        # Handle parentheses for negative numbers
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        
        # Try to parse as number
        try:
            # Handle different decimal separators
            if ',' in cleaned and '.' in cleaned:
                # Assume comma is thousands separator
                cleaned = cleaned.replace(',', '')
            elif ',' in cleaned:
                # Could be decimal separator (European style)
                if cleaned.count(',') == 1 and len(cleaned.split(',')[1]) <= 2:
                    cleaned = cleaned.replace(',', '.')
                else:
                    cleaned = cleaned.replace(',', '')
            
            if '.' in cleaned:
                return float(cleaned)
            else:
                return int(cleaned)
        except:
            return text
    
    def _is_financial_table(self, table_data: Dict) -> bool:
        """Check if a table contains financial data."""
        financial_keywords = [
            'revenue', 'ricavi', 'fatturato', 'sales',
            'ebitda', 'ebit', 'profit', 'utile',
            'assets', 'liabilities', 'equity', 'patrimonio',
            'cash', 'debt', 'cassa', 'debito'
        ]
        
        # Check headers
        headers_text = ' '.join(table_data['headers']).lower()
        for keyword in financial_keywords:
            if keyword in headers_text:
                return True
        
        # Check first column (usually contains metric names)
        if table_data['rows']:
            first_col = [str(row[0]).lower() if row else '' for row in table_data['rows'][:10]]
            first_col_text = ' '.join(first_col)
            for keyword in financial_keywords:
                if keyword in first_col_text:
                    return True
        
        return False
    
    def _extract_table_metrics(self, table_data: Dict) -> Dict[str, Any]:
        """Extract financial metrics from a table."""
        metrics = {}
        
        if not table_data['rows']:
            return metrics
        
        # Assume first column contains metric names
        for row in table_data['rows']:
            if len(row) >= 2:
                metric_name = str(row[0]).lower().strip()
                
                # Map to standard metrics
                metric_mappings = {
                    'revenue': ['revenue', 'ricavi', 'fatturato', 'sales', 'turnover'],
                    'ebitda': ['ebitda', 'mol', 'margine operativo lordo'],
                    'ebit': ['ebit', 'operating income', 'reddito operativo'],
                    'net_income': ['net income', 'utile netto', 'net profit'],
                    'total_assets': ['total assets', 'attivo totale', 'totale attività'],
                    'total_liabilities': ['total liabilities', 'passivo totale'],
                    'equity': ['equity', 'patrimonio netto', 'shareholders equity']
                }
                
                for standard_name, keywords in metric_mappings.items():
                    if any(kw in metric_name for kw in keywords):
                        # Get the value from the last numeric column
                        for i in range(len(row) - 1, 0, -1):
                            if isinstance(row[i], (int, float)):
                                metrics[standard_name] = row[i]
                                break
                        break
        
        return metrics
    
    def _is_xbrl(self, xml_dict: Dict) -> bool:
        """Check if XML is XBRL format."""
        # Check for XBRL namespaces or root elements
        xbrl_indicators = ['xbrl', 'xbrli', 'gaap', 'ifrs']
        
        for key in xml_dict.keys():
            if any(indicator in key.lower() for indicator in xbrl_indicators):
                return True
        
        return False
    
    def _parse_xbrl(self, xml_dict: Dict) -> Dict[str, Any]:
        """Parse XBRL financial report."""
        xbrl_data = {
            'format': 'xbrl',
            'contexts': {},
            'units': {},
            'facts': []
        }
        
        # Extract contexts (periods)
        contexts = self._find_nested_key(xml_dict, 'context')
        if contexts:
            if not isinstance(contexts, list):
                contexts = [contexts]
            for context in contexts:
                context_id = context.get('@id', '')
                period = context.get('period', {})
                xbrl_data['contexts'][context_id] = {
                    'instant': period.get('instant'),
                    'startDate': period.get('startDate'),
                    'endDate': period.get('endDate')
                }
        
        # Extract facts (financial values)
        facts = self._extract_xbrl_facts(xml_dict)
        xbrl_data['facts'] = facts
        
        # Map to standard metrics
        xbrl_data['financial_metrics'] = self._map_xbrl_to_metrics(facts)
        
        return xbrl_data
    
    def _extract_xbrl_facts(self, data: Any, facts: List = None) -> List[Dict]:
        """Recursively extract XBRL facts."""
        if facts is None:
            facts = []
        
        if isinstance(data, dict):
            # Check if this is a fact (has @contextRef)
            if '@contextRef' in data:
                fact = {
                    'concept': data.get('@name', 'unknown'),
                    'value': data.get('#text', data.get('$', '')),
                    'context': data.get('@contextRef'),
                    'unit': data.get('@unitRef'),
                    'decimals': data.get('@decimals')
                }
                facts.append(fact)
            
            # Recurse
            for value in data.values():
                self._extract_xbrl_facts(value, facts)
        elif isinstance(data, list):
            for item in data:
                self._extract_xbrl_facts(item, facts)
        
        return facts
    
    def _map_xbrl_to_metrics(self, facts: List[Dict]) -> Dict[str, Any]:
        """Map XBRL facts to standard financial metrics."""
        metrics = {}
        
        # Common XBRL to metric mappings
        mappings = {
            'revenue': ['revenues', 'salesrevenuenet', 'totalrevenues'],
            'ebitda': ['ebitda', 'earningsbeforeinteresttaxesdepreciationandamortization'],
            'net_income': ['netincomeloss', 'profitloss', 'netincome'],
            'total_assets': ['assets', 'totalassets'],
            'total_liabilities': ['liabilities', 'totalliabilities'],
            'equity': ['stockholdersequity', 'equity', 'totalequity']
        }
        
        for fact in facts:
            concept = fact['concept'].lower().replace(':', '').replace('_', '')
            
            for metric, keywords in mappings.items():
                if any(kw in concept for kw in keywords):
                    try:
                        value = float(fact['value'])
                        metrics[metric] = value
                    except:
                        pass
                    break
        
        return metrics
    
    def _extract_xml_metrics(self, xml_dict: Dict) -> Dict[str, Any]:
        """Extract financial metrics from generic XML."""
        metrics = {}
        
        # Look for common financial elements
        financial_elements = {
            'revenue': ['revenue', 'sales', 'ricavi', 'fatturato'],
            'ebitda': ['ebitda', 'mol'],
            'net_income': ['netincome', 'net_income', 'utile_netto'],
            'assets': ['assets', 'total_assets', 'attivo'],
            'liabilities': ['liabilities', 'total_liabilities', 'passivo'],
            'equity': ['equity', 'patrimonio_netto']
        }
        
        for metric, keywords in financial_elements.items():
            value = None
            for keyword in keywords:
                value = self._find_nested_key(xml_dict, keyword)
                if value is not None:
                    break
            
            if value is not None:
                try:
                    metrics[metric] = float(value)
                except:
                    metrics[metric] = value
        
        return metrics
    
    def _find_nested_key(self, data: Any, target_key: str) -> Any:
        """Find a key in nested dictionary/list structure."""
        target_key_lower = target_key.lower()
        
        if isinstance(data, dict):
            for key, value in data.items():
                if key.lower() == target_key_lower:
                    return value
                elif isinstance(value, (dict, list)):
                    result = self._find_nested_key(value, target_key)
                    if result is not None:
                        return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_nested_key(item, target_key)
                if result is not None:
                    return result
        
        return None
    
    def _analyze_xml_structure(self, xml_dict: Dict) -> Dict[str, Any]:
        """Analyze XML structure for debugging."""
        def get_structure(data, max_depth=3, current_depth=0):
            if current_depth >= max_depth:
                return "..."
            
            if isinstance(data, dict):
                return {k: get_structure(v, max_depth, current_depth + 1) 
                       for k, v in list(data.items())[:5]}
            elif isinstance(data, list):
                if data:
                    return [get_structure(data[0], max_depth, current_depth + 1)]
                return []
            else:
                return type(data).__name__
        
        return get_structure(xml_dict)