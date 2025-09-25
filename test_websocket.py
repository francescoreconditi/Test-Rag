# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-25
# Scopo: Test WebSocket endpoint isolato
# ============================================

"""
Test WebSocket Server for debugging voice chat functionality.
"""

import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="WebSocket Test Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/voice/realtime/{client_id}")
async def test_websocket_endpoint(websocket: WebSocket, client_id: str):
    """Test WebSocket endpoint for voice communication."""
    logger.info(f"🔌 New WebSocket connection: client_id={client_id}")

    await websocket.accept()

    # Send connection established message
    await websocket.send_text(json.dumps({
        "type": "connection_established",
        "message": "Test WebSocket connected successfully",
        "client_id": client_id
    }))

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"📨 Received from {client_id}: {data}")

            try:
                message = json.loads(data)
                message_type = message.get("type")

                # Echo the message back with some modifications
                response = {
                    "type": f"echo_{message_type}",
                    "original": message,
                    "response": f"Server received: {message_type}",
                    "timestamp": asyncio.get_event_loop().time()
                }

                await websocket.send_text(json.dumps(response))
                logger.info(f"📤 Sent response to {client_id}: {response['type']}")

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "Invalid JSON format"
                }))

    except WebSocketDisconnect:
        logger.info(f"🔌 Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"❌ Error in WebSocket for {client_id}: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "websocket_test"}

@app.get("/documents")
async def list_documents():
    """Mock documents endpoint to prevent 404 errors."""
    return {
        "total_documents": 5,
        "status": "healthy",
        "indexed_vectors": 5,
        "collection_info": {"status": "active"}
    }

if __name__ == "__main__":
    print("Starting Test WebSocket Server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")