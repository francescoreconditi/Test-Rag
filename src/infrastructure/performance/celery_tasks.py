"""
Celery-based background job queue for heavy processing tasks.
Handles document indexing, model training, and batch processing asynchronously.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import hashlib

try:
    from celery import Celery, Task, group, chain, chord
    from celery.result import AsyncResult
    from celery.schedules import crontab
    from kombu import Queue, Exchange
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None
    Task = object
    AsyncResult = None

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# Celery configuration
CELERY_CONFIG = {
    'broker_url': os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    'result_backend': os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    'task_track_started': True,
    'task_time_limit': 3600,  # 1 hour hard limit
    'task_soft_time_limit': 3000,  # 50 minutes soft limit
    'worker_prefetch_multiplier': 1 if os.name == 'nt' else 4,  # Windows needs 1
    'worker_max_tasks_per_child': 1000,  # Restart worker after 1000 tasks
    'worker_pool': 'solo' if os.name == 'nt' else 'prefork',  # Windows needs solo
    'task_acks_late': True,  # Acknowledge task after completion
    'worker_hijack_root_logger': False,
    'task_compression': 'gzip',
    'result_compression': 'gzip',
    'result_expires': 3600,  # Results expire after 1 hour
}


# Initialize Celery app
if CELERY_AVAILABLE:
    app = Celery('rag_tasks')
    app.conf.update(CELERY_CONFIG)
    
    # Define task queues
    app.conf.task_routes = {
        'tasks.indexing.*': {'queue': 'indexing'},
        'tasks.analysis.*': {'queue': 'analysis'},
        'tasks.training.*': {'queue': 'training'},
        'tasks.export.*': {'queue': 'export'},
    }
    
    # Define queue configuration
    app.conf.task_queues = (
        Queue('indexing', Exchange('indexing'), routing_key='indexing'),
        Queue('analysis', Exchange('analysis'), routing_key='analysis'),
        Queue('training', Exchange('training'), routing_key='training'),
        Queue('export', Exchange('export'), routing_key='export'),
        Queue('default', Exchange('default'), routing_key='default'),
    )
    
    # Periodic tasks schedule
    app.conf.beat_schedule = {
        'cleanup-expired-cache': {
            'task': 'tasks.maintenance.cleanup_cache',
            'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
        },
        'optimize-indexes': {
            'task': 'tasks.maintenance.optimize_indexes',
            'schedule': crontab(minute=0, hour=3),  # Daily at 3 AM
        },
        'backup-data': {
            'task': 'tasks.maintenance.backup_data',
            'schedule': crontab(minute=0, hour=2),  # Daily at 2 AM
        },
    }
else:
    app = None


class BaseTask(Task if CELERY_AVAILABLE else object):
    """Base task with error handling and monitoring."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 5}
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {self.name} failed: {exc}")
        # Send notification or alert
        self._send_failure_notification(task_id, exc)
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(f"Task {self.name} completed successfully")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        logger.warning(f"Task {self.name} retrying: {exc}")
    
    def _send_failure_notification(self, task_id: str, exc: Exception):
        """Send failure notification (implement based on your notification system)."""
        pass


