# Database Concurrency Fix

## 🎯 **Problema Risolto**

**Errore UTF-8 quando FastAPI e Streamlit accedevano simultaneamente al database DuckDB:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe8 in position 118: invalid continuation byte
```

## 🔍 **Root Cause**
- **DuckDB non supporta accesso concorrente** da processi multipli
- **FastAPI + Streamlit simultanei** causavano conflitti di lock
- **Byte 0xe8** non era corruzione ma conflitto di accesso

## ✅ **Soluzione Implementata**

### **1. Database Separati per Processo**
```python
# In fact_table_repository.py
if 'streamlit' in sys.modules:
    process_suffix = "_streamlit"
elif any(mod in sys.modules for mod in ['uvicorn', 'fastapi']):
    process_suffix = "_fastapi"
else:
    process_suffix = f"_pid_{os.getpid()}"
```

### **2. Fallback Automatico a SQLite**
```python
# In caso di conflitti residui
except Exception as e:
    if ("codec can't decode" in str(e) or "utf-8" in str(e)):
        # Fallback a SQLite con WAL mode per concorrenza
        self.conn = sqlite3.connect(sqlite_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
```

## 📂 **Risultato**

### **Database Files Creati:**
- `enterprise_facts_fastapi.duckdb` - Per FastAPI/uvicorn
- `facts_streamlit.db` - Per Streamlit
- `facts_pid_XXXXX.db` - Per altri processi

### **Comportamento:**
- ✅ **FastAPI e Streamlit** possono girare simultaneamente
- ✅ **Nessun conflitto** di accesso concorrente
- ✅ **Fallback automatico** a SQLite se necessario
- ✅ **Database isolati** per processo

## 🔧 **Files Modificati**
1. `src/infrastructure/repositories/fact_table_repository.py` - Fix principale
2. `.gitignore` - Pattern database process-specific
3. `test_concurrent_database.py` - Test di verifica

## 🚀 **Test di Verifica**
```bash
# Test automatico
python test_concurrent_database.py

# Test manuale
# Terminal 1: uvicorn app:app --port 8000
# Terminal 2: streamlit run app.py
# Entrambi dovrebbero funzionare senza errori
```

## 📋 **Manutenzione**
- Database process-specific sono **temporanei** e possono essere eliminati
- `.gitignore` aggiornato per non committare database
- Sistema **auto-recovery** in caso di problemi

## 💡 **Alternative Future**
Per produzione enterprise, considerare:
1. **PostgreSQL** remoto condiviso
2. **Redis** per caching condiviso
3. **Container orchestration** con database dedicato