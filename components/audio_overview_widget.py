# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-01-16
# Scopo: Widget Streamlit minimale per audio overview
# ============================================

"""
Streamlit widget for Audio Overview integration.
Minimal UI component that can be easily added to any Streamlit page.
"""

import asyncio
import base64
from pathlib import Path
from typing import Dict, Optional
import logging

import streamlit as st

try:
    from services.audio_overview_service import AudioOverviewService
    from services.llm_service import LLMService
    AUDIO_SERVICE_AVAILABLE = True
except ImportError:
    AUDIO_SERVICE_AVAILABLE = False

logger = logging.getLogger(__name__)


def render_audio_overview_widget(
    query: str = None,
    rag_response: Dict = None,
    rag_engine = None,
    container_key: str = "audio_widget"
):
    """Render minimal audio overview widget.
    
    Args:
        query: User query text
        rag_response: RAG engine response (optional)
        rag_engine: RAG engine instance (optional)
        container_key: Unique key for this widget instance
    """
    if not AUDIO_SERVICE_AVAILABLE:
        with st.expander("🎙️ Audio Overview (Non disponibile)"):
            st.warning("Servizio audio overview non disponibile. Installa le dipendenze:")
            st.code("uv add edge-tts pydub", language="bash")
        return
    
    # Initialize session state
    audio_key = f"audio_result_{container_key}"
    if audio_key not in st.session_state:
        st.session_state[audio_key] = None
    
    # Audio Overview UI
    with st.expander("🎙️ Audio Overview", expanded=False):
        st.markdown("*Genera una conversazione podcast dai risultati*")
        
        # Controls row
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            language = st.selectbox(
                "Lingua",
                options=["it", "en"],
                format_func=lambda x: "🇮🇹 Italiano" if x == "it" else "🇬🇧 English",
                key=f"audio_lang_{container_key}"
            )
        
        with col2:
            use_llm = st.checkbox(
                "LLM avanzato",
                value=True,
                help="Usa LLM per dialoghi più naturali",
                key=f"audio_llm_{container_key}"
            )
        
        with col3:
            generate_btn = st.button(
                "🎧 Genera",
                disabled=not query and not rag_response,
                key=f"audio_btn_{container_key}"
            )
        
        # Generate audio
        if generate_btn:
            generate_audio_content(
                query=query,
                rag_response=rag_response,
                rag_engine=rag_engine,
                language=language,
                use_llm=use_llm,
                container_key=container_key
            )
        
        # Display result
        if st.session_state[audio_key]:
            display_audio_result(
                st.session_state[audio_key],
                container_key=container_key
            )


