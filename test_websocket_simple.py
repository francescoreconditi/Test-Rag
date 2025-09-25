# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-25
# Scopo: Test WebSocket connection semplice
# ============================================

import asyncio
import websockets

async def test_websocket():
    uri = 'ws://localhost:8000/voice/realtime/test_client_123'
    try:
        async with websockets.connect(uri) as websocket:
            print('WebSocket connected successfully!')

            # Send test message
            await websocket.send('{"type": "test", "message": "hello"}')

            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f'Received: {response}')

    except Exception as e:
        print(f'Connection failed: {e}')

if __name__ == "__main__":
    asyncio.run(test_websocket())