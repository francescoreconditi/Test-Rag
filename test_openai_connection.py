# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-26
# Scopo: Test connessione OpenAI Realtime API
# ============================================

import asyncio
import os
import websockets
import json
from dotenv import load_dotenv

async def test_openai_realtime_connection():
    print("[CONNECTING] Testing OpenAI Realtime API connection...")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("[ERROR] OpenAI API key not found")
        return

    print(f"[KEY] Using API key: {api_key[:12]}...{api_key[-4:]}")

    url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1"
    }

    try:
        print("[ATTEMPTING] Connecting to OpenAI...")
        async with websockets.connect(url, additional_headers=headers) as websocket:
            print("[SUCCESS] Connected to OpenAI Realtime API!")

            # Send a simple session configuration
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text"],
                    "instructions": "You are a helpful assistant.",
                }
            }

            await websocket.send(json.dumps(session_config))
            print("[SENT] Session configuration sent")

            # Wait for response
            print("[WAITING] Waiting for response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"[RECEIVED] {response}")

    except asyncio.TimeoutError:
        print("[TIMEOUT] Connection timed out")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"[ERROR] Invalid status code: {e}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"[ERROR] Connection closed: {e}")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai_realtime_connection())