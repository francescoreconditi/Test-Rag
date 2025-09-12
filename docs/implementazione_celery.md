# Implementazione Celery per Upload Documenti

## 📊 Analisi: Integrazione Celery per Upload Documenti in Streamlit

### ✅ **Fattibilità: SÌ, È POSSIBILE E CONSIGLIATO**

Il codebase ha già una **solida infrastruttura Celery** pronta. L'integrazione con la sezione RAG Documenti è non solo possibile ma altamente raccomandata per documenti grandi.

---

## 🏗️ **Architettura Attuale**

### **Flusso Sincrono Corrente (app.py, riga 595-641)**:
1. Click su "Indicizza Documenti"
2. `st.spinner("Indicizzando documenti...")` blocca l'UI
3. `rag_engine.index_documents()` processa tutto sincronamente
4. UI bloccata fino al completamento

### **Infrastruttura Celery Esistente**:
- ✅ **Task già definito**: `index_documents` in `celery_tasks.py` (riga 124-174)
- ✅ **Code specializzate**: Queue `indexing` dedicata
- ✅ **Progress tracking**: Supporto nativo per aggiornamenti real-time
- ✅ **Redis broker**: Configurato e pronto
- ✅ **Flower monitoring**: Dashboard per monitoraggio

---

## 🎯 **Architettura Proposta con Celery**

### **1. Flusso Asincrono**:
```
Streamlit UI → Submit Task → Celery Queue → Background Worker
     ↓                                              ↓
Session State ← Progress Updates ← Redis ← Task Progress
```

### **2. Componenti Chiave**:

#### **A. Task Submission (app.py)**:
- Sostituire chiamata sincrona con submission Celery
- Salvare `task_id` in `st.session_state`
- UI non bloccante con progress bar

#### **B. Progress Tracking**:
- Polling periodico dello stato task
- Aggiornamento progress bar in real-time
- `st.rerun()` controllato per refresh UI

#### **C. Result Handling**:
- Recupero risultati quando completato
- Gestione errori e retry
- Notifiche completion

---

## 🚧 **Sfide Tecniche e Soluzioni**

### **1. 🔄 State Management in Streamlit**
**Sfida**: Streamlit ricarica l'intera pagina ad ogni interazione
**Soluzione**: 
- Usare `st.session_state` per persistere `task_id`
- Implementare polling intelligente con `st.empty()` containers
- Auto-refresh controllato con `time.sleep()` + `st.rerun()`

### **2. 📊 Progress Updates Real-Time**
**Sfida**: Streamlit non supporta WebSockets nativamente
**Soluzione**:
```python
# Polling pattern con placeholder
progress_placeholder = st.empty()
while task_status != 'SUCCESS':
    status = get_task_status(task_id)
    progress_placeholder.progress(status['progress'])
    time.sleep(1)
    st.rerun()
```

### **3. 📁 File Handling**
**Sfida**: File temporanei di Streamlit vengono eliminati
**Soluzione**:
- Salvare file permanentemente prima di inviare a Celery
- Passare path permanenti al task Celery
- Cleanup gestito post-processing

### **4. 🔐 Multi-Tenant Context**
**Sfida**: Mantenere contesto tenant attraverso task asincroni
**Soluzione**:
- Passare `tenant_id` come parametro al task
- Ricostruire contesto nel worker Celery
- Usare collection Qdrant tenant-specific

### **5. ⚡ Worker Windows Compatibility**
**Sfida**: Windows richiede `--pool=solo` per Celery
**Soluzione**:
- Già configurato in `celery_tasks.py` (riga 47)
- Script `start_flower.bat` già pronto

---

## 💡 **Implementazione Suggerita con Streamlit**

### **Step 1: Modifica Index Button Handler**
```python
if index_button:
    # Invece di processare sincronamente
    from src.infrastructure.performance.celery_tasks import index_documents
    
    # Submit task asincrono
    task = index_documents.delay(
        document_paths=file_paths,
        collection_name=f"tenant_{tenant.tenant_id}_docs",
        metadata={"tenant_id": tenant.tenant_id}
    )
    
    # Salva in session state
    st.session_state.indexing_task_id = task.id
    st.session_state.indexing_status = "PENDING"
    st.rerun()
```

### **Step 2: Progress Monitoring Component**
```python
if 'indexing_task_id' in st.session_state:
    from celery.result import AsyncResult
    
    result = AsyncResult(st.session_state.indexing_task_id)
    
    if result.state == 'PROGRESS':
        progress = result.info.get('progress', 0)
        st.progress(progress / 100)
        st.info(f"Indicizzando: {result.info.get('current_item', '')}")
        time.sleep(1)
        st.rerun()
        
    elif result.state == 'SUCCESS':
        st.success("✅ Indicizzazione completata!")
        del st.session_state.indexing_task_id
```

