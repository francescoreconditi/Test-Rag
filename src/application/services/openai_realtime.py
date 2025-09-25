"""
OpenAI Realtime API Service
==========================

Service per gestire la connessione WebSocket con OpenAI Realtime API
e fornire funzionalità di conversazione vocale in tempo reale.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Callable, Dict, Optional

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class OpenAIRealtimeService:
    """Service per gestire OpenAI Realtime API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inizializza il service.

        Args:
            api_key: API key OpenAI. Se None, viene presa da environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.websocket: Optional[WebSocketClientProtocol] = None
        self.is_connected = False
        self.session_id: Optional[str] = None

        # Callbacks for events
        self.on_session_created: Optional[Callable] = None
        self.on_user_transcript: Optional[Callable] = None
        self.on_assistant_response: Optional[Callable] = None
        self.on_audio_response: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # Configuration
        self.realtime_url = "wss://api.openai.com/v1/realtime"
        self.model = "gpt-4o-realtime-preview-2024-10-01"

    async def connect(self) -> bool:
        """
        Connette al servizio OpenAI Realtime API.

        Returns:
            True se la connessione è riuscita, False altrimenti.
        """
        try:
            logger.info("Connecting to OpenAI Realtime API...")

            # Costruisci URL con parametri
            url = f"{self.realtime_url}?model={self.model}"

            # Headers per autenticazione
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "OpenAI-Beta": "realtime=v1"
            }

            # Connetti via WebSocket
            self.websocket = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )

            self.is_connected = True
            logger.info("✅ Connected to OpenAI Realtime API")

            # Configura la sessione
            await self._configure_session()

            # Avvia il loop di gestione messaggi
            asyncio.create_task(self._message_loop())

            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to OpenAI Realtime API: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """Disconnette dal servizio."""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.close()
                logger.info("🔌 Disconnected from OpenAI Realtime API")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.is_connected = False
                self.websocket = None
                self.session_id = None

    async def _configure_session(self):
        """Configura la sessione OpenAI Realtime."""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": (
                    "Sei un assistente AI per un sistema RAG di Business Intelligence. "
                    "Rispondi sempre in italiano. Aiuta gli utenti con analisi documentali, "
                    "query sui dati aziendali e interpretazione di risultati. "
                    "Sii professionale ma amichevole. Quando non hai informazioni specifiche, "
                    "suggerisci di consultare i documenti caricati o di fare domande più specifiche."
                ),
                "voice": "alloy",  # alloy, echo, fable, onyx, nova, shimmer
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                # "input_audio_transcription": {
                #     "model": "whisper-1"
                # },
                "turn_detection": None,  # Disabilitiamo il turn detection automatico
                "tools": [
                    {
                        "type": "function",
                        "name": "query_rag_system",
                        "description": "Interroga il sistema RAG per ottenere informazioni dai documenti aziendali",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "La domanda da porre al sistema RAG"
                                },
                                "enterprise_mode": {
                                    "type": "boolean",
                                    "description": "Se usare la modalità enterprise per analisi avanzate",
                                    "default": True
                                }
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        }

        await self._send_message(session_config)
        logger.info("📋 Session configured")

    async def _message_loop(self):
        """Loop principale per gestire i messaggi dal WebSocket."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

        except ConnectionClosed:
            logger.info("🔌 WebSocket connection closed")
            self.is_connected = False
        except WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
            self.is_connected = False
            if self.on_error:
                await self.on_error(f"WebSocket error: {e}")

    async def _handle_message(self, data: Dict[str, Any]):
        """
        Gestisce i messaggi ricevuti da OpenAI Realtime API.

        Args:
            data: Dati del messaggio ricevuto
        """
        message_type = data.get("type")

        logger.info(f"📨 OpenAI message: {message_type} - {data}")  # Changed to INFO to see all messages

        if message_type == "session.created":
            self.session_id = data.get("session", {}).get("id")
            logger.info(f"🆔 Session created: {self.session_id}")
            if self.on_session_created:
                await self.on_session_created(data)

        elif message_type == "conversation.item.input_audio_transcription.completed":
            # Trascrizione del parlato dell'utente completata
            transcript = data.get("transcript", "")
            item_id = data.get("item_id")
            logger.info(f"🗣️ User transcript: {transcript}")
            if self.on_user_transcript:
                await self.on_user_transcript(transcript, item_id)

        elif message_type == "response.audio_transcript.delta":
            # Delta della trascrizione della risposta dell'assistente
            delta = data.get("delta", "")
            if self.on_assistant_response:
                await self.on_assistant_response(delta, is_delta=True)

        elif message_type == "response.audio_transcript.done":
            # Trascrizione della risposta completata
            transcript = data.get("transcript", "")
            logger.info(f"🤖 Assistant transcript: {transcript}")
            if self.on_assistant_response:
                await self.on_assistant_response(transcript, is_delta=False)

        elif message_type == "response.audio.delta":
            # Delta dell'audio della risposta
            audio_data = data.get("delta", "")
            if self.on_audio_response:
                await self.on_audio_response(audio_data, is_delta=True)

        elif message_type == "response.audio.done":
            # Audio della risposta completato
            if self.on_audio_response:
                await self.on_audio_response("", is_delta=False)

        elif message_type == "response.function_call_arguments.delta":
            # Function call in corso
            name = data.get("name")
            delta = data.get("delta", "")
            logger.info(f"🔧 Function call delta: {name} - {delta}")

        elif message_type == "response.function_call_arguments.done":
            # Function call completata
            name = data.get("name")
            arguments = data.get("arguments", "")
            call_id = data.get("call_id")
            logger.info(f"🔧 Function call done: {name} - {arguments}")

            # Gestisci la function call
            if name == "query_rag_system":
                await self._handle_rag_function_call(call_id, arguments)

        elif message_type == "conversation.item.created":
            # Item della conversazione creato
            item = data.get("item", {})
            logger.info(f"📝 Conversation item created: {item.get('type')} from {item.get('role')}")

            # Se è un messaggio utente (audio o testo), forza una risposta
            if (item.get("role") == "user" and item.get("type") == "message"):
                content_types = [content.get("type") for content in item.get("content", [])]
                logger.info(f"🚀 Forcing response creation for user message with content: {content_types}")
                await self._create_response()

        elif message_type == "error":
            error_msg = data.get("error", {})
            error_text = f"{error_msg.get('type', 'Unknown')}: {error_msg.get('message', 'No message')}"
            logger.error(f"❌ OpenAI API Error: {error_text}")
            if self.on_error:
                await self.on_error(error_text)

        else:
            logger.debug(f"📨 Unhandled message type: {message_type}")

    async def _handle_rag_function_call(self, call_id: str, arguments: str):
        """
        Gestisce una function call per il sistema RAG.

        Args:
            call_id: ID della function call
            arguments: Argomenti della funzione (JSON string)
        """
        try:
            # Parse degli argomenti
            args = json.loads(arguments) if arguments else {}
            query = args.get("query", "")
            enterprise_mode = args.get("enterprise_mode", True)

            logger.info(f"🔍 Executing RAG query: {query}")

            # TODO: Qui dovresti integrare con il tuo sistema RAG esistente
            # Per ora restituiamo una risposta mock
            mock_result = {
                "response": f"Ho trovato informazioni relative a: {query}. Questa è una risposta di esempio dal sistema RAG.",
                "sources": [
                    {"source": "documento_esempio.pdf", "confidence": 0.85},
                    {"source": "report_finanziario.xlsx", "confidence": 0.72}
                ],
                "confidence": 0.78
            }

            # Invia il risultato della function call
            function_call_output = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(mock_result)
                }
            }

            await self._send_message(function_call_output)

            # Genera la risposta
            response_create = {
                "type": "response.create"
            }

            await self._send_message(response_create)

        except Exception as e:
            logger.error(f"Error handling RAG function call: {e}")

            # Invia errore come output della function call
            error_output = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({
                        "error": f"Errore nell'esecuzione della query RAG: {str(e)}"
                    })
                }
            }

            await self._send_message(error_output)

    async def send_audio_data(self, audio_base64: str):
        """
        Invia dati audio (base64 encoded) all'API.

        Args:
            audio_base64: Audio in formato base64
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to OpenAI Realtime API")

        # Log audio info for debugging
        try:
            import base64
            audio_bytes = base64.b64decode(audio_base64)

            # Calculate duration for PCM16 mono at 24kHz (2 bytes per sample)
            duration_ms = (len(audio_bytes) / 2) / 24000 * 1000
            logger.info(f"🎵 Sending PCM16 audio: {len(audio_bytes)} bytes (~{duration_ms:.1f}ms)")

            # Validate minimum audio duration
            if duration_ms < 100:
                logger.warning(f"⚠️ Audio too short: {duration_ms:.1f}ms (minimum 100ms required)")
                return  # Don't send audio that's too short
            else:
                logger.info(f"✅ Audio duration valid: {duration_ms:.1f}ms")

        except Exception as e:
            logger.warning(f"Could not decode audio for validation: {e}")
            return

        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }

        await self._send_message(message)

    async def commit_audio_buffer(self):
        """Commit dell'audio buffer per iniziare il processing."""
        if not self.is_connected:
            raise ConnectionError("Not connected to OpenAI Realtime API")

        message = {
            "type": "input_audio_buffer.commit"
        }

        await self._send_message(message)

    async def send_text_message(self, text: str):
        """
        Invia un messaggio di testo.

        Args:
            text: Testo da inviare
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to OpenAI Realtime API")

        # Crea l'item del messaggio utente
        user_message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        }

        await self._send_message(user_message)

        # Richiedi una risposta
        response_create = {
            "type": "response.create"
        }

        await self._send_message(response_create)

    async def _send_message(self, message: Dict[str, Any]):
        """
        Invia un messaggio via WebSocket.

        Args:
            message: Messaggio da inviare
        """
        if not self.websocket or not self.is_connected:
            raise ConnectionError("WebSocket not connected")

        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            logger.debug(f"📤 Sent message: {message.get('type')}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise

    def set_callbacks(
        self,
        on_session_created: Optional[Callable] = None,
        on_user_transcript: Optional[Callable] = None,
        on_assistant_response: Optional[Callable] = None,
        on_audio_response: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        """
        Imposta le callback per gli eventi.

        Args:
            on_session_created: Callback per sessione creata
            on_user_transcript: Callback per trascrizione utente
            on_assistant_response: Callback per risposta assistente
            on_audio_response: Callback per audio risposta
            on_error: Callback per errori
        """
        self.on_session_created = on_session_created
        self.on_user_transcript = on_user_transcript
        self.on_assistant_response = on_assistant_response
        self.on_audio_response = on_audio_response
        self.on_error = on_error

    async def _create_response(self):
        """Forza la creazione di una risposta da parte di OpenAI."""
        if not self.is_connected:
            return

        response_create = {
            "type": "response.create"
        }

        await self._send_message(response_create)
        logger.info("📤 Forced response.create sent to OpenAI")

    @property
    def is_ready(self) -> bool:
        """Verifica se il servizio è pronto per l'uso."""
        return self.is_connected and self.session_id is not None