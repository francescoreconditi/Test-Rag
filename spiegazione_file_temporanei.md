# 🔍 Spiegazione: Percorsi File Temporanei nelle Fonti

## ❓ **Il Problema che Hai Riscontrato**

Quando l'app mostra i metadata delle fonti, vedevi percorsi tipo:
```
"source": "C:\Users\franc\AppData\Local\Temp\tmps62y0efr.pdf"
```

E questo file **non esisteva** più sul disco. Ecco perché:

## 🔄 **Come Funziona il Processo**

### **1. Upload del File**
```python
# L'utente carica "report_finanziario.pdf" tramite Streamlit
uploaded_file = st.file_uploader(...)
```

### **2. Salvataggio Temporaneo**
```python
# Streamlit salva il file in una cartella temp con nome casuale
with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
    tmp_file.write(uploaded_file.getbuffer())
    # tmp_file.name = "C:\...\Temp\tmps62y0efr.pdf"
```

### **3. Indicizzazione**
```python
# Il sistema indicizza il file usando il path temporaneo
rag_engine.index_documents([tmp_file.name])
# I metadata vengono salvati con il percorso temporaneo
```

### **4. Cleanup Automatico**
```python
# Dopo l'indicizzazione, il file viene eliminato per sicurezza
os.unlink(tmp_file.name)  # File eliminato!
# Ma i metadata nel database vettoriale conservano il vecchio path
```

### **5. Query Successive**
```python
# Quando fai query, il sistema trova i chunk indicizzati
# Ma nei metadata c'è ancora il path del file eliminato!
```

## ✅ **La Soluzione Implementata**

Ho risolto il problema modificando il codice per:

### **1. Conservare Nome Originale**
```python
# Ora salviamo sia il path temporaneo che il nome originale
original_names.append(uploaded_file.name)  # "report_finanziario.pdf"
```

### **2. Usare Nome Friendly nei Metadata**
```python
# Nei metadata ora viene salvato il nome leggibile
doc.metadata.update({
    'source': display_name,        # "report_finanziario.pdf" 
    'original_path': file_path,    # Path temp (per uso interno)
})
```

### **3. Messaggio Informativo**
Aggiunto un avviso che spiega:
> "I documenti sono stati processati e indicizzati. I file temporanei sono stati rimossi per sicurezza, ma il contenuto rimane accessibile per le query."

## 🛡️ **Perché è Normale e Sicuro**

### **Vantaggi della Gestione Temporanea:**
- **Sicurezza**: I file sensibili non rimangono sul server
- **Privacy**: Nessun file permanente salvato
- **Spazio**: Non si accumula spazzatura sul disco
- **Efficienza**: I dati sono comunque indicizzati e ricercabili

### **Il Contenuto Rimane Disponibile:**
- ✅ **Testo estratto**: Salvato nei vettori di Qdrant
- ✅ **Ricerca semantica**: Funziona perfettamente
- ✅ **Query AI**: Accesso completo al contenuto
- ✅ **Metadata essenziali**: Nome file, tipo, data indicizzazione

## 🎯 **Risultato Finale**

Ora nei metadata vedrai:
```json
{
  "source": "report_finanziario.pdf",  ← Nome leggibile!
  "page": 3,
  "file_type": ".pdf",
  "indexed_at": "2025-09-04T19:41:31"
}
```

Invece del vecchio percorso temporaneo illeggibile!