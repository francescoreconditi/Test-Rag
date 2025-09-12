# Procedura di Upload File nel Sistema RAG - Documentazione Tecnica Dettagliata

## Indice
1. [Introduzione e Teoria RAG](#introduzione-e-teoria-rag)
2. [Best Practices per Upload in RAG](#best-practices-per-upload-in-rag)
3. [Architettura del Sistema](#architettura-del-sistema)
4. [Implementazione Upload nell'Interfaccia Streamlit](#implementazione-upload-nellinterfaccia-streamlit)
5. [Parser per Diversi Formati](#parser-per-diversi-formati)
6. [Chunking e Embedding Generation](#chunking-e-embedding-generation)
7. [Storage Vettoriale in Qdrant](#storage-vettoriale-in-qdrant)
8. [Gestione Errori e Ottimizzazioni](#gestione-errori-e-ottimizzazioni)

---

## Introduzione e Teoria RAG

### Cos'è un sistema RAG (Retrieval-Augmented Generation)

Un sistema RAG combina le capacità di:
1. **Retrieval (Recupero)**: Ricerca semantica di informazioni rilevanti da una base di conoscenza
2. **Augmentation (Arricchimento)**: Integrazione del contesto recuperato nel prompt
3. **Generation (Generazione)**: Produzione di risposte contestualizzate tramite LLM

### Perché l'Upload è Cruciale in RAG

L'upload di documenti è il primo e più critico passaggio in un sistema RAG perché:
- **Qualità dei dati**: La qualità delle risposte dipende direttamente dalla qualità dell'estrazione del testo
- **Preservazione del contesto**: È essenziale mantenere la struttura e il contesto dei documenti
- **Indicizzazione efficiente**: Un buon chunking determina la precisione del retrieval
- **Metadati**: Permettono filtering avanzato e tracciabilità delle fonti

---

## Best Practices per Upload in RAG

### 1. Parsing Intelligente per Formato
Ogni formato richiede un approccio specifico:
- **PDF**: OCR fallback per documenti scansionati
- **Excel/CSV**: Preservazione struttura tabellare
- **Word**: Estrazione stili e formattazione
- **Immagini**: OCR multilingua

### 2. Chunking Semantico
- Chunk di dimensione ottimale (512-1024 tokens)
- Overlap del 10-20% tra chunk consecutivi
- Rispetto dei confini semantici (paragrafi, sezioni)

### 3. Embedding di Qualità
- Modelli specializzati (text-embedding-3-small)
- Batch processing per efficienza
- Caching per evitare ri-computazioni

### 4. Metadati Ricchi
- Source tracking completo
- Timestamp di indicizzazione
- Tipo di documento e formato
- Informazioni strutturali (pagine, fogli, tabelle)

---

## Architettura del Sistema

### Flusso Completo di Upload

```
[Streamlit UI] → [File Upload] → [Temp Storage] → [RAG Engine] → [Document Parser] → [Chunking] → [Embedding] → [Qdrant]
```

### Componenti Principali

1. **Frontend (Streamlit)**: `app.py`
2. **RAG Engine**: `services/rag_engine.py`
3. **Parser Specializzati**: `src/application/parsers/`, `src/application/services/format_parsers.py`
4. **Vector Store**: Qdrant con configurazione in `config/settings.py`

---

## Implementazione Upload nell'Interfaccia Streamlit

### Widget di Upload (`app.py:578-583`)

```python
# File: app.py (riga 578-583)
uploaded_files = st.file_uploader(
    "Scegli documenti per l'analisi",
    type=["pdf", "txt", "docx", "md", "json", "csv", "xls", "xlsx", "jpg", "jpeg", "png"],
    accept_multiple_files=True,
    help="Carica report aziendali, contratti, CSV con dati finanziari, file Excel, immagini con OCR, o qualsiasi documento rilevante",
)
```

**Caratteristiche chiave**:
- **Multi-file support**: `accept_multiple_files=True` permette upload batch
- **Formati supportati**: PDF, Office, immagini, testo, dati strutturati
- **Help integrato**: Guida l'utente sui formati accettati

### Gestione File Temporanei e Permanenti (`app.py:632-646`)

```python
# File: app.py (riga 632-646)
# Save uploaded files permanently for PDF viewing
for uploaded_file in uploaded_files:
    # Save temporarily for processing
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        file_paths.append(tmp_file.name)
        original_names.append(uploaded_file.name)

    # Also save permanently for PDF viewer
    permanent_path = docs_dir / uploaded_file.name
    with open(permanent_path, "wb") as f:
        uploaded_file.seek(0)  # Reset file pointer
        f.write(uploaded_file.getbuffer())
    permanent_paths.append(str(permanent_path))
```

**Strategia dual-path**:
- **File temporanei**: Per processing immediato
- **File permanenti**: Per visualizzazione PDF e riferimenti futuri
- **Preservazione nomi originali**: Migliore UX e tracciabilità

### Chiamata al RAG Engine per Indicizzazione (`app.py:655`)

```python
# File: app.py (riga 655)
rag_engine = st.session_state.services["rag_engine"]
# Index documents with original names and permanent paths
results = rag_engine.index_documents(
    file_paths=file_paths,
    original_names=original_names,
    permanent_paths=permanent_paths,
    force_prompt_type=force_prompt_type,
    csv_analyzer=csv_analyzer
)
```

---

## Parser per Diversi Formati

### Metodo Principale di Routing (`services/rag_engine.py:287-310`)

```python
# File: services/rag_engine.py (riga 287-310)
# Load document based on file type
if path.suffix.lower() == ".pdf":
    documents = self._load_pdf(file_path, metadata)
elif path.suffix.lower() in [".txt", ".md"]:
    documents = self._load_text(file_path, metadata)
elif path.suffix.lower() in [".docx", ".doc"]:
    documents = self._load_docx(file_path, metadata)
elif path.suffix.lower() == ".json":
    # JSON files are loaded as text documents
    documents = self._load_text(file_path, metadata)
elif path.suffix.lower() == ".csv" and csv_analyzer:
    # CSV files are analyzed and converted to structured documents
    documents = self._load_csv_with_analysis(file_path, csv_analyzer, metadata)
elif path.suffix.lower() == ".csv":
    # Basic CSV loading without analysis
    documents = self._load_csv_basic(file_path, metadata)
elif path.suffix.lower() in [".xls", ".xlsx"]:
    # Excel files are converted to documents
    documents = self._load_excel(file_path, metadata)
elif path.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]:
    # Image files are processed with OCR
    documents = self._load_image(file_path, metadata)
else:
    documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
```

### Parser PDF con OCR Fallback (`services/rag_engine.py:540-614`)

```python
# File: services/rag_engine.py (riga 540-580)
def _load_pdf(self, file_path: str, metadata: Optional[dict[str, Any]] = None) -> list[Document]:
    """Load and parse PDF documents with enhanced text extraction."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        documents = []
        total_extracted_text = ""

        logger.info(f"Processing PDF: {file_path} with {len(reader.pages)} pages")

        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                page_text_length = len(text.strip())
                total_extracted_text += text

                logger.debug(f"Page {i + 1}: extracted {page_text_length} characters")

                if text.strip():
                    doc = Document(
                        text=text,
                        metadata={
                            "source": file_path,
                            "page_number": i + 1,
                            "total_pages": len(reader.pages),
                        },
                    )
                    if metadata:
                        doc.metadata.update(metadata)
                    documents.append(doc)

            except Exception as e:
                logger.warning(f"Failed to extract text from page {i+1}: {str(e)}")
                # Try OCR as fallback
                try:
                    ocr_text = self._ocr_pdf_page(file_path, i)
                    if ocr_text.strip():
                        doc = Document(
                            text=ocr_text,
                            metadata={
                                "source": file_path,
                                "page_number": i + 1,
                                "extraction_method": "ocr",
                            },
                        )
                        documents.append(doc)
                except Exception as ocr_e:
                    logger.error(f"OCR also failed for page {i+1}: {str(ocr_e)}")
```

**Caratteristiche avanzate**:
- **Estrazione testo nativo**: Prima scelta per performance
- **OCR fallback automatico**: Per pagine scansionate
- **Logging dettagliato**: Per debugging e monitoring
- **Metadati per pagina**: Tracciabilità completa

### Parser Excel Avanzato (`src/application/parsers/excel_parser.py`)

```python
# File: src/application/parsers/excel_parser.py (riga 38-100)
@dataclass
class CellMetadata:
    """Metadati completi per una singola cella."""

    sheet_name: str
    cell_reference: str  # Es: "A1", "B12"
    row: int
    column: int
    value: Any
    formula: Optional[str] = None
    comment: Optional[str] = None
    number_format: Optional[str] = None
    data_type: Optional[str] = None
    is_merged: bool = False
    merge_range: Optional[str] = None
    hyperlink: Optional[str] = None
    font_bold: bool = False
    fill_color: Optional[str] = None

    def to_source_ref(self, file_path: str) -> str:
        """Genera source reference per questa cella."""
        return f"{file_path}|sheet:{self.sheet_name}|cell:{self.cell_reference}"

@dataclass
class SheetMetadata:
    """Metadati completi per un singolo foglio."""

    name: str
    index: int
    visible: bool
    protection: bool
    used_range: str  # Es: "A1:Z100"
    max_row: int
    max_column: int
    tables: list[TableMetadata] = field(default_factory=list)
    named_ranges: dict[str, str] = field(default_factory=dict)
    charts_count: int = 0
    pivot_tables_count: int = 0
    formulas_count: int = 0
    comments_count: int = 0
    merged_cells_ranges: list[str] = field(default_factory=list)
```

**Features avanzate Excel**:
- **Preservazione formule**: Mantiene logica business
- **Celle unite**: Gestione corretta layout complessi
- **Named ranges**: Supporto riferimenti Excel
- **Metadati ricchi**: Per ricostruzione completa

### Parser CSV con Analisi Automatica (`services/rag_engine.py:1714-1801`)

```python
# File: services/rag_engine.py (riga 1714-1760)
def _load_csv_with_analysis(
    self, file_path: str, csv_analyzer, metadata: Optional[dict[str, Any]] = None
) -> list[Document]:
    """Load CSV file with automatic analysis and insights generation."""
    from pathlib import Path
    import pandas as pd

    try:
        # Read CSV
        df = pd.read_csv(file_path)
        file_name = Path(file_path).name

        # Analyze CSV with csv_analyzer
        analysis = csv_analyzer.analyze(df)
        insights = csv_analyzer.generate_insights(df, analysis)

        documents = []

        # 1. Create metadata document
        metadata_text = f"""
        File CSV: {file_name}
        Tipo di dati: Dati tabellari strutturati
        Righe totali: {len(df)}
        Colonne totali: {len(df.columns)}

        Colonne disponibili:
        {', '.join(df.columns.tolist())}

        Tipi di dati per colonna:
        {df.dtypes.to_string()}

        Statistiche riassuntive:
        {df.describe().to_string() if not df.empty else 'N/A'}

        Insights automatici:
        {insights}
        """

        doc_metadata = {
            "source": file_name,
            "type": "csv_metadata",
            "row_count": len(df),
            "column_count": len(df.columns),
        }
        if metadata:
            doc_metadata.update(metadata)

        documents.append(Document(text=metadata_text.strip(), metadata=doc_metadata))

        # 2. Create data chunks for better searchability
        chunk_size = 50
        for i in range(0, len(df), chunk_size):
            chunk_df = df.iloc[i : i + chunk_size]
            chunk_text = f"Dati CSV da riga {i+1} a {min(i+chunk_size, len(df))}:\n"
            chunk_text += chunk_df.to_string()

            chunk_metadata = {
                "source": file_name,
                "type": "csv_data_chunk",
                "chunk_start": i + 1,
                "chunk_end": min(i + chunk_size, len(df)),
            }
```

**Strategia CSV**:
- **Analisi automatica**: Statistiche e insights
- **Chunking intelligente**: 50 righe per chunk
- **Preservazione struttura**: Mantiene relazioni colonne

### Parser Immagini con OCR (`services/rag_engine.py:1989-2030`)

```python
# File: services/rag_engine.py (riga 1989-2015)
def _load_image(self, file_path: str, metadata: Optional[dict[str, Any]] = None) -> list[Document]:
    """Load image file and convert to text using OCR."""
    from pathlib import Path

    try:
        file_name = Path(file_path).name

        # Use the existing image parser
        try:
            from src.application.services.format_parsers import ImageParser

            parser = ImageParser(ocr_language="ita+eng")  # Italian + English

            # Parse image with OCR
            parsed_content = parser.parse(file_path)

            # Extract OCR text
            ocr_text = parsed_content.data.get("text", "").strip()

            if not ocr_text:
                ocr_text = f"[IMMAGINE] Il file '{file_name}' non contiene testo riconoscibile tramite OCR."

            # Extract metadata
            image_metadata = parsed_content.metadata or {}

            # Create document
            doc_metadata = {
                "source": file_name,
                "type": "image_ocr",
                "ocr_confidence": image_metadata.get("confidence", 0),
                "image_dimensions": f"{image_metadata.get('width', 0)}x{image_metadata.get('height', 0)}",
                "file_type": Path(file_path).suffix.lower(),
            }
```

**OCR Features**:
- **Multilingua**: Italiano + Inglese
- **Confidence tracking**: Per validazione qualità
- **Metadata immagine**: Dimensioni e formato
- **Fallback graceful**: Messaggio quando OCR fallisce

---

## Chunking e Embedding Generation

### Configurazione Chunking (`config/settings.py:28-29`)

```python
# File: config/settings.py (riga 28-29)
chunk_size: int = Field(default=512, env="CHUNK_SIZE")
chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
```

### Processo di Chunking (`services/rag_engine.py:329-334`)

```python
# File: services/rag_engine.py (riga 329-334)
# Parse documents into nodes
parser = SimpleNodeParser.from_defaults()
nodes = parser.get_nodes_from_documents(documents)

# Add nodes to index
self.index.insert_nodes(nodes)
```

**LlamaIndex SimpleNodeParser**:
- **Chunk size**: 512 tokens (ottimale per embedding)
- **Overlap**: 50 tokens (10% per contesto)
- **Automatic splitting**: Rispetta confini semantici

### Configurazione Embedding (`services/rag_engine.py:74-82`)

```python
# File: services/rag_engine.py (riga 74-82)
# Configure global LlamaIndex settings
Settings.llm = OpenAI(
    model=settings.llm_model,
    temperature=settings.temperature,
    max_tokens=settings.max_tokens,
    api_key=settings.openai_api_key,
)
Settings.embed_model = OpenAIEmbedding(
    model=settings.embedding_model,  # text-embedding-3-small
    api_key=settings.openai_api_key
)
Settings.chunk_size = settings.chunk_size
Settings.chunk_overlap = settings.chunk_overlap
```

**Modello di Embedding**:
- **OpenAI text-embedding-3-small**: 1536 dimensioni
- **Ottimizzato per**: Testo multilingua
- **Performance**: Fast e accurato

### Metadati per Chunk (`services/rag_engine.py:313-327`)

```python
# File: services/rag_engine.py (riga 313-327)
# Add metadata to documents
for doc in documents:
    doc.metadata = doc.metadata or {}
    doc_metadata = {
        "source": display_name,  # Nome file leggibile
        "indexed_at": datetime.now().isoformat(),
        "file_type": path.suffix.lower(),
        "document_size": len(doc.text) if hasattr(doc, "text") else 0,
    }
    # Add permanent path for PDF viewing (only for PDFs)
    if permanent_path and path.suffix.lower() == ".pdf":
        doc_metadata["pdf_path"] = permanent_path

    doc.metadata.update(doc_metadata)
    if metadata:
        doc.metadata.update(metadata)
```

**Metadati essenziali**:
- **Source tracking**: Nome file originale
- **Timestamp**: Per versioning e audit
- **File type**: Per filtering
- **PDF path**: Per viewer integrato

---

## Storage Vettoriale in Qdrant

### Inizializzazione Vector Store (`services/rag_engine.py:85-95`)

```python
# File: services/rag_engine.py (riga 85-95)
# Use connection pool for Qdrant client
with self.connection_pool.get_connection() as client:
    self.client = client

# Create or recreate collection
self._setup_collection()

# Initialize vector store
self.vector_store = QdrantVectorStore(
    client=self.client, 
    collection_name=self.collection_name
)

# Initialize or load existing index
self._initialize_index()
```

### Configurazione Collection Qdrant (`services/rag_engine.py:144-157`)

```python
# File: services/rag_engine.py (metodo _setup_collection)
def _setup_collection(self):
    """Setup Qdrant collection with proper configuration."""
    try:
        # Create collection with vector configuration
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=1536,  # OpenAI text-embedding-3-small dimension
                distance=Distance.COSINE,  # Cosine similarity for semantic search
            ),
        )
        logger.info(f"Created new collection: {self.collection_name}")
    except Exception as e:
        logger.error(f"Error setting up collection: {str(e)}")
```

**Configurazione Qdrant**:
- **Dimensioni vettore**: 1536 (matching embedding model)
- **Distance metric**: Cosine (ottimale per testo)
- **Collection name**: Configurabile via env

### Inserimento Nodes nell'Index (`services/rag_engine.py:334`)

```python
# File: services/rag_engine.py (riga 334)
# Add nodes to index
self.index.insert_nodes(nodes)
```

**LlamaIndex gestisce automaticamente**:
- Generazione embeddings batch
- Upload a Qdrant
- Gestione ID univoci
- Retry su errori temporanei

---

## Gestione Errori e Ottimizzazioni

### Error Handling nell'Upload (`services/rag_engine.py:352-356`)

```python
# File: services/rag_engine.py (riga 352-356)
except Exception as e:
    results["failed_files"].append(file_path)
    results["errors"].append(f"Error indexing {file_path}: {str(e)}")
    logger.error(f"Error indexing {file_path}: {str(e)}")
```

### Connection Pool per Qdrant (`services/rag_engine.py:66-67`)

```python
# File: services/rag_engine.py (riga 66-67)
# Use connection pool for Qdrant
self.connection_pool = get_qdrant_pool()
self.query_optimizer = get_query_optimizer()
```

**Ottimizzazioni Performance**:
- **Connection pooling**: Riuso connessioni
- **Query optimizer**: Cache e batching
- **Async processing**: Per UI responsive

### Query Cache (`services/rag_engine.py:59-62`)

```python
# File: services/rag_engine.py (riga 59-62)
# Initialize query cache if enabled (with tenant namespace if multi-tenant)
cache_namespace = f"tenant_{tenant_context.tenant_id}" if tenant_context else None
self.query_cache = (
    QueryCache(ttl_seconds=3600, namespace=cache_namespace) if settings.rag_enable_caching else None
)
```

**Caching Strategy**:
- **TTL**: 1 ora default
- **Namespace**: Per multi-tenancy
- **Configurabile**: Via environment

### Batch Processing per Excel/CSV (`services/rag_engine.py:1935-1942`)

```python
# File: services/rag_engine.py (riga 1935-1942)
# Create additional documents for remaining data
chunk_size = 100
for i in range(chunk_size, len(df), chunk_size):
    chunk_end = min(i + chunk_size, len(df))
    chunk_df = df.iloc[i:chunk_end]
    
    # Create chunk document
    # ...
```

**Chunking Strategy per dati tabellari**:
- **Chunk size**: 100 righe per documento
- **Preservazione header**: In ogni chunk
- **Metadati posizione**: Per ricostruzione

---

## Configurazione Ambiente

### Settings Principali (`.env`)

```env
# OpenAI Configuration
OPENAI_API_KEY=your-api-key
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4-turbo-preview

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=business_documents

# Chunking Configuration
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# Performance
RAG_RESPONSE_MODE=compact
RAG_SIMILARITY_TOP_K=10
RAG_ENABLE_CACHING=true
```

---

## Best Practices Implementate

### 1. **Gestione File Dual-Path**
- Temporanei per processing
- Permanenti per riferimento

### 2. **Parser Specializzati per Formato**
- PDF con OCR fallback
- Excel con preservazione formule
- CSV con analisi automatica
- Immagini con OCR multilingua

### 3. **Metadati Ricchi**
- Source tracking completo
- Timestamp per versioning
- Tipo documento per filtering
- Path permanenti per viewer

### 4. **Chunking Intelligente**
- Size ottimale (512 tokens)
- Overlap per contesto
- Rispetto confini semantici

### 5. **Performance Optimization**
- Connection pooling
- Query caching
- Batch processing
- Async operations

### 6. **Error Recovery**
- Fallback parsers
- OCR quando testo extraction fallisce
- Logging dettagliato
- Graceful degradation

---

## Conclusioni

Il sistema di upload implementato in questo progetto RAG rappresenta una soluzione completa e robusta che:

1. **Supporta tutti i formati comuni** con parser specializzati
2. **Preserva struttura e metadati** per retrieval accurato
3. **Ottimizza performance** con caching e pooling
4. **Gestisce errori gracefully** con fallback automatici
5. **Scala efficacemente** grazie a chunking e batching

La combinazione di LlamaIndex per l'orchestrazione, OpenAI per embeddings, e Qdrant per storage vettoriale crea un sistema production-ready per applicazioni RAG enterprise.

Le best practices implementate assicurano che ogni documento caricato sia processato nel modo più efficace possibile, massimizzando la qualità del retrieval e quindi delle risposte generate dal sistema.