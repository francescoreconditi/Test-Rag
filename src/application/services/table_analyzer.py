"""Table analyzer for detecting totals, subtotals and truth criteria."""

import re
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from decimal import Decimal
import logging

from src.application.services.data_normalizer import DataNormalizer, NormalizedValue

logger = logging.getLogger(__name__)


class RowType(Enum):
    """Types of table rows."""
    DATA = "data"                    # Regular data row
    SUBTOTAL = "subtotal"           # Section subtotal
    TOTAL = "total"                 # Grand total
    HEADER = "header"               # Column headers
    SEPARATOR = "separator"         # Visual separator
    DERIVED = "derived"             # Calculated/derived value
    

@dataclass
class TableRow:
    """Analyzed table row with metadata."""
    index: int
    original_data: List[str]
    row_type: RowType
    label: Optional[str] = None
    values: Dict[str, NormalizedValue] = None
    confidence: float = 1.0
    parent_section: Optional[str] = None
    calculation_formula: Optional[str] = None
    source_reference: Optional[str] = None
    
    def __post_init__(self):
        if self.values is None:
            self.values = {}


@dataclass
class ValidationResult:
    """Result of table validation."""
    is_valid: bool
    confidence: float
    errors: List[str]
    warnings: List[str]
    corrections: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.corrections is None:
            self.corrections = {}


