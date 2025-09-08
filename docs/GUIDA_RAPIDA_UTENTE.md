# 🚀 Guida Rapida Utente - Sistema RAG Enterprise

## 📖 Introduzione

Benvenuto nel **Sistema RAG di Business Intelligence Enterprise**! Questa guida ti aiuterà a utilizzare rapidamente le **funzionalità avanzate** (Gennaio 2025) tra cui data quality validation, calcoli derivati automatici e tracciabilità granulare per analizzare i tuoi dati finanziari con massima precisione.

---

## 🎯 Avvio Rapido (5 Minuti)

### 1. **Avvia il Sistema**
```bash
# Windows
start.bat

# Linux/Mac  
./start.sh
```

### 2. **Apri il Browser**
- Vai su: `http://localhost:8501`
- Il sistema si avvierà automaticamente

### 3. **Attiva la Modalità Enterprise Avanzata** 
- Nella barra laterale sinistra, attiva **🚀 Modalità Enterprise**
- Vedrai apparire:
  - ✅ **Quality Metrics**: Completeness, Accuracy, Consistency, Validity 
  - 🔄 **Calculated Metrics**: 15+ formule automatiche (PFN, ROE, Current Ratio, DSO)
  - 📊 **Granular Provenance**: Tracciabilità cella-per-cella
  - ⚡ **Processing Statistics**: Tempi elaborazione e confidence scores

---

## 🖥️ Navigazione Interfaccia

### **Pagina Principale** (`Home`)
- **Chat RAG**: Interfaccia conversazionale principale
- **Upload Documenti**: Carica PDF, Excel, Word per analisi
- **Modalità Enterprise**: Attiva funzionalità avanzate
- **Sidebar**: Statistiche, configurazione, controlli

### **📊 Analytics Dashboard** 
- **Accesso**: Seleziona dalla sidebar o vai alla pagina dedicata
- **Funzionalità**: KPI interattivi, grafici trend, health score aziendale

### **🔍 Document Preview**
- **Accesso**: Pagina dedicata nel menu
- **Funzionalità**: Anteprima documenti, thumbnails, estrazione metriche

### **✏️ Interactive Editor**
- **Accesso**: Pagina dedicata nel menu  
- **Funzionalità**: Modifica metriche in tempo reale, validazione automatica

---

## 🚀 Funzionalità Enterprise Avanzate (NUOVO - Gennaio 2025)

### **✅ Data Quality Validation**
Il sistema ora include **Great Expectations** per validazioni automatiche:

**1. Validazioni Balance Sheet**
- ✅ **Coerenza Attivo = Passivo** (tolleranza ±1%)
- ⚠️ Segnala incongruenze contabili automaticamente

**2. Validazioni PFN (Posizione Finanziaria Netta)**  
- ✅ **Verifica PFN = Debito Lordo - Cassa** (tolleranza ±1%)
- 📊 Mostra deviazioni e suggerimenti correzioni

**3. Validazioni Range**
- ✅ **Percentuali ragionevoli** (-100% < x < 100%)
- ✅ **Valori finanziari non estremi** 

### **🔄 Calcoli Derivati Automatici**
Il **Calculation Engine** calcola automaticamente **15+ metriche finanziarie**:

**Metriche Disponibili:**
- **Margini**: Margine Lordo, EBITDA %, ROS %
- **Redditività**: ROE %, ROIC %  
- **Liquidità**: Current Ratio, Quick Ratio
- **Efficienza**: DSO (giorni), Rotazione Magazzino
- **Posizione Finanziaria**: PFN, PFN/EBITDA Ratio
- **Coverage**: Interest Coverage Ratio

**Lineage Completo:** Ogni calcolo include:
- 📐 **Formula** utilizzata (es: "pfn = debito_lordo - cassa")
- 📊 **Input Sources** con provenienza precisa  
- 🎯 **Confidence Score** (0.0 - 1.0)
- ⏰ **Timestamp** elaborazione

### **📍 Provenienza Granulare** 
Tracciabilità **cella-per-cella** per massima precisione:

**Excel Tracking:**
```
bilancio.xlsx|sheet:Conto Economico|cell:B12|row:Ricavi|col:2024
```

**PDF Tracking:**
```  
report.pdf|p.5|tab:2|coords(100.0,200.0,500.0,400.0)|row:EBITDA
```

**Calculated Values:**
```
calculated/pfn|formula:debito_lordo-cassa|confidence:0.85
```

---

## 📊 Dashboard Analytics - Guida d'Uso

