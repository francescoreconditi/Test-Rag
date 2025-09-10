# Redis - Cache Distribuita In-Memory

## 📋 Cos'è Redis?

**Redis** (Remote Dictionary Server) è un database NoSQL in-memory che funziona come struttura dati chiave-valore ultra-veloce. Nel nostro sistema RAG, Redis viene utilizzato come **cache distribuita** per ottimizzare drasticamente le performance dell'applicazione.

## 🎯 Ruolo nel Sistema RAG

### Cache Query Results
Redis memorizza i risultati delle query più frequenti, eliminando la necessità di ricalcoli costosi:
```python
# Prima query: calcolo completo (lento)
result = expensive_rag_query("analizza bilancio 2024")

# Query successive: servita da cache Redis (velocissima)
cached_result = redis_cache.get("analizza bilancio 2024")
```

### Gestione Sessioni Utente
Mantiene lo stato delle sessioni utente distribuito tra multiple istanze dell'applicazione:
- **Session ID**: Identificativo univoco utente
- **Cronologia Query**: Storico domande e risposte
- **Preferenze Utente**: Configurazioni personalizzate
- **Stato Applicazione**: Dati temporanei dell'interfaccia

### Cache Metadati Documenti
Memorizza informazioni sui documenti processati per accesso istantaneo:
- **Hash Documenti**: Evita riprocessing di file già analizzati
- **Embeddings Cache**: Vettori già calcolati per risparmio computazionale
- **Statistiche Performance**: Metriche di utilizzo e tempi di risposta

## ⚡ Vantaggi Performance

### Velocità Estrema
- **In-Memory Storage**: Dati mantenuti in RAM per accesso microsecondo
- **10-100x più veloce** di database tradizionali per operazioni di lettura
- **Pipeline Operations**: Batch multiple operazioni in una singola chiamata di rete

### Scalabilità Orizzontale
- **Clustering**: Distribuzione automatica dati tra multiple istanze Redis
- **Replication**: Backup automatico con master-slave setup
- **Sharding**: Partizionamento intelligente per dataset enormi

### Persistent Storage Options
- **RDB Snapshots**: Backup periodici su disco per durabilità
- **AOF (Append Only File)**: Log di tutte le operazioni per recovery completo
- **Hybrid Persistence**: Combinazione ottimale di RDB + AOF

## 🔧 Configurazione nel Progetto

### Variabili Ambiente (.env)
```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=          # Opzionale per sicurezza
REDIS_MAX_CONNECTIONS=50 # Pool size
```

### Connessione Application
```python
from src.infrastructure.performance.redis_cache import get_redis_cache

# Ottenere istanza cache singleton
cache = get_redis_cache()

# Operazioni cache basic
cache.set("chiave", "valore", ttl=300)  # 5 minuti TTL
valore = cache.get("chiave")
cache.delete("chiave")
```

## 📊 Tipi di Dati Supportati

### 1. Strings (Chiave-Valore)
```python
# Cache risultati query semplici
cache.set("query:ricavi_2024", "€2.5M", ttl=3600)
```

### 2. Hashes (Oggetti Strutturati)
```python
# Cache oggetti complessi (metadati documenti)
user_session = {
    "user_id": "12345",
    "last_query": "analisi profitti",
    "preferences": {"language": "it"}
}
cache.set("session:abc123", user_session, ttl=1800)
```

### 3. Lists (Code e Cronologie)
```python
# Cronologia query utente
cache.rpush("history:user123", "query1", "query2", "query3")
```

### 4. Sets (Collezioni Uniche)
```python
# Tag documenti processati
cache.sadd("processed_docs", "bilancio.pdf", "report.xlsx")
```

### 5. Sorted Sets (Ranking e Statistiche)
```python
# Classifica query più frequenti
cache.zadd("popular_queries", {"analisi ricavi": 100, "stato magazzino": 85})
```

## 🚀 Utilizzi Specifici nel RAG

### Query Result Caching
```python
class QueryResultCache(RedisCache):
    def cache_result(self, query: str, result: Any, ttl: int = 300):
        """Cache del risultato query RAG."""
        key = self._generate_query_key(query)
        cache_entry = {
            'query': query,
            'result': result,
            'cached_at': datetime.now().isoformat(),
            'confidence': result.confidence if hasattr(result, 'confidence') else None
        }
        self.set(key, cache_entry, ttl=ttl, namespace="query_results")
```

