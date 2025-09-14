# Database Reset Utility

## Overview
Questo utility permette di ripristinare tutti i database del sistema RAG a uno stato pulito. È particolarmente utile quando si verificano corruzioni dei dati, errori di schema, o semplicemente per iniziare con dati freschi durante lo sviluppo.

## Files
- `database_reset.py` - Script Python principale
- `reset_databases.bat` - Script batch per Windows
- `reset_databases.sh` - Script shell per Linux/Mac

## Funzionalità

### Database Gestiti
1. **Vector Database (Qdrant)** - Elimina tutte le collections
2. **Fact Table Database** - Database SQLite/DuckDB per i fatti
3. **Secure Fact Table Database** - Database con metadati di sicurezza RLS
4. **Cache Directories** - Pulizia cache Python e sistema
5. **Log Files** - Pulizia file di log

### Operazioni
- ✅ **Backup automatico** dei database prima della cancellazione
- ✅ **Reset selettivo** o completo
- ✅ **Creazione dati campione** opzionale
- ✅ **Validazione** dei risultati
- ✅ **Logging dettagliato** delle operazioni

## Utilizzo

### Modo Veloce (Windows)
```cmd
# Reset completo con dati campione
utils\reset_databases.bat

# Reset completo senza backup
utils\reset_databases.bat --no-backup

# Solo database vettoriali
utils\reset_databases.bat --vector
```

### Modo Veloce (Linux/Mac)
```bash
# Reset completo con dati campione  
./utils/reset_databases.sh

# Reset completo senza backup
./utils/reset_databases.sh --no-backup

# Solo cache e logs
./utils/reset_databases.sh --cache --logs
```

### Utilizzo Diretto Python
```bash
# Reset completo (default)
python utils/database_reset.py

# Reset con opzioni specifiche
python utils/database_reset.py --all --samples

# Reset selettivo
python utils/database_reset.py --vector --facts --secure

# Solo pulizia cache
python utils/database_reset.py --cache --logs

# Senza backup (più veloce)
python utils/database_reset.py --all --no-backup
```

## Opzioni Comando

| Opzione | Descrizione |
|---------|-------------|
| `--all` | Reset di tutti i database (default) |
| `--vector` | Reset solo database vettoriali (Qdrant) |
| `--facts` | Reset solo database fact table |
| `--secure` | Reset solo database secure fact table |
| `--cache` | Pulizia solo directory cache |
| `--logs` | Pulizia solo file di log |
| `--samples` | Crea dati campione dopo il reset |
| `--no-backup` | Salta il backup dei database |

## Backup

I database vengono automaticamente salvati con timestamp:
```
data/facts.db → data/facts.db.backup_20240913_142530
data/secure_facts.db → data/secure_facts.db.backup_20240913_142530
```

Per disabilitare il backup (operazione più veloce):
```bash
python utils/database_reset.py --no-backup
```

## Dati Campione

Con l'opzione `--samples` vengono creati:
- 3 fatti campione in aziende diverse
- Diversi livelli di classificazione (INTERNAL, CONFIDENTIAL)  
- Metadati di sicurezza completi (tenant, cost center, etc.)
- Riferimenti alle fonti tracciabili

## Scenari d'Uso

### 🚨 Emergenza - Database Corrotto
```bash
# Reset immediato senza backup
utils\reset_databases.bat --no-backup
```

### 🧪 Testing - Ambiente Pulito 
```bash
# Reset con dati campione per test
utils\reset_databases.bat --samples
```

### 🔧 Sviluppo - Reset Selettivo
```bash
# Solo vector database per cambio embedding model
python utils/database_reset.py --vector

# Solo cache per problemi import
python utils/database_reset.py --cache
```

### 📊 Demo - Preparazione Presentazione
```bash
# Reset completo con dati demo
python utils/database_reset.py --all --samples
```

## Sicurezza

⚠️ **ATTENZIONE**: Questo utility **ELIMINA PERMANENTEMENTE** tutti i dati!

- ✅ Backup automatico abilitato di default
- ✅ Conferma richiesta per operazioni distruttive
- ✅ Log dettagliato di tutte le operazioni
- ✅ Validazione della riuscita delle operazioni

## Troubleshooting

### Qdrant non disponibile
```
⚠️ Could not connect to Qdrant: Connection refused
   Make sure Qdrant is running with: docker-compose up qdrant
```
**Soluzione**: Avviare Qdrant con `docker-compose up qdrant`

### Database in uso
```
❌ Error: database is locked
```
**Soluzione**: Chiudere Streamlit app prima del reset

### Permission denied
```
❌ Permission denied: data/facts.db
```
**Soluzione**: Eseguire come amministratore o verificare permessi file

## Integrazione con Sviluppo

### Pre-commit Hook
Aggiungere al `.git/hooks/pre-commit`:
```bash
# Reset database prima dei commit importanti
if git diff --cached --name-only | grep -q "migration\|schema"; then
    ./utils/reset_databases.sh --all
fi
```

### Testing CI/CD
```yaml
# GitHub Actions / GitLab CI
- name: Reset Test Database
  run: python utils/database_reset.py --all --samples
```

## Monitoraggio

L'utility fornisce:
- 📊 **Statistiche operazioni** (successi/fallimenti)
- 🕐 **Timestamp** di ogni operazione  
- 📁 **Percorsi file** processati
- 💾 **Dimensioni backup** creati
- ⏱️ **Tempo esecuzione** totale

---

**Creato**: 13 Settembre 2024  
**Versione**: 1.0  
**Compatibilità**: Windows, Linux, Mac  
**Dipendenze**: Python 3.8+, qdrant-client (opzionale)