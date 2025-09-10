# Celery - Background Job Processing

## 📋 Cos'è Celery?

**Celery** è un sistema di code distribuite per l'elaborazione asincrona di task in background. Nel nostro sistema RAG, Celery gestisce tutte le operazioni computazionalmente intensive che altrimenti bloccherebbero l'interfaccia utente, garantendo un'esperienza fluida e reattiva.

## 🎯 Ruolo nel Sistema RAG

### Elaborazione Asincrona
Celery sposta i task pesanti in background, permettendo all'applicazione di rispondere immediatamente agli utenti:
- **Indicizzazione Documenti**: Processamento PDF, DOCX, Excel in background
- **Analisi Complesse**: Elaborazioni AI intensive senza bloccare l'UI
- **Batch Processing**: Gestione di molteplici documenti simultaneamente
- **Calcoli Derivati**: Generazione metriche finanziarie complesse

### Task Scheduling
Pianifica automaticamente operazioni di manutenzione del sistema:
- **Pulizia Cache**: Rimozione automatica dati scaduti
- **Ottimizzazione Indici**: Manutenzione database vettoriali
- **Backup Dati**: Esportazione automatica configurazioni critiche
- **Health Checks**: Monitoraggio continuo stato sistema

## ⚙️ Architettura Distribuita

### Componenti Principali

#### 1. **Celery App** - Coordinator Centrale
```python
from celery import Celery

app = Celery('rag_tasks')
app.conf.update({
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0',
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
})
```

#### 2. **Workers** - Esecutori Task
Processi separati che eseguono i task in background:
```bash
# Avvio worker con multiple code
celery -A src.infrastructure.performance.celery_tasks worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=indexing,analysis,export
```

#### 3. **Broker** - Sistema Messaggi (Redis)
Gestisce la comunicazione tra producer e consumer:
- **Invio Task**: Applicazione invia task al broker
- **Distribuzione**: Broker assegna task a workers disponibili
- **Risultati**: Workers inviano risultati tramite broker

#### 4. **Result Backend** - Storage Risultati
Memorizza i risultati dei task per recupero successivo:
```python
# Invio task asincrono
result = index_documents.delay(document_paths)

# Recupero risultato quando pronto
if result.ready():
    output = result.get()
```

## 🔧 Code Specializzate

### 1. **Queue Indexing** - Elaborazione Documenti
```python
@app.task(queue='indexing')
def index_documents(document_paths: List[str], collection_name: str):
    """Indicizza documenti in background."""
    from services.document_loader import DocumentLoader
    from services.rag_engine import RAGEngine
    
    loader = DocumentLoader()
    rag = RAGEngine()
    
    total_docs = len(document_paths)
    indexed = 0
    
    for i, path in enumerate(document_paths):
        try:
            documents = loader.load_file(path)
            rag.build_index(documents)
            indexed += 1
            
            # Aggiorna progress
            progress = (indexed / total_docs) * 100
            index_documents.update_state(
                state='PROGRESS',
                meta={'current': indexed, 'total': total_docs, 'progress': progress}
            )
        except Exception as e:
            logger.error(f"Failed to index {path}: {e}")
    
    return {
        'status': 'completed',
        'total': total_docs,
        'indexed': indexed,
        'timestamp': datetime.now().isoformat()
    }
```

### 2. **Queue Analysis** - Analisi Avanzate
```python
@app.task(queue='analysis')
def analyze_documents(document_ids: List[str], analysis_type: str = 'comprehensive'):
    """Analizza documenti con AI in background."""
    results = []
    
    for doc_id in document_ids:
        if analysis_type == 'financial':
            result = perform_financial_analysis(doc_id)
        elif analysis_type == 'sentiment':
            result = perform_sentiment_analysis(doc_id)
        else:
            result = perform_comprehensive_analysis(doc_id)
        
        results.append(result)
        
        # Progress update
        progress = (len(results) / len(document_ids)) * 100
        analyze_documents.update_state(
            state='PROGRESS', 
            meta={'progress': progress, 'current_doc': doc_id}
        )
    
    return results
```

### 3. **Queue Training** - ML Training
```python
@app.task(queue='training')
def train_custom_model(training_data: Dict, model_type: str):
    """Addestra modelli personalizzati in background."""
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    
    # Setup training
    tokenizer = AutoTokenizer.from_pretrained('bert-base-italian')
    model = AutoModelForSequenceClassification.from_pretrained('bert-base-italian')
    
    # Training loop con progress updates
    for epoch in range(num_epochs):
        train_loss = train_epoch(model, training_data)
        
        train_custom_model.update_state(
            state='PROGRESS',
            meta={'epoch': epoch, 'loss': train_loss, 'progress': (epoch/num_epochs)*100}
        )
    
    # Save trained model
    model.save_pretrained(f'models/{model_type}_{datetime.now().strftime("%Y%m%d")}')
    
    return {
        'model_path': model_path,
        'final_loss': train_loss,
        'training_time': time.time() - start_time
    }
```