### Session Management
```python
class SessionCache(RedisCache):
    def create_session(self, session_id: str, user_data: Dict):
        """Crea nuova sessione utente."""
        session_data = {
            'id': session_id,
            'created_at': datetime.now().isoformat(),
            'user_data': user_data,
            'query_history': []
        }
        self.set(session_id, session_data, ttl=self.ttl, namespace="sessions")
```

### Document Processing Cache
```python
def cache_document_embeddings(doc_hash: str, embeddings: list, metadata: dict):
    """Cache embeddings documenti per evitare ricalcoli."""
    cache_data = {
        'embeddings': embeddings,
        'metadata': metadata,
        'processed_at': datetime.now().isoformat()
    }
    cache.set(f"embeddings:{doc_hash}", cache_data, ttl=86400)  # 24 ore
```

## 📈 Metriche e Monitoring

### Statistiche Cache
```python
stats = cache.get_stats()
print(f"""
Cache Performance:
- Hit Rate: {stats['hit_rate']}%
- Total Requests: {stats['total_requests']}
- Cache Hits: {stats['hits']}
- Cache Misses: {stats['misses']}
- Memory Usage: {stats['memory_used']}MB
""")
```

### Comandi Monitoring Redis
```bash
# Connessione Redis CLI
docker exec -it rag_redis redis-cli

# Info memoria
INFO memory

# Statistiche utilizzo
INFO stats

# Chiavi attive per namespace
KEYS query_results:*
KEYS sessions:*

# Monitoring real-time
MONITOR
```

## 🔧 Ottimizzazioni Avanzate

### Memory Management
```python
# Configurazione eviction policy
redis_config = {
    'maxmemory': '2gb',
    'maxmemory-policy': 'allkeys-lru',  # Least Recently Used
    'save': '900 1',  # RDB snapshot ogni 15 min se >= 1 change
}
```

### Connection Pooling
```python
from redis import ConnectionPool

pool = ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5
)
```

### Pipeline per Performance
```python
def batch_cache_operations(operations):
    """Batch multiple operazioni Redis in una pipeline."""
    pipe = cache.client.pipeline()
    for op in operations:
        getattr(pipe, op['command'])(*op['args'])
    return pipe.execute()
```

## 🛡️ Sicurezza e Best Practices

### Sicurezza
- **AUTH Password**: Sempre impostare password in produzione
- **TLS Encryption**: Connessioni criptate per dati sensibili
- **Network Isolation**: Redis su rete privata, non esposto pubblicamente

### Data Expiration
```python
# TTL appropriati per diversi tipi di dati
CACHE_TTL = {
    'query_results': 300,     # 5 minuti - dati che cambiano frequentemente
    'user_sessions': 1800,    # 30 minuti - sessioni utente
    'document_cache': 86400,  # 24 ore - documenti processati
    'system_config': 3600,    # 1 ora - configurazioni sistema
}
```

### Fallback Strategy
```python
def get_with_fallback(key: str, fallback_func, ttl: int = 300):
    """Pattern cache con fallback a fonte originale."""
    try:
        # Tentativo cache
        result = cache.get(key)
        if result is not None:
            return result
        
        # Fallback calcolo originale
        result = fallback_func()
        cache.set(key, result, ttl=ttl)
        return result
        
    except Exception as e:
        logger.warning(f"Redis cache error: {e}")
        return fallback_func()  # Graceful degradation
```

## 🔍 Troubleshooting Comune

### Problemi Connessione
```bash
# Test connettività Redis
docker exec -it rag_redis redis-cli ping
# Dovrebbe rispondere: PONG

# Check status container
docker ps | grep redis
docker logs rag_redis
```

### Memory Issues
```bash
# Check memoria utilizzata
redis-cli info memory

# Flush cache se necessario (ATTENZIONE: cancella tutto)
redis-cli flushdb  # Solo DB corrente
redis-cli flushall # Tutti i DB
```

### Performance Monitoring
```python
import time

def monitor_cache_performance():
    """Monitora performance cache Redis."""
    start_time = time.time()
    
    # Test operazioni
    cache.set("test_key", "test_value")
    result = cache.get("test_key")
    cache.delete("test_key")
    
    execution_time = time.time() - start_time
    print(f"Redis operation time: {execution_time*1000:.2f}ms")
```

## 📚 Conclusione

Redis trasforma il nostro sistema RAG da applicazione standard a **sistema enterprise ultra-performante**. Con tempi di risposta nell'ordine dei microsecondi e capacità di gestire milioni di operazioni al secondo, Redis è il cuore pulsante delle performance optimization del sistema.

La combinazione di **query caching**, **session management** e **document processing cache** garantisce un'esperienza utente fluida e scalabile per migliaia di utenti simultanei.