def generate_audio_content(
    query: str,
    rag_response: Dict,
    rag_engine,
    language: str,
    use_llm: bool,
    container_key: str
):
    """Generate audio content and store in session state.
    
    Args:
        query: User query
        rag_response: RAG response
        rag_engine: RAG engine instance
        language: Language code
        use_llm: Whether to use LLM
        container_key: Container key for session state
    """
    with st.spinner("🎙️ Generando audio..."):
        try:
            # Initialize audio service
            audio_service = AudioOverviewService()
            
            # Check dependencies
            deps = audio_service.check_dependencies()
            if not deps["any_available"]:
                st.error("❌ Nessun motore TTS disponibile. Installa edge-tts o gtts.")
                return
            
            # Get LLM service if needed
            llm_service = None
            if use_llm:
                try:
                    llm_service = LLMService()
                except Exception as e:
                    st.warning(f"⚠️ LLM non disponibile, uso template: {e}")
            
            # Generate audio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if rag_response:
                # Use existing RAG response
                result = loop.run_until_complete(
                    audio_service.process_rag_response(
                        query=query,
                        rag_response=rag_response,
                        language=language,
                        llm_service=llm_service,
                        use_cache=True
                    )
                )
            else:
                # Generate new content or use query only
                content = query if query else "Contenuto generale per discussione"
                
                dialogue_turns = audio_service.generate_dialogue_from_content(
                    content=content,
                    query=query,
                    language=language,
                    llm_service=llm_service
                )
                
                result = loop.run_until_complete(
                    audio_service.generate_audio_from_dialogue(
                        dialogue_turns=dialogue_turns,
                        language=language
                    )
                )
                result["dialogue_turns"] = dialogue_turns
                result["from_cache"] = False
            
            # Store result in session state
            audio_key = f"audio_result_{container_key}"
            if result["success"]:
                st.session_state[audio_key] = result
                st.success("✅ Audio generato con successo!")
                st.rerun()
            else:
                st.error(f"❌ Errore: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            st.error(f"❌ Errore nella generazione audio: {str(e)}")


def display_audio_result(result: Dict, container_key: str):
    """Display generated audio result.
    
    Args:
        result: Audio generation result
        container_key: Container key for unique elements
    """
    if not result or not result.get("success"):
        return
    
    audio_path = result.get("audio_path")
    if not audio_path or not Path(audio_path).exists():
        st.warning("⚠️ File audio non trovato")
        return
    
    # Audio player
    st.markdown("#### 🎧 Audio Generato")
    
    try:
        with open(audio_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            st.audio(audio_bytes, format='audio/mp3')
    except Exception as e:
        st.error(f"Errore nel caricamento audio: {e}")
        return
    
    # Metadata
    col1, col2, col3 = st.columns(3)
    
    with col1:
        duration = result.get("duration_estimate", 0)
        st.metric("Durata stimata", f"{duration:.0f}s")
    
    with col2:
        engine = result.get("engine_used", "N/A")
        st.metric("Motore TTS", engine)
    
    with col3:
        cached = "🟢 Cache" if result.get("from_cache") else "🔵 Nuovo"
        st.metric("Stato", cached)
    
    # Download button
    if st.button(f"💾 Scarica MP3", key=f"download_{container_key}"):
        try:
            b64 = base64.b64encode(audio_bytes).decode()
            filename = f"audio_overview_{container_key}.mp3"
            st.markdown(
                f'<a href="data:audio/mp3;base64,{b64}" download="{filename}">'
                f'📥 Clicca per scaricare {filename}</a>',
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"Errore nel download: {e}")
    
    # Show transcript if available
    if result.get("dialogue_turns"):
        with st.expander("📝 Trascrizione dialogo"):
            for i, (speaker, text) in enumerate(result["dialogue_turns"]):
                emoji = "👩" if speaker == "host1" else "👨"
                name = "Host 1" if speaker == "host1" else "Host 2"
                st.markdown(f"**{emoji} {name}:** {text}")
                if i < len(result["dialogue_turns"]) - 1:
                    st.markdown("---")


def render_audio_settings_sidebar():
    """Render audio settings in sidebar (optional).
    
    Returns:
        Dictionary with audio settings
    """
    if not AUDIO_SERVICE_AVAILABLE:
        return {}
    
    with st.sidebar:
        st.markdown("### 🎙️ Audio Settings")
        
        # Global audio preferences
        default_language = st.selectbox(
            "Lingua predefinita",
            options=["it", "en"],
            format_func=lambda x: "🇮🇹 Italiano" if x == "it" else "🇬🇧 English",
            key="audio_default_lang"
        )
        
        auto_generate = st.checkbox(
            "Genera automaticamente",
            value=False,
            help="Genera audio automaticamente dopo ogni query RAG",
            key="audio_auto_generate"
        )
        
        # Cache management
        if st.button("🗑️ Pulisci cache audio", key="clear_audio_cache"):
            try:
                # Clear session state audio results
                keys_to_clear = [k for k in st.session_state.keys() if k.startswith("audio_result_")]
                for key in keys_to_clear:
                    del st.session_state[key]
                
                # Also try to clean service cache
                audio_service = AudioOverviewService()
                cleaned = audio_service.cleanup_cache(max_age_hours=0)
                st.success(f"Cache pulita! ({cleaned} file rimossi)")
            except Exception as e:
                st.error(f"Errore nella pulizia cache: {e}")
        
        return {
            "default_language": default_language,
            "auto_generate": auto_generate
        }


def integrate_with_existing_app():
    """Integration example for existing Streamlit apps.
    
    Add this to your existing app.py:
    
    ```python
    from components.audio_overview_widget import render_audio_overview_widget
    
    # After your RAG query processing:
    if query and response:
        # Your existing response display
        st.write(response['answer'])
        
        # Add audio overview widget
        render_audio_overview_widget(
            query=query,
            rag_response=response,
            rag_engine=rag_engine,
            container_key="main_query"
        )
    ```
    """
    pass