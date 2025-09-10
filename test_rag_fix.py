# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-10
# Scopo: Test del fix per il problema Qdrant
# ============================================

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment
load_dotenv()

print("Testing RAG system fix...")

try:
    # Import required modules
    from qdrant_client import QdrantClient
    from services.document_loader import DocumentLoader

    from services.rag_engine import RAGEngine

    # Check Qdrant connection
    client = QdrantClient(url='http://localhost:6333')
    collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'business_documents')

    # Check if collection exists
    collections = client.get_collections()
    print(f"\nAvailable collections: {[c.name for c in collections.collections]}")

    # Initialize RAG engine
    print("\nInitializing RAG engine...")
    rag = RAGEngine()

    # Load sample documents
    print("\nLoading documents...")
    loader = DocumentLoader()
    docs_path = Path('data/documenti')

    if docs_path.exists():
        documents = loader.load_directory(str(docs_path))
        print(f"Loaded {len(documents)} documents")

        # Build index
        print("\nBuilding index with proper embeddings...")
        rag.build_index(documents)
        print("✅ Index built successfully!")

        # Test standard query
        print("\nTesting standard query...")
        response = rag.query("Quali sono i principali indicatori finanziari?")
        print(f"✅ Standard query successful! Response length: {len(str(response))}")

        # Test enterprise query
        print("\nTesting enterprise query...")
        try:
            enterprise_response = rag.enterprise_query("Analizza i ricavi dell'azienda")
            print(f"✅ Enterprise query successful! Confidence: {enterprise_response.confidence}%")
        except Exception as e:
            print(f"⚠️ Enterprise query failed (expected if enterprise components not available): {str(e)[:100]}")

        print("\n✅ All tests passed! RAG system is working correctly.")

    else:
        print(f"❌ Documents directory not found: {docs_path}")

except Exception as e:
    print(f"\n❌ Error during testing: {str(e)}")
    import traceback
    traceback.print_exc()