### 4. **Queue Export** - Generazione Report
```python
@app.task(queue='export')
def export_to_pdf(content: Dict, template: str = 'default'):
    """Genera PDF professionale in background."""
    from services.pdf_generator import PDFGenerator
    
    generator = PDFGenerator()
    
    # Genera nome file unico
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"report_{timestamp}.pdf"
    output_path = f"exports/{filename}"
    
    # Generazione PDF con progress
    export_to_pdf.update_state(state='PROGRESS', meta={'stage': 'processing_content'})
    
    processed_content = generator.process_content(content)
    
    export_to_pdf.update_state(state='PROGRESS', meta={'stage': 'rendering_pdf'})
    
    generator.render_pdf(processed_content, output_path, template=template)
    
    return {
        'status': 'completed',
        'file_path': output_path,
        'file_size': os.path.getsize(output_path),
        'timestamp': datetime.now().isoformat()
    }
```

## 📊 Task Scheduling Automatico

### Periodic Tasks con Celery Beat
```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    # Pulizia cache ogni 6 ore
    'cleanup-expired-cache': {
        'task': 'tasks.maintenance.cleanup_cache',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    
    # Ottimizzazione indici ogni giorno alle 3:00
    'optimize-indexes': {
        'task': 'tasks.maintenance.optimize_indexes',
        'schedule': crontab(minute=0, hour=3),
    },
    
    # Backup giornaliero alle 2:00
    'backup-data': {
        'task': 'tasks.maintenance.backup_data',
        'schedule': crontab(minute=0, hour=2),
    },
    
    # Report settimanale ogni lunedì alle 8:00
    'weekly-report': {
        'task': 'tasks.reports.generate_weekly_report',
        'schedule': crontab(minute=0, hour=8, day_of_week=1),
    },
}
```

### Maintenance Tasks
```python
@app.task(name='tasks.maintenance.cleanup_cache')
def cleanup_cache():
    """Pulizia automatica cache scaduta."""
    from src.infrastructure.performance.redis_cache import get_redis_cache
    
    cache = get_redis_cache()
    if cache:
        # Cleanup logic
        expired_keys = cache.get_expired_keys()
        deleted_count = cache.delete_multiple(expired_keys)
        
        return {
            'status': 'completed',
            'deleted_keys': deleted_count,
            'timestamp': datetime.now().isoformat()
        }

@app.task(name='tasks.maintenance.optimize_indexes')
def optimize_indexes():
    """Ottimizzazione automatica indici vettoriali."""
    from qdrant_client import QdrantClient
    
    client = QdrantClient(url="http://localhost:6333")
    collections = client.get_collections()
    
    optimized = []
    for collection in collections.collections:
        client.update_collection(
            collection_name=collection.name,
            optimizer_config={'indexing_threshold': 10000}
        )
        optimized.append(collection.name)
    
    return {
        'status': 'completed',
        'collections_optimized': optimized,
        'timestamp': datetime.now().isoformat()
    }
```

## 🔄 Task Management e Monitoring

### Task States
- **PENDING**: Task in attesa di esecuzione
- **STARTED**: Task iniziato da un worker
- **PROGRESS**: Task in esecuzione con aggiornamenti progress
- **SUCCESS**: Task completato con successo
- **FAILURE**: Task fallito con errore
- **RETRY**: Task in retry dopo fallimento
- **REVOKED**: Task cancellato prima dell'esecuzione

### Progress Tracking
```python
@app.task(bind=True)
def long_running_task(self, data):
    """Task con tracking progress dettagliato."""
    total_items = len(data)
    
    for i, item in enumerate(data):
        # Processo item
        result = process_item(item)
        
        # Aggiorna progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': i + 1,
                'total': total_items,
                'progress': ((i + 1) / total_items) * 100,
                'current_item': item['name'],
                'processed_items': [r['id'] for r in results]
            }
        )
    
    return {'status': 'completed', 'results': results}
```

### Error Handling e Retry
```python
@app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 5})
def resilient_task(self, data):
    """Task con retry automatico su errori."""
    try:
        # Operazione potenzialmente fallibile
        result = risky_operation(data)
        return result
        
    except Exception as exc:
        # Log errore prima del retry
        logger.error(f"Task failed on attempt {self.request.retries + 1}: {exc}")
        
        # Personalizza retry delay basato sul numero di tentativi
        countdown = min(300, (2 ** self.request.retries) * 5)  # Exponential backoff
        
        raise self.retry(exc=exc, countdown=countdown)
```

## 🚀 Utilizzo nell'Applicazione

### Task Submission
```python
from src.infrastructure.performance.celery_tasks import get_task_manager

def upload_documents_async(document_paths: List[str]):
    """Carica documenti in background."""
    manager = get_task_manager()
    
    # Submette task di indicizzazione
    task_id = manager.submit_task(
        "tasks.indexing.index_documents",
        args=(document_paths, "business_documents"),
        kwargs={"batch_size": 10}
    )
    
    return {
        'task_id': task_id,
        'status': 'submitted',
        'estimated_time': len(document_paths) * 30  # 30 secondi per documento
    }
```

