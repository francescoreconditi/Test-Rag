# Procedura di Generazione FAQ Intelligenti nel Sistema RAG

## Indice
1. [Teoria delle FAQ Automatiche](#teoria-delle-faq-automatiche)
2. [Best Practices per FAQ Generation](#best-practices-per-faq-generation)
3. [Architettura del Sistema FAQ](#architettura-del-sistema-faq)
4. [Implementazione del Generatore FAQ](#implementazione-del-generatore-faq)
5. [Strategia di Campionamento dei Contenuti](#strategia-di-campionamento-dei-contenuti)
6. [Prompt Engineering per FAQ](#prompt-engineering-per-faq)
7. [Integrazione con RAG per Risposte](#integrazione-con-rag-per-risposte)
8. [UI Streamlit e Export PDF](#ui-streamlit-e-export-pdf)

---

## Teoria delle FAQ Automatiche

### Cos'è la Generazione Automatica di FAQ

La generazione automatica di FAQ è un processo che utilizza LLM per:
1. **Analizzare contenuti complessi** e identificare argomenti chiave
2. **Generare domande pertinenti** che gli utenti potrebbero porre
3. **Fornire risposte accurate** basate sui documenti indicizzati
4. **Creare una knowledge base** facilmente consultabile

### Perché è Importante in un Sistema RAG

- **Proattività**: Anticipa le domande degli utenti
- **Scopribilità**: Evidenzia informazioni nascoste nei documenti
- **Accessibilità**: Interfaccia user-friendly per esplorare contenuti
- **Quality Check**: Verifica che i documenti contengano informazioni utili

### Approccio Ispirato a Google NotebookLM

Il sistema implementa un approccio simile a Google NotebookLM:
- **Analisi olistica** di tutto il contenuto disponibile
- **Domande intelligenti** contestualizzate al dominio
- **Risposte dettagliate** con citazioni delle fonti
- **Formato professionale** per export e condivisione

---

## Best Practices per FAQ Generation

### 1. Campionamento Intelligente dei Contenuti

- **Quantità ottimale**: 100 documenti sample vs 20 (per migliore rappresentazione)
- **Filtraggio metadata**: Esclude informazioni tecniche (indexed_at, document_size, etc.)
- **Full text prioritario**: Usa testo completo quando disponibile vs chunk fragmentati
- **Diversità tipologica**: Rappresenta tutti i tipi di documento presenti

### 2. Prompt Engineering Rigoroso

- **Istruzioni specifiche**: Genera domande SOLO su contenuti effettivamente presenti
- **Prevenzione allucinazioni**: Vieta domande su argomenti non menzionati
- **Contestualizzazione**: Adatta le domande al tipo di documento
- **Controllo qualità**: Verifica pertinenza prima della generazione

### 3. Generazione Risposte RAG-Based

- **Query intelligente**: Ogni domanda viene interrogata al database vettoriale
- **Top-k ottimizzato**: Usa solo 2 risultati per risposta focalizzata
- **Source tracking**: Mantiene tracciabilità completa delle fonti
- **Fallback graceful**: Gestisce errori nella generazione risposte

### 4. Classificazione Automatica Documenti

- **Pattern recognition**: Riconosce automaticamente tipologia documento
- **Domande specializzate**: Adatta le FAQ al tipo (bilancio, contratto, etc.)
- **Tag informativi**: Mostra all'utente i tipi di documento analizzati

---

## Architettura del Sistema FAQ

### Flusso Completo

```
[Database Vettoriale] → [Content Sampling] → [LLM Question Generation] → [RAG Answer Generation] → [FAQ Output] → [PDF Export]
                                ↓
                        [Document Type Detection]
                                ↓
                        [Content Filtering & Validation]
```

### Componenti Chiave

1. **FAQ Generator** (`services/rag_engine.py:generate_faq`)
2. **Content Sampler** (database exploration logic)
3. **Question Validator** (anti-hallucination controls)
4. **RAG Answer Engine** (per ogni domanda generata)
5. **UI Controller** (`app.py:show_intelligent_faq`)
6. **PDF Exporter** (`src/presentation/streamlit/pdf_exporter.py`)

---

## Implementazione del Generatore FAQ

### Metodo Principale (`services/rag_engine.py:1501-1512`)

```python
# File: services/rag_engine.py (riga 1501-1512)
def generate_faq(self, num_questions: int = 10) -> dict[str, Any]:
    """Generate FAQ based on vector database content.

    Args:
        num_questions: Number of FAQ questions to generate

    Returns:
        Dictionary containing generated FAQ with questions and answers
    """
    try:
        if not self.index:
            return {"error": "Nessun documento indicizzato. Carica documenti prima di generare FAQ.", "faqs": []}

        # Get database statistics to understand content
        stats = self.get_index_stats()
        if stats.get("total_vectors", 0) == 0:
            return {"error": "Database vettoriale vuoto. Carica documenti prima di generare FAQ.", "faqs": []}

        logger.info(f"Generating FAQ with {num_questions} questions from {stats.get('total_vectors')} vectors")
```

### Validazioni Preliminari

Il sistema esegue controlli rigorosi prima di procedere:
1. **Index availability**: Verifica esistenza database vettoriale
2. **Content availability**: Controlla presenza documenti indicizzati
3. **Logging informativo**: Traccia numero di vettori disponibili

---

## Strategia di Campionamento dei Contenuti

### Campionamento Ottimizzato (`services/rag_engine.py:1521-1530`)

```python
# File: services/rag_engine.py (riga 1521-1530)
# Get a LARGER sample of documents to understand content themes
# Increased from 20 to 100 for better content representation
exploration_data = self.explore_database(limit=100)
sample_texts = []
document_types = set()

if exploration_data.get("documents"):
    for doc in exploration_data["documents"]:
        # Get actual content, NOT metadata!
        text_preview = ""

        # Try to get actual node content first
        if "metadata" in doc and "_node_content" in doc["metadata"]:
            text_preview = doc["metadata"]["_node_content"][:1000]
        elif "text_preview" in doc:
            text_preview = doc["text_preview"]
```

**Ottimizzazioni implementate**:
- **100 documenti** invece di 20 per campione più rappresentativo
- **Priorità contenuto reale** vs metadati tecnici
- **1000 caratteri per preview** bilanciando completezza e performance

### Filtraggio Anti-Metadata (`services/rag_engine.py:1539-1552`)

```python
# File: services/rag_engine.py (riga 1539-1552)
# Filter out metadata strings and technical info
if text_preview and not any(
    skip in text_preview.lower()
    for skip in [
        "metadata",
        "indexed_at",
        "source:",
        "page:",
        "document_size",
        "file_type",
        "pdf_path",
        "chunk_count",
        "total_pages",
    ]
):
    sample_texts.append(text_preview)
```

**Anti-pattern implementato**:
- **Blacklist metadata**: Esclude automaticamente chunk con info tecniche
- **Quality filtering**: Solo contenuto business value
- **Noise reduction**: Evita domande su aspetti tecnici irrilevanti

### Classificazione Automatica Documenti (`services/rag_engine.py:1554-1565`)

```python
# File: services/rag_engine.py (riga 1554-1565)
if "metadata" in doc and "source" in doc["metadata"]:
    source = doc["metadata"]["source"].lower()
    if "bilancio" in source or "balance" in source:
        document_types.add("bilancio")
    elif "fatturato" in source or "revenue" in source or "vendite" in source:
        document_types.add("fatturato")
    elif "contratto" in source or "contract" in source:
        document_types.add("contratto")
    elif "report" in source:
        document_types.add("report")
    else:
        document_types.add("generale")
```

**Pattern recognition automatico**:
- **Filename-based detection**: Analizza nome file per tipo documento
- **Multi-language support**: Supporta termini italiano/inglese
- **Fallback categorization**: Categoria "generale" per documenti non classificati

### Strategia Full-Text Priority (`services/rag_engine.py:1572-1579`)

```python
# File: services/rag_engine.py (riga 1572-1579)
# PRIORITIZE: If we have cached full text, use it INSTEAD of chunks
if hasattr(self, "_last_document_texts") and self._last_document_texts:
    # Use actual full document text for better FAQ generation
    full_texts = list(self._last_document_texts.values())
    if full_texts and any(text.strip() for text in full_texts):
        # Take substantial portion of actual document content
        content_sample = "\n\n".join([text[:20000] for text in full_texts])[:30000]
        logger.info(f"Using FULL document text for FAQ generation: {len(content_sample)} chars")
```

**Strategia intelligente**:
- **Full text priority**: Usa testo completo quando disponibile (da cache upload)
- **20k caratteri per documento**: Sostanziale porzione di contenuto
- **30k caratteri totali**: Limite per controllo costi API
- **Logging informativo**: Traccia utilizzo full text

---

## Prompt Engineering per FAQ

### Template FAQ Rigoroso (`services/rag_engine.py:1610-1643`)

```python
# File: services/rag_engine.py (riga 1610-1643)
# Generate FAQ using LLM
faq_prompt = f"""
Sei un esperto di business intelligence e analisi aziendale. Analizza ATTENTAMENTE il contenuto fornito e genera {num_questions} domande frequenti (FAQ) che siano STRETTAMENTE PERTINENTI al contenuto effettivo del documento.

IMPORTANTE: Le domande DEVONO essere basate ESCLUSIVAMENTE sul contenuto fornito sotto. Non inventare domande su argomenti non presenti nel testo.

TIPI DI DOCUMENTI PRESENTI: {document_types_str}

CONTENUTO EFFETTIVO DEL DOCUMENTO (NON metadata tecnici):
{content_sample}

NOTA CRITICA: Ignora completamente riferimenti a metadata, nomi file, date di indicizzazione, ID documento, numero pagine. Concentrati SOLO sul contenuto business del documento!

ISTRUZIONI RIGOROSE:
1. Genera {num_questions} domande basate ESCLUSIVAMENTE sul contenuto fornito sopra
2. NON inventare domande su argomenti NON menzionati nel testo (es. se non ci sono dati su marketing, NON fare domande sul marketing)
3. Le domande devono riferirsi a informazioni EFFETTIVAMENTE PRESENTI nel documento
4. Se il documento è un bilancio, fai domande su voci di bilancio, patrimonio, risultati economici, etc.
5. Usa terminologia italiana e professionale appropriata al tipo di documento
6. Prima di generare ogni domanda, verifica che l'argomento sia PRESENTE nel contenuto fornito

FORMATO RICHIESTO:
Per ogni domanda, fornisci SOLO:
- Una domanda chiara e specifica
- NON fornire risposte, solo le domande

Esempi di domande SOLO se questi argomenti sono presenti nel testo:
- Se c'è un bilancio: "Qual è il valore del patrimonio netto?", "Come sono variati i ricavi?"
- Se ci sono dati vendite: "Quali sono i trend di vendita?"
- Se ci sono dati su clienti: "Qual è il tasso di attrito dei clienti?"

RICORDA: Genera domande SOLO su ciò che è EFFETTIVAMENTE presente nel contenuto fornito!

Genera SOLO le domande, una per riga, numerate da 1 a {num_questions}:
"""
```

**Caratteristiche avanzate del prompt**:
- **Anti-hallucination controls**: Multiple istruzioni contro invenzione contenuti
- **Context awareness**: Usa tipologie documento rilevate per domande specializzate
- **Quality gates**: Verifica presenza argomenti prima della generazione
- **Professional tone**: Terminologia italiana e business-appropriate
- **Format specification**: Output strutturato e parsabile

### Parsing Intelligente delle Domande (`services/rag_engine.py:1649-1659`)

```python
# File: services/rag_engine.py (riga 1649-1659)
# Parse questions from response
questions = []
for line in faq_questions_text.split("\n"):
    line = line.strip()
    if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
        # Clean up the question
        question = line
        # Remove numbering (1., 2., -, •, etc.)
        question = question.lstrip("0123456789.-• \t")
        if question:
            questions.append(question)
```

**Parser robusto**:
- **Multiple formats**: Gestisce numerazione, bullet points, trattini
- **Cleaning automatico**: Rimuove numerazione e formattazione
- **Validation**: Solo domande non vuote vengono accettate

---

## Integrazione con RAG per Risposte

### Generazione Risposte per Ogni Domanda (`services/rag_engine.py:1661-1683`)

```python
# File: services/rag_engine.py (riga 1661-1683)
# Generate answers for each question using RAG
faqs = []
for i, question in enumerate(questions[:num_questions], 1):
    try:
        # Query the database for answer
        rag_response = self.query(question, top_k=2)

        answer = rag_response.get(
            "answer",
            "Non sono riuscito a trovare informazioni specifiche su questo argomento nei documenti caricati.",
        )
        sources = rag_response.get("sources", [])

        faqs.append(
            {
                "id": i,
                "question": question,
                "answer": answer,
                "sources": sources,
                "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }
        )

    except Exception as e:
        logger.warning(f"Error generating answer for question {i}: {e}")
        faqs.append(
            {
                "id": i,
                "question": question,
                "answer": "Errore nella generazione della risposta. Riprova più tardi.",
                "sources": [],
                "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }
        )
```

**Strategia RAG ottimizzata**:
- **Top-k=2**: Solo 2 documenti più rilevanti per risposte focalizzate
- **Error handling**: Gestisce gracefully errori nella generazione
- **Metadata ricchi**: Timestamp, ID, sources per ogni FAQ
- **Fallback answers**: Messaggio utile quando informazioni non disponibili

### Struttura Output Completa (`services/rag_engine.py:1696-1707`)

```python
# File: services/rag_engine.py (riga 1696-1707)
result = {
    "faqs": faqs,
    "metadata": {
        "total_questions": len(faqs),
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "document_types": list(document_types),
        "total_documents": stats.get("total_vectors", 0),
    },
    "success": True,
}

logger.info(f"Successfully generated {len(faqs)} FAQ questions")
return result
```

**Output strutturato**:
- **FAQ array**: Lista completa domande/risposte/fonti
- **Metadata informativo**: Statistiche sulla generazione
- **Success flag**: Indicatore stato operazione
- **Logging completo**: Tracciabilità operazioni

---

## UI Streamlit e Export PDF

### Interfaccia FAQ (`app.py:78-93`)

```python
# File: app.py (riga 78-93)
def show_intelligent_faq():
    """Show intelligent FAQ generation page."""
    st.header("💬 FAQ Intelligenti")
    st.caption("Genera automaticamente domande frequenti basate sui tuoi documenti, come Google NotebookLM")

    rag_engine = st.session_state.services["rag_engine"]

    # Check if there are documents in the database
    stats = rag_engine.get_index_stats()

    if stats.get("total_vectors", 0) == 0:
        st.warning("📭 Nessun documento nel database. Carica documenti nella sezione 'RAG Documenti' per generare FAQ.")
        return

    # Show current database stats
    st.info(f"📊 Database pronto: {stats.get('total_vectors', 0)} blocchi indicizzati")
```

### Controlli Utente (`app.py:101-111`)

```python
# File: app.py (riga 101-111)
with col1:
    num_questions = st.slider(
        "Numero di domande FAQ da generare",
        min_value=5,
        max_value=20,
        value=10,
        step=1,
        help="Scegli quante domande frequenti vuoi generare",
    )

with col2:
    st.metric("Documenti Indicizzati", stats.get("total_vectors", 0))
```

**UX ottimizzata**:
- **Range configurabile**: 5-20 domande (bilanciamento utilità/costi)
- **Default sensato**: 10 domande come compromesso ottimale
- **Help integrato**: Guida utente sulla funzionalità
- **Status visibility**: Mostra stato database prima della generazione

### Generazione FAQ con Feedback (`app.py:124-131`)

```python
# File: app.py (riga 124-131)
# Generate FAQ when button is clicked
if generate_button:
    with st.spinner("🧠 Generando FAQ intelligenti basate sui tuoi documenti..."):
        faq_result = rag_engine.generate_faq(num_questions=num_questions)

    if faq_result.get("success", False):
        # Store FAQ in session state
        st.session_state.generated_faq = faq_result
        st.rerun()
```

**UX pattern**:
- **Visual feedback**: Spinner durante elaborazione
- **Session persistence**: FAQ salvate in session state
- **Auto-refresh**: UI si aggiorna automaticamente dopo generazione

### Visualizzazione FAQ (`app.py:189-227`)

```python
# File: app.py (riga 189-227)
# Display each FAQ
for i, faq in enumerate(faqs, 1):
    with st.expander(f"❓ Domanda {i}: {faq.get('question', 'N/A')[:80]}...", expanded=i <= 3):
        # Question
        st.markdown("**🤔 Domanda:**")
        st.write(faq.get("question", "N/A"))

        # Answer
        st.markdown("**💡 Risposta:**")
        st.write(faq.get("answer", "N/A"))

        # Sources
        sources = faq.get("sources", [])
        if sources:
            st.markdown(f"**📚 Fonti ({len(sources)}):**")
            for j, source in enumerate(sources, 1):
                with st.container():
                    score = source.get("score", 0)
                    st.caption(f"Fonte {j} (Rilevanza: {score:.1%})")

                    # Source text preview
                    source_text = source.get("text", "N/A")
                    if len(source_text) > 200:
                        source_text = source_text[:200] + "..."
                    st.text(source_text)

                    # Source metadata
                    if source.get("metadata"):
                        metadata_items = []
                        for key in ["source", "page", "file_type"]:
                            if key in source["metadata"]:
                                value = source["metadata"][key]
                                metadata_items.append(f"{key.title()}: {value}")

                        if metadata_items:
                            st.caption(" | ".join(metadata_items))

        st.caption(f"Generata il: {faq.get('generated_at', 'N/A')}")
```

**Interfaccia ricca**:
- **Expander per FAQ**: Prime 3 espanse di default per immediata visibilità
- **Struttura chiara**: Domanda → Risposta → Fonti
- **Source transparency**: Rilevanza, preview testo, metadati
- **Timestamp tracking**: Quando ogni FAQ è stata generata

### Export PDF (`app.py:159-182`)

```python
# File: app.py (riga 159-182)
if st.button("📄 Esporta FAQ PDF", type="primary", key="export_faq_pdf"):
    try:
        from src.presentation.streamlit.pdf_exporter import PDFExporter

        # Generate PDF
        pdf_exporter = PDFExporter()
        pdf_buffer = pdf_exporter.export_faq(faqs=faqs, metadata=metadata)

        # Create download button
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"faq_intelligenti_{timestamp}.pdf"

        st.download_button(
            label="📥 Scarica FAQ PDF",
            data=pdf_buffer.getvalue(),
            file_name=filename,
            mime="application/pdf",
            key="download_faq_pdf",
        )

        st.success(f"✅ PDF FAQ generato con successo! ({len(faqs)} domande)")

    except Exception as e:
        st.error(f"❌ Errore nella generazione del PDF: {str(e)}")
```

**Export professionale**:
- **PDF di qualità**: Usando PDFExporter specializzato
- **Filename timestamp**: Nome file con data/ora per evitare conflitti
- **Download diretto**: Button integrato per download immediato
- **Error handling**: Gestione graceful errori export

---

## Ottimizzazioni e Performance

### Controllo Qualità Contenuti (`services/rag_engine.py:1603-1607`)

```python
# File: services/rag_engine.py (riga 1603-1607)
# Check if content is mostly metadata (bad sign)
metadata_keywords = ["source:", "indexed_at:", "file_type:", "page:", "metadata", "document_size"]
metadata_count = sum(1 for keyword in metadata_keywords if keyword in content_sample.lower())
if metadata_count > 5:
    logger.warning(f"Content seems to contain too much metadata ({metadata_count} occurrences)")
```

**Quality assurance**:
- **Metadata detection**: Identifica automaticamente contenuto di bassa qualità
- **Alert logging**: Avvisa quando troppi metadati nel campione
- **Threshold empirico**: 5+ keyword metadata = warning

### Fallback Strategy per Contenuto (`services/rag_engine.py:1581-1592`)

```python
# File: services/rag_engine.py (riga 1581-1592)
elif not sample_texts:
    # If we have no good samples, try a different approach
    logger.warning("No valid text samples found, attempting direct query")
    # Try to retrieve actual content through a query
    try:
        test_response = self.query("riassumi il contenuto principale del documento", top_k=10)
        if test_response and "sources" in test_response:
            for source in test_response["sources"]:
                if "text" in source:
                    sample_texts.append(source["text"])
            content_sample = "\n\n".join(sample_texts[:20])
    except:
        pass
```

**Resilienza del sistema**:
- **Fallback query**: Quando campionamento standard fallisce
- **Query generica**: "riassumi contenuto" per recuperare testo reale
- **Top-k aumentato**: 10 risultati per migliore coverage
- **Exception safe**: Try/except per robustezza

### Caching e Session State

```python
# File: app.py (session state management)
st.session_state.generated_faq = faq_result
```

**Performance optimization**:
- **Session persistence**: FAQ non rigenerate ad ogni refresh
- **Memory efficient**: Solo dati essenziali in session
- **User experience**: Navigazione fluida senza perdere risultati

---

## Best Practices Implementate

### 1. **Sampling Intelligente Multi-Livello**
- 100 documenti sample per rappresentatività
- Full text priority quando disponibile
- Anti-metadata filtering per qualità

### 2. **Prompt Engineering Anti-Hallucination**
- Istruzioni rigorose contro invenzione contenuti
- Verifiche multiple su presenza argomenti
- Context-aware question generation

### 3. **RAG Integration Ottimizzata**
- Top-k=2 per risposte focalizzate
- Source tracking completo
- Error handling graceful

### 4. **User Experience Professionale**
- Configurazione flessibile numero domande
- Visualizzazione ricca con source transparency
- Export PDF di qualità

### 5. **Quality Assurance Automatica**
- Document type detection
- Content quality validation
- Metadata pollution prevention

### 6. **Performance & Resilienza**
- Fallback strategies multiple
- Session state caching
- Exception handling comprehensive

---

## Conclusioni

Il sistema di generazione FAQ intelligenti rappresenta una implementazione sofisticata che:

1. **Analizza intelligentemente** il contenuto disponibile con campionamento ottimizzato e filtraggio qualità
2. **Genera domande pertinenti** usando prompt engineering rigoroso con controlli anti-hallucination
3. **Fornisce risposte accurate** tramite integrazione RAG con source tracking completo
4. **Offre UX professionale** con configurazione flessibile ed export PDF di qualità
5. **Garantisce resilienza** con multiple fallback strategies e error handling

La combinazione di tecniche avanzate di NLP, prompt engineering rigoroso, e integrazione seamless con il database vettoriale crea un sistema di FAQ generation che rivalizza con soluzioni enterprise come Google NotebookLM, fornendo agli utenti un modo proattivo e intelligente di esplorare e comprendere i propri documenti aziendali.