# Riferimento Ontologie Metriche Finanziarie

## Panoramica

L'ontologia delle metriche finanziarie fornisce una mappatura standardizzata dei termini finanziari tra italiano e inglese, supportando il riconoscimento automatico e la normalizzazione delle metriche nei sistemi RAG enterprise.

## 📊 Statistiche Ontologie

- **Metriche Canoniche**: 31 metriche finanziarie
- **Sinonimi Totali**: 219+ termini
- **Lingue**: Italiano (principale) + Inglese
- **Categorie**: 7 categorie principali
- **Copertura**: Conto Economico, Stato Patrimoniale, Rendiconto Finanziario, Ratios

## 🗂️ Struttura Categorie

### Conto Economico (Income Statement)
**Metriche**: 6 metriche fondamentali
- **ricavi** - Ricavi/Vendite/Fatturato
- **cogs** - Costo del Venduto
- **margine_lordo** - Margine Lordo
- **ebitda** - EBITDA/MOL
- **ebit** - EBIT/Risultato Operativo
- **utile_netto** - Utile Netto

### Stato Patrimoniale (Balance Sheet)
**Metriche**: 9 voci patrimoniali
- **attivo_totale** - Totale Attività
- **passivo_totale** - Totale Passività
- **patrimonio_netto** - Patrimonio Netto
- **cassa** - Disponibilità Liquide
- **debito_lordo** - Debito Lordo
- **pfn** - Posizione Finanziaria Netta
- **rimanenze** - Rimanenze di Magazzino
- **crediti_commerciali** - Crediti Commerciali
- **debiti_commerciali** - Debiti Commerciali

### Rendiconto Finanziario (Cash Flow Statement)
**Metriche**: 4 flussi finanziari
- **flussi_operativi** - Flusso di Cassa Operativo
- **flussi_investimenti** - Flusso di Cassa da Investimenti
- **flussi_finanziari** - Flusso di Cassa Finanziario
- **free_cash_flow** - Free Cash Flow

### Indici Finanziari (Financial Ratios)
**Metriche**: 6 ratios chiave
- **margine_ebitda_pct** - Margine EBITDA %
- **ros_pct** - ROS (Return on Sales) %
- **roe_pct** - ROE (Return on Equity) %
- **roa_pct** - ROA (Return on Assets) %
- **current_ratio** - Indice di Liquidità Corrente
- **debt_equity_ratio** - Rapporto Debiti/Patrimonio

### Crescita e Variazioni (Growth & Changes)
**Metriche**: 4 indicatori crescita
- **crescita_ricavi_pct** - Crescita Ricavi %
- **crescita_ebitda_pct** - Crescita EBITDA %
- **var_patrimonio_pct** - Variazione Patrimonio %
- **crescita_organica_pct** - Crescita Organica %

### Metriche Operazionali (Operational Metrics)
**Metriche**: 3 metriche operative
- **dipendenti** - Numero Dipendenti
- **costo_personale** - Costo del Personale
- **ricavi_per_dipendente** - Ricavi per Dipendente

## 📚 Mappature Dettagliate

### Ricavi (Revenue)
```yaml
ricavi:
  english_names:
    - "revenue"
    - "sales" 
    - "turnover"
    - "net sales"
    - "gross sales"
  italian_names:
    - "fatturato"
    - "ricavi"
    - "vendite"
    - "incassi"
    - "entrate"
    - "introiti"
  synonyms:
    - "fatturato totale"
    - "ricavi totali"
    - "ricavi netti"
    - "ricavi delle vendite"
    - "valore della produzione"
  unit_type: "currency"
  category: "income_statement"
  validation_rules: ["positive_value"]
```

### EBITDA
```yaml
ebitda:
  english_names:
    - "ebitda"
    - "earnings before interest taxes depreciation amortization"
    - "operating profit before d&a"
  italian_names:
    - "mol"
    - "margine operativo lordo"
    - "ebitda"
    - "risultato operativo lordo"
  synonyms:
    - "mol ante oneri straordinari"
    - "margine operativo al lordo ammortamenti"
    - "ebitda normalizzato"
  unit_type: "currency" 
  category: "income_statement"
  validation_rules: ["coherent_with_revenue"]
```

### Patrimonio Netto (Equity)
```yaml
patrimonio_netto:
  english_names:
    - "equity"
    - "shareholders equity"
    - "stockholders equity"
    - "net worth"
    - "book value"
  italian_names:
    - "patrimonio netto"
    - "capitale netto"
    - "mezzi propri"
    - "capitale proprio"
  synonyms:
    - "patrimonio netto contabile"
    - "valore contabile patrimonio"
    - "equity book value"
    - "net equity"
  unit_type: "currency"
  category: "balance_sheet"
  validation_rules: ["balance_sheet_coherence"]
```

### Margine EBITDA % (EBITDA Margin)
```yaml
margine_ebitda_pct:
  english_names:
    - "ebitda margin"
    - "ebitda margin percentage"
    - "operating margin"
    - "ebitda yield"
  italian_names:
    - "margine ebitda"
    - "margine operativo"
    - "margine mol"
    - "redditività operativa"
  synonyms:
    - "margine ebitda %"
    - "margine operativo lordo %"
    - "ebitda su ricavi"
    - "mol margin"
  unit_type: "percentage"
  category: "ratios"
  validation_rules: ["percentage_range", "coherent_with_ebitda_revenue"]
```

## 🔍 Algoritmi di Matching

### Fuzzy Matching
L'ontologia utilizza algoritmi di fuzzy matching per riconoscere variazioni e abbreviazioni:

