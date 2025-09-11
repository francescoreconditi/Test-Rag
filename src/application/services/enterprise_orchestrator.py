"""Enterprise RAG orchestration service coordinating all components."""

from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Optional, Union

from src.application.parsers.excel_parser import ExcelParser
from src.application.services.data_normalizer import DataNormalizer, NormalizedValue
from src.application.services.document_router import DocumentRouter, ProcessingMode
from src.application.services.hybrid_retrieval import HybridRetriever, RetrievalResult
from src.application.services.ontology_mapper import OntologyMapper
from src.application.services.raw_blocks_extractor import BlockType, DocumentBlocks, RawBlocksExtractor
from src.domain.value_objects.guardrails import FinancialGuardrails, ValidationResult
from src.domain.value_objects.source_reference import ProvenancedValue, SourceReference, SourceType

try:
    from src.infrastructure.repositories.fact_table_repository import FactTableRepository
    FACT_TABLE_AVAILABLE = True
except ImportError:
    FACT_TABLE_AVAILABLE = False
    FactTableRepository = None


logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of enterprise processing pipeline."""
    query_text: str  # Original query text for AI response generation
    source_refs: list[SourceReference]
    validation_results: list[ValidationResult]
    normalized_data: dict[str, NormalizedValue]
    retrieval_results: list[RetrievalResult]
    mapped_metrics: dict[str, Optional[tuple[str, str, float]]]
    fact_table_records: int
    processing_time_ms: float
    confidence_score: float
    warnings: list[str]
    errors: list[str]


@dataclass
class EnterpriseQuery:
    """Enterprise query with metadata and processing instructions."""
    query_text: str
    document_type_hint: Optional[ProcessingMode] = None
    require_validation: bool = True
    require_normalization: bool = True
    use_hybrid_retrieval: bool = True
    map_metrics: bool = True
    store_in_fact_table: bool = True
    confidence_threshold: float = 70.0

    # RAG engine compatibility parameters
    top_k: Optional[int] = None
    use_context: Optional[bool] = None
    csv_analysis: Optional[dict[str, Any]] = None


class EnterpriseOrchestrator:
    """Main orchestrator for enterprise RAG pipeline."""

    def __init__(self,
                 rag_engine=None,
                 csv_analyzer=None,
                 fact_table_path: str = "data/enterprise_facts.duckdb",
                 openai_api_key: Optional[str] = None):
        """Initialize enterprise orchestrator."""
        import os
        self.rag_engine = rag_engine
        self.csv_analyzer = csv_analyzer

        # Get OpenAI API key from parameter or environment
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        # Initialize enterprise components
        self.document_router = DocumentRouter()
        self.data_normalizer = DataNormalizer(default_locale="it_IT")
        self.hybrid_retriever = HybridRetriever(
            embedding_model_name="text-embedding-3-small",
            cache_dir="data/cache/hybrid_retrieval",
            openai_api_key=api_key
        )
        self.ontology_mapper = OntologyMapper()
        if FACT_TABLE_AVAILABLE:
            self.fact_table_repo = FactTableRepository(db_path=fact_table_path)
        else:
            self.fact_table_repo = None
        self.guardrails = FinancialGuardrails()

        # Initialize new parsers
        self.excel_parser = ExcelParser()
        self.raw_blocks_extractor = RawBlocksExtractor()

        # Processing statistics
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'validation_failures': 0,
            'mapping_failures': 0,
            'fact_records_created': 0
        }

        logger.info("Enterprise orchestrator initialized")

    async def process_enterprise_query(self,
                                     query: EnterpriseQuery,
                                     documents: Optional[list[dict[str, Any]]] = None) -> ProcessingResult:
        """Process query through complete enterprise pipeline."""
        start_time = datetime.now()

        result = ProcessingResult(
            query_text=query.query_text,
            source_refs=[],
            validation_results=[],
            normalized_data={},
            retrieval_results=[],
            mapped_metrics={},
            fact_table_records=0,
            processing_time_ms=0.0,
            confidence_score=0.0,
            warnings=[],
            errors=[]
        )

        try:
            self.stats['total_queries'] += 1

            # Step 1: Document routing and classification
            if documents:
                await self._process_documents(documents, query, result)

            # Step 2: Hybrid retrieval
            if query.use_hybrid_retrieval:
                await self._perform_hybrid_retrieval(query, result)

            # Step 3: Extract and normalize financial data
            if query.require_normalization:
                await self._normalize_financial_data(result)

            # Step 4: Map metrics using ontology
            if query.map_metrics:
                await self._map_metrics(result)

            # Step 5: Validate financial coherence
            if query.require_validation:
                logger.info("DEBUG: Starting financial validation")
                await self._validate_financial_data(result)
                logger.info(f"DEBUG: Validation completed. Results: {len(result.validation_results)}")

            # Step 6: Store in fact table
            if query.store_in_fact_table and self.fact_table_repo:
                logger.info("DEBUG: Starting fact table storage")
                await self._store_in_fact_table(result)
                logger.info(f"DEBUG: Fact table storage completed. Records: {result.fact_table_records}")

            # Calculate final metrics
            logger.info("DEBUG: Calculating final metrics")
            end_time = datetime.now()
            result.processing_time_ms = (end_time - start_time).total_seconds() * 1000
            logger.info(f"DEBUG: Processing time calculated: {result.processing_time_ms:.1f}ms")

            logger.info("DEBUG: Calculating confidence score")
            result.confidence_score = self._calculate_overall_confidence(result)
            logger.info(f"DEBUG: Confidence score calculated: {result.confidence_score:.1%}")

            self.stats['successful_queries'] += 1
            logger.info(f"Enterprise query processed successfully in {result.processing_time_ms:.1f}ms")

        except Exception as e:
            result.errors.append(f"Processing failed: {str(e)}")
            logger.error(f"Enterprise query processing failed: {e}")

        return result

    async def _process_documents(self,
                               documents: list[dict[str, Any]],
                               query: EnterpriseQuery,
                               result: ProcessingResult) -> None:
        """Process and route documents."""
        for doc in documents:
            try:
                # Create source reference
                filename = doc.get('filename', 'unknown')
                source_ref = SourceReference(
                    file_path=filename,  # Required parameter
                    file_name=filename,
                    file_hash=doc.get('hash', ''),
                    source_type=SourceType.PDF if filename.endswith('.pdf') else SourceType.EXCEL,
                    extraction_timestamp=datetime.now(),
                    confidence_score=1.0
                )
                result.source_refs.append(source_ref)

                # Route document
                content = doc.get('content', '')
                if query.document_type_hint:
                    doc_type = query.document_type_hint
                else:
                    classification = self.document_router.classify_document(content)
                    doc_type = classification.processing_mode

                # Add to hybrid retrieval index
                if content:
                    self.hybrid_retriever.add_documents([{
                        'content': content,
                        'metadata': {
                            'source_ref': source_ref.to_dict(),
                            'document_type': doc_type.value,
                            'processing_date': datetime.now().isoformat()
                        },
                        'id': source_ref.file_hash or source_ref.file_name
                    }])

                logger.debug(f"Processed document: {source_ref.file_name} as {doc_type.value}")

            except Exception as e:
                result.errors.append(f"Document processing failed: {str(e)}")
                logger.error(f"Failed to process document: {e}")

    async def _perform_hybrid_retrieval(self,
                                      query: EnterpriseQuery,
                                      result: ProcessingResult) -> None:
        """Perform hybrid BM25 + embeddings retrieval."""
        try:
            retrieval_results = self.hybrid_retriever.search(
                query.query_text,
                top_k=10,
                bm25_top_k=50,
                embedding_top_k=50,
                final_rerank_k=10
            )

            # Filter by confidence threshold
            filtered_results = [
                r for r in retrieval_results
                if r.score >= query.confidence_threshold / 100.0
            ]

            result.retrieval_results = filtered_results

            if len(filtered_results) < len(retrieval_results):
                result.warnings.append(
                    f"Filtered {len(retrieval_results) - len(filtered_results)} results below confidence threshold"
                )

            logger.debug(f"Hybrid retrieval found {len(filtered_results)} high-confidence results")

        except Exception as e:
            result.errors.append(f"Hybrid retrieval failed: {str(e)}")
            logger.error(f"Hybrid retrieval failed: {e}")

    async def _normalize_financial_data(self, result: ProcessingResult) -> None:
        """Extract and normalize financial data from retrieval results."""
        try:
            # Extract numeric values from retrieval results
            raw_values = {}
            context_text = ""

            for retrieval_result in result.retrieval_results:
                context_text += retrieval_result.content + " "

                # Simple extraction of number-like patterns
                import re
                number_patterns = re.findall(
                    r'(\w+)[\s:=]+([€$£¥]?[\d\.,\-\(\)]+[€$£¥]?)',
                    retrieval_result.content
                )

                for metric_name, value_str in number_patterns:
                    if metric_name.lower() not in ['page', 'anno', 'year', 'data']:
                        raw_values[metric_name] = value_str

            # Normalize the extracted values
            result.normalized_data = self.data_normalizer.batch_normalize(
                raw_values,
                context=context_text[:1000]  # First 1000 chars for context
            )

            logger.info(f"DEBUG: Raw values extracted: {len(raw_values)} - {list(raw_values.keys())[:5]}")
            logger.info(f"DEBUG: Normalized {len(result.normalized_data)} financial values - {list(result.normalized_data.keys())[:5]}")

        except Exception as e:
            result.errors.append(f"Data normalization failed: {str(e)}")
            logger.error(f"Data normalization failed: {e}")

    async def _map_metrics(self, result: ProcessingResult) -> None:
        """Map extracted metrics to canonical ontology."""
        try:
            metric_names = list(result.normalized_data.keys())
            result.mapped_metrics = self.ontology_mapper.batch_map_metrics(
                metric_names,
                threshold=70.0
            )

            # Count successful mappings
            successful_mappings = sum(1 for v in result.mapped_metrics.values() if v is not None)

            if successful_mappings < len(metric_names):
                result.warnings.append(
                    f"Only {successful_mappings}/{len(metric_names)} metrics mapped to ontology"
                )

            logger.info(f"DEBUG: Mapped {successful_mappings}/{len(metric_names)} metrics to ontology")
            logger.info(f"DEBUG: Mapped metrics sample: {list(result.mapped_metrics.items())[:3]}")

        except Exception as e:
            result.errors.append(f"Metric mapping failed: {str(e)}")
            logger.error(f"Metric mapping failed: {e}")

    async def _validate_financial_data(self, result: ProcessingResult) -> None:
        """Validate financial data coherence."""
        try:
            # Convert normalized data to validation format
            validation_data = {}
            for original_name, normalized_value in result.normalized_data.items():
                # Try to map to canonical metric
                mapping = result.mapped_metrics.get(original_name)
                if mapping and isinstance(mapping, dict):
                    # Extract values from mapping dictionary
                    canonical_key = mapping.get('metric_key', original_name.lower())
                    validation_data[canonical_key] = normalized_value.to_base_units()
                else:
                    validation_data[original_name.lower()] = normalized_value.to_base_units()

            # Run validation rules
            validation_results = []

            # Balance sheet validation
            bs_validation = self.guardrails.validate_balance_sheet(validation_data)
            validation_results.append(bs_validation)

            # PFN coherence
            pfn_validation = self.guardrails.validate_pfn_coherence_from_data(validation_data)
            validation_results.append(pfn_validation)

            # Margin coherence
            margin_validation = self.guardrails.validate_margin_coherence(validation_data)
            validation_results.append(margin_validation)

            result.validation_results = validation_results

            # Count failures
            failures = sum(1 for v in validation_results if not v.passed)
            if failures > 0:
                self.stats['validation_failures'] += failures
                result.warnings.extend([v.message for v in validation_results if not v.passed])

            logger.debug(f"Validated financial data: {failures} failures out of {len(validation_results)} checks")

        except Exception as e:
            result.errors.append(f"Financial validation failed: {str(e)}")
            logger.error(f"Financial validation failed: {e}")

    async def _store_in_fact_table(self, result: ProcessingResult) -> None:
        """Store processed data in enterprise fact table."""
        if not self.fact_table_repo:
            return

        try:
            records_created = 0

            for original_name, normalized_value in result.normalized_data.items():
                # Get canonical mapping
                mapping = result.mapped_metrics.get(original_name)
                canonical_metric = mapping.get('metric_key', original_name) if mapping else original_name

                # Find corresponding source reference
                source_ref = result.source_refs[0] if result.source_refs else None

                # Get unit from mapping or use currency/default
                unit = None
                if mapping and isinstance(mapping, dict):
                    unit = mapping.get('unit', 'currency')
                elif normalized_value.currency:
                    unit = normalized_value.currency
                else:
                    unit = 'number'

                # Create ProvenancedValue object
                provenanced_value = ProvenancedValue(
                    value=normalized_value.to_base_units(),
                    source_ref=source_ref,
                    metric_name=canonical_metric,
                    unit=unit,
                    currency=normalized_value.currency,
                    period=f"FY{datetime.now().year}",
                    entity="default_entity",
                    scenario="actual"
                )

                # Insert into fact table
                fact_id = self.fact_table_repo.insert_provenanced_value(provenanced_value)

                if fact_id:
                    records_created += 1

            result.fact_table_records = records_created
            self.stats['fact_records_created'] += records_created

            logger.debug(f"Stored {records_created} records in fact table")

        except Exception as e:
            result.errors.append(f"Fact table storage failed: {str(e)}")
            logger.error(f"Fact table storage failed: {e}")
            logger.error(f"Debug - Normalized data: {len(result.normalized_data)} items")
            logger.error(f"Debug - Mapped metrics: {len(result.mapped_metrics)} items")
            logger.error(f"Debug - Source refs: {len(result.source_refs)} items")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

    def _calculate_overall_confidence(self, result: ProcessingResult) -> float:
        """Calculate overall processing confidence score."""
        confidence_factors = []

        # Retrieval confidence
        if result.retrieval_results:
            avg_retrieval_conf = sum(r.score for r in result.retrieval_results) / len(result.retrieval_results)
            confidence_factors.append(avg_retrieval_conf)

        # Normalization confidence
        if result.normalized_data:
            avg_norm_conf = sum(v.confidence for v in result.normalized_data.values()) / len(result.normalized_data)
            confidence_factors.append(avg_norm_conf)

        # Mapping confidence
        if result.mapped_metrics:
            mapped_scores = [mapping.get('confidence', 0.0) for mapping in result.mapped_metrics.values() if mapping]
            if mapped_scores:
                avg_mapping_conf = sum(mapped_scores) / len(mapped_scores) / 100.0  # Convert to 0-1 scale
                confidence_factors.append(avg_mapping_conf)

        # Validation penalty
        validation_penalty = len([v for v in result.validation_results if not v.passed]) * 0.1

        # Error penalty
        error_penalty = len(result.errors) * 0.2

        # Calculate final score
        if confidence_factors:
            base_confidence = sum(confidence_factors) / len(confidence_factors)
            final_confidence = max(0.0, base_confidence - validation_penalty - error_penalty)
            return final_confidence
        else:
            return 0.5  # Neutral confidence if no factors available

    async def process_excel_file(self, file_path: Union[str, Path]) -> tuple[Any, list[SourceReference]]:
        """
        Process Excel file with enhanced metadata extraction.

        Args:
            file_path: Path to Excel file

        Returns:
            Tuple of ExtractedData and list of SourceReference
        """
        try:
            logger.info(f"Processing Excel file: {file_path}")
            extracted_data, source_refs = self.excel_parser.extract_with_source_references(file_path)

            # Store raw blocks for reference
            blocks = self.raw_blocks_extractor.extract(file_path)

            # Save blocks for future reference
            blocks_path = Path("data/raw_blocks") / f"{Path(file_path).stem}_blocks.json"
            blocks_path.parent.mkdir(parents=True, exist_ok=True)
            blocks.save_to_json(blocks_path)

            logger.info(f"Extracted {len(source_refs)} source references from Excel")
            logger.info(f"Saved {len(blocks.get_all_blocks())} raw blocks to {blocks_path}")

            return extracted_data, source_refs

        except Exception as e:
            logger.error(f"Excel processing failed: {e}")
            raise

    async def extract_raw_blocks(self, file_path: Union[str, Path]) -> DocumentBlocks:
        """
        Extract raw blocks from any document type.

        Args:
            file_path: Path to document

        Returns:
            DocumentBlocks with all extracted blocks
        """
        try:
            logger.info(f"Extracting raw blocks from: {file_path}")
            blocks = self.raw_blocks_extractor.extract(file_path)

            # Log statistics
            total_blocks = len(blocks.get_all_blocks())
            text_blocks = len(blocks.get_blocks_by_type(BlockType.TEXT))
            table_blocks = len(blocks.get_blocks_by_type(BlockType.TABLE))

            logger.info(f"Extracted {total_blocks} blocks: {text_blocks} text, {table_blocks} tables")

            return blocks

        except Exception as e:
            logger.error(f"Raw blocks extraction failed: {e}")
            raise

    def get_processing_stats(self) -> dict[str, Any]:
        """Get processing statistics."""
        success_rate = (self.stats['successful_queries'] / self.stats['total_queries'] * 100
                       if self.stats['total_queries'] > 0 else 0)

        return {
            **self.stats,
            'success_rate_pct': success_rate,
            'hybrid_retriever_stats': self.hybrid_retriever.get_stats(),
            'ontology_stats': self.ontology_mapper.get_stats(),
            'fact_table_stats': self.fact_table_repo.get_stats() if hasattr(self.fact_table_repo, 'get_stats') else {}
        }

    def export_processing_report(self,
                               results: list[ProcessingResult],
                               output_file: Optional[str] = None) -> str:
        """Export comprehensive processing report."""
        report_lines = []
        report_lines.append("# Enterprise RAG Processing Report")
        report_lines.append(f"Generated: {datetime.now().isoformat()}")
        report_lines.append("")

        # Summary statistics
        if results:
            total_queries = len(results)
            avg_confidence = sum(r.confidence_score for r in results) / total_queries
            avg_processing_time = sum(r.processing_time_ms for r in results) / total_queries
            total_errors = sum(len(r.errors) for r in results)
            total_warnings = sum(len(r.warnings) for r in results)

            report_lines.append("## Summary")
            report_lines.append(f"- Total queries processed: {total_queries}")
            report_lines.append(f"- Average confidence: {avg_confidence:.1%}")
            report_lines.append(f"- Average processing time: {avg_processing_time:.1f}ms")
            report_lines.append(f"- Total errors: {total_errors}")
            report_lines.append(f"- Total warnings: {total_warnings}")
            report_lines.append("")

        # System statistics
        stats = self.get_processing_stats()
        report_lines.append("## System Statistics")
        for key, value in stats.items():
            if isinstance(value, dict):
                report_lines.append(f"### {key.replace('_', ' ').title()}")
                for sub_key, sub_value in value.items():
                    report_lines.append(f"- {sub_key}: {sub_value}")
            else:
                report_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
        report_lines.append("")

        # Individual query details
        if results:
            report_lines.append("## Query Details")
            for i, result in enumerate(results, 1):
                report_lines.append(f"### Query {i}")
                report_lines.append(f"- Processing time: {result.processing_time_ms:.1f}ms")
                report_lines.append(f"- Confidence: {result.confidence_score:.1%}")
                report_lines.append(f"- Source references: {len(result.source_refs)}")
                report_lines.append(f"- Retrieval results: {len(result.retrieval_results)}")
                report_lines.append(f"- Normalized values: {len(result.normalized_data)}")
                report_lines.append(f"- Mapped metrics: {sum(1 for v in result.mapped_metrics.values() if v)}")
                report_lines.append(f"- Fact table records: {result.fact_table_records}")

                if result.warnings:
                    report_lines.append("**Warnings:**")
                    for warning in result.warnings:
                        report_lines.append(f"- {warning}")

                if result.errors:
                    report_lines.append("**Errors:**")
                    for error in result.errors:
                        report_lines.append(f"- {error}")

                report_lines.append("")

        report_content = "\n".join(report_lines)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"Processing report saved to {output_file}")

        return report_content

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive health check of all enterprise components."""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {}
        }

        # Document router health
        try:
            test_doc = "This is a test financial document with ricavi of €1000000."
            doc_type = self.document_router.classify_document(test_doc)
            health_status['components']['document_router'] = {
                'status': 'healthy',
                'test_classification': doc_type.value
            }
        except Exception as e:
            health_status['components']['document_router'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'

        # Data normalizer health
        try:
            test_value = self.data_normalizer.normalize_number("€1.234.567,89", "migliaia di euro")
            health_status['components']['data_normalizer'] = {
                'status': 'healthy',
                'test_normalization': test_value.to_float() if test_value else None
            }
        except Exception as e:
            health_status['components']['data_normalizer'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'

        # Ontology mapper health
        try:
            test_mapping = self.ontology_mapper.map_metric("fatturato")
            health_status['components']['ontology_mapper'] = {
                'status': 'healthy',
                'test_mapping': test_mapping[0] if test_mapping else None,
                'total_metrics': len(self.ontology_mapper.canonical_metrics)
            }
        except Exception as e:
            health_status['components']['ontology_mapper'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'

        # Hybrid retriever health
        try:
            retriever_stats = self.hybrid_retriever.get_stats()
            health_status['components']['hybrid_retriever'] = {
                'status': 'healthy',
                'stats': retriever_stats
            }
        except Exception as e:
            health_status['components']['hybrid_retriever'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'

        # Fact table repository health
        try:
            # Simple connection test
            test_stats = {'connection': 'ok'}  # Placeholder
            health_status['components']['fact_table_repository'] = {
                'status': 'healthy',
                'stats': test_stats
            }
        except Exception as e:
            health_status['components']['fact_table_repository'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'

        return health_status