### **Step 3: Threshold per Task Asincrono**
```python
# Usa Celery solo per file grandi
total_size = sum(f.size for f in uploaded_files)
USE_CELERY = total_size > 10_000_000  # 10MB threshold

if USE_CELERY:
    # Processamento asincrono
else:
    # Processamento sincrono per file piccoli
```

---

## ⚠️ **Difficoltà Maggiori dell'Implementazione Streamlit + Celery**

### **1. 🔄 Streamlit State Management** (CRITICA)
- **Problema**: Streamlit ricarica TUTTA la pagina ad ogni interazione
- **Impatto**: Perdita del task_id e stato di avanzamento
- **Complessità**: Richiede gestione meticolosa di `st.session_state` e `st.rerun()` controllati

### **2. 🚫 No WebSockets Nativi** (ALTA)
- **Problema**: Streamlit non supporta connessioni real-time
- **Impatto**: Impossibile ricevere update push dal server
- **Workaround**: Polling continuo con refresh manuali che degradano UX

### **3. 📁 File Temporanei Streamlit** (ALTA)
- **Problema**: `UploadedFile` viene eliminato dopo il request
- **Impatto**: File non più disponibile quando il worker Celery lo processa
- **Soluzione Costosa**: Duplicazione file su disco permanente

### **4. 🔐 Contesto Multi-Tenant** (MEDIA)
- **Problema**: Worker Celery gira in processo separato senza contesto utente
- **Impatto**: Perdita informazioni tenant, permessi, configurazioni
- **Complessità**: Serializzare/deserializzare tutto il contesto

### **5. 💻 Windows Compatibility** (MEDIA)
- **Problema**: Celery su Windows richiede `--pool=solo` (single thread)
- **Impatto**: Nessun parallelismo reale, performance degradate
- **Limitazione**: Un documento alla volta per worker

### **6. 🔄 UI Refresh Loop** (ALTA)
- **Problema**: Bilanciare refresh frequenti vs overhead
- **Trade-off**: 
  - Refresh rapidi (1s) = UI responsiva ma carico server alto
  - Refresh lenti (5s) = UI lag ma server stabile
- **Rischio**: Loop infiniti di `st.rerun()` se mal gestiti

### **7. 🎯 Error Handling Asincrono** (MEDIA)
- **Problema**: Errori avvengono in processo separato
- **Impatto**: Difficile mostrare errori specifici all'utente
- **UX**: Utente potrebbe non sapere cosa è andato storto

### **🔴 Difficoltà Principale**: 
**L'architettura request-response di Streamlit è fondamentalmente incompatibile con processing asincrono**, richiedendo workaround complessi che compromettono sia performance che UX.

---

## 🚀 **Soluzione Ottimale: FastAPI + React/Angular + Linux**

### **Problemi che SPARISCONO completamente:**

#### **1. WebSockets Real-Time** ✅
```python
# FastAPI backend
@app.websocket("/ws/task/{task_id}")
async def task_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    while True:
        status = celery_app.AsyncResult(task_id)
        await websocket.send_json({
            "state": status.state,
            "progress": status.info.get('progress', 0)
        })
        if status.state in ['SUCCESS', 'FAILURE']:
            break
        await asyncio.sleep(0.5)
```

```typescript
// React/Angular frontend
const ws = new WebSocket(`ws://localhost:8000/ws/task/${taskId}`);
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    setProgress(data.progress);
    // UI si aggiorna SENZA refresh pagina!
};
```

#### **2. State Management** ✅
- **React**: Redux/Context API mantiene stato globale
- **Angular**: Services con RxJS per stato persistente
- **Nessun page reload**, tutto in SPA

#### **3. File Upload Ottimizzato** ✅
```javascript
// Chunked upload con progress nativo
const formData = new FormData();
formData.append('file', file);

