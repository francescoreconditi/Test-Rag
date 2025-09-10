# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-10
# Scopo: Fix minimale per Qdrant
# ============================================

import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Load environment
load_dotenv()

# Connect to Qdrant
client = QdrantClient(url='http://localhost:6333')

# Collection name from env
collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'business_documents')

print(f"Fixing collection: {collection_name}")

try:
    # Delete existing collection
    client.delete_collection(collection_name)
    print(f"Deleted existing collection: {collection_name}")
except:
    print("Collection didn't exist")

# Create new collection with correct config
client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(
        size=1536,  # OpenAI text-embedding-3-small dimension
        distance=Distance.COSINE
    )
)

print(f"✅ Created collection '{collection_name}' with 1536 dimensions")
print("✅ Qdrant is now ready for document indexing")
print("\nNext steps:")
print("1. Use the Streamlit app to upload documents")
print("2. Or run: python -c \"from services.rag_engine import RAGEngine; rag = RAGEngine(); rag.build_index(documents)\"")