### **Come Utilizzare il Dashboard**

1. **📤 Carica i Tuoi Dati**
   - Clicca su **"Carica File Dati Finanziari"**
   - Formati supportati: `.xlsx`, `.csv`, `.json`
   - Esempio struttura dati:
   ```csv
   Metrica,Valore,Unita
   Ricavi,10000000,EUR
   EBITDA,1500000,EUR  
   Utile Netto,800000,EUR
   Attivo Totale,15000000,EUR
   Patrimonio Netto,5000000,EUR
   ```

2. **🏭 Seleziona Industria**
   - Scegli tra: **Manufacturing**, **Services**, **Tech**, **Retail**
   - Le soglie KPI si adatteranno automaticamente al tuo settore

3. **📈 Visualizza i KPI**
   - **Gauge Interattivi**: ROE, ROA, Debt-to-Equity, Current Ratio
   - **Colori Dinamici**: 🔴 Critico, 🟡 Attenzione, 🟢 Eccellente

4. **📊 Analizza i Grafici**
   - **Waterfall Chart**: Flusso da Ricavi a Utile Netto
   - **Trend Analysis**: Crescita storica multi-periodo
   - **Radar Efficienza**: Performance multi-dimensionale

### **Interpretazione Health Score**

| Punteggio | Interpretazione | Azioni Consigliate |
|-----------|-----------------|-------------------|
| **90-100** | 🟢 **Eccellente** | Mantieni performance attuali |
| **70-89** | 🟡 **Buono** | Monitora aree di miglioramento |
| **50-69** | 🟠 **Medio** | Interventi mirati necessari |
| **0-49** | 🔴 **Critico** | Azione immediata richiesta |

---

## 🔍 Document Preview - Guida d'Uso

### **Formati Supportati**

| Formato | Funzionalità | Ideale per |
|---------|--------------|------------|
| **📄 PDF** | Thumbnails + OCR + Metadati | Bilanci, Report annuali |
| **📊 Excel** | Analisi fogli + Statistiche | Dati finanziari strutturati |
| **📈 CSV** | Preview dati + Qualità | Export da sistemi gestionali |
| **🖼️ Immagini** | OCR + Proprietà | Screenshot, grafici scansionati |
| **📝 Testo** | Analisi completa | Note, documenti estratti |

### **Come Utilizzare**

1. **📁 Seleziona Origine**
   - **Upload File**: Carica da computer
   - **Documenti Folder**: Seleziona da cartella documenti esistente

2. **⚙️ Configura Preview**
   - **Max Pagine**: 1-10 pagine da analizzare
   - **Dimensione Thumbnail**: Small/Medium/Large

3. **👀 Esamina i Risultati**
   - **Tab "File Info"**: Metadati dettagliati
   - **Tab "Content Preview"**: Estratto testo principale  
   - **Tab "Thumbnails"**: Preview visivo pagine
   - **Tab "Statistics"**: Analisi quantitative 
   - **Tab "Key Metrics"**: Metriche finanziarie rilevate

4. **💾 Salva ed Esporta**
   - **Download Preview Data**: JSON completo per backup
   - **Clear Cache**: Rigenera preview se necessario

### **Rilevamento Automatico Metriche**

Il sistema identifica automaticamente:
- **💰 Valori Monetari**: Ricavi, Costi, Utili, Debiti
- **📊 Ratios**: ROE, ROA, Margini, Liquidità  
- **📈 KPI Operativi**: DSO, Rotazione, Turnover
- **🧮 Percentuali**: Crescite, Variazioni, Indici

---

## ✏️ Interactive Editor - Guida d'Uso

### **Workflow Editing**

1. **🎯 Avvia Sessione**
   - Inserisci nome documento di riferimento
   - Il sistema genera un **Session ID** univoco
   - Carica dati esistenti o inizia da zero

2. **✏️ Modifica Valori**
   - **Editing Diretto**: Clicca su cella e modifica
   - **Batch Update**: Carica CSV per aggiornamenti massivi
   - **Validazione Real-Time**: Controlli istantanei durante la digitazione

3. **🤖 Ricevi Suggerimenti**
   - Il sistema genera **suggerimenti automatici** basati su:
     - Anomalie statistiche (valori Z-score > 2)
     - Incoerenze contabili (es. bilancio sbilanciato)
     - Valori fuori range industria
     - Pattern riconosciuti errori comuni

4. **📋 Applica Correzioni**
   - Seleziona suggerimenti dalla lista
   - Applica singolarmente o in batch
   - Ogni modifica viene tracciata nella cronologia

