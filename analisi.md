Perfetto — ecco una guida **step-by-step** per gestire *qualsiasi* report che può uscire da un gestionale (bilanci, vendite, AR/AP, magazzino, HR, banca, ecc.) con una pipeline solida, ripetibile e tracciabile.

# 0) Cosa vuoi ottenere (in sintesi)

* **Input eterogenei** (PDF scansionati/nativi, Excel/CSV, HTML, JSON esportati).
* **Estrazione affidabile** di numeri e testi, con **provenienza** (pagina/sheet/cella).
* **Normalizzazione** coerente (valuta, scala, periodo, perimetro).
* **Validazione/guardrails** per evitare errori.
* **Output** in uno schema unico (facts + dimensioni) + sintesi RAG con citazioni.

# 1) Ingest & rilevamento formato

1. Rileva tipo file → instrada:

   * **PDF nativi**: `pymupdf` (testo + numeri di pagina), tabelle con `camelot`/`tabula`.
   * **PDF scansionati/immagini**: `ocrmypdf` → PDF ricercabile → `pymupdf` + `pytesseract` fallback.
   * **Excel/CSV**: `pandas` (+ `openpyxl`), leggi *tutti* i fogli e conserva sheet, range, header.
   * **HTML/JSON/XML**: parser nativi (`BeautifulSoup`, `json`, `xmltodict`).
2. Estrai **raw blocks**: testo per pagina, tabelle per pagina/sheet, immagini (se utile).
3. Salva **metadati sorgente** (file, hash, pagina/sheet, timestamp import).

# 2) Normalizzazione locale/valute/periodi

* **Locale**: rileva `it_IT` (virgola decimale, punto migliaia). Usa:

  * parsing numeri: regex + `babel.numbers` (o parser custom robusto).
  * percentuali con `%`, negativi tra parentesi `(1.234)`.
* **Scala dichiarata** (“valori in migliaia/milioni”) → propaga come metadato e **riporta a unità base**.
* **Valuta**: estrai codice (EUR, USD…). Non convertire salvo richiesta; se converti, salva **tasso e fonte**.
* **Periodo**: normalizza in `tipo_periodo` (`FY`, `Q`, `M`, `YTD`) + `inizio`/`fine`. Esempi:

  * “Esercizio 2024” → `FY2024` (2024-01-01→2024-12-31).
  * “Q2 2025” → `Q2 2025` (date coerenti con il tuo calendario fiscale).
  * “01/01–31/03/2025” → `Q1 2025` se mappa trimestri standard.

# 3) Ontologia & dizionario sinonimi (modulare)

Definisci un’**ontologia** di metriche/dimensioni che copra il 90% dei casi:

* **Dimensioni**: azienda, BU, centro di costo, cliente/fornitore, prodotto, periodo, scenario (Actual/Budget/Forecast), valuta, unità, perimetro (civilistico/consolidato/gestionale).
* **Misure canoniche** (estratte *o* calcolabili):

  * Finance: Ricavi, COGS, Margine lordo, Opex, EBITDA, EBIT, Oneri/Proventi fin., Imposte, Utile netto.
  * SP: Cassa, Debito breve/lungo, Debito lordo, PFN, PN, Rimanenze, Crediti/Debiti comm.li, Fondi.
  * CF: CFO, CFI, CFF, Capex, FCF.
  * Vendite: Fatturato, Quantità, Sconto %, Margine %, Ticket medio, Ordini, ARPU.
  * Crediti/Incassi: DSO, scaduto, incassi mese.
  * Magazzino: Stock, Rotazione, Giacenza media, Obsolescenza.
  * HR: FTE, Costo medio, Turnover.
* **Sinonimi** (YAML mantenibile):

```yaml
ricavi:
  - ricavi
  - fatturato
  - vendite
  - ricavi delle vendite
pfn:
  - pfn
  - posizione finanziaria netta
  - indebitamento netto
ebitda:
  - ebitda
  - mol
```

# 4) Router “structured vs unstructured”

* **Structured (Excel/CSV/JSON)** → parser tabellare (no LLM), mappatura header→metrica via sinonimi + fuzzy match (`rapidfuzz`), con regole di “totale/sottototale”.
* **Unstructured (PDF testuale/narrativa)** → **retrieval ibrido** (BM25 + vettoriale) a **granularità di pagina** + LLM per estrazione e sintesi.

# 5) Estrazione numeri & testo (con provenienza)

* **Tabelle**: `camelot` (lattice/stream) e `pdfplumber` come fallback; gestisci merged cells e note a piè di pagina.
* **Testo**: vicinanza *etichetta → numero* (regex robuste) e pattern tipo:

  * `^Ricavi\s*[:\-]?\s*([\-()0-9\., ]+)`
  * `%` e `x` come unità.
* **Provenienza**: salva sempre `source_ref`:

  * PDF → `file.pdf|p.12|tabella:1|riga:"Ricavi"`
  * Excel → `file.xlsx|sheet:"CE"|cell:B12`
* **Criterio di verità**: se stessa metrica appare più volte, preferisci quella:

  * più recente, con label più specifica, o dentro “Prospetti” vs narrativa.

# 6) Guardrails & validazioni

* **Coerenze contabili**:

  * `Attivo Totale == Passivo Totale` (± tolleranza).
  * `PFN == Debito lordo − Cassa` (se entrambe note).
  * `Margine lordo == Ricavi − COGS`.
