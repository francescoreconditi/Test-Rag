# Guida al Deployment RAG Enterprise

## 🚀 Opzioni di Deployment

### Opzione 1: Deployment Standard (Funzionalità Base)
**Ideale per**: Sviluppo, team piccoli, proof of concept

```bash
# 1. Solo dipendenze principali
uv pip install -r requirements.txt

# 2. Avvio applicazione  
streamlit run app.py

# Funzionalità disponibili:
# ✅ Analisi CSV, RAG documenti, insights AI
# ❌ Funzionalità modalità enterprise disabilitate con eleganza
```

### Opzione 2: Deployment Enterprise (Funzionalità Complete)  
**Ideale per**: Produzione, ambienti enterprise, funzionalità complete

```bash
# 1. Installa tutte le dipendenze incluse quelle enterprise
uv pip install -r requirements.txt
uv pip install -r requirements-enterprise.txt

# 2. Verifica componenti enterprise
python -c "from src.application.services.enterprise_orchestrator import EnterpriseOrchestrator; print('✅ Enterprise Pronto')"

# 3. Avvio con funzionalità enterprise
streamlit run app.py --server.port 8501

# Funzionalità disponibili:
# ✅ Tutte le funzionalità base
# ✅ Modalità enterprise con pipeline completa
# ✅ Recupero ibrido, validazione, tabella fatti
```

### Opzione 3: Deployment Docker
**Ideale per**: Produzione, ambienti containerizzati, scalabilità

```yaml
# docker-compose.yml
version: '3.8'
services:
  rag-app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ENTERPRISE_MODE=true
    depends_on:
      - qdrant
      
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
```

```bash
# Deployment
docker-compose up -d

# Scalabilità orizzontale
docker-compose up -d --scale rag-app=3
```

## 🔧 Configurazione Ambiente

### Configurazione Base (.env)
```env
# === OBBLIGATORIO ===
OPENAI_API_KEY=sk-la-tua-chiave-qui

# === SISTEMA RAG ===
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=business_documents

# === CONFIGURAZIONE AI ===
LLM_MODEL=gpt-4-turbo-preview
EMBEDDING_MODEL=text-embedding-3-small
TEMPERATURE=0.1
MAX_TOKENS=2000

# === PERFORMANCE ===
RAG_RESPONSE_MODE=compact
RAG_SIMILARITY_TOP_K=3
RAG_ENABLE_CACHING=True
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# === FUNZIONALITÀ ENTERPRISE ===
HF_HUB_DISABLE_SYMLINKS_WARNING=1
DEBUG_MODE=false
```

### Configurazione Produzione (.env.production)
```env
# === PERFORMANCE ===
RAG_RESPONSE_MODE=compact
RAG_SIMILARITY_TOP_K=3
RAG_ENABLE_CACHING=True
QUERY_CACHE_TTL=3600

# === DATABASE ENTERPRISE ===
FACT_TABLE_BACKEND=duckdb
FACT_TABLE_PATH=/app/data/enterprise_facts.duckdb

# === SICUREZZA ===
STREAMLIT_SERVER_ENABLE_CORS=false
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true

# === LOGGING ===
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true

# === SCALABILITÀ ===
STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
STREAMLIT_SERVER_MAX_MESSAGE_SIZE=200
```

## 🏗️ Architettura Deployment

### Deployment Singolo Nodo
```bash
# Per team < 50 utenti, documenti < 10k
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### Deployment Multi-Nodo  
```bash
# Load balancer + istanze multiple
nginx → [app1:8501, app2:8502, app3:8503] → qdrant_condiviso:6333

# Storage condiviso per tabella fatti
/shared/enterprise_facts.duckdb
```

### Deployment Microservizi
```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-enterprise
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-enterprise
  template:
    metadata:
      labels:
        app: rag-enterprise
    spec:
      containers:
      - name: rag-app
        image: rag-enterprise:latest
        ports:
        - containerPort: 8501
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        - name: ENTERPRISE_MODE
          value: "true"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

