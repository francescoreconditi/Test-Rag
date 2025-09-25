# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-25
# Scopo: Test OpenAI Realtime API diretto
# ============================================

import asyncio
import json
import base64
import websockets
from dotenv import load_dotenv
import os

load_dotenv()

async def test_openai_direct():
    """Test diretto OpenAI Realtime API senza server."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY non trovata")
        return

    url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1"
    }

    try:
        print("[CONNECTING] Connecting to OpenAI...")
        async with websockets.connect(url, additional_headers=headers) as websocket:
            print("[SUCCESS] Connected to OpenAI Realtime API")

            # Configure session
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": "You are a helpful assistant. Respond briefly.",
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "whisper-1"}
                }
            }

            await websocket.send(json.dumps(session_config))
            print("[SENT] Session config sent")

            # Wait for session created
            response = await websocket.recv()
            data = json.loads(response)
            print(f"[RECEIVED] {data.get('type')} - {data}")

            # Create a simple test audio (silence for 1 second at 24kHz)
            sample_rate = 24000
            duration_sec = 1
            samples = sample_rate * duration_sec

            # Generate simple test audio (a very quiet tone)
            import math
            audio_data = bytearray()
            for i in range(samples):
                # Simple sine wave at 440Hz, very quiet
                sample_value = int(1000 * math.sin(2 * math.pi * 440 * i / sample_rate))
                # Convert to 16-bit little-endian
                audio_data.extend(sample_value.to_bytes(2, 'little', signed=True))

            # Encode to base64
            audio_base64 = base64.b64encode(audio_data).decode()
            print(f"[AUDIO] Generated test audio: {len(audio_data)} bytes")

            # Send audio
            audio_message = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            await websocket.send(json.dumps(audio_message))
            print("[SENT] Audio sent")

            # Commit audio
            commit_message = {"type": "input_audio_buffer.commit"}
            await websocket.send(json.dumps(commit_message))
            print("[SENT] Audio committed")

            # Wait for responses
            print("[WAITING] Waiting for OpenAI responses...")
            timeout = 30
            while timeout > 0:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    msg_type = data.get('type')
                    print(f"[MSG] {msg_type}: {data}")

                    if msg_type in ['input_audio_buffer.speech_started', 'conversation.item.input_audio_transcription.completed']:
                        print("[PROCESSING] OpenAI is processing audio!")
                    elif msg_type == 'response.audio_transcript.done':
                        print(f"[TRANSCRIPT] {data.get('transcript')}")
                    elif msg_type == 'response.done':
                        print("[COMPLETE] Response complete")
                        break

                except asyncio.TimeoutError:
                    timeout -= 1
                    if timeout % 5 == 0:
                        print(f"[WAITING] Still waiting... ({timeout}s)")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_openai_direct())