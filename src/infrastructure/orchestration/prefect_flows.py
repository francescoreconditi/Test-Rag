"""Prefect orchestration flows for enterprise data pipeline."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from prefect import flow, get_run_logger, task
from prefect.artifacts import create_markdown_artifact
from prefect.task_runners import ConcurrentTaskRunner

from src.application.services.data_normalizer import DataNormalizer

# Import our services
from src.application.services.document_router import DocumentRouter
from src.application.services.ontology_mapper import OntologyMapper
from src.domain.value_objects.data_lineage import DataLineage, TransformationType
from src.domain.value_objects.guardrails import FinancialGuardrails
from src.domain.value_objects.source_reference import SourceReference
from src.infrastructure.repositories.fact_table_enhanced import EnhancedFactTableRepository


@task(retries=3, retry_delay_seconds=60, timeout_seconds=300)
async def extract_document_data(file_path: str) -> dict[str, Any]:
    """Extract data from a document with retry logic."""
    logger = get_run_logger()
    logger.info(f"Extracting data from {file_path}")

    router = DocumentRouter()

    try:
        # Read file
        with open(file_path, 'rb') as f:
            content = f.read()

        # Route and process
        doc_type = router.classify_document(file_path, content)
        result = await router.process_document({
            'path': file_path,
            'content': content,
            'type': doc_type
        })

        logger.info(f"Successfully extracted {len(result.get('data', []))} records")
        return result

    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        raise


@task(retries=2, retry_delay_seconds=30)
async def normalize_financial_data(data: dict[str, Any], locale: str = "it_IT") -> dict[str, Any]:
    """Normalize financial data with retry logic."""
    logger = get_run_logger()
    logger.info(f"Normalizing {len(data.get('records', []))} records")

    normalizer = DataNormalizer()
    normalized_records = []

    for record in data.get('records', []):
        try:
            # Track transformations for lineage
            transformations = []

            # Normalize number
            if 'value' in record:
                original_value = record['value']
                normalized_value = normalizer.normalize_number(original_value, locale)
                if normalized_value != original_value:
                    transformations.append({
                        'type': TransformationType.NORMALIZATION.value,
                        'description': f"Normalized {original_value} to {normalized_value}"
                    })
                record['normalized_value'] = normalized_value

            # Normalize period
            if 'period' in record:
                normalized_period = normalizer.normalize_period(record['period'])
                if normalized_period != record['period']:
                    transformations.append({
                        'type': TransformationType.PERIOD_ALIGNMENT.value,
                        'description': f"Aligned period {record['period']} to {normalized_period}"
                    })
                record['normalized_period'] = normalized_period

            # Add transformations to record
            record['transformations'] = transformations
            normalized_records.append(record)

        except Exception as e:
            logger.warning(f"Failed to normalize record: {e}")
            continue

    logger.info(f"Successfully normalized {len(normalized_records)} records")
    return {'normalized_records': normalized_records}


@task(retries=2)
def map_to_ontology(data: dict[str, Any]) -> dict[str, Any]:
    """Map data to canonical ontology."""
    logger = get_run_logger()
    mapper = OntologyMapper()

    mapped_records = []
    for record in data.get('normalized_records', []):
        try:
            # Map metric name
            original_metric = record.get('metric', '')
            canonical_metric = mapper.map_metric(original_metric)

            if canonical_metric:
                record['canonical_metric'] = canonical_metric['canonical_name']
                record['mapping_confidence'] = canonical_metric['confidence']

                # Add to transformations
                if 'transformations' not in record:
                    record['transformations'] = []
                record['transformations'].append({
                    'type': 'ontology_mapping',
                    'description': f"Mapped '{original_metric}' to '{canonical_metric['canonical_name']}'"
                })

                mapped_records.append(record)
            else:
                logger.warning(f"Could not map metric: {original_metric}")

        except Exception as e:
            logger.error(f"Mapping error: {e}")
            continue

    logger.info(f"Mapped {len(mapped_records)} records to ontology")
    return {'mapped_records': mapped_records}


@task(retries=1)
def validate_financial_data(data: dict[str, Any]) -> dict[str, Any]:
    """Validate financial data with guardrails."""
    logger = get_run_logger()
    FinancialGuardrails()

    validation_results = []
    valid_records = []

    for record in data.get('mapped_records', []):
        try:
            # Validate individual metric
            is_valid = True
            warnings = []

            # Check range
            if 'normalized_value' in record:
                value = record['normalized_value']
                metric = record.get('canonical_metric', '')

                # Apply specific validations based on metric type
                if ('margin' in metric.lower() or 'ros' in metric.lower()) and not -100 <= value <= 100:
                    warnings.append(f"Percentage {value} out of range")
                    is_valid = False

            record['validation_status'] = 'valid' if is_valid else 'warning'
            record['validation_warnings'] = warnings

            if is_valid or len(warnings) == 0:
                valid_records.append(record)

            validation_results.append({
                'metric': record.get('canonical_metric'),
                'status': record['validation_status'],
                'warnings': warnings
            })

        except Exception as e:
            logger.error(f"Validation error: {e}")
            continue

    logger.info(f"Validated {len(valid_records)} records")
    return {
        'valid_records': valid_records,
        'validation_results': validation_results
    }


@task(retries=2)
def store_in_fact_table(data: dict[str, Any], source_file: str) -> dict[str, Any]:
    """Store validated data in fact table with lineage."""
    logger = get_run_logger()
    repo = EnhancedFactTableRepository()

    stored_facts = []
    source_ref = SourceReference(
        file_path=source_file,
        file_hash=SourceReference._calculate_hash(Path(source_file)),
        source_type='document',
        timestamp=datetime.now()
    )

    for record in data.get('valid_records', []):
        try:
            # Create lineage if this is a calculated metric
            lineage = None
            if record.get('transformations'):
                lineage = DataLineage(
                    target_metric=record.get('canonical_metric', 'unknown'),
                    target_value=record.get('normalized_value', 0),
                    calculation_formula=record.get('formula', 'direct'),
                    confidence_score=record.get('mapping_confidence', 1.0)
                )

                # Add transformations to lineage
                for trans in record['transformations']:
                    lineage.add_transformation(
                        TransformationType.NORMALIZATION,
                        trans.get('description', ''),
                        trans
                    )

            # Store fact with lineage
            fact_id = repo.insert_fact_with_lineage(
                metric_name=record.get('canonical_metric', 'unknown'),
                value=record.get('normalized_value', 0),
                entity_id=record.get('entity_id', 'default'),
                period_type=record.get('period_type', 'FY'),
                period_year=record.get('period_year', datetime.now().year),
                source_ref=source_ref,
                lineage=lineage,
                currency=record.get('currency'),
                unit=record.get('unit')
            )

            stored_facts.append(fact_id)
            logger.info(f"Stored fact {fact_id}: {record.get('canonical_metric')}")

        except Exception as e:
            logger.error(f"Storage error: {e}")
            continue

    repo.close()
    logger.info(f"Stored {len(stored_facts)} facts in database")
    return {'stored_facts': stored_facts}


@flow(
    name="enterprise-data-pipeline",
    description="Complete enterprise data processing pipeline with Prefect",
    task_runner=ConcurrentTaskRunner(),
    retries=1,
    retry_delay_seconds=120
)
async def process_documents_flow(
    file_paths: list[str],
    locale: str = "it_IT",
    validate: bool = True
) -> dict[str, Any]:
    """Main Prefect flow for processing multiple documents."""

    logger = get_run_logger()
    logger.info(f"Starting pipeline for {len(file_paths)} documents")

    all_results = []

    for file_path in file_paths:
        try:
            # Step 1: Extract data
            extracted_data = await extract_document_data(file_path)

            # Step 2: Normalize
            normalized_data = await normalize_financial_data(extracted_data, locale)

            # Step 3: Map to ontology
            mapped_data = map_to_ontology(normalized_data)

            # Step 4: Validate (optional)
            validated_data = validate_financial_data(mapped_data) if validate else mapped_data

            # Step 5: Store in fact table
            storage_result = store_in_fact_table(validated_data, file_path)

            all_results.append({
                'file': file_path,
                'status': 'success',
                'facts_stored': len(storage_result.get('stored_facts', []))
            })

        except Exception as e:
            logger.error(f"Pipeline failed for {file_path}: {e}")
            all_results.append({
                'file': file_path,
                'status': 'failed',
                'error': str(e)
            })

    # Create summary artifact
    summary = f"""
    # Pipeline Execution Summary

    **Processed Files**: {len(file_paths)}
    **Successful**: {sum(1 for r in all_results if r['status'] == 'success')}
    **Failed**: {sum(1 for r in all_results if r['status'] == 'failed')}
    **Total Facts Stored**: {sum(r.get('facts_stored', 0) for r in all_results)}

    ## Details:
    ```json
    {json.dumps(all_results, indent=2)}
    ```
    """

    await create_markdown_artifact(
        key="pipeline-summary",
        markdown=summary,
        description="Pipeline execution summary"
    )

    return {
        'summary': all_results,
        'timestamp': datetime.now().isoformat()
    }


@flow(
    name="scheduled-data-refresh",
    description="Scheduled flow for regular data updates"
)
async def scheduled_refresh_flow():
    """Scheduled flow that runs periodically."""
    logger = get_run_logger()

    # Find new files to process
    data_dir = Path("data/uploads")
    processed_marker = Path("data/.processed_files.json")

    # Load processed files list
    if processed_marker.exists():
        with open(processed_marker) as f:
            processed_files = set(json.load(f))
    else:
        processed_files = set()

    # Find new files
    new_files = []
    for file_path in data_dir.glob("**/*"):
        if file_path.is_file() and str(file_path) not in processed_files:
            new_files.append(str(file_path))

    if new_files:
        logger.info(f"Found {len(new_files)} new files to process")

        # Process new files
        result = await process_documents_flow(new_files)

        # Update processed files list
        processed_files.update(new_files)
        with open(processed_marker, 'w') as f:
            json.dump(list(processed_files), f)

        return result
    else:
        logger.info("No new files to process")
        return {'status': 'no_new_files'}


# Deployment configuration
if __name__ == "__main__":
    # Create a deployment for scheduled execution
    from prefect.deployments import Deployment
    from prefect.server.schemas.schedules import CronSchedule

    # Deploy the scheduled flow to run every hour
    deployment = Deployment.build_from_flow(
        flow=scheduled_refresh_flow,
        name="hourly-data-refresh",
        schedule=CronSchedule(cron="0 * * * *"),  # Every hour
        work_queue_name="default",
        tags=["data", "scheduled"]
    )

    deployment.apply()

    print("Deployment created: hourly-data-refresh")
    print("Run 'prefect agent start -q default' to start processing")
