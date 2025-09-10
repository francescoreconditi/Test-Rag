# Flower - Dashboard Monitoring Celery

## 📋 Cos'è Flower?

**Flower** è una web application per il monitoraggio e l'amministrazione in tempo reale dei cluster Celery. Nel nostro sistema RAG, Flower fornisce una **dashboard visuale completa** per supervisionare tutti i background jobs, worker performance, e health status del sistema distribuito.

## 🎯 Ruolo nel Sistema RAG

### Monitoring Real-Time
Flower offre visibilità completa su tutti gli aspetti dell'elaborazione asincrona:
- **Worker Status**: Stato in tempo reale di tutti i workers attivi
- **Task Execution**: Progress e risultati dei task in esecuzione
- **Queue Management**: Monitoraggio code e backlog accumulation
- **Performance Metrics**: Statistiche throughput, latenza, error rates

### Administrative Control
Controllo operativo centralizzato del sistema distribuito:
- **Worker Management**: Start/stop/restart workers remoti
- **Task Control**: Cancel, retry, revoke task individuali
- **Queue Operations**: Purge, inspect, reroute messaggi
- **System Configuration**: Modify routing, priorities, rate limits

## 🌸 Interfaccia Dashboard

### Home Dashboard
La schermata principale mostra overview completo del sistema:

```
📊 SYSTEM OVERVIEW
├── Active Workers: 3/5 online
├── Processed Tasks: 1,247 (last 24h)
├── Failed Tasks: 12 (0.96% error rate)
├── Average Processing Time: 23.5s
└── Queue Backlog: 8 tasks pending
```

### Workers Panel
Monitoraggio dettagliato di ogni worker:

```
🔧 WORKERS STATUS
┌─────────────────────────────────────────────┐
│ worker@hostname1  [ONLINE]  CPU: 45%  MEM: 1.2GB │
│ ├── Processed: 423 tasks                   │
│ ├── Active: 2 tasks                        │
│ ├── Load Average: [1.2, 1.5, 1.8]         │
│ └── Queues: indexing, analysis             │
├─────────────────────────────────────────────┤
│ worker@hostname2  [OFFLINE] Last seen: 2m ago │
└─────────────────────────────────────────────┘
```

### Tasks Panel
Tracking completo dei task con real-time updates:

```
📋 TASKS EXECUTION
┌────────────────────────────────────────────────────────────┐
│ [RUNNING] index_documents                     Progress: 75% │
│ ├── ID: 4f4e4f4f-1234-5678-abcd-123456789012           │
│ ├── Worker: worker@indexer                              │
│ ├── Started: 2m 15s ago                                 │
│ ├── ETA: 30s remaining                                  │
│ └── Args: ['doc1.pdf', 'doc2.pdf', 'doc3.pdf']        │
├────────────────────────────────────────────────────────────┤
│ [SUCCESS] analyze_documents                Completed: 45s  │
│ [FAILURE] export_to_pdf                   Error: timeout   │
│ [PENDING] train_custom_model              Queue: training  │
└────────────────────────────────────────────────────────────┘
```

### Queues Monitoring
Visualizzazione stato delle code con metriche dettagliate:

```
📤 QUEUES STATUS
┌─────────────────────────────────────────┐
│ indexing     [8 pending] [2 processing] │
│ ├── Rate: 12 tasks/min                 │
│ ├── Avg Wait: 45s                      │
│ └── Priority: HIGH                     │
├─────────────────────────────────────────┤
│ analysis     [3 pending] [1 processing] │
│ ├── Rate: 8 tasks/min                  │
│ ├── Avg Wait: 1m 20s                   │
│ └── Priority: NORMAL                   │
├─────────────────────────────────────────┤
│ training     [1 pending] [0 processing] │
│ └── Rate: 0.5 tasks/min                │
└─────────────────────────────────────────┘
```

## 📊 Metriche e Analytics

### Performance Metrics
Flower raccoglie e visualizza metriche dettagliate:

