#!/usr/bin/env python3
"""Test di connessione a Qdrant e verifica collection"""

import requests
import json

def test_qdrant():
    # Test Qdrant health
    try:
        response = requests.get("http://localhost:6333/health")
        print(f"Qdrant health check: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Qdrant non raggiungibile: {e}")
        return False

    # Test collection
    try:
        response = requests.get("http://localhost:6333/collections/business_documents")
        if response.status_code == 200:
            data = response.json()
            print(f"Collection 'business_documents' status: {data['result']['status']}")
            print(f"Points count: {data['result']['points_count']}")
            print(f"Vectors count: {data['result']['indexed_vectors_count']}")
            return True
        else:
            print(f"[ERROR] Collection check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Errore verifica collection: {e}")
        return False

if __name__ == "__main__":
    if test_qdrant():
        print("\n[SUCCESS] Qdrant e collection pronti!")
    else:
        print("\n[ERROR] Problemi con Qdrant!")