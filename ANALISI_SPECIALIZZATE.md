# Sistema di Analisi Specializzate - Documentazione

## Panoramica
Il sistema ora supporta **analisi specializzate** in tre momenti diversi del workflow:

### 1. **Durante l'Indicizzazione** (già esistente)
Quando carichi un documento, puoi scegliere il tipo di analisi da applicare:
- **Automatico**: Il sistema sceglie il prompt migliore basandosi sul contenuto
- **Specifico**: Forzi un tipo particolare (Bilancio, Fatturato, etc.)

### 2. **Ri-analisi Post-Indicizzazione** (già esistente) 
Dopo aver indicizzato, puoi ri-analizzare i documenti con un prompt diverso usando il pulsante "Ri-analizza con Prompt Selezionato"

### 3. **Durante le Query** ⭐ **NUOVA FUNZIONALITÀ**
Ora puoi applicare analisi specializzate anche quando fai domande ai documenti già nel database!

## Come Funziona l'Analisi Specializzata nelle Query

### Selezione del Tipo di Analisi
Nella sezione "🔍 Interroga Documenti", trovi ora un menu a tendina "🎯 Tipo di Analisi per Query" con queste opzioni:

1. **Standard (RAG normale)**: Query tradizionale senza elaborazione aggiuntiva
2. **Bilancio**: Analisi finanziaria professionale con focus su metriche, trend e confronti
3. **Report Dettagliato**: Stile investment memorandum con executive summary strutturato
4. **Fatturato**: Focus su vendite, revenue e driver di crescita
5. **Magazzino**: Focus su logistica e gestione scorte
6. **Contratto**: Focus su aspetti legali e contrattuali
7. **Presentazione**: Focus su messaggi chiave e raccomandazioni strategiche

### Processo di Elaborazione

Quando selezioni un tipo di analisi diverso da "Standard":

1. **Query Enhancement**: La domanda viene arricchita con contesto specifico per il tipo di analisi
2. **Retrieval**: Il sistema recupera i documenti rilevanti dal database vettoriale
3. **Post-Processing**: La risposta viene rielaborata con un prompt specializzato che:
   - Ristruttura il contenuto secondo il formato professionale richiesto
   - Aggiunge quantificazioni e metriche specifiche
   - Applica il tono e lo stile appropriato (es. equity analyst, legal advisor, etc.)

### Esempi di Output

#### Analisi Standard
```
I principali rischi menzionati sono l'aumento dei costi operativi 
e la pressione competitiva nel mercato.
```

#### Analisi BILANCIO
```
[Analisi BILANCIO]

## Analisi Finanziaria dei Rischi

**Rischi Operativi Identificati:**
- Incremento OPEX: +24% YoY (€776.640 vs €626.495 P.Y.)
  - Impatto su marginalità: riduzione EBITDA margin di 0.5pp
  - Driver principale: costi commerciali (+46.7% YoY)
  
**Rischi di Mercato:**
- Pressione competitiva con erosione margini lordi (-1.4pp vs P.Y.)
- Concentrazione clienti: top 5 rappresentano 35% dei ricavi

**Implicazioni Finanziarie:**
- Necessità di ottimizzazione costi per mantenere target EBITDA 11%
- Rischio covenant se EBITDA scende sotto €450k (attuale: €547k)
```

#### Analisi REPORT DETTAGLIATO
```
[Analisi REPORT_DETTAGLIATO]

## Executive Summary
L'analisi evidenzia due aree critiche di rischio che richiedono 
attenzione immediata del management.

## Analisi Dettagliata
1. **Rischio Operativo - ALTO**
   - Crescita OPEX insostenibile: +39.1% vs Budget
   - ROI investimenti commerciali non dimostrato
   - Azione richiesta: cost review immediata

2. **Rischio Competitivo - MEDIO**
   - Erosione quote di mercato nei segmenti premium
   - Pricing power in diminuzione
   - Azione richiesta: revisione strategia di posizionamento

## Raccomandazioni
- Implementare controllo costi Q1 2025
- Diversificare base clienti (target: <25% concentrazione)
- Review trimestrale KPI operativi
```

## Vantaggi del Sistema

### Per l'Analisi Finanziaria (vs Google NotebookLM)
- **Strutturazione Professionale**: Output formattato come briefing document o investment memo
- **Quantificazione Precisa**: Sempre con numeri, percentuali e confronti YoY/Budget
- **Multi-prospettiva**: Stessa domanda, diverse angolazioni di analisi
- **Contesto Preservato**: Le fonti originali sono sempre citate e verificabili

### Flessibilità d'Uso
- **Non invasivo**: I documenti nel DB non vengono modificati
- **Reversibile**: Puoi sempre tornare all'analisi standard
- **Combinabile**: Puoi usare diversi tipi di analisi per diverse domande
- **Context-aware**: Funziona anche con il contesto CSV attivato

## Best Practices

1. **Usa "Standard" per**: Domande generiche, ricerca semplice di informazioni
2. **Usa "Bilancio" per**: Analisi finanziarie, metriche, confronti numerici
3. **Usa "Report Dettagliato" per**: Executive summary, presentazioni al board
4. **Usa tipi specifici quando**: Vuoi un focus particolare su un aspetto

## Note Tecniche

- Il sistema mantiene sempre le fonti originali per trasparenza
- L'analisi specializzata aggiunge 1-2 secondi al tempo di risposta
- Consuma token aggiuntivi per il post-processing (circa 500-1000 token)
- La qualità dipende dalla rilevanza dei documenti recuperati dal RAG

## Confronto con l'Approccio Precedente

| Aspetto | Prima | Ora |
|---------|-------|-----|
| Analisi durante query | Solo RAG standard | 7 tipi di analisi specializzate |
| Formato output | Testo semplice | Strutturato professionalmente |
| Quantificazione | Variabile | Sempre con metriche precise |
| Stile | Generico | Specifico per ruolo (analyst, legal, etc.) |
| Flessibilità | Limitata | Cambio analisi al volo |

## Esempio Completo di Workflow

1. **Carica documento**: Report_SWD_Aprile_2025.pdf con analisi "Automatica"
2. **Sistema identifica**: È un report finanziario, applica prompt "report_dettagliato"
3. **Query 1**: "Quali sono i rischi?" con analisi "Standard" → risposta semplice
4. **Query 2**: Stessa domanda con analisi "Report Dettagliato" → briefing professionale
5. **Query 3**: Stessa domanda con analisi "Bilancio" → focus su metriche finanziarie

Ogni query produce un output diverso, ottimizzato per lo scopo specifico!