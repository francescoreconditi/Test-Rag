# 🚀 RAG Dashboard - Angular Enterprise Application

Un'applicazione Angular moderna e professionale che replica e migliora le funzionalità del sistema Streamlit RAG, implementando tutte le best practices di sviluppo e design.

## ✨ Caratteristiche Principali

### 🏗️ **Architettura Enterprise**
- **Standalone Components**: Componenti modulari e riutilizzabili
- **Lazy Loading**: Caricamento dinamico delle feature per prestazioni ottimali
- **Dependency Injection**: Gestione avanzata delle dipendenze
- **Reactive Programming**: RxJS per gestione asincrona efficiente
- **TypeScript Strict Mode**: Type safety e robustezza del codice

### 🎨 **Design System**
- **Material Design 3**: Interfaccia moderna e accessibile
- **Custom Theme System**: Supporto temi chiaro/scuro dinamico
- **Responsive Design**: Ottimizzato per desktop, tablet e mobile
- **Typography**: Font Inter per leggibilità professionale
- **Animations**: Transizioni fluide e feedback visivo

### 🔧 **Funzionalità Implementate**

#### 📚 **Gestione Documenti RAG**
- Upload multiplo con drag & drop
- Supporto 10+ formati file (PDF, Word, Excel, CSV, immagini)
- Analisi automatica intelligente con AI
- Query semantiche avanzate
- Visualizzazione risultati con sources e confidenza
- Export PDF dei risultati

#### 🎯 **Core Features**
- **Dashboard**: Overview con KPI e statistiche
- **Document Management**: Caricamento e indicizzazione
- **Query RAG**: Interrogazione intelligente documenti
- **FAQ Generation**: Generazione automatica FAQ (come NotebookLM)
- **CSV Analysis**: Analisi avanzata dati business
- **Enterprise Mode**: Funzionalità per uso aziendale
- **Analytics**: Dashboard metriche e performance

## 🛠️ Setup e Installazione

### Prerequisiti
- **Node.js 18+**
- **Angular CLI 17+**
- **Backend FastAPI** in esecuzione su `localhost:8000`

### 🚀 Quick Start

```bash
# Naviga nella directory
cd dash_b

# Installa dipendenze
npm install

# Avvia il server di sviluppo
npm start
# Oppure
ng serve

# L'applicazione sarà disponibile su http://localhost:4200
```

## 🔌 Integrazione API

### Backend Requirements
L'applicazione si connette al backend FastAPI su:
- **Base URL**: `http://localhost:8000`
- **Health Check**: `/health`
- **Documentazione**: `http://localhost:8000/docs`

Assicurati che il backend FastAPI sia in esecuzione prima di avviare l'applicazione Angular.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