# Document Indexing Tasks
if CELERY_AVAILABLE:
    @app.task(base=BaseTask, name='tasks.indexing.index_documents', queue='indexing')
    def index_documents(
        document_paths: List[str],
        collection_name: str,
        batch_size: int = 10,
        use_gpu: bool = False
    ) -> Dict[str, Any]:
        """Index documents in background."""
        from services.document_loader import DocumentLoader
        from services.rag_engine import RAGEngine
        
        try:
            loader = DocumentLoader()
            rag = RAGEngine()
            
            total_docs = len(document_paths)
            indexed = 0
            failed = []
            
            # Process in batches
            for i in range(0, total_docs, batch_size):
                batch = document_paths[i:i + batch_size]
                
                try:
                    # Load documents
                    documents = []
                    for path in batch:
                        docs = loader.load_file(path)
                        documents.extend(docs)
                    
                    # Index batch
                    rag.build_index(documents)
                    indexed += len(batch)
                    
                    # Update progress
                    progress = (indexed / total_docs) * 100
                    index_documents.update_state(
                        state='PROGRESS',
                        meta={'current': indexed, 'total': total_docs, 'progress': progress}
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to index batch: {e}")
                    failed.extend(batch)
            
            return {
                'status': 'completed',
                'total': total_docs,
                'indexed': indexed,
                'failed': failed,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Document indexing failed: {e}")
            raise
    
    
    @app.task(base=BaseTask, name='tasks.indexing.reindex_collection', queue='indexing')
    def reindex_collection(collection_name: str) -> Dict[str, Any]:
        """Reindex entire collection."""
        from services.rag_engine import RAGEngine
        
        try:
            rag = RAGEngine()
            
            # Get all documents from collection
            # Reprocess and reindex
            # This is a placeholder - implement based on your needs
            
            return {
                'status': 'completed',
                'collection': collection_name,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Collection reindexing failed: {e}")
            raise


# Analysis Tasks
if CELERY_AVAILABLE:
    @app.task(base=BaseTask, name='tasks.analysis.analyze_documents', queue='analysis')
    def analyze_documents(
        document_ids: List[str],
        analysis_type: str = 'comprehensive'
    ) -> Dict[str, Any]:
        """Perform deep analysis on documents."""
        try:
            results = []
            
            for doc_id in document_ids:
                # Perform analysis based on type
                if analysis_type == 'comprehensive':
                    result = _comprehensive_analysis(doc_id)
                elif analysis_type == 'financial':
                    result = _financial_analysis(doc_id)
                elif analysis_type == 'sentiment':
                    result = _sentiment_analysis(doc_id)
                else:
                    result = {'error': f'Unknown analysis type: {analysis_type}'}
                
                results.append(result)
                
                # Update progress
                progress = (len(results) / len(document_ids)) * 100
                analyze_documents.update_state(
                    state='PROGRESS',
                    meta={'current': len(results), 'total': len(document_ids), 'progress': progress}
                )
            
            return {
                'status': 'completed',
                'analysis_type': analysis_type,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            raise
    
    
    @app.task(base=BaseTask, name='tasks.analysis.batch_query', queue='analysis')
    def batch_query(
        queries: List[str],
        collection_name: str,
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute batch queries."""
        from services.rag_engine import RAGEngine
        
        try:
            rag = RAGEngine()
            results = []
            
            if parallel and len(queries) > 10:
                # Use group for parallel execution
                job = group(
                    single_query.s(query, collection_name)
                    for query in queries
                )
                results = job.apply_async().get()
            else:
                # Sequential execution
                for query in queries:
                    result = rag.query(query)
                    results.append({
                        'query': query,
                        'response': str(result),
                        'timestamp': datetime.now().isoformat()
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Batch query failed: {e}")
            raise


# Export Tasks
if CELERY_AVAILABLE:
    @app.task(base=BaseTask, name='tasks.export.export_to_pdf', queue='export')
    def export_to_pdf(
        content: Dict[str, Any],
        template: str = 'default',
        output_path: Optional[str] = None
    ) -> str:
        """Export content to PDF."""
        try:
            from services.pdf_generator import PDFGenerator
            
            generator = PDFGenerator()
            
            # Generate unique filename if not provided
            if not output_path:
                hash_id = hashlib.md5(json.dumps(content, sort_keys=True).encode()).hexdigest()[:8]
                output_path = f"exports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash_id}.pdf"
            
            # Ensure directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Generate PDF
            generator.generate(content, output_path, template=template)
            
            return output_path
            
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            raise
    
    
    @app.task(base=BaseTask, name='tasks.export.export_to_excel', queue='export')
    def export_to_excel(
        data: List[Dict[str, Any]],
        output_path: Optional[str] = None
    ) -> str:
        """Export data to Excel."""
        try:
            import pandas as pd
            
            # Generate unique filename if not provided
            if not output_path:
                hash_id = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:8]
                output_path = f"exports/data_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash_id}.xlsx"
            
            # Ensure directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Create DataFrame and export
            df = pd.DataFrame(data)
            df.to_excel(output_path, index=False, engine='openpyxl')
            
            return output_path
            
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            raise


# Maintenance Tasks
if CELERY_AVAILABLE:
    @app.task(name='tasks.maintenance.cleanup_cache')
    def cleanup_cache() -> Dict[str, Any]:
        """Clean up expired cache entries."""
        try:
            from src.infrastructure.performance.redis_cache import get_redis_cache
            
            cache = get_redis_cache()
            if cache:
                # Implement cache cleanup logic
                stats = cache.get_stats()
                
                return {
                    'status': 'completed',
                    'stats': stats,
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                'status': 'skipped',
                'reason': 'Cache not available',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            raise
    
    
    @app.task(name='tasks.maintenance.optimize_indexes')
    def optimize_indexes() -> Dict[str, Any]:
        """Optimize vector indexes."""
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(url="http://localhost:6333")
            
            # Get all collections
            collections = client.get_collections()
            optimized = []
            
            for collection in collections.collections:
                # Optimize collection
                client.update_collection(
                    collection_name=collection.name,
                    optimizer_config={
                        'indexing_threshold': 10000,
                        'flush_interval_sec': 5
                    }
                )
                optimized.append(collection.name)
            
            return {
                'status': 'completed',
                'collections_optimized': optimized,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Index optimization failed: {e}")
            raise
    
    
    @app.task(name='tasks.maintenance.backup_data')
    def backup_data() -> Dict[str, Any]:
        """Backup critical data."""
        try:
            import shutil
            
            # Define backup paths
            backup_dir = Path(f"backups/{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup configurations
            configs_to_backup = [
                '.env',
                'config/settings.py',
                'CLAUDE.md'
            ]
            
            for config in configs_to_backup:
                if Path(config).exists():
                    shutil.copy2(config, backup_dir / Path(config).name)
            
            # Backup database (placeholder - implement based on your database)
            # ...
            
            return {
                'status': 'completed',
                'backup_location': str(backup_dir),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data backup failed: {e}")
            raise


# Helper functions
def _comprehensive_analysis(doc_id: str) -> Dict[str, Any]:
    """Perform comprehensive document analysis."""
    # Placeholder implementation
    return {
        'doc_id': doc_id,
        'type': 'comprehensive',
        'metrics': {
            'readability': 0.85,
            'complexity': 0.6,
            'quality': 0.9
        }
    }


def _financial_analysis(doc_id: str) -> Dict[str, Any]:
    """Perform financial document analysis."""
    # Placeholder implementation
    return {
        'doc_id': doc_id,
        'type': 'financial',
        'metrics': {
            'revenue_mentioned': True,
            'profitability': 0.7,
            'risk_score': 0.3
        }
    }


def _sentiment_analysis(doc_id: str) -> Dict[str, Any]:
    """Perform sentiment analysis on document."""
    # Placeholder implementation
    return {
        'doc_id': doc_id,
        'type': 'sentiment',
        'metrics': {
            'positive': 0.6,
            'negative': 0.2,
            'neutral': 0.2
        }
    }


# Single query task for parallel execution
if CELERY_AVAILABLE:
    @app.task
    def single_query(query: str, collection_name: str) -> Dict[str, Any]:
        """Execute single query (for parallel batch processing)."""
        from services.rag_engine import RAGEngine
        
        rag = RAGEngine()
        result = rag.query(query)
        
        return {
            'query': query,
            'response': str(result),
            'timestamp': datetime.now().isoformat()
        }


# Task management utilities
class TaskManager:
    """Manage and monitor Celery tasks."""
    
    def __init__(self):
        if not CELERY_AVAILABLE:
            raise ImportError("Celery not installed. Install with: pip install celery redis")
        
        self.app = app
    
    def submit_task(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: dict = None,
        queue: str = 'default',
        countdown: int = 0,
        eta: Optional[datetime] = None,
        expires: Optional[int] = None
    ) -> str:
        """Submit task to queue."""
        task = self.app.send_task(
            task_name,
            args=args,
            kwargs=kwargs or {},
            queue=queue,
            countdown=countdown,
            eta=eta,
            expires=expires
        )
        
        return task.id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status."""
        result = AsyncResult(task_id, app=self.app)
        
        return {
            'task_id': task_id,
            'state': result.state,
            'ready': result.ready(),
            'successful': result.successful() if result.ready() else None,
            'result': result.result if result.ready() else None,
            'info': result.info
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel task."""
        result = AsyncResult(task_id, app=self.app)
        result.revoke(terminate=True)
        return True
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get list of active tasks."""
        inspect = self.app.control.inspect()
        active = inspect.active()
        
        tasks = []
        if active:
            for worker, task_list in active.items():
                for task in task_list:
                    tasks.append({
                        'worker': worker,
                        'task_id': task['id'],
                        'name': task['name'],
                        'args': task.get('args'),
                        'kwargs': task.get('kwargs')
                    })
        
        return tasks
    
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get list of scheduled tasks."""
        inspect = self.app.control.inspect()
        scheduled = inspect.scheduled()
        
        tasks = []
        if scheduled:
            for worker, task_list in scheduled.items():
                for task in task_list:
                    tasks.append({
                        'worker': worker,
                        'task_id': task['request']['id'],
                        'name': task['request']['name'],
                        'eta': task.get('eta')
                    })
        
        return tasks


# Export singleton task manager
_task_manager = None


def get_task_manager() -> Optional[TaskManager]:
    """Get singleton task manager instance."""
    global _task_manager
    
    if not CELERY_AVAILABLE:
        logger.warning("Celery not available, task queue disabled")
        return None
    
    if _task_manager is None:
        try:
            _task_manager = TaskManager()
        except Exception as e:
            logger.error(f"Failed to initialize task manager: {e}")
            return None
    
    return _task_manager