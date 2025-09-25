"""
WebSocket Routes for Real-time Voice Communication
==============================================

Endpoints WebSocket per la comunicazione vocale in tempo reale
con OpenAI Realtime API tramite proxy.
"""

import asyncio
import base64
import json
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.websockets import WebSocketState

from src.application.services.openai_realtime import OpenAIRealtimeService
from .auth import get_optional_tenant
from src.domain.entities.tenant_context import TenantContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice Communication"])


class ConnectionManager:
    """Gestisce le connessioni WebSocket attive."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.realtime_services: Dict[str, OpenAIRealtimeService] = {}

    async def connect(self, websocket: WebSocket, client_id: str, tenant: Optional[TenantContext] = None):
        """
        Connette un nuovo client WebSocket.

        Args:
            websocket: Connessione WebSocket del client
            client_id: ID univoco del client
            tenant: Contesto tenant (opzionale)
        """
        logger.info(f"🔌 ConnectionManager.connect() called for client {client_id}")

        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"✅ WebSocket accepted for client {client_id}")

        # NON connettiamo immediatamente a OpenAI per evitare timeout
        # La connessione avverrà on-demand quando necessario
        logger.info(f"📤 Sending immediate connection confirmation to client {client_id}")

        # Invia conferma immediata al client
        await self.send_message(client_id, {
            "type": "connection_established",
            "message": "WebSocket connesso - OpenAI si connetterà quando necessario",
            "session_ready": False,
            "openai_status": "not_connected"
        })
        logger.info(f"✅ Client {client_id} WebSocket connection established (OpenAI on-demand)")

        # TODO: Creazione del servizio OpenAI sarà on-demand

    async def disconnect(self, client_id: str):
        """
        Disconnette un client.

        Args:
            client_id: ID del client da disconnettere
        """
        # Chiudi connessione OpenAI
        if client_id in self.realtime_services:
            await self.realtime_services[client_id].disconnect()
            del self.realtime_services[client_id]

        # Rimuovi connessione WebSocket
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            if websocket.client_state != WebSocketState.DISCONNECTED:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing websocket for client {client_id}: {e}")
            del self.active_connections[client_id]

        logger.info(f"🔌 Client {client_id} disconnected")

    async def send_message(self, client_id: str, message: dict):
        """
        Invia un messaggio a un client specifico.

        Args:
            client_id: ID del client destinatario
            message: Messaggio da inviare
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")
                await self.disconnect(client_id)

    async def send_error(self, client_id: str, error_message: str):
        """
        Invia un messaggio di errore a un client.

        Args:
            client_id: ID del client
            error_message: Messaggio di errore
        """
        await self.send_message(client_id, {
            "type": "error",
            "error": error_message,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def handle_client_message(self, client_id: str, message: dict):
        """
        Gestisce un messaggio ricevuto da un client.

        Args:
            client_id: ID del client che ha inviato il messaggio
            message: Messaggio ricevuto
        """
        message_type = message.get("type")

        # Initialize OpenAI service on-demand when client sends first meaningful message
        if client_id not in self.realtime_services and message_type in ["send_audio", "send_text"]:
            logger.info(f"🔄 Creating OpenAI Realtime service for client {client_id}")
            await self._create_openai_service(client_id)

        if client_id not in self.realtime_services:
            if message_type == "ping":
                # Handle ping even without OpenAI service
                await self.send_message(client_id, {"type": "pong"})
                return
            else:
                await self.send_error(client_id, "Servizio vocale non inizializzato")
                return

        realtime_service = self.realtime_services[client_id]

        try:
            if message_type == "send_audio":
                # Audio inviato dal client
                audio_data = message.get("audio", "")
                await realtime_service.send_audio_data(audio_data)

                # Commit automatico dopo l'invio dell'audio con delay più lungo
                await asyncio.sleep(0.5)  # Aspetta che OpenAI elabori l'audio
                await realtime_service.commit_audio_buffer()

            elif message_type == "commit_audio":
                # Commit esplicito dell'audio buffer (ora gestito automaticamente)
                pass  # Non fare nulla - il commit è gestito automaticamente

            elif message_type == "send_text":
                # Messaggio di testo
                text = message.get("text", "")
                await realtime_service.send_text_message(text)

            elif message_type == "ping":
                # Keep-alive ping
                await self.send_message(client_id, {"type": "pong"})

            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")

        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")
            await self.send_error(client_id, f"Errore nell'elaborazione del messaggio: {str(e)}")

    async def _create_openai_service(self, client_id: str):
        """
        Crea e configura il servizio OpenAI Realtime per un client.

        Args:
            client_id: ID del client
        """
        try:
            logger.info(f"🤖 Creating OpenAI Realtime service for client {client_id}")

            # Crea il servizio OpenAI
            realtime_service = OpenAIRealtimeService()

            # Configura i callback
            realtime_service.on_session_created = lambda data: asyncio.create_task(
                self._on_session_created(client_id, data)
            )
            realtime_service.on_user_transcript = lambda transcript, item_id: asyncio.create_task(
                self._on_user_transcript(client_id, transcript, item_id)
            )
            realtime_service.on_assistant_response = lambda response, is_delta: asyncio.create_task(
                self._on_assistant_response(client_id, response, is_delta)
            )
            realtime_service.on_audio_response = lambda audio_data, is_delta: asyncio.create_task(
                self._on_audio_response(client_id, audio_data, is_delta)
            )
            realtime_service.on_error = lambda error: asyncio.create_task(
                self._on_error(client_id, error)
            )

            # Connetti a OpenAI
            logger.info(f"🔗 Connecting to OpenAI for client {client_id}")
            connected = await realtime_service.connect()

            if connected:
                self.realtime_services[client_id] = realtime_service
                logger.info(f"✅ OpenAI service created and connected for client {client_id}")

                # Invia conferma di connessione OpenAI
                await self.send_message(client_id, {
                    "type": "openai_connected",
                    "message": "Connesso a OpenAI Realtime API",
                    "session_ready": True,
                    "openai_status": "connected"
                })
            else:
                logger.error(f"❌ Failed to connect to OpenAI for client {client_id}")
                await self.send_error(client_id, "Impossibile connettersi a OpenAI Realtime API")

        except Exception as e:
            logger.error(f"❌ Error creating OpenAI service for client {client_id}: {e}")
            await self.send_error(client_id, f"Errore creazione servizio OpenAI: {str(e)}")

    # Callback methods for OpenAI Realtime events
    async def _on_session_created(self, client_id: str, data: dict):
        """Callback per sessione creata."""
        await self.send_message(client_id, {
            "type": "session_created",
            "session_id": data.get("session", {}).get("id"),
            "timestamp": asyncio.get_event_loop().time()
        })

    async def _on_user_transcript(self, client_id: str, transcript: str, item_id: str):
        """Callback per trascrizione utente."""
        await self.send_message(client_id, {
            "type": "user_transcript",
            "transcript": transcript,
            "item_id": item_id,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def _on_assistant_response(self, client_id: str, response: str, is_delta: bool):
        """Callback per risposta assistente."""
        await self.send_message(client_id, {
            "type": "assistant_response",
            "response": response,
            "is_delta": is_delta,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def _on_audio_response(self, client_id: str, audio_data: str, is_delta: bool):
        """Callback per audio risposta."""
        if audio_data:  # Invia solo se c'è audio data
            await self.send_message(client_id, {
                "type": "audio_response",
                "audio": audio_data,
                "is_delta": is_delta,
                "timestamp": asyncio.get_event_loop().time()
            })

    async def _on_error(self, client_id: str, error: str):
        """Callback per errori."""
        await self.send_error(client_id, error)

    def get_stats(self) -> dict:
        """Restituisce statistiche delle connessioni."""
        return {
            "active_connections": len(self.active_connections),
            "realtime_services": len(self.realtime_services),
            "clients": list(self.active_connections.keys())
        }


# Singleton connection manager
connection_manager = ConnectionManager()


@router.websocket("/realtime/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    # tenant: Optional[TenantContext] = Depends(get_optional_tenant) # Temporary disabled to avoid dependency issues
):
    """
    Endpoint WebSocket per comunicazione vocale in tempo reale.

    Args:
        websocket: Connessione WebSocket
        client_id: ID univoco del client
        tenant: Contesto tenant (opzionale)
    """
    logger.info(f"🔌 New WebSocket connection: client_id={client_id}")

    try:
        await connection_manager.connect(websocket, client_id, None)  # tenant disabled for now

        while True:
            try:
                # Ricevi messaggio dal client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Gestisci il messaggio
                await connection_manager.handle_client_message(client_id, message)

            except WebSocketDisconnect:
                logger.info(f"🔌 Client {client_id} disconnected normally")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from client {client_id}: {e}")
                await connection_manager.send_error(client_id, "Formato messaggio non valido")
            except Exception as e:
                logger.error(f"Error in WebSocket loop for client {client_id}: {e}")
                await connection_manager.send_error(client_id, f"Errore interno: {str(e)}")
                break

    except Exception as e:
        logger.error(f"❌ Error in WebSocket endpoint for client {client_id}: {e}")
    finally:
        await connection_manager.disconnect(client_id)


@router.get("/stats")
async def get_voice_stats():
    """
    Restituisce statistiche delle connessioni vocali attive.

    Returns:
        Statistiche delle connessioni
    """
    return connection_manager.get_stats()


@router.post("/test-connection")
async def test_openai_connection():
    """
    Testa la connessione a OpenAI Realtime API.

    Returns:
        Risultato del test di connessione
    """
    try:
        service = OpenAIRealtimeService()
        connected = await service.connect()

        if connected:
            session_id = service.session_id
            await service.disconnect()

            return {
                "status": "success",
                "message": "Connessione a OpenAI Realtime API riuscita",
                "session_id": session_id
            }
        else:
            return {
                "status": "error",
                "message": "Impossibile connettersi a OpenAI Realtime API"
            }

    except Exception as e:
        logger.error(f"Test connection failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore test connessione: {str(e)}"
        )