```python
# Automaticamente tracciato da Flower
METRICS = {
    'task_throughput': {
        'successful_tasks_per_second': 2.3,
        'failed_tasks_per_second': 0.02,
        'total_throughput': 2.32
    },
    'response_times': {
        'p50': 12.5,  # 50th percentile
        'p95': 45.2,  # 95th percentile  
        'p99': 120.8, # 99th percentile
        'average': 23.1
    },
    'worker_utilization': {
        'cpu_usage': 34.5,
        'memory_usage': 67.2,
        'active_tasks': 5,
        'processed_tasks': 1247
    }
}
```

### Historical Data
Grafici temporali per trend analysis:

```
📈 TASK EXECUTION TRENDS (Last 24h)
    Tasks/Hour
    ┌─────────────────────────────────────┐
120 │                   ▄▄▄               │ Peak Hours
    │             ▄▄▄  ▄█████▄            │
 80 │        ▄▄▄ ▄█████████████▄          │ Business Hours  
    │   ▄▄▄ ▄███████████████████▄         │
 40 │▄▄█████████████████████████▄▄        │ 
    │█████████████████████████████▄▄▄     │ Night Hours
  0 └─────────────────────────────────────┘
    00:00    06:00    12:00    18:00    24:00
```

### Error Analysis
Dashboard errori con categorizzazione automatica:

```
🚨 ERROR ANALYSIS (Last 24h)
┌──────────────────────────────────────────────┐
│ Timeout Errors              45% │ ████████   │
│ ├── indexing queue: 8 tasks              │
│ ├── analysis queue: 4 tasks              │
│ └── Avg duration before timeout: 58m     │
├──────────────────────────────────────────────┤
│ Memory Errors                30% │ ██████     │
│ ├── Mostly in training queue             │
│ └── Peak memory usage: 3.2GB             │
├──────────────────────────────────────────────┤
│ Connection Errors            15% │ ███        │
│ └── Redis connection timeouts            │
├──────────────────────────────────────────────┤
│ Other Errors                 10% │ ██         │
└──────────────────────────────────────────────┘
```

## 🔧 Configurazione e Setup

### Basic Setup
```python
# In celery_tasks.py
from flower import Flower
from celery import Celery

app = Celery('rag_tasks')

# Flower configuration  
flower_app = Flower(celery=app)
flower_app.conf.update(
    port=5555,
    address='0.0.0.0',
    broker_api='http://guest:guest@localhost:15672/api/',
    basic_auth=['admin:secret'],  # Optional authentication
    url_prefix='/flower'          # If behind reverse proxy
)
```

### Authentication Setup
```python
# Basic HTTP Authentication
FLOWER_CONFIG = {
    'basic_auth': ['admin:password123', 'monitor:readonly'],
    'oauth2_key': 'your-oauth2-key',
    'oauth2_secret': 'your-oauth2-secret',
    'oauth2_redirect_uri': 'http://localhost:5555/login'
}
```

### Custom Monitoring
```python
# Custom task monitoring hooks
@app.task(bind=True)
def monitored_task(self, data):
    """Task con monitoring custom via Flower."""
    
    # Custom metrics che appaiono in Flower
    self.update_state(
        state='PROGRESS',
        meta={
            'current_step': 'data_processing',
            'progress': 25,
            'custom_metrics': {
                'documents_processed': 10,
                'error_count': 2,
                'performance_score': 8.5
            }
        }
    )
    
    # Flower automaticamente traccia queste metriche
    result = process_data(data)
    
    return {
        'result': result,
        'execution_time': time.time() - start_time,
        'memory_peak': get_memory_usage(),
        'custom_score': calculate_quality_score(result)
    }
```

## 📱 REST API Integration

### Flower API Endpoints
Flower espone REST API per integrazione programmatica:

```python
import requests

FLOWER_BASE_URL = "http://localhost:5555/api"

def get_worker_stats():
    """Ottiene statistiche workers via API."""
    response = requests.get(f"{FLOWER_BASE_URL}/workers")
    return response.json()

def get_task_info(task_id: str):
    """Ottiene info task specifico."""
    response = requests.get(f"{FLOWER_BASE_URL}/task/info/{task_id}")
    return response.json()

def revoke_task(task_id: str, terminate: bool = False):
    """Annulla task in esecuzione."""
    response = requests.post(f"{FLOWER_BASE_URL}/task/revoke/{task_id}", 
                           json={'terminate': terminate})
    return response.json()

def get_queue_length(queue_name: str):
    """Ottiene lunghezza coda specifica."""
    response = requests.get(f"{FLOWER_BASE_URL}/queues/length")
    return response.json().get(queue_name, 0)
```