axios.post('/api/upload', formData, {
    onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(percentCompleted);
    }
});
```

#### **4. Linux + Celery = Performance 10x** ✅
```bash
# Linux supporta fork() nativo
celery -A app worker --concurrency=8 --pool=prefork  # 8 processi paralleli!
# vs Windows: --pool=solo (1 thread singolo)
```

#### **5. Error Handling Elegante** ✅
```python
# FastAPI
@app.post("/documents/index")
async def index_documents(files: List[UploadFile]):
    try:
        task = celery_app.send_task('index_documents', args=[files])
        return {"task_id": task.id, "status": "processing"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

```typescript
// React con toast notifications
try {
    const response = await api.indexDocuments(files);
    toast.success('Processing started!');
} catch (error) {
    toast.error(`Error: ${error.message}`);
}
```

---

## 📊 **Confronto Architetture**

| Feature | Streamlit + Windows | FastAPI + React/Angular + Linux |
|---------|-------------------|----------------------------------|
| **WebSockets** | ❌ Polling only | ✅ Real-time native |
| **State Management** | ❌ Page reloads | ✅ SPA persistent |
| **File Handling** | ❌ Temp files issues | ✅ Stream processing |
| **Celery Performance** | ❌ Single thread | ✅ Multi-process |
| **UI Updates** | ❌ Full refresh | ✅ Component only |
| **Error Handling** | ❌ Complex | ✅ Try/catch standard |
| **Scalability** | ❌ Limited | ✅ Horizontal scaling |
| **Development Speed** | ✅ Rapid prototyping | ❌ More setup |

---

## 🎯 **Architettura Ideale per Enterprise**

```
┌─────────────┐     WebSocket      ┌──────────────┐
│   React/    │◄──────────────────►│   FastAPI    │
│   Angular   │     REST API       │   Backend    │
└─────────────┘                    └──────┬───────┘
                                          │
                                    Celery Tasks
                                          │
                              ┌───────────▼───────────┐
                              │   Celery Workers      │
                              │   (Linux, 8 cores)    │
                              └───────────┬───────────┘
                                          │
                                    ┌─────▼─────┐
                                    │   Redis   │
                                    │   Qdrant  │
                                    └───────────┘
```

---

## 💡 **Implementazione con FastAPI + React/Angular**

### **Backend FastAPI**
```python
# FastAPI endpoint
@app.post("/api/documents/upload")
async def upload_documents(
    files: List[UploadFile],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    # Salva files
    file_paths = await save_uploaded_files(files)
    
    # Submit Celery task
    task = index_documents.delay(
        file_paths=file_paths,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id
    )
    
    # Return immediately
    return {
        "task_id": task.id,
        "message": "Processing started",
        "ws_url": f"/ws/task/{task.id}"
    }

# WebSocket per progress real-time
@app.websocket("/ws/task/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    
    while True:
        result = AsyncResult(task_id)
        
        if result.state == 'PENDING':
            response = {'state': result.state, 'progress': 0}
        elif result.state == 'PROGRESS':
            response = {
                'state': result.state,
                'current': result.info.get('current', 0),
                'total': result.info.get('total', 1),
                'progress': result.info.get('progress', 0)
            }
        elif result.state == 'SUCCESS':
            response = {
                'state': result.state,
                'progress': 100,
                'result': result.result
            }
            await websocket.send_json(response)
            break
        else:  # FAILURE
            response = {
                'state': result.state,
                'error': str(result.info)
            }
            await websocket.send_json(response)
            break
            
        await websocket.send_json(response)
        await asyncio.sleep(0.5)
```

### **Frontend React**
```jsx
import React, { useState, useEffect } from 'react';
import { Progress, Alert, Upload } from 'antd';

function DocumentUploader() {
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [taskId, setTaskId] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (taskId) {
            const ws = new WebSocket(`ws://localhost:8000/ws/task/${taskId}`);
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.state === 'PROGRESS') {
                    setProgress(data.progress);
                } else if (data.state === 'SUCCESS') {
                    setProgress(100);
                    setUploading(false);
                    message.success('Documents indexed successfully!');
                } else if (data.state === 'FAILURE') {
                    setError(data.error);
                    setUploading(false);
                }
            };
            
            return () => ws.close();
        }
    }, [taskId]);

    const handleUpload = async (file) => {
        const formData = new FormData();
        formData.append('files', file);
        
        try {
            setUploading(true);
            setError(null);
            
            const response = await fetch('/api/documents/upload', {
                method: 'POST',
                body: formData,
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            const data = await response.json();
            setTaskId(data.task_id);
            
        } catch (err) {
            setError(err.message);
            setUploading(false);
        }
    };

    return (
        <div>
            <Upload
                customRequest={({ file }) => handleUpload(file)}
                disabled={uploading}
                multiple
                accept=".pdf,.docx,.txt,.csv,.xls,.xlsx"
            >
                <Button icon={<UploadOutlined />}>
                    Select Documents
                </Button>
            </Upload>
            
            {uploading && (
                <Progress 
                    percent={progress} 
                    status="active"
                    strokeColor={{
                        '0%': '#108ee9',
                        '100%': '#87d068',
                    }}
                />
            )}
            
            {error && (
                <Alert
                    message="Upload Failed"
                    description={error}
                    type="error"
                    closable
                    onClose={() => setError(null)}
                />
            )}
        </div>
    );
}
```

### **Frontend Angular**
```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-document-uploader',
  template: `
    <div class="upload-container">
      <input 
        type="file" 
        (change)="onFileSelected($event)" 
        multiple
        accept=".pdf,.docx,.txt,.csv,.xls,.xlsx"
        [disabled]="uploading"
      >
      
      <div *ngIf="uploading" class="progress-container">
        <mat-progress-bar 
          mode="determinate" 
          [value]="progress"
        ></mat-progress-bar>
        <span>{{ progress }}% - {{ currentFile }}</span>
      </div>
      
      <mat-error *ngIf="error">{{ error }}</mat-error>
    </div>
  `
})
export class DocumentUploaderComponent implements OnInit, OnDestroy {
  uploading = false;
  progress = 0;
  currentFile = '';
  error: string | null = null;
  private destroy$ = new Subject<void>();
  private ws: WebSocket | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit() {}

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.ws) {
      this.ws.close();
    }
  }

  async onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;

    const formData = new FormData();
    Array.from(input.files).forEach(file => {
      formData.append('files', file);
    });

    this.uploading = true;
    this.error = null;

    try {
      const response = await this.http.post<any>(
        '/api/documents/upload',
        formData
      ).toPromise();

      this.connectWebSocket(response.task_id);
    } catch (err) {
      this.error = err.message;
      this.uploading = false;
    }
  }

  private connectWebSocket(taskId: string) {
    this.ws = new WebSocket(`ws://localhost:8000/ws/task/${taskId}`);
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.state === 'PROGRESS') {
        this.progress = data.progress;
        this.currentFile = data.current_item || '';
      } else if (data.state === 'SUCCESS') {
        this.progress = 100;
        this.uploading = false;
        // Show success notification
      } else if (data.state === 'FAILURE') {
        this.error = data.error;
        this.uploading = false;
      }
    };
  }
}
```

---

## 🔥 **Bonus con Linux**

- **Docker Compose** orchestration semplice
- **Nginx** reverse proxy nativo
- **Supervisor** per gestire workers
- **systemd** per servizi automatici
- **Performance I/O** molto superiore

### **Docker Compose Example**
```yaml
version: '3.8'

