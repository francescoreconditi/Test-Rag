# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Provenienza granulare avanzata pagina/cella
# ============================================

"""
Enhanced Granular Provenance Service for detailed source tracking.
Provides cell-level, page-level, and element-level provenance tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from ..value_objects.source_reference import SourceReference, SourceType

logger = logging.getLogger(__name__)

@dataclass
class CellLocation:
    """Precise cell location within a document."""
    sheet_name: Optional[str] = None
    row_index: Optional[int] = None
    column_index: Optional[int] = None
    cell_address: Optional[str] = None  # e.g., "B12", "D5"
    row_header: Optional[str] = None    # e.g., "Ricavi"
    column_header: Optional[str] = None # e.g., "2024"

@dataclass
class PageLocation:
    """Precise location within a PDF page."""
    page_number: int
    table_index: Optional[int] = None
    table_coordinates: Optional[tuple[float, float, float, float]] = None  # x1, y1, x2, y2
    text_coordinates: Optional[tuple[float, float, float, float]] = None
    line_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None

@dataclass
class ExtractionContext:
    """Context information about the extraction process."""
    extraction_method: str  # "camelot", "tabula", "pdfplumber", "pandas", "manual"
    extraction_engine: str  # Version/engine info
    extraction_parameters: dict[str, Any] = field(default_factory=dict)
    confidence_score: Optional[float] = None
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    preprocessing_applied: list[str] = field(default_factory=list)

class GranularProvenanceService:
    """
    Enterprise service for detailed source provenance tracking.
    Provides cell-level precision for Excel, page/table/row precision for PDFs.
    """

    def __init__(self):
        self.extraction_cache = {}
        self.coordinate_mappings = {}  # Maps logical positions to physical coordinates

    def create_excel_provenance(self, file_path: str, file_hash: str,
                              sheet_name: str, cell_location: CellLocation,
                              extraction_context: ExtractionContext) -> SourceReference:
        """
        Create detailed provenance for Excel cell extraction.

        Args:
            file_path: Path to Excel file
            file_hash: File hash for integrity
            sheet_name: Excel sheet name
            cell_location: Precise cell location
            extraction_context: Extraction method details

        Returns:
            Detailed source reference with cell-level precision
        """
        return SourceReference(
            file_path=file_path,
            file_name=Path(file_path).name,
            file_hash=file_hash,
            source_type=SourceType.EXCEL,
            sheet=sheet_name,
            cell=cell_location.cell_address,
            row_label=cell_location.row_header,
            column_label=cell_location.column_header,
            extraction_method=f"{extraction_context.extraction_method}_{extraction_context.extraction_engine}",
            extraction_timestamp=extraction_context.extraction_timestamp,
            confidence_score=extraction_context.confidence_score
        )

    def create_pdf_provenance(self, file_path: str, file_hash: str,
                            page_location: PageLocation,
                            extraction_context: ExtractionContext,
                            row_label: Optional[str] = None,
                            column_label: Optional[str] = None) -> SourceReference:
        """
        Create detailed provenance for PDF extraction.

        Args:
            file_path: Path to PDF file
            file_hash: File hash for integrity
            page_location: Precise page location
            extraction_context: Extraction method details
            row_label: Label of the table row (if applicable)
            column_label: Label of the table column (if applicable)

        Returns:
            Detailed source reference with page/table/coordinate precision
        """
        # Create enhanced extraction method description
        method_details = extraction_context.extraction_method
        if page_location.table_coordinates:
            coords = page_location.table_coordinates
            method_details += f"_coords({coords[0]:.1f},{coords[1]:.1f},{coords[2]:.1f},{coords[3]:.1f})"

        return SourceReference(
            file_path=file_path,
            file_name=Path(file_path).name,
            file_hash=file_hash,
            source_type=SourceType.PDF,
            page=page_location.page_number,
            table_index=page_location.table_index,
            row_label=row_label,
            column_label=column_label,
            text_start=page_location.char_start,
            text_end=page_location.char_end,
            extraction_method=method_details,
            extraction_timestamp=extraction_context.extraction_timestamp,
            confidence_score=extraction_context.confidence_score
        )

    def create_csv_provenance(self, file_path: str, file_hash: str,
                            row_index: int, column_index: int,
                            row_label: Optional[str] = None,
                            column_label: Optional[str] = None,
                            extraction_context: Optional[ExtractionContext] = None) -> SourceReference:
        """
        Create detailed provenance for CSV extraction.

        Args:
            file_path: Path to CSV file
            file_hash: File hash for integrity
            row_index: Zero-based row index
            column_index: Zero-based column index
            row_label: Label of the row (if applicable)
            column_label: Column header name
            extraction_context: Extraction method details

        Returns:
            Detailed source reference with row/column precision
        """
        if extraction_context is None:
            extraction_context = ExtractionContext(
                extraction_method="pandas",
                extraction_engine="pandas_csv_reader"
            )

        # Format cell address like Excel (A1, B2, etc.)
        cell_address = f"{self._column_index_to_letter(column_index)}{row_index + 1}"

        return SourceReference(
            file_path=file_path,
            file_name=Path(file_path).name,
            file_hash=file_hash,
            source_type=SourceType.CSV,
            cell=cell_address,
            row_label=row_label,
            column_label=column_label,
            extraction_method=f"{extraction_context.extraction_method}_{extraction_context.extraction_engine}",
            extraction_timestamp=extraction_context.extraction_timestamp,
            confidence_score=extraction_context.confidence_score
        )

    def create_provenance_from_dataframe(self, df: pd.DataFrame,
                                       file_path: str, file_hash: str,
                                       source_type: SourceType,
                                       sheet_name: Optional[str] = None,
                                       extraction_context: Optional[ExtractionContext] = None) -> dict[tuple[int, int], SourceReference]:
        """
        Create provenance mapping for entire DataFrame.
        Maps (row_index, column_index) -> SourceReference.

        Args:
            df: Source DataFrame
            file_path: Source file path
            file_hash: File hash
            source_type: Type of source document
            sheet_name: Sheet name for Excel files
            extraction_context: Extraction details

        Returns:
            Dictionary mapping cell positions to source references
        """
        if extraction_context is None:
            extraction_context = ExtractionContext(
                extraction_method="pandas",
                extraction_engine="pandas_reader"
            )

        provenance_map = {}

        for row_idx in range(len(df)):
            for col_idx, column_name in enumerate(df.columns):
                if source_type == SourceType.EXCEL:
                    cell_loc = CellLocation(
                        sheet_name=sheet_name,
                        row_index=row_idx,
                        column_index=col_idx,
                        cell_address=f"{self._column_index_to_letter(col_idx)}{row_idx + 2}",  # +2 for header
                        row_header=str(df.index[row_idx]) if hasattr(df.index[row_idx], '__str__') else None,
                        column_header=column_name
                    )

                    source_ref = self.create_excel_provenance(
                        file_path, file_hash, sheet_name or "Sheet1",
                        cell_loc, extraction_context
                    )

                elif source_type == SourceType.CSV:
                    source_ref = self.create_csv_provenance(
                        file_path, file_hash,
                        row_idx, col_idx,
                        row_label=str(df.index[row_idx]) if hasattr(df.index[row_idx], '__str__') else None,
                        column_label=column_name,
                        extraction_context=extraction_context
                    )
                else:
                    # Generic provenance for other types
                    source_ref = SourceReference(
                        file_path=file_path,
                        file_name=Path(file_path).name,
                        file_hash=file_hash,
                        source_type=source_type,
                        row_label=str(df.index[row_idx]) if hasattr(df.index[row_idx], '__str__') else None,
                        column_label=column_name,
                        extraction_method=extraction_context.extraction_method,
                        extraction_timestamp=extraction_context.extraction_timestamp
                    )

                provenance_map[(row_idx, col_idx)] = source_ref

        return provenance_map

    def create_provenance_from_pdf_table(self, table_data: list[list[Any]],
                                       file_path: str, file_hash: str,
                                       page_number: int, table_index: int,
                                       extraction_context: ExtractionContext,
                                       table_coordinates: Optional[tuple[float, float, float, float]] = None) -> dict[tuple[int, int], SourceReference]:
        """
        Create provenance mapping for PDF table data.

        Args:
            table_data: 2D list of table cell values
            file_path: PDF file path
            file_hash: File hash
            page_number: Page number (1-based)
            table_index: Table index on the page
            extraction_context: Extraction details
            table_coordinates: Table bounding box coordinates

        Returns:
            Dictionary mapping cell positions to source references
        """
        provenance_map = {}

        for row_idx, row in enumerate(table_data):
            for col_idx, cell_value in enumerate(row):
                # Create page location with table coordinates
                page_loc = PageLocation(
                    page_number=page_number,
                    table_index=table_index,
                    table_coordinates=table_coordinates,
                    line_number=row_idx
                )

                # Determine row/column labels if possible
                row_label = None
                column_label = None

                if row_idx == 0:  # Header row
                    column_label = str(cell_value) if cell_value else None
                elif col_idx == 0:  # First column (often labels)
                    row_label = str(cell_value) if cell_value else None

                source_ref = self.create_pdf_provenance(
                    file_path, file_hash, page_loc, extraction_context,
                    row_label=row_label, column_label=column_label
                )

                provenance_map[(row_idx, col_idx)] = source_ref

        return provenance_map

    def enhance_extraction_with_coordinates(self, extraction_result: Any,
                                          coordinate_data: dict[str, Any]) -> Any:
        """
        Enhance extraction result with precise coordinate information.

        Args:
            extraction_result: Original extraction result
            coordinate_data: Coordinate information from extraction tool

        Returns:
            Enhanced extraction result with coordinate provenance
        """
        # Store coordinate mappings for later use
        extraction_id = f"{datetime.now().isoformat()}_{hash(str(extraction_result))}"
        self.coordinate_mappings[extraction_id] = coordinate_data

        # Add coordinate metadata to extraction result
        if hasattr(extraction_result, '__dict__'):
            extraction_result.__dict__['_coordinate_data'] = coordinate_data
            extraction_result.__dict__['_coordinate_id'] = extraction_id

        return extraction_result

    def create_calculated_value_provenance(self, calculated_value: Any,
                                         calculation_formula: str,
                                         input_sources: list[SourceReference],
                                         metric_name: str) -> SourceReference:
        """
        Create provenance for calculated/derived values.

        Args:
            calculated_value: The calculated result
            calculation_formula: Formula used for calculation
            input_sources: List of source references for input values
            metric_name: Name of the calculated metric

        Returns:
            Source reference for the calculated value
        """
        # Create a synthetic source reference for calculated values
        timestamp = datetime.now()

        # Build detailed calculation provenance
        input_refs_str = "|".join([src.to_string() for src in input_sources])

        return SourceReference(
            file_path=f"calculated/{metric_name}",
            file_name=f"{metric_name}_calculated.virtual",
            file_hash=f"calc_{hash(calculation_formula)}",
            source_type=SourceType.JSON,  # Use JSON as virtual type
            extraction_method=f"calculation_engine|formula:{calculation_formula}|inputs:[{input_refs_str}]",
            extraction_timestamp=timestamp,
            confidence_score=self._calculate_derived_confidence(input_sources)
        )

    def _column_index_to_letter(self, col_idx: int) -> str:
        """Convert column index (0-based) to Excel letter format (A, B, ..., Z, AA, AB, ...)."""
        result = ""
        while col_idx >= 0:
            result = chr(col_idx % 26 + ord('A')) + result
            col_idx = col_idx // 26 - 1
            if col_idx < 0:
                break
        return result

    def _calculate_derived_confidence(self, input_sources: list[SourceReference]) -> float:
        """Calculate confidence score for derived/calculated values based on input confidence."""
        if not input_sources:
            return 0.0

        # Get confidence scores from inputs
        confidences = [src.confidence_score for src in input_sources if src.confidence_score is not None]

        if not confidences:
            return 0.7  # Default medium confidence for calculations

        # Use minimum confidence (weakest link principle) with slight bonus for multiple sources
        min_confidence = min(confidences)
        source_bonus = min(0.1, len(confidences) * 0.02)  # Small bonus for more sources

        return min(1.0, min_confidence + source_bonus)

    def get_provenance_summary(self, source_refs: list[SourceReference]) -> dict[str, Any]:
        """
        Generate summary statistics of provenance data.

        Args:
            source_refs: List of source references to summarize

        Returns:
            Dictionary with provenance statistics
        """
        if not source_refs:
            return {}

        summary = {
            'total_sources': len(source_refs),
            'source_types': {},
            'extraction_methods': {},
            'files': set(),
            'confidence_stats': {},
            'temporal_range': {},
            'coordinate_coverage': {
                'excel_cells': 0,
                'pdf_pages': set(),
                'pdf_tables': 0
            }
        }

        confidences = []
        timestamps = []

        for ref in source_refs:
            # Source type distribution
            if ref.source_type:
                type_name = ref.source_type.value
                summary['source_types'][type_name] = summary['source_types'].get(type_name, 0) + 1

            # Extraction method distribution
            if ref.extraction_method:
                method = ref.extraction_method.split('_')[0]  # First part of method name
                summary['extraction_methods'][method] = summary['extraction_methods'].get(method, 0) + 1

            # File tracking
            if ref.file_name:
                summary['files'].add(ref.file_name)

            # Confidence tracking
            if ref.confidence_score is not None:
                confidences.append(ref.confidence_score)

            # Timestamp tracking
            if ref.extraction_timestamp:
                timestamps.append(ref.extraction_timestamp)

            # Coordinate coverage
            if ref.cell:
                summary['coordinate_coverage']['excel_cells'] += 1
            if ref.page:
                summary['coordinate_coverage']['pdf_pages'].add(ref.page)
            if ref.table_index:
                summary['coordinate_coverage']['pdf_tables'] += 1

        # Confidence statistics
        if confidences:
            summary['confidence_stats'] = {
                'mean': np.mean(confidences),
                'min': min(confidences),
                'max': max(confidences),
                'std': np.std(confidences)
            }

        # Temporal range
        if timestamps:
            summary['temporal_range'] = {
                'earliest': min(timestamps).isoformat(),
                'latest': max(timestamps).isoformat(),
                'span_seconds': (max(timestamps) - min(timestamps)).total_seconds()
            }

        # Convert sets to counts for JSON serialization
        summary['files'] = list(summary['files'])
        summary['coordinate_coverage']['pdf_pages'] = len(summary['coordinate_coverage']['pdf_pages'])

        return summary

    def validate_provenance_chain(self, provenance_chain: list[SourceReference]) -> dict[str, Any]:
        """
        Validate completeness and consistency of provenance chain.

        Args:
            provenance_chain: Chain of source references to validate

        Returns:
            Validation report with issues and recommendations
        """
        validation_result = {
            'is_valid': True,
            'issues': [],
            'warnings': [],
            'recommendations': []
        }

        if not provenance_chain:
            validation_result['is_valid'] = False
            validation_result['issues'].append("Empty provenance chain")
            return validation_result

        # Check for missing critical information
        for i, ref in enumerate(provenance_chain):
            if not ref.file_name:
                validation_result['issues'].append(f"Reference {i}: Missing file_name")

            if not ref.file_hash:
                validation_result['warnings'].append(f"Reference {i}: Missing file_hash (integrity check unavailable)")

            if not ref.extraction_method:
                validation_result['warnings'].append(f"Reference {i}: Missing extraction_method")

            if ref.confidence_score is None:
                validation_result['warnings'].append(f"Reference {i}: Missing confidence_score")

            # Check location specificity
            location_fields = [ref.page, ref.sheet, ref.cell, ref.table_index, ref.row_label]
            if not any(location_fields):
                validation_result['warnings'].append(f"Reference {i}: Low location specificity")

        # Check chain consistency (timestamps, file versions, etc.)
        timestamps = [ref.extraction_timestamp for ref in provenance_chain if ref.extraction_timestamp]
        if len(timestamps) > 1:
            timestamp_range = max(timestamps) - min(timestamps)
            if timestamp_range.total_seconds() > 86400:  # > 1 day
                validation_result['warnings'].append("Provenance chain spans multiple days")

        # Generate recommendations
        if validation_result['warnings']:
            validation_result['recommendations'].append("Consider enhancing provenance with missing metadata")

        if validation_result['issues']:
            validation_result['is_valid'] = False
            validation_result['recommendations'].append("Fix critical provenance issues before proceeding")

        return validation_result
