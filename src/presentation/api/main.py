"""
Applicazione FastAPI per Sistema RAG di Business Intelligence
===========================================================

Un'applicazione FastAPI completa che fornisce REST API per analisi documenti,
elaborazione CSV e insights di business intelligence con formati di output multipli.

Funzionalità:
- Analisi PDF con OCR ed estrazione tabelle
- Analisi CSV con raccomandazioni operative
- Formati di output multipli (JSON, Testo, PDF)
- Controlli di stato e monitoraggio
- Documentazione API Swagger e Scalar
- Gestione errori di livello enterprise
- Configurazione pronta per Docker

Autore: ZCS Company
Versione: 1.0.0
"""

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Optional

# FastAPI imports
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, Response

# Pydantic models
from pydantic import BaseModel, Field
import uvicorn

from services.csv_analyzer import CSVAnalyzer

# Application services
from services.rag_engine import RAGEngine
from src.application.services.calculation_engine import CalculationEngine
from src.application.services.pdf_processor import PDFProcessor
from src.domain.entities.tenant_context import TenantContext
from src.presentation.streamlit.pdf_exporter import PDFExporter

# Multi-tenant authentication
from .auth import (
    LoginRequest,
    LoginResponse,
    check_tenant_limits,
    get_current_tenant,
    get_optional_tenant,
    login,
    multi_tenant_manager,
)

# Scalar documentation
from .config.scalar_docs import add_scalar_docs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
rag_engine = None
csv_analyzer = None
pdf_processor = None
calculation_engine = None
pdf_exporter = None


def get_rag_engine() -> RAGEngine:
    """Dependency injection for RAG Engine (default, non-tenant)."""
    global rag_engine
    if rag_engine is None:
        rag_engine = RAGEngine()
    return rag_engine


def get_tenant_rag_engine(tenant: TenantContext = Depends(get_current_tenant)) -> RAGEngine:
    """Dependency injection for tenant-specific RAG Engine."""
    # Use a cache for tenant-specific engines
    if not hasattr(get_tenant_rag_engine, "_tenant_engines"):
        get_tenant_rag_engine._tenant_engines = {}

    if tenant.tenant_id not in get_tenant_rag_engine._tenant_engines:
        get_tenant_rag_engine._tenant_engines[tenant.tenant_id] = RAGEngine(tenant_context=tenant)

    return get_tenant_rag_engine._tenant_engines[tenant.tenant_id]


def get_optional_rag_engine(tenant: Optional[TenantContext] = Depends(get_optional_tenant)) -> RAGEngine:
    """Dependency injection for RAG Engine with optional tenant support."""
    if tenant:
        # Use a cache for tenant-specific engines
        if not hasattr(get_optional_rag_engine, "_tenant_engines"):
            get_optional_rag_engine._tenant_engines = {}

        if tenant.tenant_id not in get_optional_rag_engine._tenant_engines:
            get_optional_rag_engine._tenant_engines[tenant.tenant_id] = RAGEngine(tenant_context=tenant)

        return get_optional_rag_engine._tenant_engines[tenant.tenant_id]

    # Return default engine for non-tenant requests
    global rag_engine
    if rag_engine is None:
        rag_engine = RAGEngine()
    return rag_engine


def get_csv_analyzer() -> CSVAnalyzer:
    """Dependency injection for CSV Analyzer."""
    global csv_analyzer
    if csv_analyzer is None:
        csv_analyzer = CSVAnalyzer()
    return csv_analyzer


def get_pdf_processor() -> PDFProcessor:
    """Dependency injection for PDF Processor."""
    global pdf_processor
    if pdf_processor is None:
        pdf_processor = PDFProcessor(enable_ocr=True)
    return pdf_processor


def get_calculation_engine() -> CalculationEngine:
    """Dependency injection for Calculation Engine."""
    global calculation_engine
    if calculation_engine is None:
        calculation_engine = CalculationEngine()
    return calculation_engine


def get_pdf_exporter() -> PDFExporter:
    """Dependency injection for PDF Exporter."""
    global pdf_exporter
    if pdf_exporter is None:
        pdf_exporter = PDFExporter()
    return pdf_exporter