## 📊 Ottimizzazione Performance

### Ottimizzazione Memoria
```env
# Riduce utilizzo memoria modelli
EMBEDDING_BATCH_SIZE=32
MAX_CONCURRENT_REQUESTS=10
MODEL_CACHE_SIZE=100

# Per ambienti con memoria limitata
HYBRID_RETRIEVAL_ENABLED=false  # Disabilita modelli ML
ONTOLOGY_FUZZY_MATCHING=false   # Usa solo matching esatto
```

### Ottimizzazione CPU  
```env
# Carichi di lavoro CPU-bound
TORCH_NUM_THREADS=4
OMP_NUM_THREADS=4
TOKENIZERS_PARALLELISM=false

# Elaborazione asincrona
ENTERPRISE_ASYNC_WORKERS=4
QUERY_PROCESSING_TIMEOUT=30
```

### Performance Database
```env
# Ottimizzazione DuckDB
DUCKDB_MEMORY_LIMIT=4GB
DUCKDB_THREADS=4
DUCKDB_ENABLE_OPTIMIZER=true

# Fallback SQLite
SQLITE_CACHE_SIZE=10000
SQLITE_JOURNAL_MODE=WAL
```

## 🔒 Configurazione Sicurezza

### Sicurezza API
```env
# Limitazione rate
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_BURST=10

# Chiavi API
OPENAI_API_KEY_ROTATION=true
API_KEY_VALIDATION=strict

# Validazione richieste
MAX_QUERY_LENGTH=1000
MAX_DOCUMENT_SIZE=50MB
ALLOWED_FILE_TYPES=pdf,docx,txt,xlsx
```

### Sicurezza Dati
```env
# Crittografia a riposo
FACT_TABLE_ENCRYPTION=true
DOCUMENT_ENCRYPTION_KEY=/secrets/doc_key

# Gestione PII
ANONYMIZE_PII=true
PII_DETECTION_THRESHOLD=0.8

# Audit logging
AUDIT_LOG_ENABLED=true
AUDIT_LOG_PATH=/logs/audit.log
```

## 📈 Monitoraggio & Osservabilità

### Health Check
```python
# Endpoint health check personalizzato
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'enterprise_mode': enterprise_orchestrator is not None,
        'components': {
            'qdrant': check_qdrant_connection(),
            'models': check_ml_models_loaded(),
            'ontology': check_ontology_loaded()
        }
    }
```

### Raccolta Metriche
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'rag-enterprise'
    static_configs:
      - targets: ['localhost:8501']
    metrics_path: '/metrics'
```

### Regole di Alert
```yaml
# alerts.yml  
groups:
  - name: rag-enterprise
    rules:
      - alert: LatenzaQueryAlta
        expr: rag_query_duration_seconds > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "La latenza delle query RAG è alta"
          
      - alert: ComponenteEnterpriseDown
        expr: rag_component_health == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Un componente enterprise non è funzionante"
```

## 🔄 Manutenzione & Aggiornamenti

### Manutenzione Regolare
```bash
# Script manutenzione settimanale
#!/bin/bash

# 1. Aggiorna ontologia
wget https://updates.company.com/ontology/financial_metrics.yaml \
  -O config/ontology/financial_metrics.yaml

# 2. Riavvia servizi
systemctl reload rag-enterprise

# 3. Health check
curl -f http://localhost:8501/health || exit 1

# 4. Backup tabella fatti  
cp data/enterprise_facts.duckdb backups/facts_$(date +%Y%m%d).duckdb
```

### Aggiornamenti Versione
```bash
# Procedura aggiornamento elegante
1. Deploy nuova versione su staging
2. Esegui test componenti enterprise
3. Deployment blue-green su produzione
4. Monitoraggio per 24 ore
5. Piano rollback pronto
```

### Migrazioni Database
```python
# Esempio script migrazione
def migrate_fact_table_v2():
    """Aggiungi nuove colonne per tracciamento provenienza avanzato."""
    with duckdb.connect('enterprise_facts.duckdb') as conn:
        conn.execute("""
            ALTER TABLE facts 
            ADD COLUMN confidence_score REAL DEFAULT 1.0,
            ADD COLUMN validation_status TEXT DEFAULT 'unknown'
        """)
