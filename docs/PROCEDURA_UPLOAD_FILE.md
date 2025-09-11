# Procedura di Upload File - Documentazione Tecnica Dettagliata

## Indice
1. [Panoramica Generale](#panoramica-generale)
2. [Flusso di Upload nell'Interfaccia Utente](#flusso-di-upload-nellinterfaccia-utente)
3. [Processamento Backend](#processamento-backend)
4. [Analisi del Codice Sorgente](#analisi-del-codice-sorgente)
5. [Gestione degli Errori](#gestione-degli-errori)
6. [Formati Supportati](#formati-supportati)
7. [Ottimizzazioni e Performance](#ottimizzazioni-e-performance)

---

## Panoramica Generale

La procedura di upload file rappresenta il punto di ingresso principale per l'inserimento di documenti nel sistema RAG (Retrieval-Augmented Generation). Il processo è progettato per essere resiliente, scalabile e supportare multiple tipologie di documenti con parsing intelligente e memorizzazione vettoriale.

### Architettura del Sistema Upload

```
[UI Streamlit] → [Document Router] → [Parser Specifico] → [Vector Store] → [Qdrant DB]
      ↓               ↓                    ↓                 ↓
  File Upload    Classificazione    Estrazione Testo    Embedding Gen.
```

---

## Flusso di Upload nell'Interfaccia Utente

### 1. Interfaccia Streamlit (`app.py`)

**Localizzazione**: `app.py:100-150` (sezione upload)

```python
# Widget di upload principale
uploaded_file = st.file_uploader(
    "📄 Carica un documento",
    type=['pdf', 'csv', 'xlsx', 'xls', 'docx', 'txt', 'html', 'xml'],
    help="Formati supportati: PDF, Excel, Word, CSV, HTML, XML, TXT"
)
```

**Caratteristiche UI**:
- **Drag & Drop Support**: Interfaccia intuitiva con trascinamento file
- **Validazione Client-Side**: Controllo immediate del formato file
- **Progress Bar**: Indicatore visivo dello stato di processamento
- **Error Display**: Messaggi di errore user-friendly

### 2. Gestione File Temporanei

**Codice rilevante** (`app.py:155-170`):
```python
if uploaded_file is not None:
    # Salvataggio temporaneo sicuro
    temp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
    
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Validazione integrità file
    file_hash = hashlib.md5(uploaded_file.getbuffer()).hexdigest()
    st.session_state['last_uploaded_hash'] = file_hash
```

**Sicurezza**:
- **Hash MD5**: Per prevenire upload duplicati accidentali
- **Path Sanitization**: Prevenzione path traversal attacks
- **Temporary Storage**: File temporanei con pulizia automatica

---

## Processamento Backend

### 1. Document Router (`src/application/services/document_router.py`)

Il Document Router è il componente chiave che determina come processare ogni tipo di documento.

**Metodo principale**: `route_document(file_path: str) -> DocumentType`

```python
def route_document(self, file_path: str) -> DocumentType:
    """
    Classifica il documento e determina la strategia di parsing
    
    Returns:
        DocumentType: STRUCTURED, UNSTRUCTURED, o HYBRID
    """
    file_extension = Path(file_path).suffix.lower()
    
    # Mapping estensioni -> tipo documento
    structured_formats = {'.csv', '.xlsx', '.xls'}
    unstructured_formats = {'.pdf', '.docx', '.txt'}
    hybrid_formats = {'.html', '.xml'}
    
    if file_extension in structured_formats:
        return DocumentType.STRUCTURED
    elif file_extension in unstructured_formats:
        return DocumentType.UNSTRUCTURED
    else:
        return DocumentType.HYBRID
```

### 2. Parser Specifici per Tipo

#### A. Parser Strutturato - Excel/CSV

**File**: `src/application/parsers/excel_parser.py`

```python
class EnhancedExcelParser:
    def parse_excel_file(self, file_path: str) -> List[Document]:
        """
        Parsing avanzato di file Excel con riconoscimento automatico struttura
        
        Features:
        - Riconoscimento automatico header
        - Gestione celle unite
        - Estrazione metadati fogli
        - Preservazione formule
        """
        documents = []
        
        # Caricamento con pandas per performance
        excel_data = pd.read_excel(file_path, sheet_name=None, header=None)
        
        for sheet_name, df in excel_data.items():
            # Riconoscimento automatico header
            header_row = self._detect_header_row(df)
            
            # Estrazione dati strutturati
            structured_data = self._extract_structured_data(df, header_row)
            
            # Creazione documento con metadati
            document = Document(
                content=structured_data['text'],
                metadata={
                    'source': file_path,
                    'sheet_name': sheet_name,
                    'data_types': structured_data['types'],
                    'row_count': len(df),
                    'column_count': len(df.columns)
                }
            )
            documents.append(document)
            
        return documents
```

**Caratteristiche Avanzate Excel Parser**:
- **Auto-detection Headers**: Identifica automaticamente riga header
- **Data Type Inference**: Riconosce tipologie dati (date, numeri, testo)
- **Multi-sheet Support**: Gestione completa workbook multi-foglio
- **Formula Preservation**: Mantiene riferimenti formule quando possibile

#### B. Parser Non Strutturato - PDF

**File**: `src/application/services/pdf_processor.py`

```python
class AdvancedPDFProcessor:
    def process_pdf(self, file_path: str) -> List[Document]:
        """
        Processing PDF multi-modalità con OCR fallback
        
        Estrattori utilizzati:
        1. PyMuPDF (primary) - text nativo
        2. PDFPlumber (secondary) - tabelle e layout
        3. Tesseract OCR (fallback) - documenti scansionati
        """
        documents = []
        
        # Tentativo estrazione testo nativo
        try:
            pdf_doc = fitz.open(file_path)
            
            for page_num, page in enumerate(pdf_doc):
                # Estrazione testo nativo
                text_content = page.get_text()
                
                if self._is_scanned_page(text_content):
                    # Fallback OCR per pagine scansionate
                    text_content = self._ocr_extract(page)
                
                # Estrazione tabelle con PDFPlumber
                tables = self._extract_tables(file_path, page_num)
                
                document = Document(
                    content=f"{text_content}\n\n{tables}",
                    metadata={
                        'source': file_path,
                        'page_number': page_num + 1,
                        'extraction_method': 'native' if text_content else 'ocr',
                        'table_count': len(tables) if tables else 0
                    }
                )
                documents.append(document)
                
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            # Fallback completo a OCR
            return self._full_ocr_fallback(file_path)
            
        return documents
```

### 3. Chunking e Embedding Generation

**File**: `services/rag_engine.py:200-250`

```python
def _process_documents_for_storage(self, documents: List[Document]) -> List[Dict]:
    """
    Prepara i documenti per la memorizzazione vettoriale
    
    Steps:
    1. Text chunking intelligente
    2. Generazione embeddings
    3. Metadati enhancement
    4. Deduplicazione
    """
    processed_chunks = []
    
    for doc in documents:
        # Chunking semantico preservando contesto
        chunks = self._semantic_chunking(doc.content)
        
        for chunk_idx, chunk in enumerate(chunks):
            # Generazione embedding OpenAI
            embedding = self._generate_embedding(chunk.text)
            
            # Arricchimento metadati
            enhanced_metadata = {
                **doc.metadata,
                'chunk_index': chunk_idx,
                'chunk_size': len(chunk.text),
                'semantic_boundary': chunk.is_semantic_boundary,
                'upload_timestamp': datetime.utcnow().isoformat(),
                'content_hash': hashlib.sha256(chunk.text.encode()).hexdigest()
            }
            
            processed_chunks.append({
                'text': chunk.text,
                'embedding': embedding,
                'metadata': enhanced_metadata
            })
    
    return self._deduplicate_chunks(processed_chunks)
```

**Chunking Strategy**:
- **Semantic Chunking**: Mantiene coerenza semantica tra frasi
- **Overlap Strategy**: 20% overlap tra chunk consecutivi
- **Size Optimization**: Chunk da 512-1024 tokens per bilanciare contesto/performance
- **Boundary Detection**: Rispetta confini paragrafi e sezioni

### 4. Vector Storage (Qdrant)

**File**: `services/rag_engine.py:300-350`

```python
async def _store_in_vector_db(self, chunks: List[Dict]) -> bool:
    """
    Memorizzazione in Qdrant con gestione batch e retry
    """
    try:
        # Preparazione batch per performance
        batch_size = 100
        batches = [chunks[i:i+batch_size] for i in range(0, len(chunks), batch_size)]
        
        for batch in batches:
            points = []
            for chunk in batch:
                point = PointStruct(
                    id=uuid.uuid4().hex,
                    vector=chunk['embedding'],
                    payload=chunk['metadata']
                )
                points.append(point)
            
            # Upload batch con retry automatico
            await self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True  # Attende conferma scrittura
            )
            
        logger.info(f"Successfully stored {len(chunks)} chunks in vector DB")
        return True
        
    except Exception as e:
        logger.error(f"Vector storage failed: {e}")
        return False
```

---

## Analisi del Codice Sorgente

### Dependency Injection Pattern

**File**: `src/core/dependency_injection.py`

Il sistema utilizza un container DI per gestire le dipendenze tra componenti:

```python
class DIContainer:
    def __init__(self):
        self._services = {}
        self._singletons = {}
    
    def register_document_router(self):
        """Registrazione Document Router come singleton"""
        if 'document_router' not in self._singletons:
            self._singletons['document_router'] = DocumentRouter()
        return self._singletons['document_router']
```

### Error Handling e Resilience

**Pattern utilizzato**: Circuit Breaker con Exponential Backoff

```python
class ResilientUploadHandler:
    def __init__(self):
        self.retry_policy = ExponentialBackoff(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )
    
    @retry_with_backoff
    async def upload_with_retry(self, file_path: str):
        """Upload con retry automatico e circuit breaker"""
        try:
            return await self._perform_upload(file_path)
        except TemporaryError as e:
            # Retry per errori temporanei
            raise RetryableException(f"Temporary upload failure: {e}")
        except PermanentError as e:
            # Stop retry per errori permanenti
            raise FatalException(f"Permanent upload failure: {e}")
```

### Performance Monitoring

**File**: `src/core/logging_config.py`

```python
import time
from functools import wraps

def performance_monitor(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        duration = time.time() - start_time
        logger.info(f"{func.__name__} completed in {duration:.2f}s")
        
        # Metriche per monitoring
        if hasattr(st.session_state, 'performance_metrics'):
            st.session_state.performance_metrics[func.__name__] = duration
            
        return result
    return wrapper

# Utilizzo
@performance_monitor
def process_upload(file_path: str):
    # Logica upload...
    pass
```

---

## Gestione degli Errori

### Hierarchy degli Errori

```python
# src/domain/exceptions/business_exceptions.py

class UploadException(Exception):
    """Eccezione base per errori upload"""
    pass

class FileFormatNotSupportedException(UploadException):
    """Formato file non supportato"""
    def __init__(self, file_extension: str):
        super().__init__(f"File format '{file_extension}' not supported")
        self.file_extension = file_extension

class FileSizeExceededException(UploadException):
    """File troppo grande"""
    def __init__(self, file_size: int, max_size: int):
        super().__init__(f"File size {file_size}MB exceeds limit {max_size}MB")

class ParsingException(UploadException):
    """Errore durante parsing contenuto"""
    pass

class VectorStorageException(UploadException):
    """Errore memorizzazione vettoriale"""
    pass
```

### Error Recovery Strategies

```python
class UploadErrorRecoveryManager:
    def handle_upload_error(self, error: Exception, file_path: str):
        """
        Gestione intelligente errori con recovery automatico
        """
        if isinstance(error, FileFormatNotSupportedException):
            # Tentativo conversione formato
            return self._attempt_format_conversion(file_path)
            
        elif isinstance(error, ParsingException):
            # Fallback a parser alternativi
            return self._try_alternative_parsers(file_path)
            
        elif isinstance(error, VectorStorageException):
            # Retry con configurazione alternativa
            return self._retry_with_fallback_config(file_path)
            
        else:
            # Log e notifica errore generico
            logger.error(f"Unhandled upload error: {error}")
            raise error
```

---

## Formati Supportati

### Matrice Compatibilità

| Formato | Estensioni | Parser | Features Speciali |
|---------|------------|---------|-------------------|
| **PDF** | .pdf | PyMuPDF + OCR | OCR automatico, estrazione tabelle |
| **Excel** | .xlsx, .xls | Pandas + openpyxl | Multi-sheet, formule, grafici |
| **Word** | .docx | python-docx | Stili, immagini, tabelle |
| **CSV** | .csv | Pandas | Auto-delimiter detection |
| **HTML** | .html, .htm | BeautifulSoup | Struttura DOM, CSS parsing |
| **XML** | .xml | lxml | Schema validation, XPath |
| **Plain Text** | .txt | Built-in | Encoding detection |

### Configurazione Limiti

```python
# config/settings.py
UPLOAD_LIMITS = {
    'max_file_size_mb': 100,
    'max_files_per_session': 10,
    'allowed_extensions': ['.pdf', '.xlsx', '.docx', '.csv', '.html', '.xml', '.txt'],
    'virus_scan_enabled': True,
    'content_validation': True
}
```

---

## Ottimizzazioni e Performance

### 1. Chunking Parallelo

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def parallel_chunking(documents: List[Document]) -> List[Chunk]:
    """
    Chunking parallelo per documenti multipli
    """
    with ThreadPoolExecutor(max_workers=4) as executor:
        loop = asyncio.get_event_loop()
        
        tasks = [
            loop.run_in_executor(executor, chunk_document, doc)
            for doc in documents
        ]
        
        chunked_results = await asyncio.gather(*tasks)
        
    # Flatten results
    all_chunks = []
    for chunks in chunked_results:
        all_chunks.extend(chunks)
        
    return all_chunks
```

### 2. Batch Embedding Generation

```python
def batch_generate_embeddings(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """
    Generazione embeddings in batch per ottimizzazione API calls
    """
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        
        # Single API call per batch
        response = openai.Embedding.create(
            input=batch_texts,
            model="text-embedding-3-small"
        )
        
        batch_embeddings = [item['embedding'] for item in response['data']]
        embeddings.extend(batch_embeddings)
        
    return embeddings
```

### 3. Caching Strategy

```python
from functools import lru_cache
import hashlib

class DocumentCache:
    def __init__(self):
        self.cache = {}
    
    def get_cache_key(self, file_path: str) -> str:
        """Genera chiave cache basata su file path e timestamp"""
        stat = os.stat(file_path)
        key_data = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @lru_cache(maxsize=100)
    def get_parsed_document(self, cache_key: str, file_path: str):
        """Cache parsed documents per evitare re-parsing"""
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Parse e cache
        parsed_doc = self.parse_document(file_path)
        self.cache[cache_key] = parsed_doc
        
        return parsed_doc
```

---

## Monitoring e Observability

### Metriche Tracked

```python
class UploadMetrics:
    def __init__(self):
        self.metrics = {
            'total_uploads': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'avg_processing_time': 0,
            'file_type_distribution': {},
            'error_distribution': {}
        }
    
    def record_upload_success(self, file_type: str, processing_time: float):
        self.metrics['total_uploads'] += 1
        self.metrics['successful_uploads'] += 1
        self.metrics['file_type_distribution'][file_type] = \
            self.metrics['file_type_distribution'].get(file_type, 0) + 1
        
        # Rolling average processing time
        self._update_avg_processing_time(processing_time)
    
    def record_upload_failure(self, error_type: str):
        self.metrics['total_uploads'] += 1
        self.metrics['failed_uploads'] += 1
        self.metrics['error_distribution'][error_type] = \
            self.metrics['error_distribution'].get(error_type, 0) + 1
```

### Dashboard Monitoring

Nel sidebar Streamlit viene mostrato un pannello con le statistiche di upload in tempo reale:

```python
# app.py - Sidebar metrics
with st.sidebar:
    if st.session_state.get('upload_metrics'):
        st.subheader("📊 Upload Statistics")
        metrics = st.session_state.upload_metrics
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Uploads", metrics['total_uploads'])
            st.metric("Success Rate", 
                     f"{metrics['successful_uploads']/metrics['total_uploads']*100:.1f}%")
        
        with col2:
            st.metric("Avg Processing", f"{metrics['avg_processing_time']:.2f}s")
            st.metric("Failed Uploads", metrics['failed_uploads'])
```

---

## Conclusioni

La procedura di upload file rappresenta un sistema complesso e robusto che gestisce multiple tipologie di documento con parsing intelligente, gestione errori avanzata e ottimizzazioni performance. La separazione in livelli (UI → Router → Parser → Storage) garantisce modularità e manutenibilità del codice.

Le principali forze del sistema sono:
- **Resilienza**: Gestione errori multilivello con recovery automatico
- **Performance**: Chunking parallelo e batch processing
- **Scalabilità**: Architecture modulare con dependency injection
- **Monitoring**: Osservabilità completa con metriche real-time
- **Sicurezza**: Validazione file e sanitization input

Per ulteriori dettagli tecnici, consultare i file sorgente referenziati in questo documento.