* **Vincoli di range**: `%` tra −100% e 100% (salvo casi particolari), multipli noti (PFN/EBITDA non negativo se definizioni standard).
* **Perimetro/periodo**: la stessa formula usa **stesso periodo e perimetro**.
* **Duplicati**: dedup su `(metrica, periodo, perimetro, scenario, dimensioni)`.

# 7) Calcoli “consentiti”

* Calcola **solo** se **tutti gli input** sono presenti e coerenti; salva:

  * `calculated_from`: elenco input con `source_ref`.
  * `formula`: espressa in stringa (es. `"pfn = debito_lordo - cassa"`).
* Esempi utili: Margine EBITDA %, ROS, PFN/EBITDA, Coverage, CCN, Rotazione magazzino.

# 8) Modello dati (storage)

* **Facts**: tabella unica `fact_kpi` con colonne:

  * `entity_id, metrica, valore, unita, valuta, periodo_key, scenario, perimetro, dims_json, source_ref, quality_flags, calculated_from, formula`
* **Dimensioni**: `dim_periodo`, `dim_azienda`, `dim_prodotto` ecc.
* **Tecnologia**: locale → `DuckDB` o `SQLite`; server → `PostgreSQL`. Per analytics veloci: `DuckDB` + parquet.
* **Document store** (per RAG): `LanceDB`/`Chroma`/`Qdrant` con metadati (file, pagina, sezioni).

# 9) Retrieval & Sintesi (RAG)

* **Indicizzazione**: chunk per **pagina** (ID fisso), più “blocchi tabella” come chunk separati.
* **Retrieval ibrido**: BM25 (`rank_bm25`) + embedding (`sentence-transformers`) → **reranker** (cross-encoder) su top-k.
* **Generazione**:

  * Prompt robusti (come il tuo `<KPI_JSON>` + `<SINTESI>`).
  * Citation builder automatico → “p. X” (o `sheet:CE!B12`).
* **Post-gen check**: valida JSON con `pydantic`; ricalcola coerenze; rifiuta/higlight se falliscono.

# 10) Orchestrazione, logging, qualità

* **Orchestrazione**: `Prefect` (più leggero di Airflow) per flussi ingest→parse→normalize→validate→persist→rag.
* **Data quality**: `Great Expectations` per test (es. “Ricavi non null su FY”, “Attivo=Passivo”).
* **Versioning**: snapshot parquet + `DVC`/git-LFS per dati/artefatti.
* **Observability**: log strutturati (JSON), metriche estrazioni (precision/recall su campioni etichettati).

# 11) Sicurezza & PII

* Cifratura at-rest (DB) e at-transit (TLS).
* Mascheramento PII (CF, IBAN) nei log.
* Controlli accesso per azienda/BU (row-level security su Postgres).

# 12) Stack Python consigliato

* **Parsing**: `pymupdf`, `pdfplumber`, `camelot-py`/`tabula-py`, `ocrmypdf`, `pytesseract`, `pandas`, `openpyxl`.
* **NLP/RAG**: `sentence-transformers`, `faiss-cpu`/`qdrant-client`/`lancedb`, `rank-bm25`, `transformers` (cross-encoder).
* **Validazione**: `pydantic`, `great_expectations`, `babel`, `python-dateutil`, `pint` (unità).
* **Orchestrazione/DB**: `prefect`, `duckdb`, `sqlalchemy`, `postgres`.
* **Utils**: `rapidfuzz`, `regex`, `loguru`.

# 13) Skeleton operativo (minimo funzionante)

```python
# pip install pymupdf pdfplumber camelot-py ocrmypdf pytesseract pandas openpyxl rapidfuzz regex
# pip install sentence-transformers faiss-cpu rank-bm25 pydantic babel python-dateutil pint duckdb
from dataclasses import dataclass

@dataclass
class ProvenancedValue:
    value: float
    unit: str
    currency: str|None
    period: str
    perimeter: str|None
    source_ref: str   # "file.pdf|p.12|tab:1|row:Ricavi"

# 1) detect → route
def route_file(path): ...

# 2) parse tables/text per page/sheet → yield (label, number, ProvenancedValue)

# 3) normalizza (locale, scala, valuta, periodo)

# 4) map a metrica canonica (synonyms + fuzzy)
def map_metric(label:str)->str: ...

# 5) salva su fact_kpi + dims (duckdb/postgres)

# 6) RAG: indicizza pagine/tabelle (BM25+embeddings), rerank, genera <KPI_JSON>/<SINTESI>

# 7) validazioni (GE) + guardrails (pydantic), calcoli consentiti con lineage
```

# 14) Roadmap pratica (4 sprint)

* **S1 (MVP)**: ingest PDF/Excel, estrazione Ricavi/EBITDA/PFN/cassa, provenienza, storage DuckDB, prompt `<KPI_JSON>/<SINTESI>`.
* **S2**: estendi a AR/AP, vendite, magazzino; dizionario sinonimi modulare; validazioni GE; router completo.
* **S3**: RAG ibrido + cross-encoder; calcoli consentiti + lineage; UI semplice (Streamlit) con anteprima pagina.
* **S4**: orchestrazione Prefect, utenti/ruoli, audit trail, benchmark qualità su set “gold”.

---

Se vuoi, ti preparo un **repo scheletro** con:

* template YAML di ontologia/sinonimi,
* modelli `pydantic`,
* parser PDF/Excel con provenienza,
* validazioni GE,
* indice RAG con retrieval ibrido e un notebook demo che produce il tuo `<KPI_JSON>` e `<SINTESI>`.
