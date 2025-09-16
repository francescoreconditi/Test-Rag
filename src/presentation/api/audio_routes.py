# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-01-16
# Scopo: Endpoint API per audio overview service
# ============================================

"""
FastAPI routes for Audio Overview service.
Provides REST endpoints for generating audio overviews from RAG responses.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services.audio_overview_service import AudioOverviewService
from services.rag_engine import RAGEngine
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/audio", tags=["audio_overview"])

# Initialize services (will be set by main app)
audio_service: Optional[AudioOverviewService] = None
rag_engine: Optional[RAGEngine] = None
llm_service: Optional[LLMService] = None


def init_audio_routes(rag: RAGEngine, llm: LLMService):
    """Initialize audio routes with services.
    
    Args:
        rag: RAG engine instance
        llm: LLM service instance
    """
    global audio_service, rag_engine, llm_service
    rag_engine = rag
    llm_service = llm
    audio_service = AudioOverviewService()
    logger.info("Audio routes initialized")


class AudioOverviewRequest(BaseModel):
    """Request model for audio overview generation."""
    query: str = Field(..., description="User query or topic")
    content: Optional[str] = Field(None, description="Content to discuss (if not using RAG)")
    language: str = Field("it", description="Language for audio (it/en)")
    use_rag: bool = Field(True, description="Whether to use RAG engine")
    use_llm: bool = Field(True, description="Whether to use LLM for dialogue generation")
    use_cache: bool = Field(True, description="Whether to use cached audio if available")


class AudioOverviewResponse(BaseModel):
    """Response model for audio overview generation."""
    success: bool
    audio_url: Optional[str] = None
    audio_id: Optional[str] = None
    duration_estimate: Optional[float] = None
    from_cache: Optional[bool] = None
    engine_used: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None


@router.get("/status")
async def get_audio_service_status():
    """Get status of audio overview service."""
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not initialized")
    
    deps = audio_service.check_dependencies()
    return {
        "service_available": True,
        "dependencies": deps,
        "cache_dir": str(audio_service.cache_dir)
    }


@router.post("/generate", response_model=AudioOverviewResponse)
async def generate_audio_overview(
    request: AudioOverviewRequest,
    background_tasks: BackgroundTasks
):
    """Generate audio overview from query or content.
    
    Args:
        request: Audio generation request
        background_tasks: FastAPI background tasks
        
    Returns:
        Audio overview response with download information
    """
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not initialized")
    
    # Check dependencies
    deps = audio_service.check_dependencies()
    if not deps["any_available"]:
        raise HTTPException(
            status_code=503, 
            detail="No TTS engine available. Install edge-tts or gtts."
        )
    
    try:
        if request.use_rag and rag_engine:
            # Use RAG engine to get content
            rag_response = rag_engine.query(request.query)
            
            # Generate audio from RAG response
            result = await audio_service.process_rag_response(
                query=request.query,
                rag_response=rag_response,
                language=request.language,
                llm_service=llm_service if request.use_llm else None,
                use_cache=request.use_cache
            )
        else:
            # Use provided content or just the query
            content = request.content or request.query
            
            # Generate dialogue
            dialogue_turns = audio_service.generate_dialogue_from_content(
                content=content,
                query=request.query,
                language=request.language,
                llm_service=llm_service if request.use_llm else None
            )
            
            # Generate audio
            result = await audio_service.generate_audio_from_dialogue(
                dialogue_turns=dialogue_turns,
                language=request.language
            )
            
            result["metadata"] = {"content_length": len(content)}
            result["from_cache"] = False
        
        if result["success"]:
            audio_path = Path(result["audio_path"])
            audio_id = audio_path.stem
            
            # Schedule cleanup in background
            background_tasks.add_task(
                cleanup_old_files, 
                audio_service,
                max_age_hours=2
            )
            
            return AudioOverviewResponse(
                success=True,
                audio_url=f"/audio/download/{audio_id}",
                audio_id=audio_id,
                duration_estimate=result.get("duration_estimate"),
                from_cache=result.get("from_cache", False),
                engine_used=result.get("engine_used"),
                metadata=result.get("metadata")
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Audio generation failed: {result.get('error')}"
            )
            
    except Exception as e:
        logger.error(f"Error in audio generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{audio_id}")
async def download_audio(audio_id: str):
    """Download generated audio file.
    
    Args:
        audio_id: Audio file identifier
        
    Returns:
        Audio file as response
    """
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not initialized")
    
    # Find audio file
    audio_file = None
    for ext in [".mp3", ".wav"]:
        potential_file = audio_service.cache_dir / f"{audio_id}{ext}"
        if potential_file.exists():
            audio_file = potential_file
            break
    
    # Also check cached files
    if not audio_file:
        for cached_file in audio_service.cache_dir.glob(f"cached_*.mp3"):
            if audio_id in cached_file.name:
                audio_file = cached_file
                break
    
    if not audio_file or not audio_file.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=str(audio_file),
        media_type="audio/mpeg",
        filename=f"audio_overview_{audio_id}.mp3"
    )


@router.get("/stream/{audio_id}")
async def stream_audio(audio_id: str, response: Response):
    """Stream audio file (for web player).
    
    Args:
        audio_id: Audio file identifier
        response: FastAPI response object
        
    Returns:
        Streaming audio response
    """
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not initialized")
    
    # Find audio file (similar to download)
    audio_file = None
    for ext in [".mp3", ".wav"]:
        potential_file = audio_service.cache_dir / f"{audio_id}{ext}"
        if potential_file.exists():
            audio_file = potential_file
            break
    
    if not audio_file:
        for cached_file in audio_service.cache_dir.glob(f"cached_*.mp3"):
            if audio_id in cached_file.name:
                audio_file = cached_file
                break
    
    if not audio_file or not audio_file.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Set headers for streaming
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Type"] = "audio/mpeg"
    
    return FileResponse(
        path=str(audio_file),
        media_type="audio/mpeg"
    )


@router.delete("/cache/clean")
async def clean_audio_cache(max_age_hours: int = 24):
    """Clean old audio cache files.
    
    Args:
        max_age_hours: Maximum age of cache files to keep
        
    Returns:
        Cleanup statistics
    """
    if not audio_service:
        raise HTTPException(status_code=503, detail="Audio service not initialized")
    
    cleaned = audio_service.cleanup_cache(max_age_hours)
    return {
        "success": True,
        "files_cleaned": cleaned,
        "max_age_hours": max_age_hours
    }


async def cleanup_old_files(service: AudioOverviewService, max_age_hours: int = 2):
    """Background task to cleanup old files.
    
    Args:
        service: Audio overview service
        max_age_hours: Maximum age for cleanup
    """
    try:
        service.cleanup_cache(max_age_hours)
    except Exception as e:
        logger.warning(f"Background cleanup failed: {e}")


# Health check endpoint
@router.get("/health")
async def audio_health_check():
    """Health check for audio service.
    
    Returns:
        Service health status
    """
    if not audio_service:
        return {"status": "unavailable", "message": "Service not initialized"}
    
    deps = audio_service.check_dependencies()
    
    return {
        "status": "healthy" if deps["any_available"] else "degraded",
        "dependencies": deps,
        "cache_dir_exists": audio_service.cache_dir.exists(),
        "message": "Service operational" if deps["any_available"] else "No TTS engine available"
    }