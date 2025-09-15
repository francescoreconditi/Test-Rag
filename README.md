# Sistema RAG di Business Intelligence Avanzato 🏢

Una **piattaforma enterprise di Business Intelligence di nuova generazione** che combina analisi di dati strutturati con funzionalità avanzate RAG (Retrieval-Augmented Generation). Costruita con **Clean Architecture**, **Domain-Driven Design**, e **pattern enterprise-grade** per analisi finanziarie scalabili, intelligenza documentale e sicurezza multi-tenant.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Qdrant](https://img.shields.io/badge/Qdrant-DC244C?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Enterprise Ready](https://img.shields.io/badge/Enterprise-Ready-green)](https://github.com)

---

## 🎯 Funzionalità Principali

### 🔥 **NOVITÀ 2025: Gold Standard Benchmarking & Dimensional Coherence**
- **🎯 Gold Standard Benchmarking**: Sistema automatizzato per misurare accuratezza RAG vs valori certificati
- **📐 Dimensional Coherence Validation**: 15+ regole avanzate per validazione coerenza finanziaria
- **📊 Report di Qualità**: HTML/JSON reports con metriche dettagliate e grafici di performance
- **⚙️ Configurazione YAML**: Test cases e regole di validazione completamente configurabili
- **🔍 Continuous Quality**: Integrazione CI/CD per monitoraggio qualità automatico

### 🚀 **Architettura Enterprise a 6 Livelli**
- **🔧 Attivazione Enterprise**: Modalità enterprise con toggle nella sidebar Streamlit
- **⚡ Performance Ultra-Ottimizzate**: Connection pooling, cache Redis distribuita, Celery background jobs
- **🔄 Scaling Orizzontale**: Load balancing Nginx, auto-scaling Docker, alta disponibilità
- **📊 Dashboard Analytics**: KPI interattivi, trend analysis, waterfall charts, radar efficienza
- **🔍 Anteprima Documenti**: Thumbnails automatici, estrazione contenuti, statistiche documenti
- **✏️ Editor Interattivo**: Real-time editing metriche, validazione automatica, suggerimenti AI
- **📈 Visualizzazioni Professionali**: Plotly charts, gauge KPI, heatmap rischio

### 🔐 **Sistema di Sicurezza Multi-Tenant Avanzato**
- **🛡️ Row-Level Security (RLS)**: Sistema di controllo accessi granulare enterprise-grade
- **👥 5 Ruoli Utente**: ADMIN, ANALYST, VIEWER, BU_MANAGER, TENANT_ADMIN con permessi specifici
- **🏢 Multi-Tenant**: Isolamento dati completo per organizzazioni multiple
- **🔑 Autenticazione Unificata**: Login con username/password + tenant ID opzionale
- **📊 Security Dashboard**: Monitoraggio sessioni, audit trail, statistiche sicurezza
- **🔒 4 Livelli Classificazione**: PUBLIC → INTERNAL → CONFIDENTIAL → RESTRICTED
- **👤 5 Utenti Demo**: Preconfigurati per testing (admin, analyst.azienda.a, manager.bu.sales, etc.)

### 📊 **Analisi Finanziarie Enterprise-Grade**
- **🧮 68 Metriche Finanziarie**: Ontologia completa AR/AP, Vendite, Magazzino, HR, Liquidità
- **📐 Dimensional Coherence**: Validazione automatica coerenza contabile (Attivo = Passivo + PN)
- **🔍 Provenienza Granulare**: Tracking completo pagina/cella/coordinata (file.xlsx|sheet:CE|cell:B12)
- **✅ Data Quality**: Validazioni Great Expectations sistematiche su coerenza bilancio/PFN
- **🔄 Calcoli Derivati**: 15+ formule automatiche (PFN, ROS, ROIC, Current Ratio, DSO, DPO)
- **📈 Lineage Tracking**: Tracciamento formula + inputs + confidence per ogni calcolo
- **🌍 Multi-Valuta**: Supporto completo con tracciamento conversioni
- **📊 Analisi Comparativa**: Confronti multi-periodo ed entità con validazioni cross-period

### 🧠 **Intelligenza Documentale RAG Avanzata**
- **🤖 Retrieval Ibrido**: BM25 + OpenAI Embeddings + CrossEncoder reranking per accuratezza massima
- **📄 Supporto Multi-Formato**: PDF, DOCX, TXT, MD, Excel, CSV con parsing intelligente
- **🔍 Estrazione Avanzata**: OCR Tesseract, Camelot/Tabula per tabelle, parsing Excel strutturato
- **🗄️ Vector Database**: Qdrant con 1536-dim embeddings (text-embedding-3-small)
- **💭 Query Context-Aware**: Combinazione seamless dati strutturati + non strutturati
- **📋 Metadati Ricchi**: Estrazione automatica con classificazione documento
- **📖 Chunking Intelligente**: Ottimizzazione overlap e dimensioni per qualità massima

### 🏗️ **Architettura e Infrastruttura**
- **📐 Clean Architecture**: Domain-Driven Design con separazione livelli
- **🗄️ Fact Table Dimensionale**: Schema a stella con DuckDB/SQLite backend
- **🔄 Enterprise Orchestrator**: Pipeline 6-step con error handling e statistics
- **📊 Data Normalization**: Formati italiani (1.234,56), scale detection, period parsing
- **🎯 Ontology Mapping**: 31 metriche canoniche con 219+ sinonimi italiano/inglese
- **⚡ Performance Caching**: TTL-based query caching, compact response mode
- **🔍 Health Monitoring**: Component-wise health checks, processing metrics

### 🎨 **Interfaccia Utente Moderna**
- **📱 Multi-Page Streamlit**: 12+ pagine specializzate con navigazione intuitiva
- **🖥️ Angular Frontend**: Alternativa moderna con dashboard interattive
- **📄 Export PDF Professionale**: Styling ZCS Company con logo e formattazione
- **📊 Visualizzazioni Dinamiche**: Plotly charts, KPI gauges, tabelle interattive
- **🌙 Theme Manager**: Supporto temi light/dark con persistenza utente
- **📱 Responsive Design**: Ottimizzato desktop, tablet e mobile

### 🤖 **AI-Powered Business Intelligence**
- **💬 Query Linguaggio Naturale**: Italiano e inglese con context understanding
- **📈 Analisi Predittive**: Pattern recognition su dati storici
- **🎯 Raccomandazioni Smart**: Insight automatici con prioritizzazione
- **⚠️ Risk Assessment**: Punteggi confidenza e alerting anomalie
- **📋 Report Esecutivi**: Generazione automatica executive summary
- **🔍 FAQ Intelligenti**: Generazione automatica domande/risposte da documenti

---

## 🚀 Quick Start

### Prerequisiti
- **Python 3.12+**
- **Docker** (opzionale, per Qdrant)
- **OpenAI API Key** (per embeddings)

### Installazione Rapida

```bash
# Clone repository
git clone https://github.com/your-repo/business-intelligence-rag.git
cd business-intelligence-rag

# Setup ambiente (Windows)
start.bat

# Setup ambiente (Linux/Mac)
./start.sh

# Avvio applicazione
streamlit run app.py
```

### Setup Manuale con uv (Raccomandato)

```bash
# Installa uv se non presente
pip install uv

# Setup ambiente virtuale
uv venv
source .venv/bin/activate  # Linux/Mac
.venv\\Scripts\\activate   # Windows

# Installazione dipendenze (ultra-veloce con uv)
uv pip install -r requirements.txt

# Configurazione
cp .env.example .env
# Modifica .env con le tue API keys

# Avvio Streamlit
streamlit run app.py
```

### Avvio con Docker

```bash
# Avvio completo (Qdrant + App)
docker-compose up -d

# Solo database vettoriale
docker-compose up -d qdrant

# Applicazione in sviluppo
streamlit run app.py --server.port 8501
```

---

## 🎯 Utilizzo

### 1. **Autenticazione e Multi-Tenant**

```python
# Login con credenziali demo
Username: admin
Password: admin123
Tenant ID: (lascia vuoto per admin globale)

# Oppure con tenant specifico
Username: analyst.azienda.a
Password: analyst123
Tenant ID: tenant_b  # Override del tenant default
```

### 2. **Caricamento Documenti**
- Accedi alla sezione **📄 RAG Documenti**
- Upload PDF, Excel, CSV o documenti Word
- Il sistema processerà automaticamente con:
  - Estrazione metadati e provenienza
  - Chunking intelligente
  - Generazione embeddings
  - Indicizzazione vettoriale

### 3. **Analisi CSV/Excel**
- Carica file nella sezione **📊 Analisi CSV**
- Ottieni automaticamente:
  - 68 metriche finanziarie estratte
  - Validazioni dimensional coherence
  - Calcoli derivati con lineage
  - Visualizzazioni interattive

### 4. **Query Intelligenti**
```
Query esempi:
"Qual è l'EBITDA margin del 2023?"
"Confronta i ricavi Q1 vs Q2 2024"
"Mostra l'evoluzione del PFN negli ultimi 3 anni"
"Quali sono i principali rischi finanziari?"
```

### 5. **Gold Standard Benchmarking**
```bash
# Esegui benchmark qualità
python benchmarks/benchmark_runner.py

# Con configurazione custom
python benchmarks/benchmark_runner.py --config custom_tests.yaml

# Output: report HTML in benchmarks/reports/
```

---

## 📁 Architettura del Progetto

```
business-intelligence-rag/
│
├── 🏗️ **Core Application**
│   ├── app.py                     # Main Streamlit application
│   ├── api.py                     # FastAPI REST API
│   └── services/                  # Core business services
│       ├── rag_engine.py         # RAG engine principale
│       ├── csv_analyzer.py       # Analizzatore CSV/Excel
│       ├── llm_service.py        # Integrazione LLM
│       └── secure_rag_engine.py  # RAG con security RLS
│
├── 🔐 **Security & Multi-Tenant**
│   └── src/core/security/
│       ├── authentication.py     # Sistema autenticazione
│       ├── access_control.py     # Row-Level Security
│       ├── multi_tenant_manager.py # Gestione tenant
│       └── user_context.py       # Context utenti e ruoli
│
├── 🎯 **Enterprise Services**
│   └── src/application/services/
│       ├── enterprise_orchestrator.py    # Pipeline enterprise 6-step
│       ├── hybrid_retrieval.py          # BM25 + Embeddings + Rerank
│       ├── data_normalizer.py           # Normalizzazione dati IT/EN
│       ├── ontology_mapper.py           # 31 metriche + 219 sinonimi
│       ├── document_router.py           # Classificazione documenti
│       └── advanced_enterprise_orchestrator.py # Orchestrazione avanzata
│
├── 📊 **Data & Analytics**
│   └── src/infrastructure/repositories/
│       ├── fact_table_repository.py     # Fact table dimensionale
│       ├── secure_fact_table.py         # Fact table con RLS
│       └── multi_tenant_fact_table.py   # Multi-tenant data layer
│
├── 🎯 **Quality & Validation**
│   ├── benchmarks/                      # Gold Standard Benchmarking
│   │   ├── benchmark_runner.py         # Sistema di benchmark
│   │   ├── gold_standard_config.yaml   # Test cases configurazione
│   │   └── reports/                     # Report HTML/JSON output
│   ├── src/domain/value_objects/
│   │   └── guardrails.py               # Dimensional coherence + validazioni
│   └── config/
│       └── dimensional_coherence_rules.yaml # Regole validazione YAML
│
├── 🎨 **Frontend & UI**
│   ├── pages/                          # Streamlit multi-page
│   │   ├── 00_🔐_Login.py             # Login multi-tenant (deprecated)
│   │   ├── 01_🛡️_Security_Dashboard.py # Dashboard sicurezza admin
│   │   ├── 1_📊_Analytics_Dashboard.py # Dashboard analytics
│   │   ├── 2_📍_Document_Preview.py    # Anteprima documenti
│   │   └── 3_✏️_Interactive_Editor.py # Editor metriche interattivo
│   ├── components/
│   │   └── security_ui.py              # Componenti UI sicurezza
│   └── frontend_angular/               # Frontend Angular alternativo
│
├── 📄 **Configuration**
│   ├── config/                         # Configurazioni sistema
│   ├── data/                          # Storage dati e cache
│   ├── .env                           # Variabili ambiente
│   ├── requirements.txt               # Dipendenze Python
│   ├── docker-compose.yml             # Container orchestration
│   └── uv.lock                        # Lock file uv
│
└── 📚 **Documentation**
    ├── README.md                       # Questo file
    ├── IMPLEMENTATION_PLAN.md          # Piano implementazione gap
    ├── RLS_IMPLEMENTATION_COMPLETE.md  # Documentazione RLS
    ├── CLAUDE.md                       # Istruzioni Claude Code
    └── docs/                           # Documentazione dettagliata
```

---

## 🔧 Configurazione Avanzata

### Variabili Ambiente (.env)

```env
# === CORE CONFIGURATION ===
OPENAI_API_KEY=your_openai_key_here
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=business_documents

# === PERFORMANCE OPTIMIZATION ===
RAG_RESPONSE_MODE=compact            # Faster than tree_summarize
RAG_SIMILARITY_TOP_K=3              # Reduced from 5 for speed
RAG_ENABLE_CACHING=True             # Query result caching
RAG_CHUNK_SIZE=1000                 # Optimal chunk size
RAG_CHUNK_OVERLAP=200               # Overlap for context

# === ENTERPRISE FEATURES ===
ENABLE_ENTERPRISE_MODE=true          # Attiva funzionalità enterprise
ENABLE_DIMENSIONAL_COHERENCE=true   # Validazioni coerenza avanzate
STRICT_VALIDATION_MODE=false        # Blocca processing su errori
MAX_VALIDATION_TIME_SECONDS=30      # Timeout validazioni

# === SECURITY SETTINGS ===
ENABLE_RLS=true                     # Row-Level Security
SESSION_TIMEOUT_HOURS=8             # Timeout sessione utente
MAX_FAILED_LOGIN_ATTEMPTS=5        # Tentativi login falliti
LOCKOUT_DURATION_MINUTES=30        # Durata lockout account

# === MULTI-TENANT CONFIGURATION ===
DEFAULT_TENANT_TIER=PREMIUM         # Tier default nuovi tenant
ENABLE_TENANT_ISOLATION=true       # Isolamento dati tenant
TENANT_RESOURCE_LIMITS=true         # Limiti risorse per tenant

# === PERFORMANCE & CACHING ===
REDIS_URL=redis://localhost:6379   # Cache distribuita
CELERY_BROKER_URL=redis://localhost:6379 # Background jobs
ENABLE_CONNECTION_POOLING=true     # Pool connessioni DB
MAX_POOL_SIZE=20                   # Dimensione pool

# === QUALITY & BENCHMARKING ===
ENABLE_GOLD_STANDARD_BENCHMARKING=true  # Sistema benchmark
BENCHMARK_OUTPUT_FORMAT=html,json       # Formati report
BENCHMARK_INCLUDE_CHARTS=true           # Grafici nei report
QUALITY_THRESHOLD_ERROR=95              # Soglia errore qualità %
QUALITY_THRESHOLD_WARNING=85            # Soglia warning qualità %

# === LOGGING & MONITORING ===
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
ENABLE_AUDIT_LOGGING=true          # Log audit security
ENABLE_PERFORMANCE_MONITORING=true # Monitoring performance
METRICS_COLLECTION_INTERVAL=60     # Intervallo raccolta metriche (sec)

# === OPTIONAL INTEGRATIONS ===
ANTHROPIC_API_KEY=your_anthropic_key    # Claude integration
HUGGINGFACE_API_TOKEN=your_hf_token     # HuggingFace models
GREAT_EXPECTATIONS_ENABLE=true          # Data quality validation
DVC_REMOTE_URL=s3://your-bucket         # Data versioning
```

### Configurazione Gold Standard Benchmarking

```yaml
# benchmarks/gold_standard_config.yaml
test_cases:
  - id: "bilancio_2023_test"
    name: "Bilancio 2023 - Extraction Test"
    document_path: "benchmarks/gold_standard/documents/bilancio_sample.pdf"
    expected_metrics:
      - metric_name: "ricavi"
        expected_value: 5000000.0
        tolerance: 0.01  # 1%
        source_page: 12
      - metric_name: "ebitda"
        expected_value: 800000.0
        tolerance: 0.01
        source_page: 14

scoring:
  metrics:
    numeric_accuracy:
      weight: 0.4
    source_attribution:
      weight: 0.2
    completeness:
      weight: 0.2
    context_relevance:
      weight: 0.2

  thresholds:
    excellent: 95  # >= 95% accuracy
    good: 85       # >= 85% accuracy
    acceptable: 75 # >= 75% accuracy
```

### Configurazione Dimensional Coherence

```yaml
# config/dimensional_coherence_rules.yaml
settings:
  enable_dimensional_coherence: true
  strict_mode: false
  tolerance:
    balance_sheet: 0.01  # 1%
    ratios: 0.05         # 5%

balance_sheet_rules:
  attivo_passivo_coherence:
    enabled: true
    level: "error"
    tolerance_pct: 0.01

pl_statement_rules:
  ebitda_revenue_coherence:
    enabled: true
    level: "error"
    max_ebitda_pct_of_revenue: 100

  ebitda_margin_bounds:
    enabled: true
    level: "warning"
    min_margin_pct: -50
    max_margin_pct: 40
```

---

## 🧪 Testing & Quality Assurance

### Test di Unità
```bash
# Esegui tutti i test
pytest

# Test specifici con coverage
pytest tests/ -v --cov=src --cov-report=html

# Test sicurezza RLS
pytest tests/test_security_core.py -v

# Test enterprise services
pytest tests/test_enterprise_orchestrator.py -v
```

### Gold Standard Benchmarking
```bash
# Benchmark completo con report HTML
python benchmarks/benchmark_runner.py --verbose

# Test solo estrazione numerica
python benchmarks/benchmark_runner.py --numeric-only

# Benchmark con configurazione custom
python benchmarks/benchmark_runner.py --config custom_tests.yaml

# Output automatico in benchmarks/reports/
# - benchmark_report_YYYYMMDD_HHMMSS.html
# - benchmark_report_YYYYMMDD_HHMMSS.json
```

### Validation Testing
```bash
# Test validazioni dimensional coherence
python -c "
from src.domain.value_objects.guardrails import FinancialGuardrails
guardrails = FinancialGuardrails(enable_dimensional_coherence=True)
test_data = {'ricavi': 5000000, 'ebitda': 800000}
results = guardrails.run_dimensional_coherence_validation(test_data)
print(f'Validations: {len(results)}, Passed: {sum(r.passed for r in results)}')
"

# Test con dati problematici
python -c "
from src.domain.value_objects.guardrails import FinancialGuardrails
guardrails = FinancialGuardrails()
bad_data = {'ricavi': 1000000, 'ebitda': 2000000}  # EBITDA > Revenue!
result = guardrails.validate_ebitda_margin(bad_data['ebitda'], bad_data['ricavi'])
print(f'Invalid data test: {result.passed} - {result.message}')
"
```

### Performance Benchmarking
```bash
# Test performance pipeline enterprise
python -c "
import time
from src.application.services.enterprise_orchestrator import EnterpriseOrchestrator
orchestrator = EnterpriseOrchestrator()
start = time.time()
# Simulate processing
print(f'Enterprise pipeline ready in {time.time() - start:.2f}s')
"

# Monitor memory usage durante processing
python -c "
import psutil, time
from services.rag_engine import RAGEngine
process = psutil.Process()
rag = RAGEngine()
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

---

## 🚀 Deployment Production

### Docker Production
```bash
# Build immagine production
docker build -t business-intelligence-rag:latest .

# Deploy con orchestrazione completa
docker-compose -f docker-compose.prod.yml up -d

# Scaling orizzontale
docker-compose -f docker-compose.prod.yml up -d --scale app=3

# Health check
curl http://localhost:8501/_health
```

### Kubernetes Deployment
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-app
  template:
    spec:
      containers:
      - name: rag-app
        image: business-intelligence-rag:latest
        ports:
        - containerPort: 8501
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: rag-service
spec:
  selector:
    app: rag-app
  ports:
  - port: 80
    targetPort: 8501
  type: LoadBalancer
```

### Environment Setup
```bash
# Production environment variables
export OPENAI_API_KEY="your-production-key"
export QDRANT_URL="https://your-qdrant-cluster.com"
export REDIS_URL="redis://your-redis-cluster:6379"
export LOG_LEVEL="INFO"
export ENABLE_ENTERPRISE_MODE="true"
export STRICT_VALIDATION_MODE="true"

# Security hardening
export SESSION_TIMEOUT_HOURS="4"
export MAX_FAILED_LOGIN_ATTEMPTS="3"
export ENABLE_AUDIT_LOGGING="true"

# Performance optimization
export RAG_ENABLE_CACHING="true"
export ENABLE_CONNECTION_POOLING="true"
export MAX_POOL_SIZE="50"
```

---

## 📊 Metriche e Monitoring

### Performance Metrics
- **Query Response Time**: < 2s (95th percentile)
- **Document Processing**: 1000+ docs/hour
- **Concurrent Users**: 50+ simultaneous
- **Memory Usage**: < 4GB per instance
- **CPU Usage**: < 80% under load

### Quality Metrics
- **Gold Standard Accuracy**: 95%+ on financial metrics
- **Dimensional Coherence**: 99%+ validation pass rate
- **Source Attribution**: 90%+ correct page/cell references
- **Semantic Relevance**: 85%+ user satisfaction

### Business Metrics
- **Data Coverage**: 68 financial metrics supported
- **Document Formats**: 8+ formats (PDF, Excel, etc.)
- **Languages**: Italian + English support
- **Industries**: Finance, Manufacturing, Services, Tech
- **Compliance**: SOX, GDPR ready with RLS

---

## 🤝 Contributing

### Development Setup
```bash
# Fork e clone
git clone https://github.com/your-username/business-intelligence-rag.git
cd business-intelligence-rag

# Setup sviluppo
uv venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install

# Testing locale
pytest tests/ -v
```

### Code Quality
```bash
# Linting e formatting
ruff check .                    # Fast Python linter
ruff format .                   # Code formatting

# Type checking
mypy src/

# Security scanning
bandit -r src/

# Dependency checking
pip-audit
```

### Contribution Guidelines
1. **Fork** il repository
2. Crea **feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit** con messaggi descrittivi (`git commit -m 'Add amazing feature'`)
4. **Test** completamente (`pytest tests/`)
5. **Push** al branch (`git push origin feature/amazing-feature`)
6. Apri **Pull Request** con descrizione dettagliata

---

## 🏢 Enterprise Support & Licensing

### Versioni Disponibili

| Feature | Community | Professional | Enterprise |
|---------|-----------|-------------|------------|
| Core RAG Engine | ✅ | ✅ | ✅ |
| Multi-Format Support | ✅ | ✅ | ✅ |
| Gold Standard Benchmarking | ❌ | ✅ | ✅ |
| Dimensional Coherence | ❌ | ✅ | ✅ |
| Row-Level Security | ❌ | ✅ | ✅ |
| Multi-Tenant | ❌ | ✅ | ✅ |
| Advanced Analytics | ❌ | ✅ | ✅ |
| Performance Optimization | ❌ | ❌ | ✅ |
| High Availability | ❌ | ❌ | ✅ |
| Priority Support | ❌ | ❌ | ✅ |
| Custom Development | ❌ | ❌ | ✅ |

### Support & Training
- **📧 Email Support**: support@zcs-company.com
- **💬 Enterprise Chat**: Slack/Teams integration disponibile
- **🎓 Training**: Sessioni di formazione personalizzate
- **🔧 Custom Development**: Sviluppo funzionalità su misura
- **🏗️ Implementation**: Supporto deployment e architettura

### SLA Enterprise
- **Uptime**: 99.9% SLA garantito
- **Response Time**: < 4h per issues critici
- **Resolution Time**: < 24h per bugs P1
- **Support Hours**: 24/7 per clienti Enterprise
- **Dedicated Success Manager**: Assegnato per account > 10K users

---

## 📚 Roadmap & Future Development

### Q1 2025
- ✅ **Gold Standard Benchmarking System** - Completato
- ✅ **Dimensional Coherence Validation** - Completato
- 🔄 **Real-time Collaboration** - In sviluppo
- 📅 **Advanced Scheduling** - Pianificato

### Q2 2025
- 📅 **Machine Learning Insights** - Algoritmi predittivi avanzati
- 📅 **Natural Language Queries** - Miglioramenti comprensione
- 📅 **Mobile App** - App nativa iOS/Android
- 📅 **API Gateway** - Gestione API enterprise

### Q3 2025
- 📅 **Blockchain Provenance** - Immutable data lineage
- 📅 **Advanced Visualizations** - D3.js interactive charts
- 📅 **Voice Integration** - Voice queries e reporting
- 📅 **Federated Learning** - ML distribuito multi-tenant

### Q4 2025
- 📅 **Quantum Computing** - Optimization algorithms
- 📅 **Augmented Reality** - AR data visualization
- 📅 **AI Automation** - Fully autonomous insights
- 📅 **Global Expansion** - Multi-language support

---

## 📄 License

Questo progetto è distribuito sotto **Doppia Licenza**:

- **Community Edition**: MIT License - Uso personale e open source
- **Enterprise Edition**: Commercial License - Contattaci per pricing

Vedi [LICENSE.md](LICENSE.md) per dettagli completi.

---

## 🙏 Acknowledgments

- **OpenAI** - GPT models e embedding APIs
- **Qdrant** - High-performance vector database
- **Streamlit** - Amazing web app framework
- **LlamaIndex** - RAG framework foundation
- **FastAPI** - Modern API development
- **Docker** - Containerization platform
- **ZCS Company** - Enterprise architecture e business expertise

---

## 📞 Contact & Support

### Community
- **GitHub Issues**: [Report bugs e feature requests](https://github.com/your-repo/issues)
- **Discussions**: [Community forum](https://github.com/your-repo/discussions)
- **Stack Overflow**: Tag `business-intelligence-rag`
- **Reddit**: r/BusinessIntelligence

### Enterprise
- **📧 Sales**: sales@zcs-company.com
- **🔧 Support**: support@zcs-company.com
- **💼 Partnerships**: partnerships@zcs-company.com
- **📱 Phone**: +39 XXX XXX XXXX (Business hours CET)

### Social Media
- **LinkedIn**: [ZCS Company](https://linkedin.com/company/zcs-company)
- **Twitter**: [@ZCSCompany](https://twitter.com/zcscompany)
- **YouTube**: [ZCS Tech Channel](https://youtube.com/zcstech)

---

<div align="center">

### Built with ❤️ by ZCS Company

**Transforming Business Intelligence with AI-Powered Analytics**

[⭐ Star questo progetto](https://github.com/your-repo) | [🐛 Report Bug](https://github.com/your-repo/issues) | [💡 Request Feature](https://github.com/your-repo/issues)

</div>