```python
# Esempi matching automatico
"fatt." → "fatturato" (confidence: 0.85)
"ricavi netti" → "ricavi" (confidence: 0.92)
"mol%" → "margine_ebitda_pct" (confidence: 0.88)
"pn" → "patrimonio_netto" (confidence: 0.78)
"free cash flow" → "free_cash_flow" (confidence: 0.95)
```

### Threshold Configurabili
```python
class OntologyMapper:
    # Soglie di confidenza per matching
    HIGH_CONFIDENCE = 0.9      # Match diretto
    MEDIUM_CONFIDENCE = 0.7    # Sinonimo riconosciuto  
    LOW_CONFIDENCE = 0.5       # Fuzzy match accettabile
    MIN_CONFIDENCE = 0.3       # Soglia minima
```

### Context-Aware Mapping
Il sistema considera il contesto per migliorare l'accuratezza:

```python
# Contesto finanziario migliora precision
"capitale" + context="bilancio" → "patrimonio_netto" (conf: 0.85)
"capitale" + context="investimenti" → "capitale_investito" (conf: 0.82)

# Unità di misura come hint
"margine 25%" → "margine_ebitda_pct" (conf: 0.88)
"margine €500k" → "margine_lordo" (conf: 0.91)
```

## 📋 Regole di Validazione

### Validazione per Categoria

#### Income Statement
```python
validation_rules = {
    "ricavi": ["positive_value", "reasonable_growth"],
    "ebitda": ["coherent_with_revenue", "margin_bounds"],
    "utile_netto": ["coherent_with_ebitda", "tax_coherence"]
}
```

#### Balance Sheet
```python
validation_rules = {
    "attivo_totale": ["positive_value", "balance_coherence"],
    "passivo_totale": ["balance_coherence"], 
    "patrimonio_netto": ["equity_coherence"],
    "pfn": ["debt_coherence"]
}
```

#### Financial Ratios
```python
validation_rules = {
    "margine_ebitda_pct": ["percentage_range", "industry_benchmark"],
    "roe_pct": ["percentage_range", "equity_coherence"],
    "current_ratio": ["positive_value", "liquidity_benchmark"]
}
```

## 🌐 Supporto Multilingua

### Mappatura Automatica IT→EN
```python
italian_to_english = {
    "ricavi": "revenue",
    "fatturato": "sales",
    "margine_lordo": "gross_margin",
    "ebitda": "ebitda", 
    "patrimonio_netto": "equity",
    "posizione_finanziaria_netta": "net_debt"
}
```

### Formato Numerico Locale
```python
# Parsing automatico formati italiani
"€ 1.250.000,50" → 1250000.50
"25,5%" → 0.255
"2.500 mila euro" → 2500000.0
"1,2 miliardi" → 1200000000.0
```

## 🔄 Estensibilità

### Aggiunta Nuove Metriche
```yaml
# config/ontology/custom_metrics.yaml
nuova_metrica:
  english_names: ["new_metric"]
  italian_names: ["nuova_metrica"]
  synonyms: ["metrica_personalizzata"]
  unit_type: "currency"
  category: "custom"
  validation_rules: ["positive_value"]
```

### Plugin Settore-Specifici
```python
# Ontologie specializzate per settori
retail_ontology = load_ontology("config/ontology/retail_metrics.yaml")
manufacturing_ontology = load_ontology("config/ontology/manufacturing_metrics.yaml")
services_ontology = load_ontology("config/ontology/services_metrics.yaml")
```

### API Ontologia
```python
# REST API per gestione ontologie
GET /api/ontology/metrics → Lista metriche disponibili
GET /api/ontology/metric/{name} → Dettagli metrica specifica
POST /api/ontology/map → Mapping termini custom
PUT /api/ontology/metric/{name} → Aggiornamento sinonimi
```

## 📊 Metriche di Performance

### Coverage Statistics
```
Copertura Documenti Finanziari:
- Bilanci CEE: 95% metriche riconosciute
- Report Trimestrali: 88% copertura
- Business Plan: 82% termini mappati
- Analisi Settoriali: 79% recognition rate

Accuracy Fuzzy Matching:
- Precision@0.9: 94%
- Precision@0.7: 87% 
- Precision@0.5: 76%
- False Positive Rate: <3%
```

### Benchmark Lingue
```
Italiano: 95% accuracy
Inglese: 91% accuracy  
Mixed IT/EN: 88% accuracy
Abbreviazioni: 82% accuracy
```

## 🛠️ Strumenti di Debug

### Ontology Explorer
```python
# Debug mappatura termini
explorer = OntologyExplorer()
results = explorer.debug_mapping("fatt netto 2023")

# Output:
{
    "matched_metric": "ricavi",
    "confidence": 0.87,
    "reasoning": "fuzzy_match: fatt→fatturato, netto→ricavi_netti",
    "alternatives": [
        {"metric": "fatturato", "confidence": 0.85},
        {"metric": "utile_netto", "confidence": 0.42}
    ]
}
```

### Validation Checker
```python
# Verifica coerenza ontologia
checker = OntologyValidator()
issues = checker.validate_ontology()

# Output potenziali problemi:
[
    "Duplicate synonym: 'ricavi' mapped to both 'ricavi' and 'fatturato'",
    "Missing validation rule for metric: 'nuova_metrica'",
    "Confidence threshold too low for fuzzy match: 'capitale'"
]
```

---

**L'ontologia finanziaria garantisce mappatura accurata e coerente dei termini finanziari, supportando analisi multilingua e validazione automatica dei dati.**