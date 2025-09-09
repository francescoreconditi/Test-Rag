"""RAG Engine using LlamaIndex and Qdrant for document retrieval and analysis."""

from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from llama_index.core import Document, Settings, SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from config.settings import settings
from services.format_helper import format_analysis_result
from services.prompt_router import choose_prompt
from services.query_cache import QueryCache
from src.domain.entities.tenant_context import TenantContext
try:
    from src.application.services.enterprise_orchestrator import EnterpriseOrchestrator, EnterpriseQuery
    ENTERPRISE_AVAILABLE = True
except ImportError:
    logger.warning("Enterprise orchestrator not available")
    ENTERPRISE_AVAILABLE = False
    EnterpriseOrchestrator = None
    EnterpriseQuery = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG engine for document indexing and retrieval using LlamaIndex and Qdrant."""

    def __init__(self, tenant_context: Optional[TenantContext] = None):
        """Initialize RAG engine with Qdrant and OpenAI, optionally with tenant context."""
        self.client = None
        self.vector_store = None
        self.index = None
        self.tenant_context = tenant_context
        self.collection_name = self._get_tenant_collection_name()
        # Initialize query cache if enabled (with tenant namespace if multi-tenant)
        cache_namespace = f"tenant_{tenant_context.tenant_id}" if tenant_context else None
        self.query_cache = QueryCache(ttl_seconds=3600, namespace=cache_namespace) if settings.rag_enable_caching else None
        # Initialize enterprise orchestrator
        self.enterprise_orchestrator = None
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
            
            # Initialize enterprise orchestrator after RAG components are ready
            if ENTERPRISE_AVAILABLE:
                self.enterprise_orchestrator = EnterpriseOrchestrator(
                    rag_engine=self,
                    csv_analyzer=None,  # Will be set externally if needed
                    openai_api_key=settings.openai_api_key  # Pass API key for embeddings
                )
            else:
                self.enterprise_orchestrator = None

            tenant_info = f" for tenant {self.tenant_context.tenant_id}" if self.tenant_context else ""
            logger.info(f"RAG Engine initialized successfully with enterprise orchestrator{tenant_info}")

        except Exception as e:
            logger.error(f"Error initializing RAG Engine: {str(e)}")
            raise

    def _get_tenant_collection_name(self) -> str:
        """Get collection name based on tenant context."""
        if self.tenant_context:
            return f"tenant_{self.tenant_context.tenant_id}_docs"
        return settings.qdrant_collection_name

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

    def index_documents(self, file_paths: List[str], metadata: Optional[Dict[str, Any]] = None, original_names: Optional[List[str]] = None, permanent_paths: Optional[List[str]] = None, force_prompt_type: Optional[str] = None, csv_analyzer=None) -> Dict[str, Any]:
        """Index documents from file paths."""
        results = {
            'indexed_files': [],
            'failed_files': [],
            'total_chunks': 0,
            'errors': [],
            'document_analyses': {}  # Store automatic analyses
        }

        for i, file_path in enumerate(file_paths):
            try:
                path = Path(file_path)
                if not path.exists():
                    results['failed_files'].append(file_path)
                    results['errors'].append(f"File not found: {file_path}")
                    continue

                # Use original filename if provided, otherwise use current filename
                display_name = original_names[i] if original_names and i < len(original_names) else path.name
                # Get permanent path for PDF viewing
                permanent_path = permanent_paths[i] if permanent_paths and i < len(permanent_paths) else None

                # Load document based on file type
                if path.suffix.lower() == '.pdf':
                    documents = self._load_pdf(file_path, metadata)
                elif path.suffix.lower() in ['.txt', '.md']:
                    documents = self._load_text(file_path, metadata)
                elif path.suffix.lower() in ['.docx', '.doc']:
                    documents = self._load_docx(file_path, metadata)
                elif path.suffix.lower() == '.json':
                    # JSON files are loaded as text documents
                    documents = self._load_text(file_path, metadata)
                elif path.suffix.lower() == '.csv' and csv_analyzer:
                    # CSV files are analyzed and converted to structured documents
                    documents = self._load_csv_with_analysis(file_path, csv_analyzer, metadata)
                elif path.suffix.lower() == '.csv':
                    # Basic CSV loading without analysis
                    documents = self._load_csv_basic(file_path, metadata)
                else:
                    documents = SimpleDirectoryReader(
                        input_files=[file_path]
                    ).load_data()

                # Add metadata to documents
                for doc in documents:
                    doc.metadata = doc.metadata or {}
                    doc_metadata = {
                        'source': display_name,  # Nome file leggibile
                        'indexed_at': datetime.now().isoformat(),
                        'file_type': path.suffix.lower(),
                        'document_size': len(doc.text) if hasattr(doc, 'text') else 0
                    }
                    # Add permanent path for PDF viewing (only for PDFs)
                    if permanent_path and path.suffix.lower() == '.pdf':
                        doc_metadata['pdf_path'] = permanent_path

                    doc.metadata.update(doc_metadata)
                    if metadata:
                        doc.metadata.update(metadata)

                # Parse documents into nodes
                parser = SimpleNodeParser.from_defaults()
                nodes = parser.get_nodes_from_documents(documents)

                # Add nodes to index
                self.index.insert_nodes(nodes)

                # Generate automatic analysis of the document content
                if documents:
                    full_text = '\n'.join([doc.text for doc in documents])

                    # Cache the document text for potential re-analysis
                    if not hasattr(self, '_last_document_texts'):
                        self._last_document_texts = {}
                    self._last_document_texts[display_name] = full_text

                    analysis = self.analyze_document_content(full_text, display_name, force_prompt_type)
                    results['document_analyses'][display_name] = analysis

                results['indexed_files'].append(file_path)
                results['total_chunks'] += len(nodes)
                logger.info(f"Indexed {file_path}: {len(nodes)} chunks")

            except Exception as e:
                results['failed_files'].append(file_path)
                results['errors'].append(f"Error indexing {file_path}: {str(e)}")
                logger.error(f"Error indexing {file_path}: {str(e)}")

        return results

    def clean_metadata_paths(self) -> bool:
        """Remove temporary paths from existing document metadata."""
        try:
            logger.info("Cleaning metadata paths from existing documents...")
            # Use the same logic as delete_documents to ensure clean slate
            return self.delete_documents("*")
        except Exception as e:
            logger.error(f"Error cleaning metadata: {str(e)}")
            return False

    def analyze_document_content(self, document_text: str, file_name: str, force_prompt_type: Optional[str] = None) -> str:
        """Generate automatic analysis of document content using specialized prompts."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)

            # Truncate text if too long (keep first 8000 chars for analysis)
            analysis_text = document_text[:8000] if len(document_text) > 8000 else document_text

            logger.debug(f"Document text length: {len(document_text)}, Analysis text length: {len(analysis_text)}")
            logger.debug(f"Analysis text preview: {analysis_text[:200]}...")

            # Use prompt router to select the best prompt (or force a specific one)
            if force_prompt_type and force_prompt_type != "automatico":
                # Force a specific prompt type
                from services.prompt_router import PROMPT_GENERAL, ROUTER

                if force_prompt_type == "generale":
                    # Handle general prompt explicitly
                    prompt_name = "generale"
                    prompt_text = PROMPT_GENERAL(file_name, analysis_text)
                    debug_info = {"forced": True, "type": "generale"}
                    logger.info(f"Forcing general prompt for document '{file_name}'")
                elif force_prompt_type in ROUTER:
                    # Use specialized prompt from router
                    prompt_name = force_prompt_type
                    prompt_text = ROUTER[force_prompt_type].builder(file_name, analysis_text)
                    debug_info = {"forced": True, "type": force_prompt_type}
                    logger.info(f"Forcing prompt type '{prompt_name}' for document '{file_name}'")
                else:
                    # Unknown prompt type, fallback to general
                    prompt_name = "generale"
                    prompt_text = PROMPT_GENERAL(file_name, analysis_text)
                    debug_info = {"forced": True, "type": "generale", "fallback": True}
                    logger.warning(f"Unknown prompt type '{force_prompt_type}', using general prompt for document '{file_name}'")
            else:
                # Use automatic selection
                prompt_name, prompt_text, debug_info = choose_prompt(file_name, analysis_text)
                logger.info(f"Auto-selected prompt type '{prompt_name}' for document '{file_name}'")
            logger.debug(f"Prompt selection debug info: {debug_info}")

            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sei un analista aziendale esperto che crea analisi professionali di documenti. Rispondi sempre in italiano perfetto e in modo strutturato e chiaro. Segui esattamente il formato richiesto nel prompt."
                    },
                    {
                        "role": "user",
                        "content": prompt_text
                    }
                ],
                temperature=0.2,  # Lower temperature for more structured output
                max_tokens=1500  # Increased for JSON + summary format
            )

            analysis_result = response.choices[0].message.content

            # Add prompt type metadata to result for raw format
            raw_result = f"[Analisi tipo: {prompt_name.upper()}]\n\n{analysis_result}"

            # Format the result for better readability
            formatted_result = format_analysis_result(raw_result)

            return formatted_result

        except Exception as e:
            logger.error(f"Error analyzing document content: {str(e)}")
            return "Analisi automatica non disponibile per questo documento. Contenuto indicizzato correttamente per le ricerche."

    def reanalyze_documents_with_prompt(self, force_prompt_type: str) -> Dict[str, str]:
        """Re-analyze existing documents with a specific prompt type."""
        try:
            # Check if we have existing analyses in memory that can be re-processed
            if hasattr(self, '_last_document_texts') and self._last_document_texts:
                logger.info("Using cached document texts for re-analysis")
                results = {}
                for source, text in self._last_document_texts.items():
                    if text and text.strip():
                        logger.info(f"Re-analyzing cached document '{source}': {len(text)} characters")
                        analysis = self.analyze_document_content(text, source, force_prompt_type)
                        results[source] = analysis
                    else:
                        results[source] = f"## Errore di Ri-analisi\n\nNessun contenuto disponibile per il documento '{source}'."
                return results

            # Fallback: try to get content from vector store (less reliable)
            if not self.index:
                return {"error": "Nessun documento indicizzato trovato"}

            results = {}

            # Get all documents from the vector store
            collection_info = self.client.get_collection(self.collection_name)
            if collection_info.points_count == 0:
                return {"error": "Nessun documento nel database vettoriale"}

            # Try to retrieve documents using a broad query
            logger.info("Attempting to retrieve document content via similarity search")
            query_engine = self.index.as_query_engine(similarity_top_k=50, response_mode="no_text")

            # Use a generic query to get document nodes
            try:
                response = query_engine.query("contenuto documento analisi")

                if hasattr(response, 'source_nodes') and response.source_nodes:
                    documents_content = {}

                    for node in response.source_nodes:
                        source = node.node.metadata.get('source', 'Unknown')
                        text = node.node.text or node.node.get_content()

                        if source not in documents_content:
                            documents_content[source] = []
                        documents_content[source].append(text)

                    logger.info(f"Retrieved content from {len(documents_content)} documents via query")

                    # Re-analyze each document
                    for source, text_chunks in documents_content.items():
                        try:
                            # Combine all chunks for this document
                            full_text = '\n\n'.join(text_chunks)

                            logger.info(f"Re-analyzing document '{source}': {len(text_chunks)} chunks, {len(full_text)} total characters")

                            # Check if we have actual content
                            if not full_text.strip() or len(full_text.strip()) < 50:
                                logger.warning(f"Insufficient content for document '{source}' ({len(full_text)} chars)")
                                results[source] = f"""## Documento Non Disponibile per Ri-analisi

**Documento:** {source}

**Problema:** Il contenuto del documento non è disponibile per la ri-analisi. Questo può accadere quando:
- Il documento originale conteneva principalmente immagini
- Si è verificato un errore durante l'estrazione del testo
- Il documento è stato indicizzato ma il contenuto non è completamente recuperabile

**Soluzione:** Per ri-analizzare questo documento:
1. Ricarica il documento originale
2. Assicurati che contenga testo selezionabile
3. Considera l'uso di OCR se il documento è basato su immagini"""
                                continue

                            # Re-analyze with the forced prompt
                            analysis = self.analyze_document_content(full_text, source, force_prompt_type)
                            results[source] = analysis

                        except Exception as e:
                            logger.error(f"Error re-analyzing document {source}: {str(e)}")
                            results[source] = f"Errore nella ri-analisi: {str(e)}"

                    return results
                else:
                    return {"error": "Impossibile recuperare il contenuto dei documenti dal database vettoriale"}

            except Exception as query_error:
                logger.error(f"Error querying for document content: {str(query_error)}")
                return {"error": f"Errore nel recupero del contenuto: {str(query_error)}"}

        except Exception as e:
            logger.error(f"Error in reanalyze_documents_with_prompt: {str(e)}")
            return {"error": f"Errore nella ri-analisi: {str(e)}"}

    def _load_pdf(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Load and parse PDF documents with enhanced text extraction."""
        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            documents = []
            total_extracted_text = ""

            logger.info(f"Processing PDF: {file_path} with {len(reader.pages)} pages")

            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    page_text_length = len(text.strip())
                    total_extracted_text += text

                    logger.debug(f"Page {i+1}: extracted {page_text_length} characters")

                    if text.strip():
                        doc = Document(
                            text=text,
                            metadata={
                                'page': i + 1,
                                'total_pages': len(reader.pages),
                                'source': file_path,
                                'page_text_length': page_text_length
                            }
                        )
                        if metadata:
                            doc.metadata.update(metadata)
                        documents.append(doc)
                    else:
                        logger.warning(f"Page {i+1} in {file_path} has no extractable text")

                except Exception as page_error:
                    logger.error(f"Error extracting text from page {i+1} in {file_path}: {str(page_error)}")
                    continue

            total_text_length = len(total_extracted_text.strip())
            logger.info(f"PDF processing complete: {len(documents)} pages with text, {total_text_length} total characters")

            # If we extracted very little text, try alternative approach
            if total_text_length < 100:
                logger.warning(f"Very little text extracted ({total_text_length} chars). PDF might be image-based or have extraction issues.")

                # Create a placeholder document with a warning
                if not documents:
                    warning_doc = Document(
                        text=f"[ATTENZIONE] Il documento PDF '{file_path}' potrebbe contenere principalmente immagini o avere problemi di estrazione testo. "
                              f"Sono stati estratti solo {total_text_length} caratteri da {len(reader.pages)} pagine. "
                              f"Per un'analisi completa, si consiglia di utilizzare un documento con testo selezionabile o di convertire "
                              f"le immagini in testo utilizzando OCR.",
                        metadata={
                            'page': 1,
                            'total_pages': len(reader.pages),
                            'source': file_path,
                            'extraction_warning': True,
                            'total_text_length': total_text_length
                        }
                    )
                    if metadata:
                        warning_doc.metadata.update(metadata)
                    documents.append(warning_doc)

            return documents

        except Exception as e:
            logger.error(f"Error loading PDF {file_path}: {str(e)}")
            raise

    def _load_text(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Load text or markdown files."""
        try:
            with open(file_path, encoding='utf-8') as f:
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

    def query(self, query_text: str, top_k: int = 3, filters: Optional[Dict[str, Any]] = None, analysis_type: Optional[str] = None) -> Dict[str, Any]:
        """Query the indexed documents with optional specialized analysis."""
        try:
            if not self.index:
                return {
                    'answer': "Nessun documento è stato ancora indicizzato.",
                    'sources': [],
                    'confidence': 0
                }

            # Check cache first if enabled
            if self.query_cache:
                cached_result = self.query_cache.get(query_text, top_k, analysis_type)
                if cached_result:
                    logger.info(f"Returning cached result for query: {query_text[:50]}...")
                    return cached_result

            # Create query engine with specific parameters
            # Using configurable response mode for performance optimization
            query_engine = self.index.as_query_engine(
                similarity_top_k=top_k or settings.rag_similarity_top_k,
                response_mode=settings.rag_response_mode,  # Configurable: compact, tree_summarize, simple
                verbose=settings.debug_mode,
                streaming=False
            )

            # If analysis_type is specified, enhance the query with specialized context
            if analysis_type and analysis_type != "standard":
                query_text = self._enhance_query_with_analysis_type(query_text, analysis_type)

            # Aggiungi prompt per rispondere in italiano
            query_text_it = f"Per favore rispondi in italiano. {query_text}"

            # Execute query
            response = query_engine.query(query_text_it)

            # Extract source information
            sources = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    sources.append({
                        'text': node.node.text[:200] + "...",
                        'score': node.score,
                        'metadata': node.node.metadata
                    })

            # If specialized analysis is requested, post-process the response
            if analysis_type and analysis_type != "standard":
                response_text = self._apply_specialized_analysis(str(response), sources, query_text, analysis_type)
            else:
                response_text = str(response)

            result = {
                'answer': response_text,
                'sources': sources,
                'confidence': sources[0]['score'] if sources else 0,
                'analysis_type': analysis_type or 'standard'
            }

            # Cache the result if caching is enabled
            if self.query_cache:
                self.query_cache.set(query_text, top_k, result, analysis_type)

            return result

        except Exception as e:
            logger.error(f"Error querying index: {str(e)}")
            return {
                'answer': f"Error processing query: {str(e)}",
                'sources': [],
                'confidence': 0
            }

    async def enterprise_query(self, 
                             query_text: str, 
                             enable_enterprise_features: bool = True,
                             **kwargs) -> Dict[str, Any]:
        """
        Enterprise query with full validation, normalization, and fact table integration.
        
        Args:
            query_text: The query to process
            enable_enterprise_features: Whether to use enterprise processing pipeline
            **kwargs: Additional parameters for EnterpriseQuery
        """
        if not enable_enterprise_features or not self.enterprise_orchestrator or not ENTERPRISE_AVAILABLE:
            # Fallback to standard query
            return self.query(query_text, **kwargs)
        
        try:
            # Create enterprise query - filter known parameters
            valid_params = {
                'query_text': query_text,
                'top_k': kwargs.get('top_k'),
                'use_context': kwargs.get('use_context'),
                'csv_analysis': kwargs.get('csv_analysis'),
                'confidence_threshold': kwargs.get('confidence_threshold', 70.0)
            }
            
            # Remove None values
            valid_params = {k: v for k, v in valid_params.items() if v is not None}
            
            enterprise_query = EnterpriseQuery(**valid_params)
            
            # Get current documents for processing
            documents = []
            if hasattr(self, '_last_document_texts'):
                for filename, content in self._last_document_texts.items():
                    documents.append({
                        'filename': filename,
                        'content': content,
                        'hash': str(hash(content))
                    })
            
            # Process through enterprise pipeline
            processing_result = await self.enterprise_orchestrator.process_enterprise_query(
                enterprise_query, 
                documents
            )
            
            # Generate AI response and get sources
            ai_response = self._generate_ai_response_with_sources(processing_result)
            
            # Convert processing result to standard query response format
            enterprise_response = {
                'answer': ai_response['answer'],
                'sources': ai_response['sources'],
                'confidence': processing_result.confidence_score,
                'analysis_type': 'enterprise',
                'enterprise_data': {
                    'source_references': [ref.to_dict() for ref in processing_result.source_refs],
                    'validation_results': [val.to_dict() for val in processing_result.validation_results],
                    'normalized_metrics': {
                        k: {
                            'value': v.to_float(),
                            'original': v.original_value,
                            'scale': v.scale_applied.unit_name,
                            'confidence': v.confidence
                        } for k, v in processing_result.normalized_data.items()
                    },
                    'mapped_metrics': processing_result.mapped_metrics,
                    'fact_table_records': processing_result.fact_table_records,
                    'processing_time_ms': processing_result.processing_time_ms,
                    'warnings': processing_result.warnings,
                    'errors': processing_result.errors
                }
            }
            
            logger.info(f"Enterprise query processed with confidence {processing_result.confidence_score:.1%}")
            return enterprise_response
            
        except Exception as e:
            logger.error(f"Enterprise query failed, falling back to standard: {e}")
            # Fallback to standard query on error
            return self.query(query_text, **kwargs)
    
    def _generate_ai_response_with_sources(self, processing_result) -> Dict[str, Any]:
        """Generate AI response with sources from processing result."""
        try:
            # Use standard query method to get AI response and sources
            if hasattr(processing_result, 'query_text') and self.index:
                standard_response = self.query(processing_result.query_text, top_k=3)
                
                # Format enterprise response with AI answer + enterprise metadata
                enhanced_answer = standard_response['answer']
                
                # Add enterprise metadata to the response
                metadata_parts = []
                
                # Add normalized metrics if found
                if processing_result.normalized_data:
                    metadata_parts.append("\n\n## 📊 Metriche Finanziarie Rilevate")
                    for metric_name, normalized in processing_result.normalized_data.items():
                        mapped = processing_result.mapped_metrics.get(metric_name)
                        canonical_name = mapped.get('canonical_name', metric_name) if mapped else metric_name
                        metadata_parts.append(
                            f"- **{canonical_name}**: {normalized.to_base_units():,.0f}"
                            f" (scala: {normalized.scale_applied.unit_name})"
                        )
                
                # Add validation warnings if any
                if processing_result.validation_results:
                    failed_validations = [v for v in processing_result.validation_results if not v.passed]
                    if failed_validations:
                        metadata_parts.append("\n\n## ⚠️ Avvisi di Validazione")
                        for validation in failed_validations:
                            metadata_parts.append(f"- {validation.message}")
                
                # Add processing metadata at the end
                processing_metadata = []
                if processing_result.fact_table_records > 0:
                    processing_metadata.append(f"{processing_result.fact_table_records} record salvati nel fact table")
                processing_metadata.append(f"Elaborato in {processing_result.processing_time_ms:.0f}ms con confidenza {processing_result.confidence_score:.1%}")
                
                if processing_metadata:
                    metadata_parts.append(f"\n\n*{' • '.join(processing_metadata)}*")
                
                # Combine AI answer with enterprise metadata
                if metadata_parts:
                    enhanced_answer = enhanced_answer + "\n".join(metadata_parts)
                
                return {
                    'answer': enhanced_answer,
                    'sources': standard_response['sources']
                }
            
            # Fallback if no query_text or index
            return {
                'answer': f"Elaborato in {processing_result.processing_time_ms:.0f}ms con confidenza {processing_result.confidence_score:.1%}",
                'sources': []
            }
            
        except Exception as e:
            logger.error(f"Error generating AI response with sources: {e}")
            return {
                'answer': f"Errore nella generazione della risposta: {str(e)}",
                'sources': []
            }
    

    def _enhance_query_with_analysis_type(self, query_text: str, analysis_type: str) -> str:
        """Enhance query based on analysis type."""
        enhancements = {
            'bilancio': """Analizza questa domanda dal punto di vista finanziario e di bilancio. 
                         Considera metriche come ricavi, EBITDA, margini, cash flow, PFN e covenant.
                         Fornisci numeri specifici e confronti YoY quando disponibili.
                         """,
            'fatturato': """Analizza questa domanda focalizzandoti su vendite e fatturato.
                          Considera ASP, volumi, mix prodotto/cliente, pipeline e forecast.
                          Evidenzia trend di crescita e driver principali.
                          """,
            'magazzino': """Analizza questa domanda dal punto di vista logistico e di gestione scorte.
                          Considera rotazione, OTIF, lead time, obsoleti e livelli di servizio.
                          """,
            'contratto': """Analizza questa domanda dal punto di vista legale e contrattuale.
                          Considera obblighi, SLA, penali, responsabilità e clausole rilevanti.
                          """,
            'presentazione': """Analizza questa domanda estraendo i messaggi chiave e le raccomandazioni strategiche.
                             Identifica obiettivi, milestone e next steps.
                             """,
            'report_dettagliato': """Fornisci un'analisi approfondita in stile investment memorandum.
                                   Include executive summary, analisi per sezione, KPI, rischi e raccomandazioni.
                                   Quantifica sempre le variazioni e usa confronti YoY/Budget.
                                   """
        }

        enhancement = enhancements.get(analysis_type, "")
        if enhancement:
            return f"{enhancement}\n\nDomanda: {query_text}"
        return query_text

    def _apply_specialized_analysis(self, response: str, sources: List[Dict], query: str, analysis_type: str) -> str:
        """Apply specialized post-processing based on analysis type."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)

            # Prepare source context
            source_context = "\n\n".join([
                f"Fonte {i+1} (rilevanza: {s['score']:.2f}):\n{s['text']}"
                for i, s in enumerate(sources[:3])  # Use top 3 sources
            ])

            # Create specialized prompt based on analysis type
            specialized_prompts = {
                'bilancio': f"""Riformula questa risposta con focus finanziario professionale:
                            
                            Risposta originale: {response}
                            
                            Fonti rilevanti:
                            {source_context}
                            
                            Produci un'analisi finanziaria strutturata che include:
                            - Metriche chiave con valori specifici
                            - Trend e variazioni percentuali
                            - Confronti con periodi precedenti
                            - Implicazioni finanziarie
                            
                            Usa un tono da equity analyst professionale.""",

                'report_dettagliato': f"""Trasforma questa risposta in un briefing professionale dettagliato:
                            
                            Risposta originale: {response}
                            
                            Fonti rilevanti:
                            {source_context}
                            
                            Struttura l'analisi come:
                            ## Executive Summary
                            [Sintesi in 2-3 righe]
                            
                            ## Analisi Dettagliata
                            [Punti chiave con quantificazione]
                            
                            ## Implicazioni e Raccomandazioni
                            [Azioni suggerite basate sui dati]
                            
                            Mantieni un tono professionale da investment analyst.""",

                'fatturato': f"""Riformula con focus su vendite e revenue:
                            
                            Risposta: {response}
                            Fonti: {source_context}
                            
                            Evidenzia: driver di crescita, mix prodotto, trend vendite, forecast."""
            }

            prompt = specialized_prompts.get(analysis_type)
            if not prompt:
                return response  # Return original if no specialized prompt

            # Get specialized analysis
            completion = client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "Sei un analista esperto che fornisce analisi specializzate basate sul tipo di documento."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            specialized_response = completion.choices[0].message.content

            # Add analysis type marker
            return f"[Analisi {analysis_type.upper()}]\n\n{specialized_response}"

        except Exception as e:
            logger.error(f"Error applying specialized analysis: {str(e)}")
            return response  # Return original response on error

    def query_with_context(self, query_text: str, context_data: Dict[str, Any], top_k: int = 2, analysis_type: Optional[str] = None) -> Dict[str, Any]:
        """Query with additional context from CSV analysis."""
        try:
            # Enhance query with context
            enhanced_query = f"""
            Basandoti sul seguente contesto di dati aziendali:
            {self._format_context(context_data)}
            
            Domanda: {query_text}
            
            Per favore fornisci una risposta dettagliata considerando sia i documenti che i dati aziendali forniti. Rispondi in italiano.
            """

            return self.query(enhanced_query, top_k=top_k, analysis_type=analysis_type)

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
            formatted_parts.append("Metriche di riepilogo:")
            for key, value in context_data['summary'].items():
                formatted_parts.append(f"- {key}: {value}")

        if 'trends' in context_data:
            formatted_parts.append("\nTendenze:")
            if 'yoy_growth' in context_data['trends']:
                for growth in context_data['trends']['yoy_growth'][-2:]:  # Last 2 years
                    formatted_parts.append(f"- Anno {growth['year']}: {growth['growth_percentage']}% crescita")

        if 'insights' in context_data:
            formatted_parts.append("\nApprofondimenti chiave:")
            for insight in context_data['insights'][:3]:  # Top 3 insights
                formatted_parts.append(f"- {insight}")

        return '\n'.join(formatted_parts)

    def delete_documents(self, source_filter: str) -> bool:
        """Delete documents by source filter."""
        try:
            # Delete the entire collection and recreate it
            logger.info(f"Deleting collection: {self.collection_name}")

            # Clear query cache when deleting documents
            if self.query_cache:
                self.query_cache.clear()
                logger.info("Query cache cleared after document deletion")

            # Delete the collection completely
            try:
                self.client.delete_collection(self.collection_name)
                logger.info(f"Collection {self.collection_name} deleted successfully")
            except Exception as e:
                logger.warning(f"Collection might not exist: {str(e)}")

            # Recreate the collection from scratch
            vector_size = 1536  # OpenAI text-embedding-3-small dimension
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created fresh collection: {self.collection_name}")

            # Reinitialize the index
            self._initialize_index()
            logger.info("Successfully cleared all documents from collection")
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

    def explore_database(self, limit: int = 100, offset: int = 0, search_text: Optional[str] = None) -> Dict[str, Any]:
        """Explore documents in the vector database with pagination and search."""
        try:

            # Get collection info
            collection_info = self.client.get_collection(self.collection_name)
            total_points = collection_info.points_count

            if total_points == 0:
                return {
                    'documents': [],
                    'total_count': 0,
                    'unique_sources': [],
                    'stats': {}
                }

            # Retrieve points with pagination
            # Note: Qdrant doesn't support traditional pagination, so we use scroll
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False  # Don't need vectors for exploration
            )

            # Process points to extract document information
            documents = []
            source_set = set()
            file_types = {}
            total_size = 0

            for point in points:
                payload = point.payload if point.payload else {}

                # Extract metadata
                source = payload.get('source', 'Unknown')
                source_set.add(source)

                doc_info = {
                    'id': str(point.id),
                    'source': source,
                    'indexed_at': payload.get('indexed_at', 'Unknown'),
                    'file_type': payload.get('file_type', 'Unknown'),
                    'document_size': payload.get('document_size', 0),
                    'page': payload.get('page', None),
                    'total_pages': payload.get('total_pages', None),
                    'pdf_path': payload.get('pdf_path', None),
                    'text_preview': payload.get('_node_content', '')[:200] + '...' if payload.get('_node_content') else 'No content',
                    'metadata': payload
                }

                documents.append(doc_info)

                # Collect stats
                file_type = doc_info['file_type']
                file_types[file_type] = file_types.get(file_type, 0) + 1
                total_size += doc_info['document_size']

            # Get unique sources with more details
            unique_sources = self._get_unique_sources_details()

            return {
                'documents': documents,
                'total_count': total_points,
                'current_page': offset // limit + 1,
                'total_pages': (total_points + limit - 1) // limit,
                'unique_sources': unique_sources,
                'stats': {
                    'total_documents': len(unique_sources),
                    'total_chunks': total_points,
                    'file_types': file_types,
                    'total_size_bytes': total_size,
                    'avg_chunk_size': total_size // total_points if total_points > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error exploring database: {str(e)}")
            return {
                'documents': [],
                'total_count': 0,
                'unique_sources': [],
                'stats': {},
                'error': str(e)
            }

    def _get_unique_sources_details(self) -> List[Dict[str, Any]]:
        """Get detailed information about unique document sources."""
        try:
            # Use scroll to get all points and extract unique sources
            all_points = []
            offset = None

            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )

                if not points:
                    break

                all_points.extend(points)
                offset = next_offset

                if offset is None:
                    break

            # Group by source
            sources_map = {}
            for point in all_points:
                payload = point.payload if point.payload else {}
                source = payload.get('source', 'Unknown')

                if source not in sources_map:
                    sources_map[source] = {
                        'name': source,
                        'file_type': payload.get('file_type', 'Unknown'),
                        'indexed_at': payload.get('indexed_at', 'Unknown'),
                        'chunk_count': 0,
                        'total_size': 0,
                        'pages': set(),
                        'pdf_path': payload.get('pdf_path'),
                        'has_analysis': False
                    }

                sources_map[source]['chunk_count'] += 1
                sources_map[source]['total_size'] += payload.get('document_size', 0)

                if payload.get('page'):
                    sources_map[source]['pages'].add(payload.get('page'))

            # Convert to list and process
            unique_sources = []
            for source_info in sources_map.values():
                source_info['page_count'] = len(source_info['pages']) if source_info['pages'] else None
                source_info['pages'] = sorted(list(source_info['pages'])) if source_info['pages'] else []

                # Check if we have cached analysis for this document
                if hasattr(self, '_last_document_texts') and source_info['name'] in self._last_document_texts:
                    source_info['has_analysis'] = True

                unique_sources.append(source_info)

            # Sort by indexed date (most recent first)
            unique_sources.sort(key=lambda x: x['indexed_at'], reverse=True)

            return unique_sources

        except Exception as e:
            logger.error(f"Error getting unique sources: {str(e)}")
            return []

    def get_document_chunks(self, source_name: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document source."""
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            # Create filter for specific source
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value=source_name)
                    )
                ]
            )

            # Retrieve all chunks for this source
            chunks = []
            offset = None

            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=filter_condition,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )

                if not points:
                    break

                for point in points:
                    payload = point.payload if point.payload else {}
                    chunk_info = {
                        'id': str(point.id),
                        'page': payload.get('page'),
                        'text': payload.get('_node_content', '')[:500] if payload.get('_node_content') else 'No content',
                        'size': payload.get('document_size', 0),
                        'metadata': payload
                    }
                    chunks.append(chunk_info)

                offset = next_offset
                if offset is None:
                    break

            # Sort by page number if available
            chunks.sort(key=lambda x: x['page'] if x['page'] else 0)

            return chunks

        except Exception as e:
            logger.error(f"Error getting document chunks: {str(e)}")
            return []

    def delete_document_by_source(self, source_name: str) -> bool:
        """Delete all chunks for a specific document source."""
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            # Create filter for specific source
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value=source_name)
                    )
                ]
            )

            # Get all point IDs for this source
            points_to_delete = []
            offset = None

            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=filter_condition,
                    limit=100,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False
                )

                if not points:
                    break

                points_to_delete.extend([point.id for point in points])

                offset = next_offset
                if offset is None:
                    break

            # Delete points
            if points_to_delete:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=points_to_delete
                )
                logger.info(f"Deleted {len(points_to_delete)} chunks for document '{source_name}'")

                # Clear from cache if present
                if hasattr(self, '_last_document_texts') and source_name in self._last_document_texts:
                    del self._last_document_texts[source_name]

                # Clear query cache as document changed
                if self.query_cache:
                    self.query_cache.clear()
                    logger.info("Query cache cleared after document deletion")

                return True
            else:
                logger.warning(f"No chunks found for document '{source_name}'")
                return False

        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return False

    def search_in_database(self, search_query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for specific content in the database using semantic search."""
        try:
            # Use the existing query infrastructure for semantic search
            query_engine = self.index.as_query_engine(
                similarity_top_k=limit,
                response_mode="no_text"  # Just get the nodes, no synthesis
            )

            response = query_engine.query(search_query)

            results = []
            if hasattr(response, 'source_nodes'):
                for node in response.source_nodes:
                    results.append({
                        'source': node.node.metadata.get('source', 'Unknown'),
                        'page': node.node.metadata.get('page'),
                        'score': node.score,
                        'text': node.node.text[:300] + '...' if len(node.node.text) > 300 else node.node.text,
                        'metadata': node.node.metadata
                    })

            return results

        except Exception as e:
            logger.error(f"Error searching in database: {str(e)}")
            return []

    def generate_faq(self, num_questions: int = 10) -> Dict[str, Any]:
        """Generate FAQ based on vector database content.
        
        Args:
            num_questions: Number of FAQ questions to generate
            
        Returns:
            Dictionary containing generated FAQ with questions and answers
        """
        try:
            if not self.index:
                return {
                    'error': 'Nessun documento indicizzato. Carica documenti prima di generare FAQ.',
                    'faqs': []
                }

            # Get database statistics to understand content
            stats = self.get_index_stats()
            if stats.get('total_vectors', 0) == 0:
                return {
                    'error': 'Database vettoriale vuoto. Carica documenti prima di generare FAQ.',
                    'faqs': []
                }

            logger.info(f"Generating FAQ with {num_questions} questions from {stats.get('total_vectors')} vectors")

            # Get a LARGER sample of documents to understand content themes
            # Increased from 20 to 100 for better content representation
            exploration_data = self.explore_database(limit=100)
            sample_texts = []
            document_types = set()

            if exploration_data.get('documents'):
                for doc in exploration_data['documents']:
                    # Get actual content, NOT metadata!
                    text_preview = ""
                    
                    # Try to get actual node content first
                    if 'metadata' in doc and '_node_content' in doc['metadata']:
                        text_preview = doc['metadata']['_node_content'][:1000]
                    elif 'text_preview' in doc:
                        text_preview = doc['text_preview']
                    
                    # Filter out metadata strings and technical info
                    if text_preview and not any(skip in text_preview.lower() for skip in 
                        ['metadata', 'indexed_at', 'source:', 'page:', 'document_size', 
                         'file_type', 'pdf_path', 'chunk_count', 'total_pages']):
                        sample_texts.append(text_preview)
                    if 'metadata' in doc and 'source' in doc['metadata']:
                        source = doc['metadata']['source'].lower()
                        if 'bilancio' in source or 'balance' in source:
                            document_types.add('bilancio')
                        elif 'fatturato' in source or 'revenue' in source or 'vendite' in source:
                            document_types.add('fatturato')
                        elif 'contratto' in source or 'contract' in source:
                            document_types.add('contratto')
                        elif 'report' in source:
                            document_types.add('report')
                        else:
                            document_types.add('generale')

            # Create context for FAQ generation
            # Use MORE samples (30 instead of 10) for better context
            content_sample = '\n\n---\n\n'.join(sample_texts[:30]) if sample_texts else ""
            document_types_str = ', '.join(document_types) if document_types else 'documenti aziendali'
            
            # PRIORITIZE: If we have cached full text, use it INSTEAD of chunks
            if hasattr(self, '_last_document_texts') and self._last_document_texts:
                # Use actual full document text for better FAQ generation
                full_texts = list(self._last_document_texts.values())
                if full_texts and any(text.strip() for text in full_texts):
                    # Take substantial portion of actual document content
                    content_sample = '\n\n'.join([text[:20000] for text in full_texts])[:30000]
                    logger.info(f"Using FULL document text for FAQ generation: {len(content_sample)} chars")
            elif not sample_texts:
                # If we have no good samples, try a different approach
                logger.warning("No valid text samples found, attempting direct query")
                # Try to retrieve actual content through a query
                try:
                    test_response = self.query("riassumi il contenuto principale del documento", top_k=10)
                    if test_response and 'sources' in test_response:
                        for source in test_response['sources']:
                            if 'text' in source:
                                sample_texts.append(source['text'])
                        content_sample = '\n\n'.join(sample_texts[:20])
                except:
                    pass

            # Validate we have real content, not metadata
            if not content_sample or len(content_sample) < 100:
                logger.error("Insufficient real content for FAQ generation")
                return {
                    'error': 'Contenuto insufficiente per generare FAQ. Assicurati che i documenti siano stati indicizzati correttamente.',
                    'faqs': [],
                    'success': False
                }
            
            # Check if content is mostly metadata (bad sign)
            metadata_keywords = ['source:', 'indexed_at:', 'file_type:', 'page:', 'metadata', 'document_size']
            metadata_count = sum(1 for keyword in metadata_keywords if keyword in content_sample.lower())
            if metadata_count > 5:
                logger.warning(f"Content seems to contain too much metadata ({metadata_count} occurrences)")
            
            # Generate FAQ using LLM
            faq_prompt = f"""
Sei un esperto di business intelligence e analisi aziendale. Analizza ATTENTAMENTE il contenuto fornito e genera {num_questions} domande frequenti (FAQ) che siano STRETTAMENTE PERTINENTI al contenuto effettivo del documento.

IMPORTANTE: Le domande DEVONO essere basate ESCLUSIVAMENTE sul contenuto fornito sotto. Non inventare domande su argomenti non presenti nel testo.

TIPI DI DOCUMENTI PRESENTI: {document_types_str}

CONTENUTO EFFETTIVO DEL DOCUMENTO (NON metadata tecnici):
{content_sample}

NOTA CRITICA: Ignora completamente riferimenti a metadata, nomi file, date di indicizzazione, ID documento, numero pagine. Concentrati SOLO sul contenuto business del documento!

ISTRUZIONI RIGOROSE:
1. Genera {num_questions} domande basate ESCLUSIVAMENTE sul contenuto fornito sopra
2. NON inventare domande su argomenti NON menzionati nel testo (es. se non ci sono dati su marketing, NON fare domande sul marketing)
3. Le domande devono riferirsi a informazioni EFFETTIVAMENTE PRESENTI nel documento
4. Se il documento è un bilancio, fai domande su voci di bilancio, patrimonio, risultati economici, etc.
5. Usa terminologia italiana e professionale appropriata al tipo di documento
6. Prima di generare ogni domanda, verifica che l'argomento sia PRESENTE nel contenuto fornito

FORMATO RICHIESTO:
Per ogni domanda, fornisci SOLO:
- Una domanda chiara e specifica
- NON fornire risposte, solo le domande

Esempi di domande SOLO se questi argomenti sono presenti nel testo:
- Se c'è un bilancio: "Qual è il valore del patrimonio netto?", "Come sono variati i ricavi?"
- Se ci sono dati vendite: "Quali sono i trend di vendita?"
- Se ci sono dati su clienti: "Qual è il tasso di attrito dei clienti?"

RICORDA: Genera domande SOLO su ciò che è EFFETTIVAMENTE presente nel contenuto fornito!

Genera SOLO le domande, una per riga, numerate da 1 a {num_questions}:
"""

            # Query the LLM for FAQ generation
            llm_response = Settings.llm.complete(faq_prompt)
            faq_questions_text = str(llm_response)

            # Parse questions from response
            questions = []
            for line in faq_questions_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Clean up the question
                    question = line
                    # Remove numbering (1., 2., -, •, etc.)
                    question = question.lstrip('0123456789.-• \t')
                    if question:
                        questions.append(question)

            # Generate answers for each question using RAG
            faqs = []
            for i, question in enumerate(questions[:num_questions], 1):
                try:
                    # Query the database for answer
                    rag_response = self.query(question, top_k=2)

                    answer = rag_response.get('answer', 'Non sono riuscito a trovare informazioni specifiche su questo argomento nei documenti caricati.')
                    sources = rag_response.get('sources', [])

                    faqs.append({
                        'id': i,
                        'question': question,
                        'answer': answer,
                        'sources': sources,
                        'generated_at': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    })

                except Exception as e:
                    logger.warning(f"Error generating answer for question {i}: {e}")
                    faqs.append({
                        'id': i,
                        'question': question,
                        'answer': 'Errore nella generazione della risposta. Riprova più tardi.',
                        'sources': [],
                        'generated_at': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    })

            result = {
                'faqs': faqs,
                'metadata': {
                    'total_questions': len(faqs),
                    'generated_at': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    'document_types': list(document_types),
                    'total_documents': stats.get('total_vectors', 0)
                },
                'success': True
            }

            logger.info(f"Successfully generated {len(faqs)} FAQ questions")
            return result

        except Exception as e:
            logger.error(f"Error generating FAQ: {str(e)}")
            return {
                'error': f'Errore nella generazione delle FAQ: {str(e)}',
                'faqs': [],
                'success': False
            }

    def _load_csv_with_analysis(self, file_path: str, csv_analyzer, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Load CSV file with automatic analysis and insights generation."""
        import pandas as pd
        from pathlib import Path
        
        try:
            # Read CSV
            df = pd.read_csv(file_path)
            file_name = Path(file_path).name
            
            # Analyze CSV with csv_analyzer
            analysis = csv_analyzer.analyze(df)
            insights = csv_analyzer.generate_insights(df, analysis)
            
            documents = []
            
            # 1. Create metadata document
            metadata_text = f"""
            Dataset: {file_name}
            Righe: {len(df)}
            Colonne: {len(df.columns)}
            Colonne disponibili: {', '.join(df.columns.tolist())}
            
            Tipi di Dati:
            {chr(10).join([f"- {col}: {dtype}" for col, dtype in analysis.get('data_types', {}).items()])}
            
            Valori Mancanti:
            {chr(10).join([f"- {col}: {count}" for col, count in analysis.get('missing_values', {}).items()]) if 'missing_values' in analysis else 'Nessun valore mancante'}
            
            Statistiche Principali:
            {analysis.get('summary_stats', pd.DataFrame()).to_string() if 'summary_stats' in analysis else 'Non disponibili'}
            """
            
            doc_metadata = {'source': file_name, 'type': 'csv_metadata', 'file_type': '.csv'}
            if metadata:
                doc_metadata.update(metadata)
            
            documents.append(Document(text=metadata_text.strip(), metadata=doc_metadata))
            
            # 2. Create documents from insights
            for i, insight in enumerate(insights[:10], 1):  # Limit to top 10 insights
                insight_doc = Document(
                    text=f"Insight #{i}: {insight}",
                    metadata={
                        'source': file_name, 
                        'type': 'csv_insight',
                        'insight_id': i,
                        'file_type': '.csv',
                        **(metadata or {})
                    }
                )
                documents.append(insight_doc)
            
            # 3. Create documents from sample data (first 100 rows max)
            sample_size = min(100, len(df))
            sample_df = df.head(sample_size)
            
            # Convert to readable text chunks (10 rows at a time)
            for i in range(0, sample_size, 10):
                chunk = sample_df.iloc[i:i+10]
                chunk_text = f"Dati dal CSV '{file_name}' (righe {i+1}-{min(i+10, sample_size)}):\n\n{chunk.to_string()}"
                
                chunk_doc = Document(
                    text=chunk_text,
                    metadata={
                        'source': file_name,
                        'type': 'csv_data',
                        'rows_range': f"{i+1}-{min(i+10, sample_size)}",
                        'file_type': '.csv',
                        **(metadata or {})
                    }
                )
                documents.append(chunk_doc)
            
            logger.info(f"CSV '{file_name}' processed: {len(insights)} insights, {len(documents)-1-len(insights)} data chunks")
            return documents
            
        except Exception as e:
            logger.error(f"Error processing CSV {file_path}: {e}")
            # Fallback to basic CSV loading
            return self._load_csv_basic(file_path, metadata)

    def _load_csv_basic(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Basic CSV loading without analysis (fallback method)."""
        import pandas as pd
        from pathlib import Path
        
        try:
            # Read CSV
            df = pd.read_csv(file_path)
            file_name = Path(file_path).name
            
            # Create a single document with CSV overview
            csv_text = f"""
            File CSV: {file_name}
            Righe: {len(df)}
            Colonne: {len(df.columns)}
            
            Colonne disponibili:
            {', '.join(df.columns.tolist())}
            
            Prime 20 righe di dati:
            {df.head(20).to_string()}
            
            Ultime 5 righe di dati:
            {df.tail(5).to_string()}
            """
            
            doc_metadata = {'source': file_name, 'type': 'csv_basic', 'file_type': '.csv'}
            if metadata:
                doc_metadata.update(metadata)
            
            document = Document(text=csv_text.strip(), metadata=doc_metadata)
            
            logger.info(f"CSV '{file_name}' loaded with basic processing")
            return [document]
            
        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {e}")
            # Ultimate fallback - treat as text file
            return self._load_text(file_path, metadata)