services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
  
  celery_worker:
    build: .
    command: celery -A src.infrastructure.performance.celery_tasks worker --loglevel=info --concurrency=8
    depends_on:
      - redis
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
  
  celery_beat:
    build: .
    command: celery -A src.infrastructure.performance.celery_tasks beat --loglevel=info
    depends_on:
      - redis
  
  flower:
    build: .
    command: celery -A src.infrastructure.performance.celery_tasks flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      - redis
  
  fastapi:
    build: .
    command: uvicorn app:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - qdrant
      - celery_worker
    volumes:
      - ./:/app
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - fastapi
```

---

## 📈 **Risultato Finale**

### **Con Streamlit + Windows**:
- ⚠️ Workarounds complessi necessari
- ⚠️ Performance limitata (single thread)
- ⚠️ UX degradata (polling, page refresh)
- ✅ Sviluppo rapido per POC

### **Con FastAPI + React/Angular + Linux**:
- ✅ **10x performance** su documenti grandi
- ✅ **UX fluida** senza refresh
- ✅ **Scalabilità enterprise** reale
- ✅ **Manutenzione semplificata**
- ✅ **Monitoring professionale** con Flower/Prometheus
- ⚠️ Setup iniziale più complesso

---

## 🎯 **Raccomandazione Finale**

### **Per POC/Demo**: 
Streamlit con processamento sincrono (file < 10MB)

### **Per Produzione Enterprise**:
FastAPI + React/Angular + Linux + Celery

### **Approccio Ibrido Consigliato**:
1. **Fase 1**: POC con Streamlit per validare funzionalità
2. **Fase 2**: Migrazione a FastAPI + React per produzione
3. **Fase 3**: Scaling con Kubernetes per enterprise

**Streamlit è ottimo per prototipazione rapida, ma per un sistema RAG enterprise con processing di documenti pesanti, l'architettura FastAPI + React/Angular + Linux + Celery è la scelta tecnicamente corretta.**