### Task Status Monitoring
```python
def get_task_progress(task_id: str):
    """Ottiene progress di un task in esecuzione."""
    manager = get_task_manager()
    status = manager.get_task_status(task_id)
    
    if status['state'] == 'PROGRESS':
        return {
            'progress': status['info']['progress'],
            'current_step': status['info']['current_item'],
            'eta_seconds': calculate_eta(status['info'])
        }
    elif status['state'] == 'SUCCESS':
        return {
            'progress': 100,
            'result': status['result'],
            'completed_at': status['info']['timestamp']
        }
    elif status['state'] == 'FAILURE':
        return {
            'error': str(status['info']),
            'failed_at': datetime.now().isoformat()
        }
```

### Batch Processing
```python
def process_multiple_documents(file_list: List[str]):
    """Processa multiple documenti in batch paralleli."""
    from celery import group
    
    # Crea gruppo di task paralleli
    job = group(
        analyze_document.s(file_path) 
        for file_path in file_list
    )
    
    # Esegue in parallelo
    result = job.apply_async()
    
    # Aspetta completamento di tutti
    results = result.get()  # Blocca fino a completamento
    
    return {
        'total_processed': len(results),
        'successful': len([r for r in results if r.get('status') == 'success']),
        'failed': len([r for r in results if r.get('status') == 'error']),
        'results': results
    }
```

## 📈 Performance e Scalabilità

### Worker Scaling
```bash
# Avvia multiple workers per load balancing
celery -A src.infrastructure.performance.celery_tasks worker --concurrency=8 --hostname=worker1@%h
celery -A src.infrastructure.performance.celery_tasks worker --concurrency=4 --hostname=worker2@%h

# Workers specializzati per code specifiche
celery -A src.infrastructure.performance.celery_tasks worker -Q indexing --hostname=indexer@%h
celery -A src.infrastructure.performance.celery_tasks worker -Q analysis --hostname=analyzer@%h
```

### Resource Management
```python
# Configurazione avanzata workers
CELERY_CONFIG.update({
    'worker_prefetch_multiplier': 4,     # Tasks pre-fetch per worker
    'worker_max_tasks_per_child': 1000,  # Restart worker ogni 1000 tasks
    'task_time_limit': 3600,             # Hard limit 1 ora
    'task_soft_time_limit': 3000,        # Soft limit 50 minuti
    'worker_disable_rate_limits': False,  # Rate limiting attivo
})
```

### Queue Prioritization
```python
# Code con priorità differenziate
app.conf.task_routes = {
    'tasks.urgent.*': {'queue': 'high_priority'},
    'tasks.normal.*': {'queue': 'normal_priority'},
    'tasks.batch.*': {'queue': 'low_priority'},
}

# Worker configuration per priorità
# celery -A app worker -Q high_priority,normal_priority,low_priority
```

## 🔍 Troubleshooting e Debugging

### Common Issues

#### Worker Non Risponde
```bash
# Check worker status
celery -A src.infrastructure.performance.celery_tasks status

# Inspect active tasks
celery -A src.infrastructure.performance.celery_tasks inspect active

# Restart workers
pkill -f celery
celery -A src.infrastructure.performance.celery_tasks worker --loglevel=info
```

#### Memory Leaks
```python
# Monitor memory usage workers
import psutil
import os

def monitor_worker_memory():
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    if memory_mb > 1000:  # 1GB limit
        logger.warning(f"Worker using {memory_mb:.1f}MB memory")
        
        # Force restart se necessario
        if memory_mb > 2000:  # 2GB hard limit
            os._exit(0)  # Force worker restart
```

#### Task Stuck in PENDING
```bash
# Purge all tasks
celery -A src.infrastructure.performance.celery_tasks purge

# Reset Redis broker
redis-cli flushdb

# Inspect broker connection
celery -A src.infrastructure.performance.celery_tasks inspect ping
```

### Logging e Monitoring
```python
import logging

# Setup logging dettagliato per debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/celery.log'),
        logging.StreamHandler()
    ]
)

# Task-specific logging
@app.task(bind=True)
def logged_task(self, data):
    logger = logging.getLogger(self.name)
    logger.info(f"Starting task with data: {data}")
    
    try:
        result = process_data(data)
        logger.info(f"Task completed successfully: {result}")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        raise
```

## 📚 Conclusione

Celery trasforma il nostro sistema RAG in una **piattaforma di elaborazione distribuita** capace di gestire carichi di lavoro enterprise. Con la sua architettura a microservizi, task specializzati e capacità di scaling orizzontale, Celery garantisce:

- **Responsività UI**: Operazioni pesanti non bloccano mai l'interfaccia
- **Scalabilità**: Aggiungi workers per gestire più carico
- **Affidabilità**: Retry automatici e error handling robusto  
- **Osservabilità**: Monitoring completo con Flower dashboard

Il risultato è un sistema capace di processare migliaia di documenti simultaneamente mantenendo sempre performance ottimali per tutti gli utenti.