### Integration con Streamlit
```python
# In app.py Streamlit
import streamlit as st
import requests

def show_celery_dashboard():
    """Integra metriche Flower in Streamlit sidebar."""
    
    st.sidebar.markdown("## 🌸 Celery Status")
    
    try:
        # Ottieni stats da Flower API
        workers = requests.get("http://localhost:5555/api/workers").json()
        active_tasks = requests.get("http://localhost:5555/api/tasks?state=PROGRESS").json()
        
        # Display workers status
        worker_count = len(workers)
        active_workers = len([w for w in workers.values() if w.get('status') == 'OK'])
        
        st.sidebar.metric(
            label="Workers", 
            value=f"{active_workers}/{worker_count}",
            delta="All Online" if active_workers == worker_count else "Issues Detected"
        )
        
        # Display active tasks
        st.sidebar.metric(
            label="Active Tasks",
            value=len(active_tasks),
            delta="+3" if len(active_tasks) > 0 else "Idle"
        )
        
        # Link to full dashboard
        st.sidebar.markdown("🔗 [Open Full Dashboard](http://localhost:5555)")
        
    except Exception as e:
        st.sidebar.error(f"Flower connection error: {e}")
```

## 🔍 Advanced Monitoring Features

### Custom Task States Visualization
```python
# Custom task state colors in Flower
TASK_STATE_COLORS = {
    'PENDING': '#ffc107',     # Yellow
    'PROGRESS': '#007bff',    # Blue  
    'SUCCESS': '#28a745',     # Green
    'FAILURE': '#dc3545',     # Red
    'RETRY': '#fd7e14',       # Orange
    'REVOKED': '#6c757d'      # Gray
}
```

### Real-Time Task Progress
```javascript
// Flower frontend JavaScript per real-time updates
function updateTaskProgress() {
    fetch('/api/tasks?state=PROGRESS')
        .then(response => response.json())
        .then(tasks => {
            tasks.forEach(task => {
                const progressBar = document.getElementById(`progress-${task.uuid}`);
                const meta = task.result || {};
                
                if (progressBar && meta.progress) {
                    progressBar.style.width = `${meta.progress}%`;
                    progressBar.textContent = `${meta.progress}% - ${meta.current_step}`;
                }
            });
        });
}

// Update ogni 2 secondi
setInterval(updateTaskProgress, 2000);
```

### Alert System Integration
```python
class FlowerAlerts:
    """Sistema di alert integrato con Flower."""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url
        
    def check_system_health(self):
        """Monitora salute sistema e invia alert."""
        try:
            workers = requests.get("http://localhost:5555/api/workers").json()
            
            # Check worker health
            offline_workers = [
                name for name, info in workers.items() 
                if info.get('status') != 'OK'
            ]
            
            if offline_workers:
                self.send_alert(
                    level='WARNING',
                    message=f"Workers offline: {', '.join(offline_workers)}"
                )
            
            # Check queue backlog
            queue_lengths = requests.get("http://localhost:5555/api/queues/length").json()
            high_backlog_queues = [
                queue for queue, length in queue_lengths.items() 
                if length > 50
            ]
            
            if high_backlog_queues:
                self.send_alert(
                    level='CRITICAL',
                    message=f"High queue backlog: {high_backlog_queues}"
                )
                
        except Exception as e:
            self.send_alert(
                level='ERROR', 
                message=f"Flower monitoring failed: {e}"
            )
    
    def send_alert(self, level: str, message: str):
        """Invia alert a sistema esterno."""
        if self.webhook_url:
            payload = {
                'level': level,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'service': 'flower-monitoring'
            }
            requests.post(self.webhook_url, json=payload)
```

## 🛡️ Security e Best Practices

