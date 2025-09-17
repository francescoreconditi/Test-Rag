# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-01-16
# Scopo: Servizio indipendente per generazione audio overview
# ============================================

"""
Audio Overview Service - Standalone service for generating podcast-style audio from text.
Can be used by both Streamlit UI and REST API endpoints.
"""

import asyncio
from datetime import datetime
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

# Check for available TTS engines
try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from gtts import gTTS

    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

logger = logging.getLogger(__name__)


def clean_markdown(text: str) -> str:
    """Convert markdown to plain text for TTS"""
    import re

    if not text:
        return ""
    text = re.sub(r"#+\s*", "", text)  # headers
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # italics
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text)  # inline/code blocks
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)  # links [text](url)
    text = re.sub(r">\s*", "", text)  # blockquotes
    text = re.sub(r"-\s*", "", text)  # lists
    return text.strip()


class AudioOverviewService:
    """Standalone service for generating audio overviews from text content."""

    # Voice configurations
    VOICES = {
        "it": {
            "edge": {
                "host1": "it-IT-ElsaNeural",  # Female Italian
                "host2": "it-IT-DiegoNeural",  # Male Italian
            }
        },
        "en": {
            "edge": {
                "host1": "en-US-AriaNeural",  # Female English
                "host2": "en-US-GuyNeural",  # Male English
            }
        },
    }

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the audio overview service.

        Args:
            cache_dir: Directory for caching audio files. If None, uses temp directory.
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            import tempfile

            self.cache_dir = Path(tempfile.gettempdir()) / "audio_overview_cache"

        self.cache_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"Audio cache directory: {self.cache_dir}")

    def check_dependencies(self) -> Dict[str, bool]:
        """Check which TTS engines are available.

        Returns:
            Dictionary with availability status for each engine.
        """
        return {
            "edge_tts": EDGE_TTS_AVAILABLE,
            "gtts": GTTS_AVAILABLE,
            "any_available": EDGE_TTS_AVAILABLE or GTTS_AVAILABLE,
        }

    def generate_dialogue_from_content(
        self,
        content: str,
        query: Optional[str] = None,
        metadata: Optional[Dict] = None,
        language: str = "it",
        llm_service: Optional[Any] = None,
    ) -> List[Tuple[str, str]]:
        """Generate dialogue from content without requiring LLM.

        Args:
            content: Main content to discuss
            query: Optional user query that prompted this content
            metadata: Optional metadata about the content
            language: Language for dialogue ("it" or "en")
            llm_service: Optional LLM service for advanced dialogue generation

        Returns:
            List of (speaker, text) tuples
        """
        if llm_service:
            # Use LLM if available
            return self._generate_llm_dialogue(content, query, metadata, language, llm_service)
        else:
            # Use template-based dialogue
            return self._generate_template_dialogue(content, query, metadata, language)

    def _generate_template_dialogue(
        self, content: str, query: Optional[str], metadata: Optional[Dict], language: str
    ) -> List[Tuple[str, str]]:
        """Generate dialogue using templates (no LLM required).

        Args:
            content: Content to discuss
            query: User query
            metadata: Content metadata
            language: Language code

        Returns:
            List of dialogue turns
        """
        # Split content into manageable chunks
        max_chunk_size = 200
        content_chunks = [content[i : i + max_chunk_size] for i in range(0, len(content), max_chunk_size)]

        dialogue = []

        if language == "it":
            # Italian dialogue template
            dialogue.append(
                ("host1", f"Benvenuti! Oggi parliamo di una domanda interessante{': ' + query if query else '.'}")
            )
            dialogue.append(("host2", "Sì, abbiamo analizzato i documenti e trovato informazioni molto rilevanti."))

            for i, chunk in enumerate(content_chunks[:3]):
                if i == 0:
                    dialogue.append(("host1", f"Iniziamo con questo: {chunk}"))
                    dialogue.append(("host2", "Molto interessante! Questo è un punto chiave."))
                elif i == 1:
                    dialogue.append(("host1", f"C'è anche da considerare: {chunk}"))
                    dialogue.append(("host2", "Esatto, questo aggiunge un'altra prospettiva importante."))
                elif i == 2:
                    dialogue.append(("host1", f"E non dimentichiamo: {chunk}"))

            if metadata and metadata.get("num_sources"):
                dialogue.append(
                    ("host2", f"Queste informazioni provengono da {metadata['num_sources']} fonti diverse.")
                )

            dialogue.append(("host1", "In conclusione, abbiamo visto aspetti molto importanti di questo argomento."))
            dialogue.append(
                ("host2", "Sì, spero che questa discussione sia stata utile per comprendere meglio il tema.")
            )

        else:
            # English dialogue template
            dialogue.append(
                ("host1", f"Welcome! Today we're discussing an interesting question{': ' + query if query else '.'}")
            )
            dialogue.append(("host2", "Yes, we've analyzed the documents and found very relevant information."))

            for i, chunk in enumerate(content_chunks[:3]):
                if i == 0:
                    dialogue.append(("host1", f"Let's start with this: {chunk}"))
                    dialogue.append(("host2", "Very interesting! This is a key point."))
                elif i == 1:
                    dialogue.append(("host1", f"There's also this to consider: {chunk}"))
                    dialogue.append(("host2", "Exactly, this adds another important perspective."))
                elif i == 2:
                    dialogue.append(("host1", f"And let's not forget: {chunk}"))

            if metadata and metadata.get("num_sources"):
                dialogue.append(("host2", f"This information comes from {metadata['num_sources']} different sources."))

            dialogue.append(("host1", "In conclusion, we've covered very important aspects of this topic."))
            dialogue.append(
                ("host2", "Yes, I hope this discussion has been helpful in understanding the subject better.")
            )

        return dialogue

    def _generate_llm_dialogue(
        self, content: str, query: Optional[str], metadata: Optional[Dict], language: str, llm_service: Any
    ) -> List[Tuple[str, str]]:
        """Generate dialogue using LLM service.

        Args:
            content: Content to discuss
            query: User query
            metadata: Content metadata
            language: Language code
            llm_service: LLM service instance

        Returns:
            List of dialogue turns
        """
        prompt = self._create_llm_prompt(content, query, metadata, language)

        try:
            # Call LLM service
            if hasattr(llm_service, "generate"):
                response = llm_service.generate(prompt)
            elif hasattr(llm_service, "complete"):
                response = llm_service.complete(prompt)
            else:
                # Fallback to template if LLM doesn't have expected methods
                logger.warning("LLM service doesn't have expected methods, falling back to template")
                return self._generate_template_dialogue(content, query, metadata, language)

            # Parse LLM response into dialogue turns
            dialogue = self._parse_llm_dialogue(response)

            if not dialogue:
                # Fallback if parsing fails
                return self._generate_template_dialogue(content, query, metadata, language)

            return dialogue

        except Exception as e:
            logger.error(f"Error generating LLM dialogue: {e}")
            return self._generate_template_dialogue(content, query, metadata, language)

    def _create_llm_prompt(self, content: str, query: Optional[str], metadata: Optional[Dict], language: str) -> str:
        """Create prompt for LLM dialogue generation."""
        if language == "it":
            return f"""
Crea un dialogo naturale tra due host di un podcast che discutono questo contenuto.

DOMANDA: {query or "Discussione generale"}

CONTENUTO:
{content[:1500]}  # Limit content length

REGOLE:
- Usa ESATTAMENTE il formato: HOST1: [testo] / HOST2: [testo]
- Alterna sempre tra HOST1 e HOST2
- Mantieni un tono professionale ma accessibile
- 6-8 scambi totali
"""
        else:
            return f"""
Create a natural dialogue between two podcast hosts discussing this content.

QUESTION: {query or "General discussion"}

CONTENT:
{content[:1500]}  # Limit content length

RULES:
- Use EXACTLY this format: HOST1: [text] / HOST2: [text]
- Always alternate between HOST1 and HOST2
- Keep a professional yet accessible tone
- 6-8 total exchanges
"""

    def _parse_llm_dialogue(self, response: str) -> List[Tuple[str, str]]:
        """Parse LLM response into dialogue turns."""
        dialogue = []
        lines = response.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("HOST1:"):
                text = line.replace("HOST1:", "").strip()
                if text:
                    dialogue.append(("host1", text))
            elif line.startswith("HOST2:"):
                text = line.replace("HOST2:", "").strip()
                if text:
                    dialogue.append(("host2", text))

        return dialogue

    async def generate_audio_from_dialogue(
        self,
        dialogue_turns: List[Tuple[str, str]],
        language: str = "it",
        output_path: Optional[Path] = None,
        engine: str = "auto",
    ) -> Dict[str, Any]:
        """Generate audio file from dialogue turns.

        Args:
            dialogue_turns: List of (speaker, text) tuples
            language: Language code
            output_path: Optional output path
            engine: TTS engine to use ("edge", "gtts", or "auto")

        Returns:
            Dictionary with result information
        """
        if not dialogue_turns:
            return {"success": False, "error": "No dialogue turns provided"}

        # Auto-select engine if needed
        if engine == "auto":
            if EDGE_TTS_AVAILABLE:
                engine = "edge"
            elif GTTS_AVAILABLE:
                engine = "gtts"
            else:
                return {"success": False, "error": "No TTS engine available"}

        # Generate output path if not provided
        if not output_path:
            output_path = self.cache_dir / f"audio_{uuid.uuid4().hex[:8]}.mp3"

        try:
            if engine == "edge" and EDGE_TTS_AVAILABLE:
                await self._generate_with_edge_tts(dialogue_turns, language, output_path)
            elif engine == "gtts" and GTTS_AVAILABLE:
                await self._generate_with_gtts(dialogue_turns, language, output_path)
            else:
                return {"success": False, "error": f"Engine {engine} not available"}

            return {
                "success": True,
                "audio_path": str(output_path),
                "engine_used": engine,
                "duration_estimate": self._estimate_duration(dialogue_turns),
                "created_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_with_edge_tts(self, dialogue_turns: List[Tuple[str, str]], language: str, output_path: Path):
        """Generate audio using Edge TTS."""
        temp_files = []

        try:
            # Get voices for language
            voices = self.VOICES.get(language, self.VOICES["en"])["edge"]

            # Generate audio for each turn with unique filenames
            import time

            timestamp = int(time.time() * 1000)  # millisecond timestamp

            for i, (speaker, text) in enumerate(dialogue_turns):
                temp_file = self.cache_dir / f"temp_{timestamp}_{i}_{speaker}.mp3"
                temp_files.append(temp_file)

                # Ensure file doesn't exist
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass

                voice = voices.get(speaker, voices["host1"])
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(str(temp_file))

                # Small delay to avoid conflicts
                await asyncio.sleep(0.1)

            # Combine audio files
            await self._combine_audio_files(temp_files, output_path)

        finally:
            # Cleanup temp files with error handling
            await asyncio.sleep(0.5)  # Wait for file handles to close
            for temp_file in temp_files:
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception as e:
                        logger.warning(f"Could not delete temp file {temp_file}: {e}")

    async def _generate_with_gtts(self, dialogue_turns: List[Tuple[str, str]], language: str, output_path: Path):
        """Generate audio using Google TTS."""
        try:
            from pydub import AudioSegment

            combined = AudioSegment.empty()

            for speaker, text in dialogue_turns:
                # gTTS doesn't support voice selection
                tts = gTTS(text=text, lang=language[:2], slow=False)

                temp_file = self.cache_dir / f"temp_{uuid.uuid4().hex[:8]}.mp3"
                tts.save(str(temp_file))

                audio_segment = AudioSegment.from_mp3(str(temp_file))
                combined += audio_segment
                combined += AudioSegment.silent(duration=500)  # 500ms pause

                temp_file.unlink()

            combined.export(str(output_path), format="mp3")

        except ImportError:
            # If pydub not available, save just the first turn
            if dialogue_turns:
                tts = gTTS(text=dialogue_turns[0][1], lang=language[:2], slow=False)
                tts.save(str(output_path))

    async def _combine_audio_files(self, audio_files: List[Path], output_path: Path):
        """Combine multiple audio files into one."""
        try:
            from pydub import AudioSegment

            combined = AudioSegment.empty()

            for audio_file in audio_files:
                if audio_file.exists():
                    audio_segment = AudioSegment.from_mp3(str(audio_file))
                    combined += audio_segment
                    combined += AudioSegment.silent(duration=300)  # 300ms pause

            combined.export(str(output_path), format="mp3")

        except ImportError:
            # Fallback: just copy first file
            if audio_files and audio_files[0].exists():
                import shutil

                shutil.copy(audio_files[0], output_path)

    def _estimate_duration(self, dialogue_turns: List[Tuple[str, str]]) -> float:
        """Estimate audio duration in seconds."""
        # Rough estimate: 150 words per minute
        total_words = sum(len(text.split()) for _, text in dialogue_turns)
        return (total_words / 150) * 60

    async def process_rag_response(
        self,
        query: str,
        rag_response: Dict,
        language: str = "it",
        llm_service: Optional[Any] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Process a RAG response and generate audio overview.

        Args:
            query: Original user query
            rag_response: Response from RAG system
            language: Language for audio
            llm_service: Optional LLM service
            use_cache: Whether to use cached audio if available

        Returns:
            Dictionary with audio generation results
        """
        # Extract content from RAG response
        content = rag_response.get("answer", rag_response.get("response", ""))
        sources = rag_response.get("sources", [])

        # Create metadata
        metadata = {
            "num_sources": len(sources),
            "confidence": rag_response.get("confidence", 0),
            "timestamp": datetime.now().isoformat(),
        }

        # Generate cache key if caching is enabled
        cache_key = None
        if use_cache:
            cache_key = hashlib.md5(f"{query}_{content[:500]}_{language}".encode()).hexdigest()
            cached_audio = self._get_cached_audio(cache_key)
            if cached_audio:
                return {"success": True, "audio_path": str(cached_audio), "from_cache": True, "metadata": metadata}

        # Clean up content for dialogue generation
        content = clean_markdown(content)
        # Generate dialogue
        dialogue_turns = self.generate_dialogue_from_content(
            content=content, query=query, metadata=metadata, language=language, llm_service=llm_service
        )

        # Generate audio
        result = await self.generate_audio_from_dialogue(dialogue_turns=dialogue_turns, language=language)

        # Cache if successful and caching enabled
        if result["success"] and cache_key:
            self._cache_audio(cache_key, Path(result["audio_path"]))

        # Add metadata to result
        result["metadata"] = metadata
        result["dialogue_turns"] = dialogue_turns
        result["from_cache"] = False

        return result

    def _get_cached_audio(self, cache_key: str) -> Optional[Path]:
        """Get cached audio file if exists."""
        cache_file = self.cache_dir / f"cached_{cache_key}.mp3"
        if cache_file.exists():
            # Check if cache is not too old (24 hours)
            import time

            if time.time() - cache_file.stat().st_mtime < 86400:
                return cache_file
        return None

    def _cache_audio(self, cache_key: str, audio_path: Path):
        """Cache audio file."""
        try:
            import shutil

            cache_file = self.cache_dir / f"cached_{cache_key}.mp3"
            shutil.copy(audio_path, cache_file)
        except Exception as e:
            logger.warning(f"Failed to cache audio: {e}")

    def cleanup_cache(self, max_age_hours: int = 24):
        """Clean up old cached files.

        Args:
            max_age_hours: Maximum age of cache files in hours
        """
        import time

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        cleaned = 0
        for cache_file in self.cache_dir.glob("cached_*.mp3"):
            if current_time - cache_file.stat().st_mtime > max_age_seconds:
                try:
                    cache_file.unlink()
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to delete cache file {cache_file}: {e}")

        logger.info(f"Cleaned {cleaned} old cache files")
        return cleaned
