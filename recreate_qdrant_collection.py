#!/usr/bin/env python3
"""
Script per ricreare la collection Qdrant 'business_documents' con configurazione pulita
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import sys

def recreate_collection():
    """Ricrea la collection business_documents in Qdrant"""

    # Configurazione
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "business_documents")
    VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small dimension

    print(f"Connessione a Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")

    # Inizializza client
    client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT
    )

    # Verifica se la collection esiste
    try:
        collections = client.get_collections()
        existing_collections = [col.name for col in collections.collections]

        if COLLECTION_NAME in existing_collections:
            print(f"Collection '{COLLECTION_NAME}' esistente trovata. Eliminazione in corso...")
            client.delete_collection(collection_name=COLLECTION_NAME)
            print(f"Collection '{COLLECTION_NAME}' eliminata con successo.")
    except Exception as e:
        print(f"Errore durante la verifica delle collections: {e}")

    # Crea nuova collection con configurazione corretta
    try:
        print(f"Creazione nuova collection '{COLLECTION_NAME}'...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )
        print(f"[OK] Collection '{COLLECTION_NAME}' creata con successo!")

        # Verifica la creazione
        collection_info = client.get_collection(collection_name=COLLECTION_NAME)
        print(f"Dettagli collection:")
        print(f"  - Vectors count: {collection_info.vectors_count}")
        print(f"  - Points count: {collection_info.points_count}")
        print(f"  - Status: {collection_info.status}")
        print(f"  - Config: {collection_info.config}")

    except Exception as e:
        print(f"[ERROR] Errore durante la creazione della collection: {e}")
        sys.exit(1)

    print("\n[SUCCESS] Database Qdrant ripulito e pronto all'uso!")

if __name__ == "__main__":
    recreate_collection()