### Production Security
```python
FLOWER_PRODUCTION_CONFIG = {
    # HTTPS only in production
    'certfile': '/path/to/cert.pem',
    'keyfile': '/path/to/key.pem',
    
    # Strong authentication
    'basic_auth': ['admin:very-secure-password'],
    
    # Rate limiting
    'max_tasks': 10000,
    'enable_events': True,
    
    # Logging
    'logging': 'INFO',
    'access_log': '/var/log/flower/access.log',
    
    # Network security  
    'address': '127.0.0.1',  # Bind only to localhost
    'url_prefix': '/flower',  # Behind reverse proxy
}
```

### Reverse Proxy Setup (Nginx)
```nginx
# Nginx configuration per Flower
location /flower/ {
    proxy_pass http://localhost:5555/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket support per real-time updates
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # Authentication
    auth_basic "Flower Admin";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
```

## 📚 Troubleshooting

### Common Issues

#### Flower Non Si Avvia
```bash
# Check Celery app configuration
celery -A src.infrastructure.performance.celery_tasks inspect ping

# Verify Redis connection
redis-cli ping

# Start Flower with debug
celery -A src.infrastructure.performance.celery_tasks flower --debug
```

#### Workers Non Visibili
```python
# Assicurati che workers abbiano eventi abilitati
celery -A src.infrastructure.performance.celery_tasks worker --loglevel=info -E

# O configura in app
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True
```

#### Performance Issues
```python
# Ottimizza configurazione Flower per grandi volumi
FLOWER_CONFIG.update({
    'max_workers': 200,        # Limite workers visualizzati
    'max_tasks': 1000,         # Limite tasks in history
    'purge_offline_workers': 60,  # Remove workers offline da 60s
    'refresh_interval': 5000   # Update interval in ms
})
```

### Debugging Task Issues
```python
# Enable detailed task logging in Flower
import logging

flower_logger = logging.getLogger('flower')
flower_logger.setLevel(logging.DEBUG)

# Custom task inspection
@app.task(bind=True)
def debug_task(self):
    """Task per debugging con Flower."""
    print(f'Request: {self.request!r}')
    return {
        'task_id': self.request.id,
        'task_name': self.name,
        'args': self.request.args,
        'kwargs': self.request.kwargs,
        'retries': self.request.retries,
        'hostname': self.request.hostname
    }
```

## 📊 Performance Optimization

### Flower Configuration per High Load
```python
# Configurazione per ambienti ad alto carico
HIGH_LOAD_CONFIG = {
    'max_tasks': 5000,           # Più tasks in history
    'tasks_columns': 'name,uuid,state,received,started',  # Colonne essenziali
    'persistent': True,          # Persisti stato tra restart
    'db': 'flower.db',          # SQLite per persistenza
    'enable_events': True,       # Real-time events
    'natural_time': False,       # Disabilita human-readable time
    'tasks_refresh_interval': 10000,  # 10s refresh interval
}
```

### Memory Management
```python
def optimize_flower_memory():
    """Ottimizza utilizzo memoria Flower."""
    
    # Cleanup old tasks automaticamente
    from flower.views.tasks import TaskView
    
    # Mantieni solo tasks recenti
    cutoff_time = datetime.now() - timedelta(hours=24)
    TaskView.cleanup_old_tasks(cutoff_time)
    
    # Force garbage collection
    import gc
    gc.collect()
```

## 📚 Conclusione

Flower trasforma il monitoring del sistema Celery da operazione complessa a **dashboard intuitiva e potente**. Con la sua interfaccia web ricca di funzionalità, API RESTful completa e capacità di integrazione avanzate, Flower fornisce:

- **Visibilità Totale**: Ogni aspetto del sistema distribuito è monitorabile
- **Controllo Operativo**: Gestione remota workers e tasks
- **Analytics Avanzate**: Metriche storiche e trend analysis  
- **Alert Proattivi**: Identificazione precoce di problemi
- **Integrazione Seamless**: API per integrazione con altri sistemi

Il risultato è un sistema distribuito completamente osservabile e controllabile, essenziale per operazioni enterprise mission-critical.