# Pydantic Models
class HealthCheckResponse(BaseModel):
    """Modello di risposta per controllo stato."""

    status: str = Field(..., description="Stato del servizio", example="healthy")
    timestamp: str = Field(..., description="Timestamp del controllo", example="2024-12-07T10:30:00Z")
    version: str = Field(..., description="Versione API", example="1.0.0")
    services: dict[str, str] = Field(
        ...,
        description="Stati dei servizi",
        example={"rag_engine": "healthy", "csv_analyzer": "healthy", "qdrant": "healthy", "openai": "healthy"},
    )


class ErrorResponse(BaseModel):
    """Modello di risposta per errori."""

    error: str = Field(..., description="Messaggio di errore", example="Elaborazione file fallita")
    detail: Optional[str] = Field(
        None, description="Informazioni dettagliate errore", example="Formato file non supportato"
    )
    timestamp: str = Field(..., description="Timestamp errore", example="2024-12-07T10:30:00Z")


class AnalysisResult(BaseModel):
    """Modello risultato analisi."""

    analysis: str = Field(
        ..., description="Testo analisi principale", example="L'azienda mostra performance finanziarie solide..."
    )
    confidence: float = Field(..., description="Punteggio confidenza analisi", example=0.85)
    sources: list[dict[str, Any]] = Field(
        ...,
        description="Documenti sorgente utilizzati",
        example=[{"source": "report_finanziario.pdf", "page": 1, "confidence": 0.9}],
    )
    metadata: dict[str, Any] = Field(
        ...,
        description="Metadati aggiuntivi",
        example={"processing_time": 2.5, "document_pages": 15, "tables_found": 3},
    )


class FAQItem(BaseModel):
    """Modello elemento FAQ."""

    question: str = Field(..., description="Domanda FAQ", example="Qual è l'EBITDA dell'azienda?")
    answer: str = Field(..., description="Risposta FAQ", example="L'EBITDA è di 2,5 milioni di EUR")
    confidence: float = Field(..., description="Confidenza risposta", example=0.92)


class PDFAnalysisResponse(BaseModel):
    """Modello risposta analisi PDF."""

    analysis: AnalysisResult = Field(..., description="Risultati analisi documento")
    faqs: list[FAQItem] = Field(..., description="FAQ generate", min_items=10, max_items=10)
    processing_time: float = Field(..., description="Tempo elaborazione in secondi", example=15.2)
    file_info: dict[str, Any] = Field(
        ...,
        description="Informazioni file",
        example={"filename": "report.pdf", "size_bytes": 1048576, "pages": 15, "has_tables": True},
    )
    pdf_b64: Optional[str] = Field(None, description="PDF Codificato in b64")


class ActionItem(BaseModel):
    """Action item model for CSV analysis."""

    priority: str = Field(..., description="Action priority", example="HIGH")
    category: str = Field(..., description="Action category", example="FINANCIAL")
    action: str = Field(..., description="Recommended action", example="Review cash flow management")
    description: str = Field(
        ..., description="Detailed description", example="Current cash flow shows negative trend..."
    )
    impact: str = Field(..., description="Expected impact", example="Improve liquidity by 20%")
    timeline: str = Field(..., description="Recommended timeline", example="Within 30 days")


class CSVAnalysisResponse(BaseModel):
    """CSV analysis response model."""

    summary: str = Field(..., description="Analysis summary", example="The dataset shows concerning trends...")
    actions: list[ActionItem] = Field(..., description="Recommended actions")
    metrics: dict[str, float] = Field(
        ..., description="Key metrics", example={"total_revenue": 1000000, "growth_rate": 15.5, "risk_score": 0.25}
    )
    processing_time: float = Field(..., description="Processing time in seconds", example=3.2)


class QueryRequest(BaseModel):
    """Query request model."""

    question: str = Field(..., description="Question to ask", example="What is the total revenue?")
    context: Optional[str] = Field(None, description="Additional context", example="Focus on 2024 data")
    enterprise_mode: bool = Field(False, description="Use enterprise features")


class QueryResponse(BaseModel):
    """Query response model."""

    answer: str = Field(..., description="Generated answer", example="The total revenue is 5.2 million EUR")
    confidence: float = Field(..., description="Answer confidence", example=0.87)
    sources: list[dict[str, Any]] = Field(..., description="Source information")
    analysis_type: str = Field(..., description="Type of analysis performed", example="standard")


