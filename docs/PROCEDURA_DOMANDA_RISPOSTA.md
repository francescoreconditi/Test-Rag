# Procedura di Domanda e Risposta (Q&A) nel Sistema RAG

## Indice
1. [Teoria del Sistema Q&A in RAG](#teoria-del-sistema-qa-in-rag)
2. [Best Practices per Q&A Systems](#best-practices-per-qa-systems)
3. [Architettura del Sistema Q&A](#architettura-del-sistema-qa)
4. [Implementazione del Query Engine](#implementazione-del-query-engine)
5. [Modalità di Query Specializzate](#modalità-di-query-specializzate)
6. [Enterprise Mode e Advanced Features](#enterprise-mode-e-advanced-features)
7. [Interfaccia Utente e UX](#interfaccia-utente-e-ux)
8. [Ottimizzazioni Performance e Caching](#ottimizzazioni-performance-e-caching)

---

## Teoria del Sistema Q&A in RAG

### Cos'è un Sistema Question-Answering

Un sistema Q&A basato su RAG combina:
1. **Retrieval semantico**: Trova documenti rilevanti usando embedding vettoriali
2. **Context augmentation**: Arricchisce la query con informazioni contestuali
3. **LLM generation**: Genera risposte naturali basate sui documenti recuperati
4. **Source attribution**: Mantiene tracciabilità delle fonti utilizzate

### Componenti Chiave di un Q&A System

- **Query Understanding**: Comprende l'intento dell'utente e il dominio della domanda
- **Document Retrieval**: Ricerca semantica nei documenti indicizzati
- **Context Ranking**: Ordina i documenti per rilevanza
- **Answer Generation**: Sintetizza informazioni in risposta coerente
- **Source Tracking**: Mantiene riferimenti ai documenti originali

### Vantaggi del RAG vs LLM Puro

- **Informazioni aggiornate**: Accesso a documenti specifici dell'organizzazione
- **Riduzione allucinazioni**: Risposte basate su fonti verificabili
- **Tracciabilità**: Ogni risposta è supportata da documenti specifici
- **Personalizzazione**: Adattabile al dominio e ai dati aziendali

---

## Best Practices per Q&A Systems

### 1. Query Enhancement

- **Intent detection**: Riconosce automaticamente il tipo di domanda
- **Context injection**: Arricchisce query con informazioni contestuali
- **Language consistency**: Forza risposte in italiano
- **Domain specialization**: Applica prompt specializzati per settore

### 2. Retrieval Optimization

- **Similarity top-k**: Configurabile (1-10) per bilanciare qualità/performance
- **Multi-modal retrieval**: Supporta testo, CSV, Excel, PDF, immagini
- **Hybrid search**: Combina semantic search con keyword matching
- **Reranking**: Riordina risultati per massimizzare rilevanza

### 3. Answer Generation

- **Structured output**: Risposta + fonti + confidence score
- **Source attribution**: Ogni claim è tracciabile alla fonte
- **Confidence scoring**: Quantifica affidabilità della risposta
- **Error handling**: Gestione graceful di query ambigue o senza match

### 4. User Experience

- **Real-time feedback**: Spinner e progress indicators
- **Interactive sources**: Link cliccabili alle pagine specifiche
- **Export capabilities**: PDF generation per sessioni Q&A
- **Session persistence**: Mantiene storico conversazione

---

## Architettura del Sistema Q&A

### Flusso Completo

```
[User Query] → [Query Enhancement] → [Vector Search] → [Context Ranking] → [LLM Generation] → [Response + Sources]
                        ↓                    ↓                   ↓                   ↓
                [Intent Detection]   [Semantic Search]   [Source Attribution] [Answer Synthesis]
                        ↓                    ↓                   ↓                   ↓
                [Domain Analysis]    [Top-K Selection]   [Metadata Extraction] [Quality Control]
```

### Componenti Principali

1. **Query Processor** (`services/rag_engine.py:query`)
2. **Enterprise Orchestrator** (modalità avanzata)
3. **Context Manager** (gestione CSV/multi-source)
4. **Response Formatter** (`services/format_helper.py`)
5. **UI Controller** (`app.py:734-850`)
6. **Export System** (`src/presentation/streamlit/pdf_exporter.py`)

---

## Implementazione del Query Engine

### Metodo Base Query (`services/rag_engine.py:660-715`)

```python
# File: services/rag_engine.py (riga 660-715)
def query(
    self,
    query_text: str,
    top_k: int = 3,
    filters: Optional[dict[str, Any]] = None,
    analysis_type: Optional[str] = None,
) -> dict[str, Any]:
    """Query the indexed documents with optional specialized analysis."""
    try:
        if not self.index:
            return {"answer": "Nessun documento è stato ancora indicizzato.", "sources": [], "confidence": 0}

        # Check cache first if enabled
        if self.query_cache:
            cached_result = self.query_cache.get(query_text, top_k, analysis_type)
            if cached_result:
                logger.info(f"Returning cached result for query: {query_text[:50]}...")
                return cached_result

        # Create query engine with specific parameters
        # Using configurable response mode for performance optimization
        query_engine = self.index.as_query_engine(
            similarity_top_k=top_k or settings.rag_similarity_top_k,
            response_mode=settings.rag_response_mode,  # Configurable: compact, tree_summarize, simple
            verbose=settings.debug_mode,
            streaming=False,
        )

        # If analysis_type is specified, enhance the query with specialized context
        if analysis_type and analysis_type != "standard":
            query_text = self._enhance_query_with_analysis_type(query_text, analysis_type)

        # Aggiungi prompt per rispondere in italiano
        query_text_it = f"Per favore rispondi in italiano. {query_text}"

        # Execute query
        response = query_engine.query(query_text_it)

        # Extract source information
        sources = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                sources.append(
                    {"text": node.node.text[:200] + "...", "score": node.score, "metadata": node.node.metadata}
                )

        # If specialized analysis is requested, post-process the response
        if analysis_type and analysis_type != "standard":
            response_text = self._apply_specialized_analysis(str(response), sources, query_text, analysis_type)
        else:
            response_text = str(response)
```

**Caratteristiche del query engine**:
- **Cache integration**: Prima controlla cache per query ripetute
- **Configurable parameters**: Top-k e response mode da settings
- **Language consistency**: Forza risposte in italiano
- **Analysis type support**: Applicazione post-processing specializzato
- **Source extraction**: Estrazione automatica metadati fonte

### Query Engine Configuration (`services/rag_engine.py:681-686`)

```python
# File: services/rag_engine.py (riga 681-686)
# Create query engine with specific parameters
# Using configurable response mode for performance optimization
query_engine = self.index.as_query_engine(
    similarity_top_k=top_k or settings.rag_similarity_top_k,
    response_mode=settings.rag_response_mode,  # Configurable: compact, tree_summarize, simple
    verbose=settings.debug_mode,
    streaming=False,
)
```

**Response modes disponibili**:
- **compact**: Più veloce, concatena documenti direttamente
- **tree_summarize**: Più accurato, sintetizza ricorsivamente
- **simple**: Baseline, usa primo documento più rilevante

### Language Consistency (`services/rag_engine.py:692-693`)

```python
# File: services/rag_engine.py (riga 692-693)
# Aggiungi prompt per rispondere in italiano
query_text_it = f"Per favore rispondi in italiano. {query_text}"
```

**Forcing Italian responses**:
- Prepends ogni query con istruzione linguistica
- Garantisce consistency nelle risposte
- Importante per user experience italiana

---

## Modalità di Query Specializzate

### Query with Context (`services/rag_engine.py:1026-1045`)

```python
# File: services/rag_engine.py (riga 1026-1045)
def query_with_context(
    self, query_text: str, context_data: dict[str, Any], top_k: int = 2, analysis_type: Optional[str] = None
) -> dict[str, Any]:
    """Query with additional context from CSV analysis."""
    try:
        # Enhance query with context
        enhanced_query = f"""
        Basandoti sul seguente contesto di dati aziendali:
        {self._format_context(context_data)}

        Domanda: {query_text}

        Per favore fornisci una risposta dettagliata considerando sia i documenti che i dati aziendali forniti. Rispondi in italiano.
        """

        return self.query(enhanced_query, top_k=top_k, analysis_type=analysis_type)

    except Exception as e:
        logger.error(f"Error in query with context: {str(e)}")
        return {"answer": f"Error processing query: {str(e)}", "sources": [], "confidence": 0}
```

**Context enhancement features**:
- **Multi-source integration**: Combina documenti RAG con dati CSV
- **Structured context**: Formato leggibile per LLM
- **Reduced top-k**: Default a 2 per query più focalizzate con contesto

### Context Formatting (`services/rag_engine.py:1047-1067`)

```python
# File: services/rag_engine.py (riga 1047-1067)
def _format_context(self, context_data: dict[str, Any]) -> str:
    """Format context data for query enhancement."""
    formatted_parts = []

    if "summary" in context_data:
        formatted_parts.append("Metriche di riepilogo:")
        for key, value in context_data["summary"].items():
            formatted_parts.append(f"- {key}: {value}")

    if "trends" in context_data:
        formatted_parts.append("\nTendenze:")
        if "yoy_growth" in context_data["trends"]:
            for growth in context_data["trends"]["yoy_growth"][-2:]:  # Last 2 years
                formatted_parts.append(f"- Anno {growth['year']}: {growth['growth_percentage']}% crescita")

    if "insights" in context_data:
        formatted_parts.append("\nApprofondimenti chiave:")
        for insight in context_data["insights"][:3]:  # Top 3 insights
            formatted_parts.append(f"- {insight}")

    return "\n".join(formatted_parts)
```

**Smart context formatting**:
- **Structured summary**: Estrae metriche chiave dal CSV
- **Trend analysis**: Mostra crescite YoY degli ultimi 2 anni
- **Key insights**: Top 3 insights più rilevanti
- **Readable format**: Formato ottimizzato per comprensione LLM

### Analysis Type Enhancement (`services/rag_engine.py:analysis_type`)

Il sistema applica enhancement specifici per tipo di analisi:
- **bilancio**: Aggiunge context finanziario e KPI
- **contratto**: Focus su clausole e obbligazioni
- **fatturato**: Emphasis su metriche vendite
- **magazzino**: Context logistico e operativo
- **presentazione**: Struttura slide e messaggi chiave

---

## Enterprise Mode e Advanced Features

### Enterprise Query Implementation (`app.py:799-833`)

```python
# File: app.py (riga 799-833)
if enterprise_mode:
    # Use enterprise query mode
    import asyncio

    try:
        # Run enterprise query asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        response = loop.run_until_complete(
            rag_engine.enterprise_query(
                query_text=query,
                enable_enterprise_features=True,
                top_k=top_k,
                use_context=use_context,
                csv_analysis=st.session_state.csv_analysis if use_context else None,
            )
        )

        # Show enterprise processing details
        if "enterprise_data" in response:
            enterprise_data = response["enterprise_data"]

            # Show processing stats in sidebar
            with st.sidebar:
                st.header("🚀 Stats Enterprise")
                st.metric("Tempo Elaborazione", f"{enterprise_data['processing_time_ms']:.0f}ms")
                st.metric("Confidenza", f"{response['confidence']:.1%}")
                st.metric("Record Fact Table", enterprise_data["fact_table_records"])

                if enterprise_data["warnings"]:
                    st.warning(f"⚠️ {len(enterprise_data['warnings'])} avvisi")
                if enterprise_data["errors"]:
                    st.error(f"❌ {len(enterprise_data['errors'])} errori")
```

**Enterprise features**:
- **Async processing**: Query asincrone per performance
- **Advanced analytics**: Processing time, confidence, fact table records
- **Error monitoring**: Warning e error tracking
- **Sidebar metrics**: Real-time performance stats

### Streaming Query Support (`services/rag_engine.py:1069-1095`)

```python
# File: services/rag_engine.py (riga 1069-1095)
async def query_stream(self, query_text: str, top_k: int = 3, **kwargs):
    """
    Stream query response in real-time.

    Args:
        query_text: User query
        top_k: Number of documents to retrieve
        **kwargs: Additional arguments

    Yields:
        StreamingChunk objects with tokens and metadata
    """
    if not self.streaming_engine:
        logger.warning("Streaming not available, falling back to standard query")
        result = self.query(query_text, top_k=top_k)
        # Convert standard response to single chunk
        if ADVANCED_FEATURES_AVAILABLE:
            yield StreamingChunk(
                token=result.get("answer", ""), metadata={"sources": result.get("sources", [])}, is_final=True
            )
        else:
            yield {"answer": result.get("answer", ""), "sources": result.get("sources", [])}
        return

    # Stream the response
    async for chunk in self.streaming_engine.stream_query(query_text, **kwargs):
        yield chunk
```

### HyDE Query Enhancement (`services/rag_engine.py:1097-1141`)

```python
# File: services/rag_engine.py (riga 1097-1141)
def query_with_hyde(self, query_text: str, top_k: int = 3, **kwargs) -> dict[str, Any]:
    """
    Query using HyDE for improved retrieval.

    Args:
        query_text: User query
        top_k: Number of documents to retrieve
        **kwargs: Additional arguments

    Returns:
        Query response with improved retrieval
    """
    if not self.hyde_engine:
        logger.warning("HyDE not available, falling back to standard query")
        return self.query(query_text, top_k=top_k)

    try:
        # Use HyDE engine for query
        response = self.hyde_engine.query(query_text, **kwargs)

        # Format response
        sources = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes[:top_k]:
                sources.append(
                    {
                        "content": node.node.text[:500],
                        "metadata": node.node.metadata,
                        "score": float(node.score) if node.score else 0.0,
                    }
                )

        result = {
            "answer": str(response),
            "sources": sources,
            "confidence": sum(s["score"] for s in sources) / len(sources) if sources else 0.0,
            "method": "hyde",
        }

        logger.info(f"HyDE query completed with {len(sources)} sources")
        return result

    except Exception as e:
        logger.error(f"Error in HyDE query: {str(e)}")
        return self.query(query_text, top_k=top_k)
```

**HyDE (Hypothetical Document Embeddings)**:
- **Better retrieval**: Genera documenti ipotetici per matching migliore
- **Improved relevance**: Scoring più accurato per query complesse
- **Graceful fallback**: Fallback automatico a query standard se non disponibile

---

## Interfaccia Utente e UX

### Query Input Interface (`app.py:746-751`)

```python
# File: app.py (riga 746-751)
query = st.text_area(
    "Fai domande sui tuoi documenti",
    value=default_value,
    placeholder="es., Quali sono i principali rischi aziendali menzionati? Qual era il focus strategico per il 2024?",
    height=100,
)
```

### Analysis Type Selection (`app.py:754-770`)

```python
# File: app.py (riga 754-770)
# Analysis type selection for queries
st.subheader("🎯 Tipo di Analisi per Query")
query_analysis_options = [
    "Standard (RAG normale)",
    "Bilancio - Analisi finanziaria per bilanci e report finanziari",
    "Report Dettagliato - Stile Investment memo",
    "Fatturato - Analisi vendite e ricavi",
    "Magazzino - Analisi logistica e gestione scorte",
    "Contratto - Analisi legale e contrattuale",
    "Presentazione - Analisi di presentazioni e slide deck",
]

selected_query_analysis = st.selectbox(
    "Applica un tipo di analisi specializzata alla risposta:",
    options=query_analysis_options,
    index=0,
    help="Puoi applicare un'analisi specializzata anche alle query sui documenti già indicizzati",
)
```

**UX features**:
- **Multi-line input**: Text area per query lunghe e complesse
- **Smart placeholders**: Esempi realistici di query
- **Analysis type selector**: Specializzazione risposta per dominio
- **Help integrato**: Tooltip esplicativi per ogni opzione

### Advanced Query Controls (`app.py:777-782`)

```python
# File: app.py (riga 777-782)
col1_query, col2_query = st.columns([1, 1])
with col1_query:
    top_k = st.slider("Numero di fonti", min_value=1, max_value=10, value=5)
with col2_query:
    use_context = st.checkbox("Includi contesto analisi CSV", value=bool(st.session_state.csv_analysis))
```

**Power user controls**:
- **Top-k slider**: Controllo numero fonti (1-10)
- **Context integration**: Toggle per includere analisi CSV
- **Smart defaults**: Default basato su disponibilità dati

### Query Execution with Feedback (`app.py:784-792`)

```python
# File: app.py (riga 784-792)
# Execute query either manually or automatically
execute_query = st.button("🤔 Fai Domanda", type="primary", disabled=not query) or auto_execute

if execute_query and query:
    # Show different spinner message for auto queries
    spinner_message = "Eseguendo query automatica..." if auto_execute else "Cercando e analizzando documenti..."
    if query_analysis_type:
        spinner_message = f"Applicando analisi {query_analysis_type.upper()}..."

    with st.spinner(spinner_message):
```

**Interactive feedback**:
- **Context-aware spinners**: Messaggi diversi per tipo operazione
- **Auto-execution support**: Per query triggered da altre sezioni
- **Smart button states**: Disabilitato quando query vuota

### Response Display and Source Attribution

```python
# File: app.py (sezione display response)
# Display response with sources
if st.session_state.rag_response:
    response_data = st.session_state.rag_response
    
    # Answer section
    st.subheader("💡 Risposta")
    st.write(response_data.get("answer", "Nessuna risposta disponibile"))
    
    # Sources section with interactive elements
    sources = response_data.get("sources", [])
    if sources:
        st.subheader(f"📚 Fonti ({len(sources)})")
        
        for i, source in enumerate(sources, 1):
            with st.expander(f"📄 Fonte {i} - {source.get('metadata', {}).get('source', 'N/A')} (Score: {source.get('score', 0):.3f})"):
                # Source text
                st.text(source.get("text", "N/A"))
                
                # Metadata with clickable page links
                metadata = source.get("metadata", {})
                if "page_number" in metadata and "pdf_path" in metadata:
                    if st.button(f"📄 Vai a pagina {metadata['page_number']}", key=f"pdf_{i}"):
                        st.session_state.pdf_to_view = {
                            "source_name": metadata.get("source", "N/A"),
                            "page": metadata["page_number"],
                            "path": metadata["pdf_path"]
                        }
                        st.rerun()
```

**Rich response interface**:
- **Structured display**: Risposta + fonti chiaramente separate
- **Source scoring**: Mostra confidence score per ogni fonte
- **Interactive PDF links**: Click per aprire pagina specifica
- **Expandable sources**: Gestione clean di multiple fonti

---

## Ottimizzazioni Performance e Caching

### Query Caching (`services/rag_engine.py:672-677`)

```python
# File: services/rag_engine.py (riga 672-677)
# Check cache first if enabled
if self.query_cache:
    cached_result = self.query_cache.get(query_text, top_k, analysis_type)
    if cached_result:
        logger.info(f"Returning cached result for query: {query_text[:50]}...")
        return cached_result
```

**Smart caching strategy**:
- **Multi-key cache**: Query text + top_k + analysis_type
- **TTL-based**: 1 ora default per bilanciare freshness/performance
- **Namespace support**: Per multi-tenancy
- **Logging integrato**: Tracking cache hits per ottimizzazioni

### Response Mode Optimization (`config/settings.py:32`)

```python
# File: config/settings.py (riga 32)
rag_response_mode: str = Field(default="compact", env="RAG_RESPONSE_MODE")  # compact, tree_summarize, simple
```

**Performance tuning**:
- **compact mode**: Default per velocità (vs tree_summarize)
- **Configurable**: Via environment variable
- **Balance quality/speed**: Compact mantiene buona qualità

### Connection Pooling (`services/rag_engine.py:66-67`)

```python
# File: services/rag_engine.py (riga 66-67)
# Use connection pool for Qdrant
self.connection_pool = get_qdrant_pool()
self.query_optimizer = get_query_optimizer()
```

**Infrastructure optimization**:
- **Connection reuse**: Evita overhead connessione Qdrant
- **Query optimization**: Pre-processing ottimizzazioni
- **Resource efficiency**: Gestione pool per scalabilità

### Session State Management

```python
# File: app.py (session state management)
# Store query results in session state
st.session_state.rag_response = response
st.session_state.last_query = query

# PDF viewer state management
if "pdf_to_view" in metadata:
    st.session_state.pdf_to_view = pdf_metadata
```

**User experience optimization**:
- **Response persistence**: Query results mantengono stato
- **Navigation state**: PDF viewer integrato
- **History tracking**: Last query per context

---

## Error Handling e Resilienza

### Graceful Degradation

```python
# File: app.py (enterprise fallback)
except Exception as e:
    st.warning(f"Enterprise mode fallback: {e}")
    # Fallback to standard mode
    if use_context and st.session_state.csv_analysis:
        response = rag_engine.query_with_context(
            query, st.session_state.csv_analysis, top_k=top_k, analysis_type=query_analysis_type
        )
    else:
        response = rag_engine.query(query, top_k=top_k, analysis_type=query_analysis_type)
```

### User-Friendly Error Messages

```python
# File: services/rag_engine.py (error handling)
except Exception as e:
    logger.error(f"Error in query: {str(e)}")
    return {
        "answer": f"Si è verificato un errore durante l'elaborazione della domanda: {str(e)}",
        "sources": [],
        "confidence": 0
    }
```

**Error resilience patterns**:
- **Multiple fallback levels**: Enterprise → Context → Standard
- **User-friendly messages**: Errori tecnici tradotti in linguaggio utente
- **Logging completo**: Per debugging e monitoring
- **Graceful degradation**: Sistema sempre utilizzabile anche con errori parziali

---

## Export e Condivisione

### PDF Export for Q&A Sessions (`app.py:896-913`)

```python
# File: app.py (riga 896-913)
# Generate PDF
pdf_exporter = PDFExporter()
pdf_buffer = pdf_exporter.export_qa_session(
    question=question, answer=answer, sources=sources, metadata=metadata
)

# Create download button
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"qa_session_{timestamp}.pdf"

st.download_button(
    label="📥 Scarica PDF",
    data=pdf_buffer.getvalue(),
    file_name=filename,
    mime="application/pdf",
    key="download_qa_pdf",
)

st.success("✅ PDF generato con successo! Usa il pulsante 'Scarica PDF' per salvarlo.")
```

### Session Save Functionality (`app.py:919-935`)

```python
# File: app.py (riga 919-935)
if st.button("📋 Salva Sessione", key="save_session"):
    # Store the current session for later export
    if "qa_sessions" not in st.session_state:
        st.session_state.qa_sessions = []

    session_data = {
        "question": st.session_state.get(
            "last_query", query if "query" in locals() and query else "Domanda non disponibile"
        ),
        "answer": st.session_state.rag_response["answer"],
        "sources": st.session_state.rag_response.get("sources", []),
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "confidence": st.session_state.rag_response.get("confidence", 0),
    }

    st.session_state.qa_sessions.append(session_data)
    st.success(f"✅ Sessione salvata! ({len(st.session_state.qa_sessions)} sessioni totali)")
```

**Professional sharing features**:
- **PDF generation**: Export completo sessione Q&A
- **Timestamped files**: Nomi file con data/ora per organizzazione
- **Session history**: Accumula multiple sessioni per export batch
- **Metadata ricchi**: Confidence score, fonti, timestamp per ogni sessione

---

## Best Practices Implementate

### 1. **Multi-Modal Query Processing**
- Context integration con CSV
- Analysis type specialization
- Enterprise mode per advanced features

### 2. **Performance Optimization**
- Query caching con TTL
- Connection pooling per Qdrant
- Configurable response modes

### 3. **User Experience Excellence**
- Real-time feedback con spinner
- Interactive source attribution
- PDF viewer integrato
- Export professionale

### 4. **Resilienza e Error Handling**
- Multiple fallback levels
- Graceful degradation
- User-friendly error messages

### 5. **Enterprise Features**
- Async processing
- Performance monitoring
- Advanced analytics
- Streaming support

### 6. **Source Transparency**
- Complete attribution tracking
- Clickable page references
- Confidence scoring
- Metadata preservation

---

## Conclusioni

Il sistema di Domanda e Risposta implementato rappresenta una soluzione enterprise-grade che:

1. **Combina retrieval semantico avanzato** con generation di qualità tramite LLM
2. **Offre modalità specializzate** per diversi domini (bilancio, contratto, etc.)
3. **Garantisce performance ottimali** con caching, pooling e response mode configurabili
4. **Mantiene trasparenza completa** con source attribution e confidence scoring
5. **Supporta workflow professionali** con export PDF e session management
6. **Scala enterprise features** con async processing e advanced analytics

La combinazione di tecnologie all'avanguardia (LlamaIndex, Qdrant, OpenAI), ottimizzazioni performance, e UX curata crea un sistema Q&A che permette agli utenti di interrogare naturalmente i propri documenti aziendali con la qualità e affidabilità richieste in contesti professionali.