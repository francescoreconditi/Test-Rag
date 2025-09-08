# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Orchestratore Enterprise Avanzato con nuove funzionalità
# ============================================

"""
Advanced Enterprise Orchestrator integrating:
- Great Expectations for data quality
- Automatic calculations with lineage
- Granular provenance tracking
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio
import pandas as pd

from .enterprise_orchestrator import EnterpriseOrchestrator
from ...domain.services.data_quality_service import DataQualityService, ValidationResult, QualityMetrics
from ...domain.services.calculation_engine import CalculationEngine, CalculatedMetric
from ...domain.services.granular_provenance_service import (
    GranularProvenanceService, 
    ExtractionContext,
    CellLocation,
    PageLocation
)
from ...domain.value_objects.source_reference import SourceReference, ProvenancedValue

logger = logging.getLogger(__name__)

class AdvancedEnterpriseOrchestrator:
    """
    Advanced Enterprise Orchestrator with enhanced capabilities:
    - Comprehensive data quality validation
    - Automatic financial calculations with lineage
    - Granular provenance tracking
    """
    
    def __init__(self):
        # Initialize base orchestrator
        self.base_orchestrator = EnterpriseOrchestrator()
        
        # Initialize new services
        self.data_quality_service = DataQualityService()
        self.calculation_engine = CalculationEngine()
        self.provenance_service = GranularProvenanceService()
        
        # Performance tracking
        self.performance_metrics = {}
        
        logger.info("Advanced Enterprise Orchestrator initialized with enhanced capabilities")

    async def process_document_advanced(self, file_path: str, 
                                      enable_calculations: bool = True,
                                      enable_quality_validation: bool = True,
                                      granular_provenance: bool = True) -> Dict[str, Any]:
        """
        Advanced document processing with all enterprise features.
        
        Args:
            file_path: Path to document to process
            enable_calculations: Whether to compute derived metrics
            enable_quality_validation: Whether to run data quality checks
            granular_provenance: Whether to use enhanced provenance tracking
            
        Returns:
            Comprehensive processing result with quality metrics and calculations
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Base document processing
            logger.info("Starting advanced document processing")
            base_result = await self.base_orchestrator.process_document(file_path)
            
            if not base_result['success']:
                return self._create_error_result("Base processing failed", base_result)
            
            # Step 2: Enhance with granular provenance
            if granular_provenance:
                enhanced_data = await self._enhance_provenance(base_result, file_path)
            else:
                enhanced_data = base_result
            
            # Step 3: Run data quality validation
            quality_results = {}
            if enable_quality_validation:
                quality_results = await self._validate_data_quality(enhanced_data)
            
            # Step 4: Calculate derived metrics
            calculated_metrics = []
            if enable_calculations:
                calculated_metrics = await self._calculate_derived_metrics(enhanced_data)
            
            # Step 5: Final quality assessment with calculated metrics
            final_quality = {}
            if enable_quality_validation and calculated_metrics:
                final_quality = await self._validate_calculated_metrics(calculated_metrics)
            
            # Step 6: Compile comprehensive result
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'processing_time_seconds': processing_time,
                'base_processing': base_result,
                'data_quality': quality_results,
                'calculated_metrics': [calc.to_dict() for calc in calculated_metrics],
                'final_quality_assessment': final_quality,
                'provenance_summary': self._create_provenance_summary(enhanced_data),
                'enterprise_statistics': {
                    'extracted_metrics': len(enhanced_data.get('extracted_metrics', [])),
                    'calculated_metrics': len(calculated_metrics),
                    'quality_checks_performed': len(quality_results),
                    'overall_confidence': self._calculate_overall_confidence(enhanced_data, calculated_metrics, quality_results)
                }
            }
            
            # Update performance metrics
            self._update_performance_metrics(processing_time, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Advanced processing failed: {e}")
            return self._create_error_result(f"Advanced processing error: {str(e)}")

    async def _enhance_provenance(self, base_result: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Enhance base result with granular provenance information."""
        try:
            enhanced_result = base_result.copy()
            
            # Get file hash for integrity tracking
            from ...domain.value_objects.source_reference import calculate_file_hash
            file_hash = calculate_file_hash(file_path)
            
            # Process extracted metrics with enhanced provenance
            if 'extracted_metrics' in base_result:
                enhanced_metrics = []
                
                for metric in base_result['extracted_metrics']:
                    # Create enhanced extraction context
                    extraction_context = ExtractionContext(
                        extraction_method=metric.get('extraction_method', 'unknown'),
                        extraction_engine='enterprise_orchestrator',
                        extraction_parameters={'file_path': file_path},
                        confidence_score=metric.get('confidence', 0.8),
                        extraction_timestamp=datetime.now()
                    )
                    
                    # Create granular source reference
                    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                        # Excel file - create cell-level provenance
                        cell_location = CellLocation(
                            sheet_name=metric.get('sheet', 'Sheet1'),
                            cell_address=metric.get('cell', 'A1'),
                            row_header=metric.get('row_label'),
                            column_header=metric.get('column_label')
                        )
                        
                        enhanced_source_ref = self.provenance_service.create_excel_provenance(
                            file_path, file_hash, cell_location.sheet_name or 'Sheet1',
                            cell_location, extraction_context
                        )
                        
                    elif file_path.endswith('.pdf'):
                        # PDF file - create page/table-level provenance
                        page_location = PageLocation(
                            page_number=metric.get('page', 1),
                            table_index=metric.get('table_index'),
                            line_number=metric.get('line_number')
                        )
                        
                        enhanced_source_ref = self.provenance_service.create_pdf_provenance(
                            file_path, file_hash, page_location, extraction_context,
                            row_label=metric.get('row_label'),
                            column_label=metric.get('column_label')
                        )
                    else:
                        # Generic provenance for other file types
                        enhanced_source_ref = SourceReference(
                            file_path=file_path,
                            file_hash=file_hash,
                            extraction_method=extraction_context.extraction_method,
                            extraction_timestamp=extraction_context.extraction_timestamp,
                            confidence_score=extraction_context.confidence_score
                        )
                    
                    # Create provenance value
                    provenance_value = ProvenancedValue(
                        value=metric.get('value'),
                        source_ref=enhanced_source_ref,
                        metric_name=metric.get('metric_name'),
                        unit=metric.get('unit'),
                        currency=metric.get('currency'),
                        period=metric.get('period'),
                        entity=metric.get('entity'),
                        scenario=metric.get('scenario', 'actual'),
                        quality_flags=metric.get('quality_flags', {})
                    )
                    
                    enhanced_metric = metric.copy()
                    enhanced_metric['provenance'] = provenance_value.to_dict()
                    enhanced_metric['enhanced_source_ref'] = enhanced_source_ref.to_string()
                    
                    enhanced_metrics.append(enhanced_metric)
                
                enhanced_result['extracted_metrics'] = enhanced_metrics
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Provenance enhancement failed: {e}")
            return base_result

    async def _validate_data_quality(self, enhanced_data: Dict[str, Any]) -> Dict[str, ValidationResult]:
        """Run comprehensive data quality validation."""
        try:
            validation_results = {}
            
            # Convert extracted metrics to DataFrame for validation
            metrics = enhanced_data.get('extracted_metrics', [])
            if not metrics:
                return validation_results
            
            # Create DataFrame from metrics
            df_data = []
            for metric in metrics:
                row = {
                    'metric_name': metric.get('metric_name'),
                    'value': metric.get('value'),
                    'unit': metric.get('unit'),
                    'currency': metric.get('currency'),
                    'period': metric.get('period')
                }
                
                # Add metric-specific columns for validation
                metric_name = metric.get('metric_name', '').lower()
                if metric_name:
                    row[metric_name] = metric.get('value')
                
                df_data.append(row)
            
            if not df_data:
                return validation_results
            
            df = pd.DataFrame(df_data)
            
            # Run balance sheet validation if applicable
            balance_columns = ['attivo_totale', 'passivo_totale', 'debito_lordo', 'cassa', 'pfn']
            if any(col in df.columns for col in balance_columns):
                validation_results['balance_sheet'] = self.data_quality_service.validate_balance_sheet_coherence(df)
            
            # Run income statement validation if applicable
            income_columns = ['ricavi', 'ebitda', 'margine_lordo']
            if any(col in df.columns for col in income_columns):
                validation_results['income_statement'] = self.data_quality_service.validate_income_statement(df)
            
            # Run range validation
            validation_results['ranges'] = self.data_quality_service.validate_metric_ranges(df)
            
            # Calculate overall quality metrics
            quality_metrics = self.data_quality_service.calculate_quality_metrics(df)
            validation_results['quality_metrics'] = quality_metrics.__dict__
            
            logger.info(f"Data quality validation completed with {len(validation_results)} checks")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Data quality validation failed: {e}")
            return {}

    async def _calculate_derived_metrics(self, enhanced_data: Dict[str, Any]) -> List[CalculatedMetric]:
        """Calculate derived financial metrics with lineage tracking."""
        try:
            # Extract available data for calculations
            available_data = {}
            source_refs = {}
            
            metrics = enhanced_data.get('extracted_metrics', [])
            for metric in metrics:
                metric_name = metric.get('metric_name')
                value = metric.get('value')
                
                if metric_name and value is not None:
                    available_data[metric_name] = value
                    source_refs[metric_name] = metric.get('enhanced_source_ref', metric.get('source_ref', 'unknown'))
            
            # Calculate all possible metrics
            calculated_metrics = self.calculation_engine.calculate_all_possible(available_data, source_refs)
            
            logger.info(f"Calculated {len(calculated_metrics)} derived metrics")
            
            # Log calculated metrics for debugging
            for calc in calculated_metrics:
                logger.debug(f"Calculated {calc.metric_name} = {calc.value} ({calc.unit})")
            
            return calculated_metrics
            
        except Exception as e:
            logger.error(f"Metric calculation failed: {e}")
            return []

    async def _validate_calculated_metrics(self, calculated_metrics: List[CalculatedMetric]) -> Dict[str, Any]:
        """Validate calculated metrics for consistency and reasonableness."""
        try:
            # Convert calculated metrics to DataFrame
            df_data = []
            for calc in calculated_metrics:
                df_data.append({
                    'metric_name': calc.metric_name,
                    calc.metric_name: calc.value,
                    'unit': calc.unit,
                    'confidence': calc.lineage.confidence_score
                })
            
            if not df_data:
                return {}
            
            df = pd.DataFrame(df_data)
            
            # Run validation on calculated metrics
            validation_result = self.data_quality_service.validate_metric_ranges(df)
            
            # Additional validation for calculated metrics
            reasonableness_checks = {
                'extreme_values': [],
                'suspicious_ratios': [],
                'confidence_warnings': []
            }
            
            for calc in calculated_metrics:
                # Check for extreme values
                if abs(calc.value) > 1e10:
                    reasonableness_checks['extreme_values'].append(f"{calc.metric_name}: {calc.value}")
                
                # Check for suspicious ratios (e.g., negative margins where positive expected)
                if calc.metric_name.endswith('_percent') and calc.value < -100:
                    reasonableness_checks['suspicious_ratios'].append(f"{calc.metric_name}: {calc.value}%")
                
                # Check for low confidence calculations
                if calc.lineage.confidence_score < 0.5:
                    reasonableness_checks['confidence_warnings'].append(f"{calc.metric_name}: confidence {calc.lineage.confidence_score:.2f}")
            
            return {
                'validation_result': validation_result.__dict__,
                'reasonableness_checks': reasonableness_checks,
                'total_calculated': len(calculated_metrics),
                'high_confidence': len([c for c in calculated_metrics if c.lineage.confidence_score > 0.8]),
                'medium_confidence': len([c for c in calculated_metrics if 0.5 <= c.lineage.confidence_score <= 0.8]),
                'low_confidence': len([c for c in calculated_metrics if c.lineage.confidence_score < 0.5])
            }
            
        except Exception as e:
            logger.error(f"Calculated metrics validation failed: {e}")
            return {}

    def _create_provenance_summary(self, enhanced_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of provenance information."""
        try:
            metrics = enhanced_data.get('extracted_metrics', [])
            source_refs = []
            
            for metric in metrics:
                if 'provenance' in metric:
                    # Reconstruct source reference from provenance data
                    prov_data = metric['provenance']
                    source_ref_data = prov_data.get('source_ref', {})
                    
                    if source_ref_data:
                        source_ref = SourceReference(
                            file_path=source_ref_data.get('file_path', ''),
                            file_name=source_ref_data.get('file_name', ''),
                            file_hash=source_ref_data.get('file_hash', ''),
                            page=source_ref_data.get('page'),
                            sheet=source_ref_data.get('sheet'),
                            cell=source_ref_data.get('cell'),
                            extraction_method=source_ref_data.get('extraction_method'),
                            confidence_score=source_ref_data.get('confidence_score')
                        )
                        source_refs.append(source_ref)
            
            if source_refs:
                return self.provenance_service.get_provenance_summary(source_refs)
            else:
                return {'message': 'No detailed provenance data available'}
                
        except Exception as e:
            logger.error(f"Provenance summary creation failed: {e}")
            return {'error': str(e)}

    def _calculate_overall_confidence(self, enhanced_data: Dict[str, Any], 
                                    calculated_metrics: List[CalculatedMetric],
                                    quality_results: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the processing result."""
        try:
            confidence_scores = []
            
            # Confidence from extracted metrics
            metrics = enhanced_data.get('extracted_metrics', [])
            for metric in metrics:
                if 'provenance' in metric:
                    prov_data = metric['provenance']
                    source_ref = prov_data.get('source_ref', {})
                    conf = source_ref.get('confidence_score')
                    if conf is not None:
                        confidence_scores.append(conf)
            
            # Confidence from calculated metrics
            for calc in calculated_metrics:
                confidence_scores.append(calc.lineage.confidence_score)
            
            # Quality validation impact
            quality_penalty = 0.0
            for validation_name, validation_result in quality_results.items():
                if validation_name == 'quality_metrics':
                    continue
                    
                if hasattr(validation_result, 'failed_count'):
                    if validation_result.failed_count > 0:
                        quality_penalty += 0.1 * validation_result.failed_count
            
            # Calculate weighted average
            if confidence_scores:
                base_confidence = sum(confidence_scores) / len(confidence_scores)
                overall_confidence = max(0.0, base_confidence - quality_penalty)
                return min(1.0, overall_confidence)
            else:
                return 0.5  # Default medium confidence
                
        except Exception as e:
            logger.error(f"Overall confidence calculation failed: {e}")
            return 0.5

    def _update_performance_metrics(self, processing_time: float, result: Dict[str, Any]):
        """Update performance tracking metrics."""
        timestamp = datetime.now().isoformat()
        
        self.performance_metrics[timestamp] = {
            'processing_time': processing_time,
            'success': result.get('success', False),
            'extracted_metrics': result.get('enterprise_statistics', {}).get('extracted_metrics', 0),
            'calculated_metrics': result.get('enterprise_statistics', {}).get('calculated_metrics', 0),
            'quality_checks': result.get('enterprise_statistics', {}).get('quality_checks_performed', 0),
            'overall_confidence': result.get('enterprise_statistics', {}).get('overall_confidence', 0.0)
        }
        
        # Keep only last 100 entries
        if len(self.performance_metrics) > 100:
            oldest_key = min(self.performance_metrics.keys())
            del self.performance_metrics[oldest_key]

    def _create_error_result(self, error_message: str, base_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create standardized error result."""
        return {
            'success': False,
            'error': error_message,
            'base_processing': base_result,
            'data_quality': {},
            'calculated_metrics': [],
            'final_quality_assessment': {},
            'provenance_summary': {},
            'enterprise_statistics': {
                'extracted_metrics': 0,
                'calculated_metrics': 0,
                'quality_checks_performed': 0,
                'overall_confidence': 0.0
            }
        }

    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring."""
        if not self.performance_metrics:
            return {'message': 'No performance data available'}
        
        recent_metrics = list(self.performance_metrics.values())[-10:]  # Last 10 runs
        
        processing_times = [m['processing_time'] for m in recent_metrics]
        confidences = [m['overall_confidence'] for m in recent_metrics]
        
        return {
            'total_runs': len(self.performance_metrics),
            'recent_runs': len(recent_metrics),
            'average_processing_time': sum(processing_times) / len(processing_times) if processing_times else 0,
            'average_confidence': sum(confidences) / len(confidences) if confidences else 0,
            'success_rate': sum(1 for m in recent_metrics if m['success']) / len(recent_metrics) if recent_metrics else 0
        }

# Backward compatibility with existing code
def to_dict(calculated_metric: CalculatedMetric) -> Dict[str, Any]:
    """Convert CalculatedMetric to dictionary for JSON serialization."""
    return {
        'metric_name': calculated_metric.metric_name,
        'value': calculated_metric.value,
        'unit': calculated_metric.unit,
        'source_ref': calculated_metric.source_ref,
        'lineage': {
            'formula': calculated_metric.lineage.formula,
            'inputs': [
                {
                    'metric_name': inp.metric_name,
                    'value': inp.value,
                    'source_ref': inp.source_ref,
                    'quality_score': inp.quality_score
                }
                for inp in calculated_metric.lineage.inputs
            ],
            'calculation_method': calculated_metric.lineage.calculation_method,
            'timestamp': calculated_metric.lineage.timestamp.isoformat(),
            'status': calculated_metric.lineage.status.value,
            'confidence_score': calculated_metric.lineage.confidence_score,
            'notes': calculated_metric.lineage.notes
        }
    }

# Add to_dict method to CalculatedMetric class
CalculatedMetric.to_dict = lambda self: to_dict(self)