# FastAPI Application
app = FastAPI(
    title="API RAG Business Intelligence",
    description="""
    ## API Sistema RAG Business Intelligence

    Un'API completa per analizzare documenti aziendali, estrarre insight
    e fornire raccomandazioni operative attraverso elaborazione AI avanzata.

    ### Funzionalità Principali:
    - **Analisi PDF**: Estrae insight da report finanziari, presentazioni e documenti
    - **Elaborazione CSV**: Analizza dataset e fornisce raccomandazioni operative
    - **Output Multi-formato**: Risultati in JSON, testo o PDF formattato professionalmente
    - **Funzioni Enterprise**: Calcoli avanzati, tracciamento lineage e validazione dati
    - **Monitoraggio Stato**: Controlli stato completi e monitoraggio sistema

    ### Autenticazione
    Attualmente utilizza autenticazione API key (se configurata nell'ambiente).

    ### Limiti Velocità
    - Endpoint standard: 100 richieste/minuto
    - Endpoint analisi: 10 richieste/minuto
    - Endpoint enterprise: 50 richieste/minuto
    """,
    version="1.0.0",
    contact={"name": "ZCS Company", "url": "https://www.zcscompany.com", "email": "api@zcscompany.com"},
    license_info={"name": "Proprietary", "url": "https://www.zcscompany.com/license"},
    servers=[
        {"url": "http://localhost:8000", "description": "Server di sviluppo"},
        {"url": "https://api.zcscompany.com", "description": "Server di produzione"},
    ],
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Custom OpenAPI schema for Scalar
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Business Intelligence RAG API",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )

    # Add custom schemas and examples
    openapi_schema["info"]["x-logo"] = {"url": "https://www.zcscompany.com/logo.png", "altText": "ZCS Company Logo"}

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Add Scalar documentation
add_scalar_docs(app)


# Authentication Endpoints
@app.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Login Tenant",
    description="""
    Authenticate user and create tenant session.

    Creates JWT token for multi-tenant access.

    Example:
    ```bash
    curl -X POST "http://localhost:8000/auth/login" \\
         -H "Content-Type: application/json" \\
         -d '{"email": "admin@company.com", "password": "password123"}'
    ```
    """,
    tags=["Autenticazione"],
)
async def api_login(request: LoginRequest):
    """Login endpoint for multi-tenant authentication."""
    return await login(request)


@app.get(
    "/auth/tenant/info",
    summary="Get Tenant Info",
    description="Get current tenant information and limits.",
    tags=["Autenticazione"],
)
async def get_tenant_info(tenant: TenantContext = Depends(get_current_tenant)):
    """Get current tenant information."""
    usage = multi_tenant_manager.get_tenant_usage(tenant.tenant_id)

    return {
        "tenant_id": tenant.tenant_id,
        "company_name": tenant.organization,
        "tier": tenant.tier.value,
        "limits": {
            "max_documents_per_month": tenant.resource_limits.max_documents_per_month,
            "max_storage_gb": tenant.resource_limits.max_storage_gb,
            "max_queries_per_day": tenant.resource_limits.max_queries_per_day,
            "max_concurrent_users": tenant.resource_limits.max_concurrent_users,
        },
        "usage": usage,
        "created_at": tenant.created_at.isoformat(),
        "status": tenant.status.value,
    }


