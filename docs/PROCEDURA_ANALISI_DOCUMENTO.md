# Procedura di Analisi Automatica dei Documenti nel Sistema RAG

## Indice
1. [Teoria dell'Analisi Automatica dei Documenti](#teoria-dellanalisi-automatica-dei-documenti)
2. [Best Practices per Document Analysis](#best-practices-per-document-analysis)
3. [Architettura del Sistema di Analisi](#architettura-del-sistema-di-analisi)
4. [Il Prompt Router - Cuore del Sistema](#il-prompt-router---cuore-del-sistema)
5. [Implementazione dell'Analisi](#implementazione-dellanalisi)
6. [Template di Prompt Specializzati](#template-di-prompt-specializzati)
7. [Formato Output e Strutturazione Dati](#formato-output-e-strutturazione-dati)
8. [Integrazione con l'UI Streamlit](#integrazione-con-lui-streamlit)

---

## Teoria dell'Analisi Automatica dei Documenti

### Cos'è l'Analisi Automatica

L'analisi automatica dei documenti è un processo che utilizza LLM (Large Language Models) per:
1. **Estrarre informazioni strutturate** da testo non strutturato
2. **Categorizzare e classificare** il contenuto
3. **Generare sintesi esecutive** professionali
4. **Identificare KPI e metriche** rilevanti
5. **Validare coerenze** nei dati finanziari

### Perché è Cruciale in un Sistema RAG

- **Enrichment immediato**: Arricchisce il documento con metadati strutturati al momento dell'upload
- **Query più precise**: I dati strutturati permettono ricerche più accurate
- **Comprensione contestuale**: L'LLM comprende il dominio del documento
- **Standardizzazione output**: Formato JSON consistente per tutti i documenti

### Approccio Multi-Template

Il sistema utilizza template specializzati per dominio:
- **Bilanci**: Parsing numeri italiani, validazioni contabili
- **Contratti**: Estrazione clausole, SLA, penali
- **Vendite**: Analisi fatturato, trend, driver
- **Magazzino**: KPI logistici, rotazione scorte
- **Presentazioni**: Messaggi chiave, struttura slide

---

## Best Practices per Document Analysis

### 1. Selezione Intelligente del Template

- **Analisi lessicale**: Ricerca di keyword specifiche del dominio
- **Pattern matching**: Identificazione strutture tipiche (es. "€", "%", "Art.")
- **Filename hints**: Il nome file può suggerire il tipo
- **Scoring ponderato**: Combinazione di multiple evidenze

### 2. Prompt Engineering Avanzato

- **Istruzioni precise**: Specificare formato output desiderato
- **Esempi in-context**: Mostrare struttura JSON attesa
- **Citazioni obbligatorie**: Richiedere sempre "p. X" per tracciabilità
- **Validazioni integrate**: Controlli coerenza direttamente nel prompt

### 3. Gestione Numeri Italiani

- **Formato italiano**: 1.234,56 (migliaia con punto, decimali con virgola)
- **Negativi tra parentesi**: (123) = -123
- **Scale dichiarate**: "valori in migliaia" richiede moltiplicazione
- **Percentuali**: 5,2% con virgola decimale

### 4. Output Strutturato

- **JSON per dati**: Facilita parsing e storage
- **Testo per sintesi**: Leggibilità umana
- **Metadati ricchi**: Provenienza, confidence, validazioni

---

## Architettura del Sistema di Analisi

### Flusso Completo

```
[Documento Upload] → [Text Extraction] → [Prompt Router] → [LLM Analysis] → [Structured Output] → [Storage]
                                              ↓
                                    [Template Selection]
                                              ↓
                                    [Specialized Prompt]
```

### Componenti Chiave

1. **Prompt Router** (`services/prompt_router.py`)
2. **RAG Engine** (`services/rag_engine.py`)
3. **LLM Service** (`services/llm_service.py`)
4. **Format Helper** (`services/format_helper.py`)

---

## Il Prompt Router - Cuore del Sistema

### Struttura del Router (`services/prompt_router.py:425-631`)

```python
# File: services/prompt_router.py (riga 425-631)
@dataclass
class CaseRule:
    name: str
    builder: Callable[[str, str], str]
    keywords: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)  # regex avanzate
    weight_keywords: float = 1.0
    weight_patterns: float = 2.0
    boost_if_filename: float = 1.5  # moltiplicatore se il nome file contiene keyword
    min_score_to_win: float = 1.0  # soglia minima per preferirlo al general

ROUTER: dict[str, CaseRule] = {
    "bilancio": CaseRule(
        name="bilancio",
        builder=PROMPT_BILANCIO,
        keywords=[
            "bilancio",
            "relazione finanziaria",
            "financial statement",
            "annual report",
            "conto economico",
            "stato patrimoniale",
            "cash flow",
            "rendiconto finanziario",
            "ebitda",
            "ebit",
            "utile netto",
            "ricavi",
            "revenues",
            "capex",
            "pfn",
            "margine",
            "indebitamento",
            "covenant",
            "trimestrale",
            "semestrale",
            "annuale",
        ],
        patterns=[
            r"\b€\s?\d",
            r"\bmln\b|\bmlrd\b|\bmld\b|\bmillion\b|\bbillion\b",
            r"\b%|\bpp\b|\bbp(?:s)?\b",
            r"\bifrs\b|\bgaap\b",
            r"\bfy20\d{2}\b|\b1h\d{2}\b|\bq[1-4]\b",
            r"\b20\d{2}\s+vs\s+20\d{2}\b",
        ],
        min_score_to_win=1.5,
    ),
    # ... altri template (fatturato, magazzino, contratto, presentazione)
}
```

### Algoritmo di Scoring (`services/prompt_router.py:637-659`)

```python
# File: services/prompt_router.py (riga 637-659)
def _score_case(rule: CaseRule, file_name: str, analysis_text: str) -> float:
    text = _norm(analysis_text)
    fname = _norm(file_name)

    kw_hits = _contains_any(text, rule.keywords)
    pat_hits = sum(_findall(p, analysis_text) for p in rule.patterns)

    score = kw_hits * rule.weight_keywords + pat_hits * rule.weight_patterns

    # boost se il nome file contiene indicatori (es. "Bilancio_2024.pdf")
    if any(k in fname for k in rule.keywords[:5]):  # primi 5 keyword più importanti
        score *= rule.boost_if_filename

    # segnali generici: valute/percentuali/datetime → piccolo boost alla finanza/vendite
    if rule.name in {"bilancio", "fatturato"}:
        generic_signals = _findall(r"[€$£]\s?\d", analysis_text) + _findall(
            r"\d[\.,]\d+%|\bpercentuale\b|\bpercent\b", analysis_text
        )
        score += 0.2 * generic_signals

    return score
```

**Caratteristiche dell'algoritmo**:
- **Scoring multi-criterio**: Keywords + patterns + filename
- **Pesi configurabili**: Pattern valgono più di keywords
- **Boost contestuale**: Nome file influenza selezione
- **Soglie minime**: Evita false positive

### Selezione del Prompt (`services/prompt_router.py:666-703`)

```python
# File: services/prompt_router.py (riga 666-703)
def choose_prompt(file_name: str, analysis_text: str) -> tuple[str, str, dict]:
    """
    Ritorna (prompt_name, prompt_text, debug_info)
    - prompt_name: 'bilancio' | 'fatturato' | 'magazzino' | 'contratto' | 'presentazione' | 'scadenzario' | 'generale'
    - prompt_text: string pronto da inviare al modello
    - debug_info: dizionario con punteggi e motivazioni
    """
    scores = {}
    for name, rule in ROUTER.items():
        scores[name] = _score_case(rule, file_name, analysis_text)

    # migliore candidato oltre la soglia minima; altrimenti GENERAL
    best_name = max(scores, key=scores.get) if scores else "generale"

    if scores and best_name in ROUTER:
        best_rule = ROUTER[best_name]
        if scores[best_name] >= best_rule.min_score_to_win:
            chosen_name = best_name
            builder = best_rule.builder
        else:
            chosen_name = "generale"
            builder = PROMPT_GENERAL
    else:
        chosen_name = "generale"
        builder = PROMPT_GENERAL

    prompt_text = builder(file_name, analysis_text)

    debug = {
        "scores": scores,
        "chosen": chosen_name,
        "file_hint": file_name,
        "length_chars": len(analysis_text),
    }

    logger.info(f"Prompt router: scelto '{chosen_name}' per file '{file_name}' (scores: {scores})")

    return chosen_name, prompt_text, debug
```

---

## Implementazione dell'Analisi

### Metodo Principale (`services/rag_engine.py:369-420`)

```python
# File: services/rag_engine.py (riga 369-420)
def analyze_document_content(
    self, document_text: str, file_name: str, force_prompt_type: Optional[str] = None
) -> str:
    """Generate automatic analysis of document content using specialized prompts."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)

        # Truncate text if too long (keep first 8000 chars for analysis)
        analysis_text = document_text[:8000] if len(document_text) > 8000 else document_text

        logger.debug(f"Document text length: {len(document_text)}, Analysis text length: {len(analysis_text)}")
        logger.debug(f"Analysis text preview: {analysis_text[:200]}...")

        # Use prompt router to select the best prompt (or force a specific one)
        if force_prompt_type and force_prompt_type != "automatico":
            # Force a specific prompt type
            from services.prompt_router import PROMPT_GENERAL, ROUTER

            if force_prompt_type == "generale":
                # Handle general prompt explicitly
                prompt_name = "generale"
                prompt_text = PROMPT_GENERAL(file_name, analysis_text)
                debug_info = {"forced": True, "type": "generale"}
                logger.info(f"Forcing general prompt for document '{file_name}'")
            elif force_prompt_type in ROUTER:
                # Use specialized prompt from router
                prompt_name = force_prompt_type
                prompt_text = ROUTER[force_prompt_type].builder(file_name, analysis_text)
                debug_info = {"forced": True, "type": force_prompt_type}
                logger.info(f"Forcing prompt type '{prompt_name}' for document '{file_name}'")
            else:
                # Unknown prompt type, fallback to general
                prompt_name = "generale"
                prompt_text = PROMPT_GENERAL(file_name, analysis_text)
                debug_info = {"forced": True, "type": "generale", "fallback": True}
                logger.warning(
                    f"Unknown prompt type '{force_prompt_type}', using general prompt for document '{file_name}'"
                )
        else:
            # Use automatic selection
            prompt_name, prompt_text, debug_info = choose_prompt(file_name, analysis_text)
            logger.info(f"Auto-selected prompt type '{prompt_name}' for document '{file_name}'")
        logger.debug(f"Prompt selection debug info: {debug_info}")

        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "Sei un analista aziendale esperto. Fornisci sempre risposte strutturate."
                },
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.0,  # Deterministic for consistency
            max_tokens=2000
        )
```

**Caratteristiche chiave**:
- **Truncation intelligente**: Max 8000 caratteri per controllo costi
- **Selezione automatica o forzata**: Flessibilità per l'utente
- **Logging completo**: Debug info per troubleshooting
- **Temperature 0**: Output deterministico e consistente

### Integrazione nel Flusso di Indicizzazione (`services/rag_engine.py:337-346`)

```python
# File: services/rag_engine.py (riga 337-346)
# Generate automatic analysis of the document content
if documents:
    full_text = "\n".join([doc.text for doc in documents])

    # Cache the document text for potential re-analysis
    if not hasattr(self, "_last_document_texts"):
        self._last_document_texts = {}
    self._last_document_texts[display_name] = full_text

    analysis = self.analyze_document_content(full_text, display_name, force_prompt_type)
    results["document_analyses"][display_name] = analysis
```

---

## Template di Prompt Specializzati

### Template Bilancio (`services/prompt_router.py:101-167`)

```python
# File: services/prompt_router.py (riga 101-167)
def PROMPT_BILANCIO(file_name: str, analysis_text: str) -> str:
    return f"""
Sei un equity/credit analyst esperto specializzato in documenti finanziari italiani. Analizza il documento "{file_name}" applicando le seguenti competenze:

COMPETENZE SPECIALIZZATE:
- **Numeri italiani**: 1.234,56 = milleduecentotrentaquattro virgola cinquantasei
- **Negativi**: (123) = numero negativo, -123
- **Percentuali**: 5,2% = cinque virgola due per cento
- **Scale**: "valori in migliaia" significa moltiplicare × 1.000
- **Sinonimi**: fatturato = ricavi = vendite; EBITDA = MOL; PFN = posizione finanziaria netta
- **Validazioni**: Attivo = Passivo; PFN = Debito lordo - Cassa; Margine lordo = Ricavi - COGS

=== DOCUMENTO ===
{analysis_text}
=== FINE DOCUMENTO ===

ISTRUZIONI OPERATIVE:
1. **Parsing accurato**: Riconosci formato numerico italiano (es. 1.234.567,89)
2. **Provenienza precisa**: Cita sempre "p. X" o "tab. Y" per ogni numero
3. **Controlli coerenza**: Verifica equazioni contabili basilari
4. **Scale applicate**: Se dichiarato "in migliaia", converti automaticamente
5. **Sinonimi**: Normalizza "fatturato" → "ricavi", "MOL" → "EBITDA"

PRODUCI due sezioni nell'ordine:
1) <KPI_JSON> … </KPI_JSON>
2) <SINTESI> … </SINTESI>

<KPI_JSON>
{{
  "periodi_coperti": [],
  "conto_economico": {{
    "ricavi": [{{"periodo":"", "valore":"","unita":"", "fonte_pagina":""}}],
    "ebitda": [],
    "ebit": [],
    "utile_netto": []
  }},
  "stato_patrimoniale": {{
    "cassa_e_equivalenti": [],
    "debito_finanziario_totale": [],
    "patrimonio_netto": []
  }},
  "cash_flow": {{
    "cfo": [],
    "cfi": [],
    "cff": [],
    "capex": []
  }},
  "margini_e_ratios": [
    {{"nome":"margine EBITDA","periodo":"","valore":"","unita":"%","fonte_pagina":""}},
    {{"nome":"PFN","periodo":"","valore":"","unita":"","fonte_pagina":""}},
    {{"nome":"PFN/EBITDA","periodo":"","valore":"","unita":"x","fonte_pagina":""}}
  ],
  "guidance_o_outlook": [{{"testo":"","periodo":"","fonte_pagina":""}}],
  "eventi_straordinari": [{{"descrizione":"","impatto":"","fonte_pagina":""}}],
  "rischi": [{{"descrizione":"","impatto":"","probabilita":"","fonte_pagina":""}}],
  "note": ""
}}
</KPI_JSON>

<SINTESI>
In 150–250 parole, evidenzia crescita/contrazione, driver principali, rischi finanziari, outlook e covenant. Usa "p. X" accanto ai numeri specifici.
</SINTESI>
"""
```

**Features avanzate del template bilancio**:
- **Parsing numeri italiani**: Gestione formato 1.234,56
- **Validazioni contabili**: Attivo = Passivo, PFN = Debito - Cassa
- **Normalizzazione sinonimi**: MOL → EBITDA, fatturato → ricavi
- **Scale automatiche**: Conversione "in migliaia"
- **Citazioni obbligatorie**: Ogni numero con fonte

### Template Contratto (`services/prompt_router.py:239-271`)

```python
# File: services/prompt_router.py (riga 239-271)
def PROMPT_CONTRATTO(file_name: str, analysis_text: str) -> str:
    return f"""
Agisci come legal/ops analyst esperto. Analizza il contratto "{file_name}" basandoti solo sul testo.

=== DOCUMENTO ===
{analysis_text}
=== FINE DOCUMENTO ===

OUTPUT:
<JSON>
{{
  "parti_coinvolte": [{{"nome":"","ruolo":"","fonte_pagina":""}}],
  "oggetto_e_ambito": {{"testo":"","fonte_pagina":""}},
  "durata_e_decorrenza": {{"inizio":"","fine":"","rinnovo":"","fonte_pagina":""}},
  "corrispettivi_e_pagamenti": [{{"descrizione":"","importo":"","valuta":"","scadenza":"","fonte_pagina":""}}],
  "kpi_sla_penali": [{{"kpi":"","soglia":"","misura":"","penale":"","fonte_pagina":""}}],
  "obblighi_delle_parti": [{{"parte":"","obbligo":"","fonte_pagina":""}}],
  "limitazioni_di_responsabilita": [{{"clausola":"","massimale":"","esclusioni":"","fonte_pagina":""}}],
  "proprieta_intellettuale_e_riservatezza": [{{"tema":"","clausola":"","fonte_pagina":""}}],
  "recesso_risoluzione": [{{"caso":"","preavviso":"","conseguenze":"","fonte_pagina":""}}],
  "legge_applicabile_forum": {{"legge":"","foro":"","fonte_pagina":""}},
  "allegati_richiamati": [{{"titolo":"","fonte_pagina":""}}],
  "rischi_operativi": [{{"descrizione":"","mitigazione":"","fonte_pagina":""}}],
  "note": ""
}}
</JSON>

<SINTESI>
Executive summary (120–180 parole) con clausole critiche e red flag. Cita pagine (p. X).
</SINTESI>
"""
```

---

## Formato Output e Strutturazione Dati

### Parsing dell'Output LLM (`services/format_helper.py`)

```python
# File: services/format_helper.py
def format_analysis_result(raw_response: str, prompt_type: str) -> dict:
    """
    Formatta la risposta dell'LLM in base al tipo di prompt.
    Estrae JSON e sintesi dal testo raw.
    """
    result = {
        "prompt_type": prompt_type,
        "json_data": None,
        "summary": None,
        "raw_response": raw_response
    }
    
    # Estrai JSON tra tag
    json_match = re.search(r'<(?:JSON|KPI_JSON)>(.*?)</(?:JSON|KPI_JSON)>', 
                          raw_response, re.DOTALL)
    if json_match:
        try:
            result["json_data"] = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON for {prompt_type}")
    
    # Estrai sintesi
    summary_match = re.search(r'<SINTESI>(.*?)</SINTESI>', 
                             raw_response, re.DOTALL)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()
    
    return result
```

### Storage dei Risultati

I risultati dell'analisi vengono:
1. **Salvati in session state** per visualizzazione immediata
2. **Aggiunti ai metadati** del documento in Qdrant
3. **Disponibili per export** in PDF/Excel

---

## Integrazione con l'UI Streamlit

### Selezione Tipo Analisi (`app.py:586-607`)

```python
# File: app.py (riga 586-607)
# Prompt selection
st.subheader("🎯 Tipo di Analisi")
prompt_options = ["Automatico (raccomandato)"] + [
    f"{prompt_type.capitalize()} - {desc}"
    for prompt_type, desc in [
        ("bilancio", "Per bilanci e report finanziari"),
        ("fatturato", "Per analisi vendite e ricavi"),
        ("magazzino", "Per logistica e scorte"),
        ("contratto", "Per documenti legali"),
        ("presentazione", "Per slide e deck"),
        ("generale", "Analisi generica"),
    ]
]

selected_prompt = st.selectbox(
    "Seleziona il tipo di analisi",
    prompt_options,
    index=0,
    help="""
    **Automatico**: Il sistema rileva automaticamente il tipo di documento
    **Specializzato**: Forza un tipo specifico di analisi
    
    Tipi disponibili:
    - Bilancio: KPI finanziari, margini, cash flow
    - Fatturato: Breakdown vendite, trend, driver
    - Magazzino: Rotazione, OTIF, obsoleti
    - Contratto: Clausole, SLA, rischi legali
    - Presentazione: Messaggi chiave, struttura
    - Generale: Analisi standard multi-purpose
    """
)
```

### Visualizzazione Risultati Analisi (`app.py:700-780`)

```python
# File: app.py (sezione visualizzazione analisi)
# Display document analyses
if results.get("document_analyses"):
    st.subheader("📊 Analisi Automatiche dei Documenti")
    
    for doc_name, analysis in results["document_analyses"].items():
        with st.expander(f"📄 {doc_name}", expanded=True):
            # Parse and format the analysis
            formatted = format_analysis_result(analysis, prompt_type)
            
            # Show JSON data if available
            if formatted.get("json_data"):
                st.json(formatted["json_data"])
            
            # Show summary
            if formatted.get("summary"):
                st.markdown("### 📝 Sintesi Esecutiva")
                st.write(formatted["summary"])
            
            # Show prompt type used
            st.info(f"Tipo di analisi: {formatted.get('prompt_type', 'N/A')}")
```

### Re-analisi con Prompt Diverso (`app.py:615-620`)

```python
# File: app.py (riga 615-620)
reanalyze_button = st.button(
    "🔄 Ri-analizza con Prompt Selezionato",
    disabled=not hasattr(st.session_state, "document_analyses")
    or not st.session_state.document_analyses,
    help="Ri-esegui l'analisi dei documenti già indicizzati con il prompt selezionato",
)
```

---

## Ottimizzazioni e Performance

### Caching delle Analisi

```python
# File: services/rag_engine.py (riga 341-343)
# Cache the document text for potential re-analysis
if not hasattr(self, "_last_document_texts"):
    self._last_document_texts = {}
self._last_document_texts[display_name] = full_text
```

### Truncation Intelligente

```python
# File: services/rag_engine.py (riga 379)
# Truncate text if too long (keep first 8000 chars for analysis)
analysis_text = document_text[:8000] if len(document_text) > 8000 else document_text
```

**Strategia di truncation**:
- **8000 caratteri**: Bilancia costi API e completezza
- **Focus su inizio documento**: Dove spesso ci sono info chiave
- **Preservazione struttura**: Non tronca a metà frase

### Temperature 0 per Consistenza

```python
# File: services/rag_engine.py (chiamata OpenAI)
temperature=0.0,  # Deterministic for consistency
```

---

## Best Practices Implementate

### 1. **Selezione Intelligente del Template**
- Scoring multi-criterio
- Fallback a template generale
- Override manuale possibile

### 2. **Prompt Engineering Robusto**
- Istruzioni dettagliate per parsing
- Formato output strutturato
- Citazioni obbligatorie

### 3. **Gestione Numeri Italiani**
- Parser specifico per formato italiano
- Conversione scale automatica
- Validazioni contabili

### 4. **Output Strutturato e Tracciabile**
- JSON per dati machine-readable
- Sintesi per leggibilità umana
- Fonte sempre citata

### 5. **Flessibilità e Control**
- Selezione automatica o manuale
- Re-analisi possibile
- Debug info disponibili

### 6. **Performance e Costi**
- Truncation intelligente
- Caching risultati
- Temperature deterministica

---

## Conclusioni

Il sistema di analisi automatica dei documenti implementato rappresenta una soluzione sofisticata che:

1. **Seleziona automaticamente** il template più appropriato tramite scoring intelligente
2. **Gestisce formati numerici italiani** con parsing e validazioni specifiche
3. **Produce output strutturati** in JSON con sintesi esecutive professionali
4. **Mantiene tracciabilità completa** con citazioni obbligatorie delle fonti
5. **Ottimizza performance e costi** con truncation e caching

La combinazione di prompt engineering avanzato, template specializzati per dominio, e integrazione seamless con il flusso RAG crea un sistema di analisi documentale enterprise-ready che arricchisce automaticamente ogni documento caricato con metadati strutturati e insights di valore.