class TableAnalyzer:
    """Analyzes table structure and validates totals."""
    
    def __init__(self, normalizer: DataNormalizer = None):
        """Initialize table analyzer."""
        self.normalizer = normalizer or DataNormalizer()
        
        # Patterns for detecting totals and subtotals
        self.total_patterns = [
            r'(?i)^totale?\s*(?:generale|complessivo)?$',
            r'(?i)^total?\s*(?:general|overall)?$',
            r'(?i)^somma\s*(?:totale)?$',
            r'(?i)^sum\s*(?:total)?$',
            r'(?i)^grand\s*total$',
            r'(?i)^totale\s+(?:attivo|passivo|ricavi|costi)$'
        ]
        
        self.subtotal_patterns = [
            r'(?i)^subtotale?\s*',
            r'(?i)^subtotal\s*',
            r'(?i)^totale\s+(?:parziale|sezione|gruppo)',
            r'(?i)^partial\s*total',
            r'(?i)^section\s*total',
            r'(?i)^di\s*cui\s*:',
            r'(?i)^\s*-\s*\w+'  # Indented items like "- Marketing"
        ]
        
        self.derived_patterns = [
            r'(?i)margine\s*(?:lordo|netto|operativo)?',
            r'(?i)ebitda?',
            r'(?i)ebit(?:da)?',
            r'(?i)utile\s*(?:lordo|netto|operativo)?',
            r'(?i)risultato\s*(?:operativo|netto)?',
            r'(?i)differenza',
            r'(?i)variazione',
            r'(?i)incremento|decremento',
            r'(?i)crescita|diminuzione'
        ]
        
        # Section markers
        self.section_patterns = [
            r'(?i)^(?:attivo|assets?)\s*$',
            r'(?i)^(?:passivo|liabilities?)\s*$',
            r'(?i)^(?:patrimonio|equity)\s*$',
            r'(?i)^(?:ricavi|revenues?)\s*$',
            r'(?i)^(?:costi|costs?|expenses?)\s*$',
            r'(?i)^(?:immobilizzazioni?|fixed\s*assets?)\s*$',
            r'(?i)^(?:circolante|current\s*assets?)\s*$'
        ]
    
    def analyze_table(self, 
                     table_data: List[List[str]], 
                     headers: Optional[List[str]] = None,
                     context: str = "") -> List[TableRow]:
        """Analyze table structure and classify rows."""
        if not table_data:
            return []
        
        analyzed_rows = []
        current_section = None
        
        for idx, row_data in enumerate(table_data):
            # Skip empty rows
            if not any(cell.strip() for cell in row_data if cell):
                continue
            
            # Get the first non-empty cell as potential label
            label = None
            for cell in row_data:
                if cell and cell.strip():
                    label = cell.strip()
                    break
            
            if not label:
                continue
            
            # Classify row type
            row_type = self._classify_row_type(label, row_data, idx)
            
            # Update current section if this is a section header
            if self._is_section_header(label):
                current_section = label
                row_type = RowType.HEADER
            
            # Normalize numeric values in the row
            values = self._extract_values(row_data, context)
            
            # Detect calculation formula for derived values
            formula = None
            if row_type == RowType.DERIVED:
                formula = self._detect_formula(label, values)
            
            analyzed_row = TableRow(
                index=idx,
                original_data=row_data[:],  # Make a copy
                row_type=row_type,
                label=label,
                values=values,
                confidence=self._calculate_row_confidence(label, values, row_type),
                parent_section=current_section,
                calculation_formula=formula
            )
            
            analyzed_rows.append(analyzed_row)
        
        return analyzed_rows
    
    def _classify_row_type(self, label: str, row_data: List[str], row_index: int) -> RowType:
        """Classify the type of table row."""
        # Check for totals
        for pattern in self.total_patterns:
            if re.search(pattern, label):
                return RowType.TOTAL
        
        # Check for subtotals  
        for pattern in self.subtotal_patterns:
            if re.search(pattern, label):
                return RowType.SUBTOTAL
        
        # Check for derived/calculated values
        for pattern in self.derived_patterns:
            if re.search(pattern, label):
                return RowType.DERIVED
        
        # Check for section headers
        if self._is_section_header(label):
            return RowType.HEADER
        
        # Default to data row
        return RowType.DATA
    
    def _is_section_header(self, label: str) -> bool:
        """Check if label is a section header."""
        for pattern in self.section_patterns:
            if re.search(pattern, label):
                return True
        return False
    
    def _extract_values(self, row_data: List[str], context: str) -> Dict[str, NormalizedValue]:
        """Extract and normalize numeric values from row."""
        values = {}
        
        for i, cell in enumerate(row_data):
            if not cell or not cell.strip():
                continue
            
            # Try to normalize as number
            normalized = self.normalizer.normalize_number(cell, context)
            if normalized:
                # Use column index as key, or try to infer column name
                col_key = f"col_{i}"
                values[col_key] = normalized
        
        return values
    
    def _detect_formula(self, label: str, values: Dict[str, NormalizedValue]) -> Optional[str]:
        """Detect calculation formula for derived values."""
        label_lower = label.lower()
        
        # Common financial formulas
        if 'margine' in label_lower and 'lordo' in label_lower:
            return "ricavi - costo_del_venduto"
        elif 'ebitda' in label_lower or 'mol' in label_lower:
            return "utile_operativo + ammortamenti + accantonamenti"
        elif 'ebit' in label_lower:
            return "ebitda - ammortamenti"
        elif 'utile' in label_lower and 'netto' in label_lower:
            return "utile_ante_imposte - imposte"
        elif 'differenza' in label_lower or 'variazione' in label_lower:
            return "valore_corrente - valore_precedente"
        
        return None
    
    def _calculate_row_confidence(self, 
                                 label: str, 
                                 values: Dict[str, NormalizedValue], 
                                 row_type: RowType) -> float:
        """Calculate confidence score for row classification."""
        base_confidence = 0.7
        
        # Boost confidence for clear patterns
        if row_type == RowType.TOTAL and any(p for p in self.total_patterns if re.search(p, label)):
            base_confidence += 0.2
        elif row_type == RowType.SUBTOTAL and any(p for p in self.subtotal_patterns if re.search(p, label)):
            base_confidence += 0.15
        elif row_type == RowType.DERIVED and any(p for p in self.derived_patterns if re.search(p, label)):
            base_confidence += 0.1
        
        # Boost confidence if we have numeric values
        if values:
            avg_value_confidence = sum(v.confidence for v in values.values()) / len(values)
            base_confidence += avg_value_confidence * 0.2
        
        return min(1.0, base_confidence)
    
    def validate_table(self, analyzed_rows: List[TableRow]) -> ValidationResult:
        """Validate table totals and calculations."""
        errors = []
        warnings = []
        corrections = {}
        
        # Group rows by section and type
        sections = self._group_by_section(analyzed_rows)
        
        for section_name, section_rows in sections.items():
            # Validate totals within each section
            section_validation = self._validate_section_totals(section_rows, section_name)
            errors.extend(section_validation['errors'])
            warnings.extend(section_validation['warnings'])
            corrections.update(section_validation['corrections'])
        
        # Cross-section validations (e.g., Attivo = Passivo + PN)
        cross_validation = self._validate_cross_sections(sections)
        errors.extend(cross_validation['errors'])
        warnings.extend(cross_validation['warnings'])
        
        is_valid = len(errors) == 0
        confidence = 1.0 - (len(errors) * 0.2 + len(warnings) * 0.1)
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=max(0.0, confidence),
            errors=errors,
            warnings=warnings,
            corrections=corrections
        )
    
    def _group_by_section(self, analyzed_rows: List[TableRow]) -> Dict[str, List[TableRow]]:
        """Group analyzed rows by section."""
        sections = {}
        current_section = "default"
        
        for row in analyzed_rows:
            if row.row_type == RowType.HEADER and self._is_section_header(row.label):
                current_section = row.label
                sections[current_section] = []
            else:
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].append(row)
        
        return sections
    
    def _validate_section_totals(self, 
                                section_rows: List[TableRow], 
                                section_name: str) -> Dict[str, List[str]]:
        """Validate totals within a section."""
        errors = []
        warnings = []
        corrections = {}
        
        # Find data rows and totals
        data_rows = [r for r in section_rows if r.row_type == RowType.DATA]
        total_rows = [r for r in section_rows if r.row_type == RowType.TOTAL]
        subtotal_rows = [r for r in section_rows if r.row_type == RowType.SUBTOTAL]
        
        # Validate each total row
        for total_row in total_rows:
            validation = self._validate_total_calculation(total_row, data_rows + subtotal_rows)
            if not validation['is_valid']:
                error_msg = f"Totale '{total_row.label}' in sezione '{section_name}': {validation['message']}"
                if validation['severity'] == 'error':
                    errors.append(error_msg)
                else:
                    warnings.append(error_msg)
                
                if 'suggested_value' in validation:
                    corrections[f"{section_name}_{total_row.label}"] = validation['suggested_value']
        
        return {
            'errors': errors,
            'warnings': warnings,
            'corrections': corrections
        }
    
    def _validate_total_calculation(self, 
                                  total_row: TableRow, 
                                  component_rows: List[TableRow]) -> Dict[str, Any]:
        """Validate if total equals sum of components."""
        if not total_row.values or not component_rows:
            return {'is_valid': True, 'message': 'No values to validate'}
        
        # For each numeric column in the total row
        for col_key, total_value in total_row.values.items():
            # Sum corresponding values from component rows
            component_sum = Decimal('0')
            component_count = 0
            
            for row in component_rows:
                if col_key in row.values:
                    component_value = row.values[col_key]
                    # Convert to base units for comparison
                    component_sum += Decimal(str(component_value.to_base_units()))
                    component_count += 1
            
            if component_count == 0:
                continue  # No components to validate against
            
            # Convert total to base units
            total_base = Decimal(str(total_value.to_base_units()))
            
            # Calculate tolerance (0.5% or minimum 0.01)
            tolerance = max(abs(total_base) * Decimal('0.005'), Decimal('0.01'))
            
            # Check if total matches sum within tolerance
            difference = abs(total_base - component_sum)
            
            if difference > tolerance:
                percentage_error = (difference / abs(total_base)) * 100 if total_base != 0 else 100
                
                return {
                    'is_valid': False,
                    'message': f"Somma componenti ({component_sum}) ≠ Totale ({total_base}). Differenza: {difference} ({percentage_error:.2f}%)",
                    'severity': 'error' if percentage_error > 5 else 'warning',
                    'suggested_value': float(component_sum),
                    'actual_difference': float(difference),
                    'percentage_error': float(percentage_error)
                }
        
        return {'is_valid': True, 'message': 'Totals validate correctly'}
    
    def _validate_cross_sections(self, sections: Dict[str, List[TableRow]]) -> Dict[str, List[str]]:
        """Validate cross-section constraints (e.g., balance sheet equation)."""
        errors = []
        warnings = []
        
        # Try to find balance sheet sections
        attivo_section = None
        passivo_section = None
        patrimonio_section = None
        
        for section_name, rows in sections.items():
            section_lower = section_name.lower()
            if 'attivo' in section_lower or 'assets' in section_lower:
                attivo_section = rows
            elif 'passivo' in section_lower and 'patrimonio' not in section_lower:
                passivo_section = rows
            elif 'patrimonio' in section_lower or 'equity' in section_lower:
                patrimonio_section = rows
        
        # Validate balance sheet equation: Attivo = Passivo + Patrimonio
        if attivo_section and (passivo_section or patrimonio_section):
            validation = self._validate_balance_sheet_equation(
                attivo_section, passivo_section, patrimonio_section
            )
            
            if not validation['is_valid']:
                if validation['severity'] == 'error':
                    errors.append(validation['message'])
                else:
                    warnings.append(validation['message'])
        
        return {
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_balance_sheet_equation(self,
                                       attivo_rows: List[TableRow],
                                       passivo_rows: Optional[List[TableRow]],
                                       patrimonio_rows: Optional[List[TableRow]]) -> Dict[str, Any]:
        """Validate: Total Assets = Total Liabilities + Total Equity."""
        
        # Find total values
        attivo_total = self._find_section_total(attivo_rows)
        passivo_total = self._find_section_total(passivo_rows) if passivo_rows else Decimal('0')
        patrimonio_total = self._find_section_total(patrimonio_rows) if patrimonio_rows else Decimal('0')
        
        if attivo_total is None:
            return {'is_valid': True, 'message': 'No Attivo total found'}
        
        passivo_patrimonio_sum = passivo_total + patrimonio_total
        
        # Calculate tolerance
        tolerance = max(abs(attivo_total) * Decimal('0.01'), Decimal('1'))  # 1% tolerance
        difference = abs(attivo_total - passivo_patrimonio_sum)
        
        if difference > tolerance:
            percentage_error = (difference / abs(attivo_total)) * 100 if attivo_total != 0 else 100
            
            return {
                'is_valid': False,
                'message': f"Equazione di bilancio non bilanciata: Attivo ({attivo_total}) ≠ Passivo+PN ({passivo_patrimonio_sum}). Differenza: {difference} ({percentage_error:.2f}%)",
                'severity': 'error' if percentage_error > 2 else 'warning',
                'attivo_total': float(attivo_total),
                'passivo_patrimonio_total': float(passivo_patrimonio_sum),
                'difference': float(difference),
                'percentage_error': float(percentage_error)
            }
        
        return {'is_valid': True, 'message': 'Balance sheet equation validates correctly'}
    
    def _find_section_total(self, section_rows: List[TableRow]) -> Optional[Decimal]:
        """Find the main total value in a section."""
        if not section_rows:
            return None
        
        # Look for total rows first
        total_rows = [r for r in section_rows if r.row_type == RowType.TOTAL]
        
        if total_rows:
            # Use the first total row's first numeric value
            total_row = total_rows[0]
            if total_row.values:
                first_value = list(total_row.values.values())[0]
                return Decimal(str(first_value.to_base_units()))
        
        # Fallback: sum all data rows
        total_sum = Decimal('0')
        data_rows = [r for r in section_rows if r.row_type == RowType.DATA]
        
        if data_rows and data_rows[0].values:
            col_key = list(data_rows[0].values.keys())[0]  # Use first column
            
            for row in data_rows:
                if col_key in row.values:
                    total_sum += Decimal(str(row.values[col_key].to_base_units()))
        
        return total_sum if total_sum != 0 else None
    
    def apply_truth_criteria(self, analyzed_rows: List[TableRow]) -> List[TableRow]:
        """Apply truth criteria to resolve conflicts between duplicate values."""
        
        # Group by metric/label
        metric_groups = {}
        for row in analyzed_rows:
            if row.label:
                key = self._normalize_metric_key(row.label)
                if key not in metric_groups:
                    metric_groups[key] = []
                metric_groups[key].append(row)
        
        # Resolve conflicts within each group
        resolved_rows = []
        for metric_key, rows in metric_groups.items():
            if len(rows) == 1:
                resolved_rows.extend(rows)  # No conflict
            else:
                # Apply truth criteria to select the best row
                best_row = self._select_best_row(rows)
                resolved_rows.append(best_row)
                
                # Log the conflict resolution
                logger.info(f"Truth criteria applied for '{metric_key}': selected row {best_row.index} over {[r.index for r in rows if r != best_row]}")
        
        return resolved_rows
    
    def _normalize_metric_key(self, label: str) -> str:
        """Normalize metric label for grouping."""
        # Remove common variations
        normalized = re.sub(r'\s+', ' ', label.lower().strip())
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        
        # Handle common synonyms
        synonyms = {
            'fatturato': 'ricavi',
            'vendite': 'ricavi', 
            'mol': 'ebitda',
            'margine operativo lordo': 'ebitda',
            'indebitamento netto': 'pfn',
            'posizione finanziaria netta': 'pfn'
        }
        
        for synonym, canonical in synonyms.items():
            if synonym in normalized:
                normalized = normalized.replace(synonym, canonical)
        
        return normalized
    
    def _select_best_row(self, rows: List[TableRow]) -> TableRow:
        """Select the best row using truth criteria."""
        # Criteria in order of priority:
        # 1. Higher confidence score
        # 2. More recent/specific context (prefer detailed tables over summaries)
        # 3. More structured format (TOTAL > SUBTOTAL > DATA)
        # 4. More complete values (more columns with data)
        
        def row_score(row: TableRow) -> Tuple[float, int, int, int]:
            confidence = row.confidence
            
            # Type priority: TOTAL(3) > SUBTOTAL(2) > DATA(1) > OTHER(0)
            type_priority = {
                RowType.TOTAL: 3,
                RowType.SUBTOTAL: 2, 
                RowType.DATA: 1
            }.get(row.row_type, 0)
            
            # Count non-zero values
            value_count = len([v for v in row.values.values() if v.to_base_units() != 0])
            
            # Prefer rows in "Prospetti" vs narrative sections
            context_priority = 1 if row.parent_section and 'prospett' in row.parent_section.lower() else 0
            
            return (confidence, type_priority, value_count, context_priority)
        
        # Select row with highest score
        best_row = max(rows, key=row_score)
        return best_row