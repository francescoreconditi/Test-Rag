# 📊 CSV Support in RAG Documents

## Overview

Il sistema RAG ora supporta completamente i **file CSV** con **analisi automatica** e **insights AI-generated** per l'indicizzazione intelligente.

## ✨ Funzionalità CSV Implementate

### 1. **Upload CSV nella Sezione RAG Documenti**
- Supporto **drag & drop** per file CSV
- Processing automatico con analisi avanzata
- Compatibilità con formati CSV standard

### 2. **Analisi Automatica dei Dati**
Quando carichi un CSV, il sistema automaticamente:

**📊 Analisi Strutturale:**
- Identificazione tipi di dati (numeric, string, date, etc.)
- Conteggio valori mancanti per colonna
- Statistiche descrittive (media, mediana, deviazione standard)
- Analisi correlazioni tra variabili numeriche

**🔍 Insights AI-Generated:**
- Top 10 insight estratti dai dati con LLM
- Pattern detection automatico
- Identificazione anomalie e outliers
- Suggerimenti per analisi aggiuntive

### 3. **Conversione Intelligente per RAG**
I CSV vengono convertiti in **3 tipi di documenti** searchable:

**1. Metadata Document:**
```
Dataset: sales_data.csv
Righe: 1,250
Colonne: 8
Colonne disponibili: date, product, revenue, quantity, region, customer_type, discount, profit

Tipi di Dati:
- date: datetime64
- product: object
- revenue: float64
- quantity: int64
...

Statistiche Principali:
[Summary statistics table]
```

**2. Insight Documents:**
```
Insight #1: Le vendite mostrano una crescita del 15% nel Q4 rispetto al Q3
Insight #2: La regione Nord ha il 35% del fatturato totale
Insight #3: I clienti premium generano il 60% dei profitti
...
```

**3. Data Sample Documents:**
```
Dati dal CSV 'sales_data.csv' (righe 1-10):
[Formatted table with first 10 rows]

Dati dal CSV 'sales_data.csv' (righe 11-20):
[Next 10 rows]
...
```

## 🎯 Modalità di Utilizzo

### Via App Principale (app.py)

1. **Accedi alla sezione** "📚 Analisi Documenti (RAG)"
2. **Carica il CSV** tramite il file uploader
3. **Seleziona tipo analisi**: "Csv - Analisi dati CSV con insights automatici"
4. **Clicca "Indicizza Documenti"**
5. **Visualizza risultati** con notifica specifica per CSV

### Query Examples

Dopo l'indicizzazione, puoi fare query come:
```
"Quali sono i trend principali in questo dataset?"
"Mostrami le correlazioni più interessanti"
"Che insights puoi estrarre dai dati di vendita?"
"Quali anomalie hai trovato nei dati?"
"Dimmi le statistiche principali del dataset"
```

### Con Background Processing (Celery)

Se hai attivato Celery, i CSV vengono processati **in background**:
1. Upload immediato senza blocking UI
2. Processing asincrono con insights generation
3. Notifica al completamento
4. Monitoring progress nella sidebar

## 📈 Tipi di CSV Supportati

### Financial Data
- Bilanci, P&L, cash flow
- Dati di vendita e fatturato
- Budget e forecast

### Business Analytics
- Customer data e CRM exports
- Web analytics e metrics
- Inventory e supply chain data

### Scientific/Technical
- Time series data
- Experimental results
- Survey responses

## 🔧 Configurazione Avanzata

### Prompt Specializzato CSV
- Selezione automatica per riconoscimento CSV
- Prompt "Csv - Analisi dati CSV con insights automatici"
- Ottimizzazione per analisi quantitative

### Fallback Mechanisms
1. **Con CSV Analyzer**: Full analysis + insights
2. **Senza CSV Analyzer**: Basic processing con schema + sample data
3. **Ultimate Fallback**: Trattamento come file di testo

### Performance Optimizations
- **Sample Limiting**: Massimo 100 righe per CSV grandi
- **Chunk Processing**: 10 righe per documento
- **Insight Limiting**: Top 10 insights più rilevanti
- **Caching**: Results caching per query ripetute

## 🎨 User Experience

### Visual Feedback
- **📊 Notifica CSV Detection**: "Rilevati N file CSV..."
- **✅ Success Message**: "File CSV processati con analisi automatica"
- **📊 Processing Info**: "CSV convertiti in documenti searchable"

### Error Handling
- **Graceful Degradation**: Basic processing se analyzer non disponibile
- **Detailed Error Messages**: Info specifiche per troubleshooting
- **Automatic Retry**: Fallback a processing text se CSV parsing fallisce

## 💡 Query Tips

### Best Practices per Query CSV
```
❌ Evita: "Mostrami i dati"
✅ Meglio: "Quali sono le top 5 insight dal dataset?"

❌ Evita: "Cosa c'è nel file?"
✅ Meglio: "Analizza i trend di vendita per regione"

❌ Evita: "Leggi tutto"
✅ Meglio: "Trova correlazioni tra variabili numeriche"
```

### Query Patterns Efficaci
- **Analytical**: "Quali pattern emergono dai dati?"
- **Statistical**: "Mostra le statistiche chiave"
- **Comparative**: "Confronta le performance tra segmenti"
- **Predictive**: "Che trend prevedi basandoti sui dati?"

## 🚀 Future Enhancements

### Planned Features
- **Advanced Charting**: Auto-generation di grafici per insights
- **Data Validation**: Controlli qualità dati automatici
- **Schema Inference**: Auto-detection di business entities
- **Time Series Analysis**: Analisi specializzata per dati temporali
- **Multi-CSV Relations**: Cross-reference tra dataset multipli

### Integration Possibilities
- **BI Tools**: Export verso Tableau, PowerBI
- **Database Connectors**: Import diretto da DB
- **API Endpoints**: RESTful access ai dataset processati
- **Real-time Updates**: Streaming CSV processing

Il supporto CSV trasforma il sistema RAG da document processor a **data intelligence platform** completa!

## 🎯 Example Workflow

```
1. Upload: sales_2024.csv (1,500 rows, 12 columns)
2. Auto-Analysis: 
   - Data types detection
   - 8 insights generated
   - 15 document chunks created
3. Index: All searchable in vector DB
4. Query: "Analizza le performance Q4"
5. Response: AI combines insights + raw data + statistics
```

Questo workflow rende i CSV **query-ready** in pochi secondi con insights automatici!