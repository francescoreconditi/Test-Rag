"""
PDF Export Router for FastAPI
============================

Router per l'esportazione di PDF con endpoint dedicati per:
- Salvataggio analisi documenti
- Salvataggio FAQ

Autore: ZCS Company
"""

import base64
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.presentation.streamlit.pdf_exporter import PDFExporter


router = APIRouter(
    prefix="/export/pdf",
    tags=["PDF Export"],
    responses={404: {"description": "Not found"}, 500: {"description": "Internal server error"}},
)


class AnalysisPDFRequest(BaseModel):
    """Request model per esportazione analisi PDF."""

    analysis: str = Field(
        ...,
        description="Testo dell'analisi da salvare nel PDF",
        example="L'azienda mostra performance finanziarie solide con un EBITDA di 2.5M EUR...",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Metadati aggiuntivi per il report",
        example={"numero_documenti": 5, "timestamp": "2024-12-07 10:30:00", "tipo_analisi": "Analisi Finanziaria"},
    )
    filename: Optional[str] = Field(
        None, description="Nome del file senza estensione", example="analisi_finanziaria_2024"
    )


class FAQPDFRequest(BaseModel):
    """Request model per esportazione FAQ PDF."""

    faqs: str = Field(
        ...,
        description="Stringa contenente le FAQ formattate",
        example="Q: Qual è il fatturato?\nA: Il fatturato è di 10M EUR\n\nQ: Qual è l'EBITDA?\nA: L'EBITDA è di 2.5M EUR",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Metadati aggiuntivi per il report FAQ",
        example={"numero_faq": 10, "timestamp": "2024-12-07 10:30:00", "categoria": "FAQ Finanziarie"},
    )
    filename: Optional[str] = Field(None, description="Nome del file senza estensione", example="faq_aziendali_2024")


class PDFResponse(BaseModel):
    """Response model per esportazione PDF."""

    success: bool = Field(..., description="Stato dell'operazione")
    filename: str = Field(..., description="Nome del file generato")
    pdf_b64: str = Field(..., description="PDF codificato in base64")
    size_bytes: int = Field(..., description="Dimensione del file in bytes")
    timestamp: str = Field(..., description="Timestamp di generazione")


def get_pdf_exporter() -> PDFExporter:
    """Dependency injection per PDF Exporter."""
    return PDFExporter()


@router.post(
    "/analysis",
    response_model=PDFResponse,
    summary="Salva Analisi come PDF",
    description="""
    Genera e salva un PDF contenente l'analisi dei documenti.

    Il PDF viene generato con styling professionale ZCS Company e include:
    - Header con logo aziendale
    - Analisi formattata
    - Metadati del documento
    - Footer con informazioni di contatto

    Il PDF viene restituito codificato in base64 per facilitare il download o l'invio.
    """,
)
async def save_analysis_pdf(
    request: AnalysisPDFRequest, pdf_exporter: PDFExporter = Depends(get_pdf_exporter)
) -> PDFResponse:
    """
    Salva l'analisi come PDF formattato professionalmente.

    Args:
        request: Dati dell'analisi e metadati
        pdf_exporter: Servizio di esportazione PDF

    Returns:
        PDFResponse: PDF codificato in base64 con metadati
    """
    try:
        # Prepara i metadati
        metadata = request.metadata or {}
        if "timestamp" not in metadata:
            metadata["timestamp"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if "tipo_analisi" not in metadata:
            metadata["tipo_analisi"] = "Analisi Documenti RAG"

        # Genera nome file se non fornito
        filename = request.filename or f"analisi_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not filename.endswith(".pdf"):
            filename += ".pdf"

        # Crea struttura documento per il metodo export_document_analysis
        document_analyses = {filename: request.analysis}

        # Genera PDF usando il metodo esistente
        pdf_buffer = pdf_exporter.export_document_analysis(
            document_analyses=document_analyses, metadata=metadata, filename=filename
        )

        # Ottieni bytes del PDF
        pdf_bytes = pdf_buffer.getvalue()

        # Codifica in base64
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        return PDFResponse(
            success=True,
            filename=filename,
            pdf_b64=pdf_b64,
            size_bytes=len(pdf_bytes),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella generazione del PDF analisi: {str(e)}")


@router.post(
    "/faq",
    response_model=PDFResponse,
    summary="Salva FAQ come PDF",
    description="""
    Genera e salva un PDF contenente le FAQ.

    Il PDF viene generato con styling professionale ZCS Company e include:
    - Header con logo aziendale
    - FAQ formattate in modo leggibile
    - Indice delle domande
    - Footer con informazioni di contatto

    Il PDF viene restituito codificato in base64.
    """,
)
async def save_faq_pdf(request: FAQPDFRequest, pdf_exporter: PDFExporter = Depends(get_pdf_exporter)) -> PDFResponse:
    """
    Salva le FAQ come PDF formattato professionalmente.

    Args:
        request: FAQ e metadati
        pdf_exporter: Servizio di esportazione PDF

    Returns:
        PDFResponse: PDF codificato in base64 con metadati
    """
    try:
        # Prepara i metadati
        metadata = request.metadata or {}
        if "timestamp" not in metadata:
            metadata["timestamp"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if "categoria" not in metadata:
            metadata["categoria"] = "FAQ Intelligenti"

        # Genera nome file se non fornito
        filename = request.filename or f"faq_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not filename.endswith(".pdf"):
            filename += ".pdf"

        # Converti stringa FAQ in formato lista di dizionari per export_faq
        faq_list = []

        # Parsing delle FAQ dalla stringa
        faq_sections = request.faqs.strip().split("\n\n")
        for section in faq_sections:
            lines = section.strip().split("\n")
            question = ""
            answer = ""

            for line in lines:
                if line.startswith("Q:") or line.startswith("Domanda:"):
                    question = line.replace("Q:", "").replace("Domanda:", "").strip()
                elif line.startswith("A:") or line.startswith("Risposta:"):
                    answer = line.replace("A:", "").replace("Risposta:", "").strip()
                elif question and not answer:
                    # Continuazione della domanda
                    question += " " + line.strip()
                elif answer:
                    # Continuazione della risposta
                    answer += " " + line.strip()

            if question and answer:
                faq_list.append({"question": question, "answer": answer})

        # Se non ci sono FAQ parsate, usa il testo originale come singola FAQ
        if not faq_list:
            faq_list = [{"question": "Contenuto FAQ", "answer": request.faqs}]

        # Aggiorna metadati con numero FAQ
        metadata["numero_faq"] = len(faq_list)

        # Genera PDF usando il metodo esistente export_faq
        pdf_buffer = pdf_exporter.export_faq(faqs=faq_list, metadata=metadata, filename=filename)

        # Ottieni bytes del PDF
        pdf_bytes = pdf_buffer.getvalue()

        # Codifica in base64
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        return PDFResponse(
            success=True,
            filename=filename,
            pdf_b64=pdf_b64,
            size_bytes=len(pdf_bytes),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella generazione del PDF FAQ: {str(e)}")


@router.get(
    "/health",
    summary="Health Check PDF Export",
    description="Verifica che il servizio di esportazione PDF sia funzionante",
)
async def health_check():
    """
    Verifica lo stato del servizio di esportazione PDF.

    Returns:
        Dict con stato del servizio
    """
    try:
        pdf_exporter = get_pdf_exporter()
        return {"status": "healthy", "service": "pdf_export", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "pdf_export",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