5. **💾 Gestisci Cronologia**
   - **Undo/Redo**: Annulla/ripristina operazioni
   - **History Timeline**: Visualizza tutte le modifiche
   - **Comments**: Aggiungi note alle modifiche

### **Validazioni Implementate**

#### **🏦 Validazioni Finanziarie Base**
- ✅ **Bilancio**: `Attivo = Passivo + Patrimonio Netto`
- ✅ **PFN**: `Posizione Finanziaria Netta = Debito Lordo - Cassa`
- ✅ **Margini**: `EBITDA ≤ Ricavi`, `Utile Netto ≤ EBITDA`

#### **🎯 Validazioni Dominio-Specifiche**

| Dominio | Metriche | Range Tipici | Soglie Allerta |
|---------|----------|--------------|----------------|
| **💳 AR/AP** | DSO, DPO | 15-180 giorni | >90 giorni |
| **💰 Sales** | Churn Rate | 0-50% | >25% |
| **📦 Inventory** | Rotazione | 2-12x/anno | <2x/anno |
| **👥 HR** | Turnover | 0-30% | >20% |

#### **⚠️ Tipi di Alert**

- 🔴 **Errore Critico**: Blocca salvataggio, richiede correzione immediata
- 🟡 **Avviso**: Segnalazione anomalia, salvataggio consentito
- 🔵 **Informativo**: Suggerimento miglioramento, nessun blocco

---

## 🧠 Modalità Enterprise Avanzata

### **Attivazione Funzionalità Enterprise**

1. **👆 Attiva Toggle**: Sidebar → 🚀 **Modalità Enterprise**

2. **📊 Statistiche Real-Time**: Visualizza nella sidebar:
   - Documenti elaborati
   - Metriche estratte e validate  
   - Performance sistema
   - Riferimenti provenienza dati

3. **🎯 Pipeline Automatica**: Ad ogni query, il sistema:
   - **Classifica** documenti (strutturati/non strutturati)
   - **Recupera** con algoritmi ibridi (BM25 + Embeddings)
   - **Normalizza** formati italiani e multi-valuta
   - **Mappa** all'ontologia di 68 metriche
   - **Valida** coerenza finanziaria
   - **Archivia** in tabella dimensionale con provenienza completa

### **Interpretazione Risultati Enterprise**

#### **📊 Sezione Metriche Rilevate**
```
✅ EBITDA: €1.500.000 (Confidenza: 95%)
✅ ROE: 16.2% (Confidenza: 89%) 
⚠️ DSO: 127 giorni (Sopra media industria)
```

#### **✅ Risultati Validazione**
```
🟢 Bilancio: Bilanciato (Attivo = Passivo + PN)
🟡 PFN: Coerente ma alto (€3.2M vs benchmark €2M)
🔴 Liquidità: Critica (Current Ratio: 0.8 < 1.2 minimo)
```

#### **⚡ Statistiche Elaborazione**  
```
• Tempo elaborazione: 2.3s
• Documenti processati: 5 PDF + 2 Excel
• Metriche estratte: 23/68 disponibili
• Record salvati: 156 fatti dimensionali
• Confidenza media: 91.2%
```

---

## 🎨 Personalizzazione e Configurazione

### **Configurazione Industria**

Adatta soglie e benchmark al tuo settore:

| Settore | ROE Target | EBITDA Margin | Current Ratio | DSO Target |
|---------|------------|---------------|---------------|------------|
| **Manufacturing** | >12% | >15% | 1.5-2.5 | <60gg |
| **Services** | >15% | >20% | 1.2-2.0 | <45gg |
| **Technology** | >18% | >25% | 2.0-4.0 | <30gg |
| **Retail** | >10% | >8% | 1.0-1.8 | <30gg |

### **Impostazioni Visualizzazione**

- **Tema Colori**: Professionale (default) / Colorato / Monocromatico
- **Unità Misura**: EUR (default) / USD / Multiple
- **Formato Numeri**: Italiano (1.234,56) / Internazionale (1,234.56)
- **Lingua Interface**: Italiano (default) / English

---

## 🚨 Risoluzione Problemi Comuni

### **❌ "Servizi Non Disponibili"**
- **Causa**: Dipendenze mancanti (PyMuPDF, Pillow, etc.)
- **Soluzione**: `uv pip install -r requirements.txt`

### **⚠️ "Validazione Fallita"**
- **Causa**: Dati incoerenti o fuori range
- **Soluzione**: Controlla tab "Validation Results" per dettagli specifici