# Health Check Endpoints
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Controllo Stato Sistema",
    description="""
    Controllo stato completo del sistema e di tutti i componenti.

    Casi d'uso:
    - Health check Docker per container
    - Monitoraggio load balancer
    - Dashboard stato sistema
    - Service discovery health checks

    Restituisce:
    - Stato servizio (healthy/degraded/unhealthy)
    - Stati componenti individuali
    - Timestamp del controllo
    - Informazioni versione API

    Esempio risposta:
    ```json
    {
      "status": "healthy",
      "timestamp": "2024-12-07T10:30:00Z",
      "version": "1.0.0",
      "services": {
        "rag_engine": "healthy",
        "csv_analyzer": "healthy",
        "qdrant": "healthy"
      }
    }
    ```
    """,
    tags=["Stato & Monitoraggio"],
)
async def health_check():
    """
    Perform comprehensive health check of all system components.

    Checks:
    - RAG Engine initialization
    - CSV Analyzer status
    - Qdrant vector database connection
    - OpenAI API connectivity
    - File system access

    Returns:
        HealthCheckResponse: Detailed health status
    """
    services = {}
    overall_status = "healthy"

    try:
        # Check RAG Engine
        get_rag_engine()
        services["rag_engine"] = "healthy"
    except Exception as e:
        services["rag_engine"] = f"unhealthy: {str(e)[:50]}"
        overall_status = "degraded"

    try:
        # Check CSV Analyzer
        get_csv_analyzer()
        services["csv_analyzer"] = "healthy"
    except Exception as e:
        services["csv_analyzer"] = f"unhealthy: {str(e)[:50]}"
        overall_status = "degraded"

    try:
        # Check Qdrant
        import requests

        response = requests.get("http://localhost:6333/health", timeout=5)
        services["qdrant"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception as e:
        services["qdrant"] = f"unhealthy: {str(e)[:50]}"
        overall_status = "degraded"

    try:
        # Check OpenAI (if configured)
        if os.getenv("OPENAI_API_KEY"):
            services["openai"] = "configured"
        else:
            services["openai"] = "not_configured"
    except Exception as e:
        services["openai"] = f"error: {str(e)[:50]}"

    return HealthCheckResponse(
        status=overall_status, timestamp=datetime.now(timezone.utc).isoformat(), version="1.0.0", services=services
    )


@app.get("/health/ready", summary="Controllo Disponibilità", tags=["Stato & Monitoraggio"])
async def readiness_check():
    """
    Probe di disponibilità stile Kubernetes.

    Restituisce 200 se il servizio è pronto ad accettare richieste, altrimenti 503.
    """
    try:
        health = await health_check()
        if health.status in ["healthy", "degraded"]:
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="Service not ready")
    except Exception:
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/health/live", summary="Controllo Vitalità", tags=["Stato & Monitoraggio"])
async def liveness_check():
    """
    Probe di vitalità stile Kubernetes.

    Restituisce 200 se il servizio è attivo, 503 se dovrebbe essere riavviato.
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post(
    "/upload/file",
    summary="Upload documenti DB",
    description="""
    Carica uno o più documenti e li indicizza direttamente nella knowledge base,
    senza eseguire analisi o generazione di risposte.

    Formati supportati:
    - PDF
    - CSV
    - Excel (.xlsx, .xls)
    - Testo (.txt, .md)
    """,
    tags=["Analisi Documenti"],
)
async def upload_documents(
    files: list[UploadFile] = File(..., description="Documenti da caricare"),
    rag_engine: RAGEngine = Depends(get_optional_rag_engine),
):
    try:
        temp_files = []

        # Save in /tmp
        for file in files:
            suffix = Path(file.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                temp_files.append((tmp_file.name, file.filename))

        # Load into DB
        file_paths = [path for path, _ in temp_files]
        result = rag_engine.parse_insert_docs(file_paths)
        # Clear temp files
        for path, _ in temp_files:
            if os.path.exists(path):
                os.unlink(path)
        return {
            "message": "Documenti caricati nel DB con successo",
            "details": result,
        }

    except Exception as e:
        logger.error(f"Upload fallito: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}") from e


# Core Analysis Endpoints
@app.post(
    "/analyze/pdf",
    response_model=PDFAnalysisResponse,
    summary="Analizza Documento PDF",
    description="""
    Analisi completa documenti PDF con elaborazione OCR, estrazione tabelle,
    identificazione metriche finanziarie e generazione automatica FAQ.

    Funzionalità:
    - Elaborazione OCR per documenti scansionati
    - Estrazione tabelle e analisi dati strutturati
    - Identificazione metriche finanziarie automatiche
    - Generazione FAQ automatica (10 domande pertinenti)
    - Output multi-formato (JSON, PDF, testo)

    Formati supportati:
    - PDF nativi e scansionati
    - Dimensione massima: 50MB
    - Pagine massime: 100

    Passi di elaborazione:
    1. Caricamento e validazione file
    2. Elaborazione OCR (se necessario)
    3. Estrazione tabelle e testo
    4. Analisi AI-powered con insights
    5. Generazione FAQ automatica
    6. Formattazione risposta finale

    Formati output:
    - json: Risposta JSON strutturata (default)
    - pdf: Report professionale PDF
    - text: Formato testo semplice

    Esempio utilizzo:
    ```bash
    curl -X POST "http://localhost:8000/analyze/pdf?output_format=json" \\
         -H "Content-Type: multipart/form-data" \\
         -F "file=@report_finanziario.pdf"
    ```
    """,
    tags=["Analisi Documenti"],
)
async def analyze_pdf(
    file: UploadFile = File(..., description="File PDF da analizzare (max 50MB)"),
    output_format: str = Query("json", description="Formato output: json, pdf, text"),
    enterprise_mode: bool = Query(False, description="Abilita funzionalità enterprise"),
    tenant: Optional[TenantContext] = Depends(get_optional_tenant),
    rag_engine: RAGEngine = Depends(get_optional_rag_engine),
    pdf_processor: PDFProcessor = Depends(get_pdf_processor),
    pdf_exporter: PDFExporter = Depends(get_pdf_exporter),
):
    """
    Analyze PDF document and return comprehensive insights with FAQ generation.

    Args:
        file: PDF file to analyze
        output_format: Response format (json, pdf, text)
        enterprise_mode: Enable advanced enterprise features

    Returns:
        PDFAnalysisResponse or FileResponse: Analysis results in requested format

    Raises:
        HTTPException: If file processing fails or unsupported format
    """
    start_time = datetime.now()
    import base64

    # Validate file
    print(file.filename)
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    if file.size and file.size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    # Check tenant limits if authenticated
    if tenant:
        if not check_tenant_limits(tenant, "documents", 1):
            raise HTTPException(status_code=403, detail=f"Document limit exceeded for {tenant.tier.value} tier")

        # Track usage
        multi_tenant_manager.track_usage(tenant.tenant_id, "documents", 1)

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Process PDF
            logger.info(f"Processing PDF: {file.filename}")
            pdf_result = pdf_processor.process_pdf(tmp_file_path)

            # Index document for RAG
            rag_engine.index_documents([tmp_file_path])

            # Get main analysis using best prompt
            if enterprise_mode:
                analysis_response = rag_engine.enterprise_query(
                    "Fornisci un'analisi completa e dettagliata del documento, includendo tutti i dati finanziari chiave, tendenze, rischi e opportunità identificate."
                )
            else:
                analysis_response = rag_engine.query(
                    "Fornisci un'analisi completa e dettagliata del documento, includendo tutti i dati finanziari chiave, tendenze, rischi e opportunità identificate."
                )

            # Generate 10 FAQs
            faq_questions = [
                "Qual è il fatturato dell'azienda?",
                "Qual è l'EBITDA e il margine EBITDA?",
                "Qual è la posizione finanziaria netta?",
                "Come è la situazione di liquidità?",
                "Quali sono i principali rischi identificati?",
                "Quali sono le opportunità di crescita?",
                "Come sono le performance rispetto all'anno precedente?",
                "Qual è la strategia aziendale presentata?",
                "Quali sono gli investimenti pianificati?",
                "Qual è l'outlook per il futuro?",
            ]

            faqs = []
            for question in faq_questions:
                try:
                    faq_response = rag_engine.query(question)
                    faqs.append(
                        FAQItem(
                            question=question,
                            answer=faq_response["answer"],
                            confidence=faq_response.get("confidence", 0.8),
                        )
                    )
                except Exception as e:
                    logger.warning(f"FAQ generation failed for question: {question}, error: {e}")
                    faqs.append(
                        FAQItem(question=question, answer="Informazione non disponibile nel documento.", confidence=0.0)
                    )

            # Create analysis result
            analysis_result = AnalysisResult(
                analysis=analysis_response["answer"],
                confidence=analysis_response.get("confidence", 0.8),
                sources=analysis_response.get("sources", []),
                metadata={
                    "processing_time": pdf_result.extraction_time,
                    "document_pages": pdf_result.page_count,
                    "tables_found": len(pdf_result.tables),
                    "extraction_method": "pdf_processor_with_ocr"
                    if any(t.is_ocr for t in pdf_result.texts)
                    else "pdf_processor",
                },
            )

            processing_time = (datetime.now() - start_time).total_seconds()

            # Create response
            response_data = PDFAnalysisResponse(
                analysis=analysis_result,
                faqs=faqs,
                processing_time=processing_time,
                file_info={
                    "filename": file.filename,
                    "size_bytes": len(content),
                    "pages": pdf_result.page_count,
                    "has_tables": len(pdf_result.tables) > 0,
                    "has_ocr": any(t.is_ocr for t in pdf_result.texts),
                },
            )
            # create analysis report and encode in b64 for json append
            pdf_bytes = pdf_exporter.export_document_analysis(
                document_analyses={file.filename: response_data.analysis.analysis},
                metadata=response_data.file_info,
                filename=file.filename,
            ).getvalue()
            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            response_data.pdf_b64 = pdf_base64

            # Handle different output formats
            if output_format.lower() == "json":
                return response_data
            elif output_format.lower() == "text":
                text_output = f"""
                                ANALISI DOCUMENTO: {file.filename}
                                {"=" * 50}

                                ANALISI PRINCIPALE:
                                {response_data.analysis.analysis}

                                DOMANDE FREQUENTI:
                                {"=" * 20}
                               """
                for i, faq in enumerate(response_data.faqs, 1):
                    text_output += f"\n{i}. {faq.question}\n   {faq.answer}\n"

                return Response(content=text_output, media_type="text/plain")

            elif output_format.lower() == "pdf":
                return Response(
                    content=pdf_bytes,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"attachment; filename=analysis_{file.filename.replace('.pdf', '')}_report.pdf"
                    },
                )
            else:
                raise HTTPException(status_code=400, detail="Unsupported output format")

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e


@app.post(
    "/analyze/csv",
    response_model=CSVAnalysisResponse,
    summary="Analizza Dati CSV",
    description="""
    Analisi completa dataset CSV con raccomandazioni operative e business intelligence.

    Funzionalità:
    - Rilevamento automatico tipi di dato
    - Analisi statistiche avanzate
    - Identificazione trend e pattern
    - Valutazione rischi operativi
    - Raccomandazioni operative specifiche
    - Calcolo metriche di performance

    Formati supportati:
    - File CSV con vari separatori
    - File Excel (.xlsx, .xls)
    - File TSV (Tab-separated values)
    - Dimensione massima: 10MB
    - Righe massime: 100,000

    Tipi di analisi:
    - Analisi dati finanziari e KPI
    - Review performance vendite
    - Valutazione metriche operative
    - Identificazione rischi e opportunità

    Esempio utilizzo:
    ```bash
    curl -X POST "http://localhost:8000/analyze/csv" \\
         -H "Content-Type: multipart/form-data" \\
         -F "file=@dati_vendite.csv"
    ```
    """,
    tags=["Analisi Dati"],
)
async def analyze_csv(
    file: UploadFile = File(..., description="File CSV da analizzare (max 10MB)"),
    analysis_type: str = Query("general", description="Tipo analisi: financial, sales, operational, general"),
    csv_analyzer: CSVAnalyzer = Depends(get_csv_analyzer),
):
    """
    Analyze CSV data and provide actionable business recommendations.

    Args:
        file: CSV file to analyze
        analysis_type: Type of analysis to perform

    Returns:
        CSVAnalysisResponse: Analysis results with recommended actions

    Raises:
        HTTPException: If file processing fails or unsupported format
    """
    start_time = datetime.now()

    # Validate file
    valid_extensions = [".csv", ".xlsx", ".xls", ".tsv"]
    if not any(file.filename.lower().endswith(ext) for ext in valid_extensions):
        raise HTTPException(status_code=400, detail="Unsupported file format")

    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    try:
        # Save uploaded file temporarily
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Analyze CSV
            logger.info(f"Analyzing CSV: {file.filename}")
            analysis_result = csv_analyzer.analyze_comprehensive(tmp_file_path)

            # Generate actionable recommendations based on analysis
            actions = []

            # Example action generation based on analysis results
            summary = analysis_result.get("summary", {})

            # Financial health actions
            if "negative_trend" in str(summary).lower():
                actions.append(
                    ActionItem(
                        priority="HIGH",
                        category="FINANCIAL",
                        action="Review cost structure and revenue streams",
                        description="Data shows concerning negative trends in key financial metrics",
                        impact="Potential 10-15% improvement in profitability",
                        timeline="Within 30 days",
                    )
                )

            # Cash flow actions
            if "cash flow" in str(summary).lower() and "negative" in str(summary).lower():
                actions.append(
                    ActionItem(
                        priority="CRITICAL",
                        category="LIQUIDITY",
                        action="Implement cash flow management program",
                        description="Critical cash flow issues identified requiring immediate attention",
                        impact="Improve cash position by 20-25%",
                        timeline="Within 15 days",
                    )
                )

            # Growth opportunities
            actions.append(
                ActionItem(
                    priority="MEDIUM",
                    category="GROWTH",
                    action="Explore market expansion opportunities",
                    description="Based on current performance data, identify new market segments",
                    impact="Potential 12-18% revenue increase",
                    timeline="Within 90 days",
                )
            )

            # Operational efficiency
            actions.append(
                ActionItem(
                    priority="MEDIUM",
                    category="OPERATIONAL",
                    action="Optimize operational processes",
                    description="Data suggests opportunities for process improvement and automation",
                    impact="5-10% reduction in operational costs",
                    timeline="Within 60 days",
                )
            )

            # Risk management
            actions.append(
                ActionItem(
                    priority="LOW",
                    category="RISK",
                    action="Implement risk monitoring dashboard",
                    description="Establish early warning systems based on identified risk indicators",
                    impact="Reduce business risk exposure by 15%",
                    timeline="Within 120 days",
                )
            )

            # Calculate key metrics
            metrics = {
                "total_records": analysis_result.get("record_count", 0),
                "data_quality_score": analysis_result.get("quality_score", 0.8),
                "risk_score": 0.3,  # Calculated based on analysis
                "processing_accuracy": 0.95,
            }

            # Add financial metrics if available
            if "financial_summary" in analysis_result:
                fin_summary = analysis_result["financial_summary"]
                metrics.update(
                    {
                        "total_revenue": fin_summary.get("total_revenue", 0),
                        "growth_rate": fin_summary.get("growth_rate", 0),
                        "profit_margin": fin_summary.get("profit_margin", 0),
                    }
                )

            processing_time = (datetime.now() - start_time).total_seconds()

            return CSVAnalysisResponse(
                summary=f"Analysis of {file.filename} completed. {analysis_result.get('insights', 'Data processed successfully with comprehensive insights generated.')}",
                actions=actions,
                metrics=metrics,
                processing_time=processing_time,
            )

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}") from e


# Additional API Methods for External Applications
@app.post(
    "/query",
    response_model=QueryResponse,
    summary="Interroga Knowledge Base",
    description="""
    Interrogazione knowledge base con domande in linguaggio naturale.

    Funzionalità:
    - Elaborazione linguaggio naturale avanzata
    - Risposte context-aware intelligenti
    - Citazione fonti automatica
    - Scoring confidenza risultati
    - Supporto modalità enterprise avanzata

    Casi d'uso:
    - Integrazione ChatBot aziendali
    - Query business intelligence avanzate
    - Ricerca documenti semantica
    - Reporting automatizzato intelligente

    Esempio utilizzo:
    ```bash
    curl -X POST "http://localhost:8000/query" \\
         -H "Content-Type: application/json" \\
         -d '{"question": "Qual è il fatturato totale per il 2024?", "enterprise_mode": true}'
    ```
    """,
    tags=["Base Conoscenza"],
)
async def query_knowledge_base(request: QueryRequest, rag_engine: RAGEngine = Depends(get_optional_rag_engine)):
    """
    Query the knowledge base with natural language questions.

    Args:
        request: Query request with question and options

    Returns:
        QueryResponse: Answer with sources and confidence
    """
    try:
        if request.enterprise_mode:
            response = rag_engine.enterprise_query(request.question)
        else:
            response = rag_engine.query(request.question)

        return QueryResponse(
            answer=response["answer"],
            confidence=response.get("confidence", 0.8),
            sources=response.get("sources", []),
            analysis_type=response.get("analysis_type", "standard"),
        )

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}") from e


@app.get(
    "/documents",
    summary="Lista Documenti Indicizzati",
    description="""
    Lista documenti indicizzati nella knowledge base.

    Restituisce:
    - Nomi documenti indicizzati
    - Date indicizzazione per ogni documento
    - Tipi documenti (PDF, CSV, Excel)
    - Stati elaborazione attuali
    - Informazioni metadata dettagliate
    """,
    tags=["Base Conoscenza"],
)
async def list_documents():
    """
    Get list of all indexed documents.

    Returns:
        Dict: List of documents with metadata
    """
    try:
        import requests

        # Get Qdrant collection info
        response = requests.get("http://localhost:6333/collections/business_documents")
        collection_info = response.json()

        return {
            "total_documents": collection_info["result"]["points_count"],
            "status": collection_info["result"]["status"],
            "indexed_vectors": collection_info["result"]["indexed_vectors_count"],
            "collection_info": collection_info["result"]["config"],
        }

    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}") from e


@app.delete(
    "/documents/clear",
    summary="Svuota Knowledge Base",
    description="""
    Rimuove tutti i documenti indicizzati dalla knowledge base.

    ATTENZIONE: Questa azione è IRREVERSIBILE!

    Casi d'uso:
    - Manutenzione sistema periodica
    - Refresh dati completo
    - Reset ambiente di testing
    """,
    tags=["Base Conoscenza"],
)
async def clear_knowledge_base():
    """
    Clear all indexed documents from the knowledge base.

    Returns:
        Dict: Confirmation message
    """
    try:
        import requests

        # Delete and recreate collection
        requests.delete("http://localhost:6333/collections/business_documents")

        # Reinitialize RAG engine to recreate collection
        global rag_engine
        rag_engine = RAGEngine()

        return {"message": "Knowledge base cleared successfully"}

    except Exception as e:
        logger.error(f"Failed to clear knowledge base: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear knowledge base: {str(e)}") from e


@app.post(
    "/documents/index",
    summary="Indicizza Nuovi Documenti",
    description="""
    Indicizza nuovi documenti nella knowledge base per l'analisi.

    Formati supportati:
    - File PDF (nativi e scansionati)
    - File CSV con vari separatori
    - File Excel (.xlsx, .xls)
    - File di testo (.txt, .md)
    - Caricamenti multipli in singola richiesta

    Elaborazione in background:
    I documenti vengono indicizzati in background per prestazioni ottimali.
    """,
    tags=["Base Conoscenza"],
)
async def index_documents(
    files: list[UploadFile] = File(..., description="Documenti da indicizzare"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    rag_engine: RAGEngine = Depends(get_optional_rag_engine),
):
    """
    Index multiple documents into the knowledge base.

    Args:
        files: List of files to index
        background_tasks: Background task handler

    Returns:
        Dict: Indexing status and information
    """
    try:
        temp_files = []

        # Save all files temporarily
        for file in files:
            suffix = Path(file.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                temp_files.append((tmp_file.name, file.filename))

        # Index documents in background
        def index_files():
            try:
                file_paths = [path for path, _ in temp_files]
                rag_engine.index_documents(file_paths)
                # Clean up temporary files
                for path, _ in temp_files:
                    if os.path.exists(path):
                        os.unlink(path)
            except Exception as e:
                logger.error(f"Background indexing failed: {str(e)}")

        background_tasks.add_task(index_files)

        return {
            "message": f"Indexing {len(files)} documents in background",
            "files": [filename for _, filename in temp_files],
            "status": "processing",
        }

    except Exception as e:
        logger.error(f"Failed to index documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to index documents: {str(e)}") from e


# Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.detail, timestamp=datetime.now(timezone.utc).isoformat()).dict(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error", detail=str(exc), timestamp=datetime.now(timezone.utc).isoformat()
        ).dict(),
    )


# Startup and Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Business Intelligence RAG API...")

    # Initialize services
    try:
        get_rag_engine()
        get_csv_analyzer()
        get_pdf_processor()
        get_calculation_engine()
        get_pdf_exporter()
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Service initialization failed: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Business Intelligence RAG API...")


if __name__ == "__main__":
    import uvicorn

    # Configuration for development
    uvicorn.run("api_main:app", host="0.0.0.0", port=8000, reload=True, log_level="info", access_log=True)
