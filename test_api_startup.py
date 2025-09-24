#!/usr/bin/env python3
"""Test avvio API FastAPI"""

import sys
import os

# Aggiungi il path per l'importazione
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Importazione modulo API...")
    from api import app
    print("[OK] API importata con successo")

    # Test base
    print(f"FastAPI app: {app.title}")
    print(f"Version: {app.version}")
    print(f"Routes registered: {len(app.routes)}")

    print("\n[SUCCESS] API pronta per essere avviata!")
    print("\nPer avviare l'API, esegui:")
    print("python -m uvicorn api:app --host 127.0.0.1 --port 8000")

except Exception as e:
    print(f"[ERROR] Errore durante l'importazione API: {e}")
    import traceback
    traceback.print_exc()