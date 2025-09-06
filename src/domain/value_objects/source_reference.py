"""Source reference value objects for detailed provenance tracking."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Union
import hashlib
from datetime import datetime


class SourceType(Enum):
    """Types of document sources."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    DOCX = "docx" 
    TXT = "txt"
    MD = "markdown"
    JSON = "json"
    HTML = "html"


@dataclass(frozen=True)
class SourceReference:
    """Immutable source reference with detailed provenance."""
    
    # Core identification
    file_name: str
    file_hash: str  # SHA-256 of original file
    source_type: SourceType
    
    # Location within document
    page: Optional[int] = None
    sheet: Optional[str] = None  
    cell: Optional[str] = None
    table_index: Optional[int] = None
    row_label: Optional[str] = None
    column_label: Optional[str] = None
    
    # Text/content location
    text_start: Optional[int] = None  # Character position
    text_end: Optional[int] = None
    xpath: Optional[str] = None  # For HTML/XML
    
    # Metadata
    extraction_timestamp: datetime = None
    confidence_score: Optional[float] = None
    
    def __post_init__(self):
        """Set extraction timestamp if not provided."""
        if self.extraction_timestamp is None:
            object.__setattr__(self, 'extraction_timestamp', datetime.now())
    
    def to_string(self) -> str:
        """Convert to standardized string format: file.pdf|p.12|tab:1|row:Ricavi"""
        parts = [self.file_name]
        
        if self.page:
            parts.append(f"p.{self.page}")
        
        if self.sheet:
            parts.append(f"sheet:{self.sheet}")
            
        if self.cell:
            parts.append(f"cell:{self.cell}")
            
        if self.table_index:
            parts.append(f"tab:{self.table_index}")
            
        if self.row_label:
            parts.append(f"row:{self.row_label}")
            
        if self.column_label:
            parts.append(f"col:{self.column_label}")
            
        if self.xpath:
            parts.append(f"xpath:{self.xpath}")
            
        return "|".join(parts)
    
    @classmethod
    def from_string(cls, ref_string: str) -> 'SourceReference':
        """Parse from standardized string format."""
        parts = ref_string.split("|")
        if not parts:
            raise ValueError(f"Invalid source reference string: {ref_string}")
        
        file_name = parts[0]
        
        # Determine source type from file extension
        ext = file_name.split('.')[-1].lower()
        source_type = SourceType.PDF  # default
        for st in SourceType:
            if st.value == ext:
                source_type = st
                break
        
        kwargs = {
            'file_name': file_name,
            'file_hash': '',  # Will need to be set separately
            'source_type': source_type
        }
        
        # Parse location parts
        for part in parts[1:]:
            if part.startswith('p.'):
                kwargs['page'] = int(part[2:])
            elif part.startswith('sheet:'):
                kwargs['sheet'] = part[6:]
            elif part.startswith('cell:'):
                kwargs['cell'] = part[5:]
            elif part.startswith('tab:'):
                kwargs['table_index'] = int(part[4:])
            elif part.startswith('row:'):
                kwargs['row_label'] = part[4:]
            elif part.startswith('col:'):
                kwargs['column_label'] = part[4:]
            elif part.startswith('xpath:'):
                kwargs['xpath'] = part[6:]
        
        return cls(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'file_name': self.file_name,
            'file_hash': self.file_hash,
            'source_type': self.source_type.value,
            'page': self.page,
            'sheet': self.sheet,
            'cell': self.cell,
            'table_index': self.table_index,
            'row_label': self.row_label,
            'column_label': self.column_label,
            'text_start': self.text_start,
            'text_end': self.text_end,
            'xpath': self.xpath,
            'extraction_timestamp': self.extraction_timestamp.isoformat() if self.extraction_timestamp else None,
            'confidence_score': self.confidence_score,
            'reference_string': self.to_string()
        }


@dataclass(frozen=True)
class ProvenancedValue:
    """A value with its complete provenance chain."""
    
    # The actual value
    value: Union[float, int, str, bool]
    
    # Where it came from
    source_ref: SourceReference
    
    # What it represents
    metric_name: Optional[str] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    
    # Temporal context
    period: Optional[str] = None  # e.g., "FY2024", "Q2_2025"
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # Business context
    entity: Optional[str] = None  # Company/BU
    scenario: Optional[str] = None  # Actual/Budget/Forecast
    perimeter: Optional[str] = None  # Consolidated/Standalone
    
    # Quality indicators
    is_calculated: bool = False
    calculation_formula: Optional[str] = None
    input_sources: Optional[list] = None  # List of other ProvenancedValues used in calculation
    
    # Validation flags
    quality_flags: Optional[Dict[str, bool]] = None  # e.g., {'range_check': True, 'coherence_check': False}
    
    def __post_init__(self):
        """Initialize quality flags if not provided."""
        if self.quality_flags is None:
            object.__setattr__(self, 'quality_flags', {})
    
    def get_lineage(self) -> Dict[str, Any]:
        """Get complete lineage information."""
        lineage = {
            'primary_source': self.source_ref.to_string(),
            'is_calculated': self.is_calculated,
            'extraction_timestamp': self.source_ref.extraction_timestamp.isoformat(),
        }
        
        if self.is_calculated and self.input_sources:
            lineage['calculation_formula'] = self.calculation_formula
            lineage['input_sources'] = [
                source.source_ref.to_string() if hasattr(source, 'source_ref') else str(source)
                for source in self.input_sources
            ]
        
        return lineage
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API."""
        return {
            'value': self.value,
            'source_ref': self.source_ref.to_dict(),
            'metric_name': self.metric_name,
            'unit': self.unit,
            'currency': self.currency,
            'period': self.period,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'entity': self.entity,
            'scenario': self.scenario,
            'perimeter': self.perimeter,
            'is_calculated': self.is_calculated,
            'calculation_formula': self.calculation_formula,
            'quality_flags': self.quality_flags,
            'lineage': self.get_lineage()
        }


class SourceReferenceBuilder:
    """Builder for creating source references easily."""
    
    @staticmethod
    def for_pdf(file_name: str, file_hash: str, page: int, 
                table_index: Optional[int] = None, 
                row_label: Optional[str] = None) -> SourceReference:
        """Create reference for PDF source."""
        return SourceReference(
            file_name=file_name,
            file_hash=file_hash,
            source_type=SourceType.PDF,
            page=page,
            table_index=table_index,
            row_label=row_label
        )
    
    @staticmethod
    def for_excel(file_name: str, file_hash: str, sheet: str, 
                  cell: Optional[str] = None,
                  row_label: Optional[str] = None, 
                  column_label: Optional[str] = None) -> SourceReference:
        """Create reference for Excel source."""
        return SourceReference(
            file_name=file_name,
            file_hash=file_hash,
            source_type=SourceType.EXCEL,
            sheet=sheet,
            cell=cell,
            row_label=row_label,
            column_label=column_label
        )
    
    @staticmethod
    def for_csv(file_name: str, file_hash: str, 
                row_label: Optional[str] = None,
                column_label: Optional[str] = None) -> SourceReference:
        """Create reference for CSV source."""
        return SourceReference(
            file_name=file_name,
            file_hash=file_hash,
            source_type=SourceType.CSV,
            row_label=row_label,
            column_label=column_label
        )


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of file for provenance tracking."""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()[:16]  # First 16 chars for brevity
    except Exception:
        return f"hash_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"