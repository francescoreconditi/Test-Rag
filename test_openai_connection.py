# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-25
# Scopo: Test OpenAI Realtime API connection
# ============================================

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.application.services.openai_realtime import OpenAIRealtimeService

async def test_openai_connection():
    print("Testing OpenAI Realtime API connection...")
    try:
        service = OpenAIRealtimeService()
        print(f"API Key present: {bool(service.api_key)}")
        print(f"API Key length: {len(service.api_key) if service.api_key else 0}")

        result = await service.connect()
        print(f"Connection result: {result}")

        if result:
            print(f"Session ID: {service.session_id}")
            await service.disconnect()
            print("Test successful!")
        else:
            print("Connection failed")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_openai_connection())