### **🐌 Performance Lente**
- **Causa**: Cache piena o documenti troppo grandi
- **Soluzione**: Clicca "Clear Cache" nelle impostazioni

### **📊 "Nessuna Metrica Rilevata"**
- **Causa**: Formato documento non supportato o OCR fallito
- **Soluzione**: Converti in PDF o Excel, verifica Tesseract installato

### **🔄 "Sessione Editing Scaduta"**
- **Causa**: Inattività prolungata (>30 min)
- **Soluzione**: Riavvia sessione, i dati modificati sono salvati automaticamente

---

## 🎓 Tutorial Video e Esempi

### **📹 Tutorial Consigliati**

1. **🚀 Primo Avvio** (3 min)
   - Installazione e configurazione base
   - Prima query e risultati

2. **📊 Dashboard Analytics** (5 min)
   - Upload dati finanziari
   - Interpretazione KPI e grafici

3. **🔍 Document Preview** (4 min)  
   - Caricamento PDF di bilancio
   - Analisi thumbnails e metriche

4. **✏️ Interactive Editing** (6 min)
   - Sessione editing completa
   - Validazione e suggerimenti

### **📄 File di Esempio**

Nella cartella `examples/` trovi:
- `bilancio_esempio.pdf` - Bilancio societario completo
- `dati_finanziari.xlsx` - Dataset Excel strutturato  
- `kpi_dashboard.csv` - Metriche per dashboard
- `documento_misto.pdf` - PDF con tabelle e testo

---

## 📞 Supporto e Assistenza

### **🆘 Canali di Supporto**

- **📖 Documentazione**: `docs/` folder completa
- **🐛 Bug Reports**: GitHub Issues
- **💬 Discussioni**: GitHub Discussions
- **📧 Email**: support@example.com

### **📋 Prima di Contattare il Supporto**

1. ✅ Hai seguito la guida di installazione?
2. ✅ Hai controllato i log di errore?
3. ✅ Hai provato a riavviare il sistema?
4. ✅ Hai verificato i requisiti di sistema?

### **🔍 Informazioni Utili da Fornire**

- Sistema operativo e versione Python
- Messaggio errore completo
- File di log (`logs/app.log`)
- Passi per riprodurre il problema

---

## 🎯 Best Practices per Risultati Ottimali

### **📊 Preparazione Dati**

1. **Formato Standardizzato**: Usa template Excel/CSV forniti
2. **Denominazioni Coerenti**: "Ricavi" non "Revenue" o "Fatturato"  
3. **Unità Esplicite**: Sempre specificare EUR, %, giorni, etc.
4. **Periodi Chiari**: FY2024, Q1-2024, Gen-24, etc.

### **🔍 Caricamento Documenti**

1. **Qualità PDF**: Evita scansioni a bassa risoluzione
2. **Dimensioni File**: Max 50MB per documento
3. **Lingua Consistente**: Documenti in italiano per risultati ottimali
4. **Struttura Logica**: Tabelle ben formattate, intestazioni chiare

### **✏️ Editing Efficace**

1. **Sessioni Brevi**: Max 20-30 metriche per sessione
2. **Validazione Costante**: Correggi errori immediatamente
3. **Commenti Descrittivi**: Documenta modifiche significative  
4. **Backup Regolari**: Export JSON delle sessioni importanti

### **📈 Monitoraggio Performance**

1. **Health Score Trend**: Monitora variazioni nel tempo
2. **Alert Proattivi**: Configura soglie personalizzate
3. **Benchmark Industria**: Confronta regolarmente con competitor
4. **Review Periodiche**: Revisioni mensili/trimestrali

---

## 🎉 Conclusione

Congratulazioni! Ora hai tutti gli strumenti per utilizzare efficacemente il **Sistema RAG Enterprise** per le tue analisi di Business Intelligence.

### **🚀 Prossimi Passi Consigliati**

1. **Prova il Sistema** con i tuoi primi dati
2. **Esplora le Funzionalità** avanzate gradualmente  
3. **Personalizza** le configurazioni per il tuo settore
4. **Monitora** le performance e ottimizza l'uso

### **📚 Approfondimenti**

- **Documentazione Tecnica**: `docs/UI_UX_ADVANCED.md`
- **Guide Sviluppatori**: `docs/DEVELOPMENT.md`  
- **API Reference**: `docs/API.md`

---

**🎯 Pronto per trasformare i tuoi dati in insight strategici? Inizia ora!**

*Guida aggiornata - Sistema RAG Enterprise v2.0*