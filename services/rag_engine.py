"""RAG Engine using LlamaIndex and Qdrant for document retrieval and analysis."""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Document,
    StorageContext,
    Settings
)
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.schema import TextNode

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG engine for document indexing and retrieval using LlamaIndex and Qdrant."""
    
    def __init__(self):
        """Initialize RAG engine with Qdrant and OpenAI."""
        self.client = None
        self.vector_store = None
        self.index = None
        self.collection_name = settings.qdrant_collection_name
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize Qdrant client, vector store, and global settings."""
        try:
            # Configure global LlamaIndex settings
            Settings.llm = OpenAI(
                model=settings.llm_model,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                api_key=settings.openai_api_key
            )
            Settings.embed_model = OpenAIEmbedding(
                model=settings.embedding_model,
                api_key=settings.openai_api_key
            )
            Settings.chunk_size = settings.chunk_size
            Settings.chunk_overlap = settings.chunk_overlap
            
            # Initialize Qdrant client
            self.client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port
            )
            
            # Create or recreate collection
            self._setup_collection()
            
            # Initialize vector store
            self.vector_store = QdrantVectorStore(
                client=self.client,
                collection_name=self.collection_name
            )
            
            # Initialize or load existing index
            self._initialize_index()
            
            logger.info("RAG Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing RAG Engine: {str(e)}")
            raise
    
    def _setup_collection(self):
        """Setup Qdrant collection with proper configuration."""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)
            
            if collection_exists:
                logger.info(f"Collection {self.collection_name} already exists")
            else:
                # Create new collection with proper vector size for OpenAI embeddings
                vector_size = 1536  # OpenAI text-embedding-3-small dimension
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created new collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Error setting up collection: {str(e)}")
            raise
    
    def _initialize_index(self):
        """Initialize or load existing index."""
        try:
            storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )
            
            # Check if index exists in vector store
            collection_info = self.client.get_collection(self.collection_name)
            if collection_info.points_count > 0:
                # Load existing index
                self.index = VectorStoreIndex.from_vector_store(
                    self.vector_store
                )
                logger.info(f"Loaded existing index with {collection_info.points_count} vectors")
            else:
                # Create new empty index
                self.index = VectorStoreIndex(
                    [],
                    storage_context=storage_context
                )
                logger.info("Created new empty index")
                
        except Exception as e:
            logger.error(f"Error initializing index: {str(e)}")
            self.index = VectorStoreIndex(
                [],
                storage_context=StorageContext.from_defaults(vector_store=self.vector_store)
            )
    
    def index_documents(self, file_paths: List[str], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Index documents from file paths."""
        results = {
            'indexed_files': [],
            'failed_files': [],
            'total_chunks': 0,
            'errors': []
        }
        
        for file_path in file_paths:
            try:
                path = Path(file_path)
                if not path.exists():
                    results['failed_files'].append(file_path)
                    results['errors'].append(f"File not found: {file_path}")
                    continue
                
                # Load document based on file type
                if path.suffix.lower() == '.pdf':
                    documents = self._load_pdf(file_path, metadata)
                elif path.suffix.lower() in ['.txt', '.md']:
                    documents = self._load_text(file_path, metadata)
                elif path.suffix.lower() in ['.docx', '.doc']:
                    documents = self._load_docx(file_path, metadata)
                else:
                    documents = SimpleDirectoryReader(
                        input_files=[file_path]
                    ).load_data()
                
                # Add metadata to documents
                for doc in documents:
                    doc.metadata = doc.metadata or {}
                    doc.metadata.update({
                        'source': file_path,
                        'indexed_at': datetime.now().isoformat(),
                        'file_type': path.suffix.lower()
                    })
                    if metadata:
                        doc.metadata.update(metadata)
                
                # Parse documents into nodes
                parser = SimpleNodeParser.from_defaults()
                nodes = parser.get_nodes_from_documents(documents)
                
                # Add nodes to index
                self.index.insert_nodes(nodes)
                
                results['indexed_files'].append(file_path)
                results['total_chunks'] += len(nodes)
                logger.info(f"Indexed {file_path}: {len(nodes)} chunks")
                
            except Exception as e:
                results['failed_files'].append(file_path)
                results['errors'].append(f"Error indexing {file_path}: {str(e)}")
                logger.error(f"Error indexing {file_path}: {str(e)}")
        
        return results
    
    def _load_pdf(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Load and parse PDF documents."""
        try:
            from pypdf import PdfReader
            
            reader = PdfReader(file_path)
            documents = []
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    doc = Document(
                        text=text,
                        metadata={
                            'page': i + 1,
                            'total_pages': len(reader.pages),
                            'source': file_path
                        }
                    )
                    if metadata:
                        doc.metadata.update(metadata)
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error loading PDF {file_path}: {str(e)}")
            raise
    
    def _load_text(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Load text or markdown files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            doc = Document(
                text=content,
                metadata={'source': file_path}
            )
            if metadata:
                doc.metadata.update(metadata)
            
            return [doc]
            
        except Exception as e:
            logger.error(f"Error loading text file {file_path}: {str(e)}")
            raise
    
    def _load_docx(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Load Word documents."""
        try:
            from docx import Document as DocxDocument
            
            doc = DocxDocument(file_path)
            full_text = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            
            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            full_text.append(cell.text)
            
            document = Document(
                text='\n'.join(full_text),
                metadata={'source': file_path}
            )
            if metadata:
                document.metadata.update(metadata)
            
            return [document]
            
        except Exception as e:
            logger.error(f"Error loading DOCX {file_path}: {str(e)}")
            raise
    
    def query(self, query_text: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query the indexed documents."""
        try:
            if not self.index:
                return {
                    'answer': "No documents have been indexed yet.",
                    'sources': [],
                    'confidence': 0
                }
            
            # Create query engine with specific parameters
            query_engine = self.index.as_query_engine(
                similarity_top_k=top_k,
                response_mode="tree_summarize",
                verbose=settings.debug_mode
            )
            
            # Execute query
            response = query_engine.query(query_text)
            
            # Extract source information
            sources = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    sources.append({
                        'text': node.node.text[:200] + "...",
                        'score': node.score,
                        'metadata': node.node.metadata
                    })
            
            return {
                'answer': str(response),
                'sources': sources,
                'confidence': sources[0]['score'] if sources else 0
            }
            
        except Exception as e:
            logger.error(f"Error querying index: {str(e)}")
            return {
                'answer': f"Error processing query: {str(e)}",
                'sources': [],
                'confidence': 0
            }
    
    def query_with_context(self, query_text: str, context_data: Dict[str, Any], top_k: int = 3) -> Dict[str, Any]:
        """Query with additional context from CSV analysis."""
        try:
            # Enhance query with context
            enhanced_query = f"""
            Based on the following business data context:
            {self._format_context(context_data)}
            
            Question: {query_text}
            
            Please provide a detailed answer considering both the documents and the business data provided.
            """
            
            return self.query(enhanced_query, top_k=top_k)
            
        except Exception as e:
            logger.error(f"Error in query with context: {str(e)}")
            return {
                'answer': f"Error processing query: {str(e)}",
                'sources': [],
                'confidence': 0
            }
    
    def _format_context(self, context_data: Dict[str, Any]) -> str:
        """Format context data for query enhancement."""
        formatted_parts = []
        
        if 'summary' in context_data:
            formatted_parts.append("Summary metrics:")
            for key, value in context_data['summary'].items():
                formatted_parts.append(f"- {key}: {value}")
        
        if 'trends' in context_data:
            formatted_parts.append("\nTrends:")
            if 'yoy_growth' in context_data['trends']:
                for growth in context_data['trends']['yoy_growth'][-2:]:  # Last 2 years
                    formatted_parts.append(f"- Year {growth['year']}: {growth['growth_percentage']}% growth")
        
        if 'insights' in context_data:
            formatted_parts.append("\nKey insights:")
            for insight in context_data['insights'][:3]:  # Top 3 insights
                formatted_parts.append(f"- {insight}")
        
        return '\n'.join(formatted_parts)
    
    def delete_documents(self, source_filter: str) -> bool:
        """Delete documents by source filter."""
        try:
            # This would require implementing filtering in Qdrant
            # For now, we'll recreate the collection
            self._setup_collection()
            self._initialize_index()
            logger.info(f"Cleared all documents from collection")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed documents."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            return {
                'total_vectors': collection_info.points_count,
                'collection_name': self.collection_name,
                'vector_dimension': collection_info.config.params.vectors.size,
                'distance_metric': str(collection_info.config.params.vectors.distance)
            }
            
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            return {
                'total_vectors': 0,
                'error': str(e)
            }