```

## 🚨 Risoluzione Problemi

### Problemi Comuni

#### Modalità Enterprise Non Disponibile
```bash
# Controlla componenti enterprise
python -c "from src.application.services.enterprise_orchestrator import EnterpriseOrchestrator"

# Se errore, installa dipendenze enterprise
uv pip install -r requirements-enterprise.txt
```

#### Modelli ML Non Caricano
```bash
# Controlla modelli disponibili
python -c "import sentence_transformers; print('✅ SentenceTransformers OK')"
python -c "from rank_bm25 import BM25Okapi; print('✅ BM25 OK')"

# Pulisci cache modelli se corrotta
rm -rf ~/.cache/huggingface/
rm -rf ~/.cache/torch/
```

#### Problemi Connessione Tabella Fatti
```bash
# Controlla permessi file database
ls -la data/enterprise_facts.duckdb

# Testa connessione
python -c "import duckdb; duckdb.connect('data/enterprise_facts.duckdb').execute('SELECT 1')"

# Ricostruisci se corrotto
rm data/enterprise_facts.duckdb  # Si ricreerà automaticamente
```

### Problemi Performance

#### Performance Query Lente
```env
# Ottimizza per velocità rispetto accuratezza
RAG_SIMILARITY_TOP_K=1
RAG_RESPONSE_MODE=simple  
HYBRID_RETRIEVAL_ENABLED=false
```

#### Problemi Memoria
```env
# Riduci utilizzo memoria
EMBEDDING_BATCH_SIZE=8
MODEL_CACHE_SIZE=50
QUERY_CACHE_SIZE=100
```

### Configurazione Logging
```python
# Logging avanzato
import logging
import structlog

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enterprise.log'),
        logging.StreamHandler()
    ]
)

# Logging strutturato per produzione
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

## 📋 Checklist Pre-Deployment

### Ambiente Sviluppo
- [ ] File `.env` configurato correttamente
- [ ] Qdrant funzionante su porta 6333
- [ ] Chiave OpenAI API valida e testata
- [ ] Dipendenze installate (`requirements.txt`)
- [ ] Test base superati

### Ambiente Enterprise
- [ ] Dipendenze enterprise installate (`requirements-enterprise.txt`)
- [ ] Componenti ML funzionanti (SentenceTransformers, BM25)
- [ ] Database DuckDB accessibile e scrivibile
- [ ] Ontologie caricate correttamente
- [ ] Toggle enterprise attivo nell'UI

### Ambiente Produzione
- [ ] Variabili ambiente produzione configurate
- [ ] SSL/TLS attivo
- [ ] Load balancer configurato
- [ ] Storage persistente per database
- [ ] Backup automatici attivi
- [ ] Monitoraggio e alerting funzionanti
- [ ] Health check endpoint testato
- [ ] Piano disaster recovery pronto

## 🎯 Best Practices

### Sicurezza
1. **Mai esporre chiavi API** in repository o logs
2. **Usa secrets management** per credenziali produzione
3. **Abilita HTTPS** sempre in produzione
4. **Audit trail** per tutte le operazioni sensibili
5. **Backup crittografati** per dati business

### Performance
1. **Cache aggressivo** per embeddings e risultati
2. **Load balancing** per gestire traffico alto
3. **Monitoring proattivo** di latenze e errori
4. **Database tuning** per query frequenti
5. **CDN** per asset statici se applicabile

### Operazioni
1. **Deployment automatizzato** con CI/CD
2. **Rollback rapido** in caso problemi
3. **Testing in staging** identico a produzione
4. **Documentazione aggiornata** per team ops
5. **Runbook** per scenari emergenza

---

**Questa guida deployment garantisce installazione sicura, scalabile e mantenibile del sistema RAG enterprise in tutti gli ambienti.**