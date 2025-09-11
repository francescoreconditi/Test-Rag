# Porre Domande - Documentazione Tecnica Dettagliata

## Indice
1. [Panoramica del Sistema Q&A](#panoramica-del-sistema-qa)
2. [Architettura RAG Enterprise](#architettura-rag-enterprise)
3. [Pipeline di Query Processing](#pipeline-di-query-processing)
4. [Analisi del Codice Sorgente](#analisi-del-codice-sorgente)
5. [Algoritmi di Retrieval e Ranking](#algoritmi-di-retrieval-e-ranking)
6. [Generazione Risposte Contextual](#generazione-risposte-contextual)
7. [Ottimizzazioni Performance](#ottimizzazioni-performance)

---

## Panoramica del Sistema Q&A

Il sistema di Question & Answering rappresenta il cuore dell'interazione utente con il sistema RAG Enterprise. È progettato per comprendere domande in linguaggio naturale, recuperare informazioni rilevanti dai documenti e generare risposte accurate e contestualizzate con tracciabilità completa delle fonti.

### Flusso End-to-End

```
[User Query] → [Query Processing] → [Intent Recognition] → [Retrieval] → [Reranking] → [Answer Generation] → [Source Attribution] → [Response]
     ↓              ↓                    ↓                 ↓              ↓               ↓                    ↓
Query Analysis  Preprocessing    Classification    Document Search  Relevance Scoring  LLM Generation    Provenance Tracking
```

---

## Architettura RAG Enterprise

### Enhanced RAG Engine (`services/rag_engine.py`)

Il componente principale che orchestra l'intero processo di risposta:

```python
class EnhancedRAGEngine:
    """
    RAG Engine potenziato con capacità enterprise e hybrid retrieval
    """
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.llm_service = self._initialize_llm_service()
        self.vector_store = self._initialize_vector_store()
        self.hybrid_retrieval = HybridRetrievalEngine()
        self.query_processor = IntelligentQueryProcessor()
        self.response_generator = ContextualResponseGenerator()
        self.source_tracker = SourceTracker()
        
        # Cache per query frequenti
        self.query_cache = TTLCache(maxsize=1000, ttl=3600)
        
        # Metrics tracking
        self.performance_metrics = PerformanceTracker()
    
    async def enterprise_query(self, query: str, context: QueryContext = None) -> EnterpriseResponse:
        """
        Query enterprise con pipeline completa:
        1. Query analysis e preprocessing
        2. Intent recognition e classification  
        3. Multi-modal retrieval (hybrid)
        4. Context-aware answer generation
        5. Source attribution e provenance
        6. Response validation e quality scoring
        """
        
        start_time = time.time()
        query_id = uuid.uuid4().hex
        
        # Check cache prima di processare
        cache_key = self._generate_cache_key(query, context)
        if cache_key in self.query_cache:
            logger.info(f"Cache hit for query: {query_id}")
            cached_response = self.query_cache[cache_key]
            return self._enhance_cached_response(cached_response, query_id)
        
        try:
            # FASE 1: Query Analysis e Preprocessing
            processed_query = await self.query_processor.process_query(query, context)
            
            # FASE 2: Intent Recognition
            query_intent = await self._recognize_query_intent(processed_query)
            
            # FASE 3: Hybrid Retrieval
            retrieval_results = await self.hybrid_retrieval.retrieve_relevant_docs(
                processed_query, query_intent, top_k=self.config.retrieval_top_k
            )
            
            # FASE 4: Context Building
            response_context = await self._build_response_context(
                processed_query, retrieval_results, query_intent
            )
            
            # FASE 5: Answer Generation
            answer = await self.response_generator.generate_contextual_answer(
                processed_query, response_context, query_intent
            )
            
            # FASE 6: Source Attribution
            attributed_sources = await self.source_tracker.attribute_sources(
                answer, retrieval_results
            )
            
            # FASE 7: Quality Validation
            quality_score = await self._validate_response_quality(
                query, answer, attributed_sources
            )
            
            # Compilation response finale
            enterprise_response = EnterpriseResponse(
                query_id=query_id,
                original_query=query,
                processed_query=processed_query.text,
                answer=answer.text,
                confidence_score=quality_score,
                sources=attributed_sources,
                processing_time=time.time() - start_time,
                query_intent=query_intent,
                retrieval_stats=retrieval_results.stats,
                performance_metrics=self._collect_performance_metrics()
            )
            
            # Cache response
            self.query_cache[cache_key] = enterprise_response
            
            # Record metrics
            self.performance_metrics.record_query(enterprise_response)
            
            return enterprise_response
            
        except Exception as e:
            logger.error(f"Query processing failed for {query_id}: {e}")
            return self._create_error_response(query_id, query, str(e))
    
    async def _recognize_query_intent(self, processed_query: ProcessedQuery) -> QueryIntent:
        """
        Riconoscimento intent della query per personalizzare retrieval e generation
        
        Intent types supportati:
        - FACTUAL: Richiesta informazioni specifiche
        - ANALYTICAL: Richiesta analisi o calcoli  
        - COMPARATIVE: Confronti tra elementi
        - TEMPORAL: Query con componenti temporali
        - SUMMARIZATION: Richiesta riassunti
        - EXPLORATORY: Esplorazione open-ended
        """
        
        intent_classifier = QueryIntentClassifier()
        
        # Multi-layer intent recognition
        primary_intent = await intent_classifier.classify_primary_intent(processed_query.text)
        
        # Sub-intent classification
        sub_intents = await intent_classifier.classify_sub_intents(
            processed_query.text, primary_intent
        )
        
        # Financial domain specific intents
        financial_intent = await self._classify_financial_intent(processed_query)
        
        # Entity-based intent refinement
        entity_based_intent = await self._refine_intent_with_entities(
            processed_query.entities, primary_intent
        )
        
        return QueryIntent(
            primary=primary_intent,
            sub_intents=sub_intents,
            financial_domain=financial_intent,
            entity_context=entity_based_intent,
            confidence=intent_classifier.confidence_score,
            processing_strategy=self._determine_processing_strategy(
                primary_intent, sub_intents, financial_intent
            )
        )
```

---

## Pipeline di Query Processing

### 1. Intelligent Query Processor (`services/query_processor.py`)

Componente responsabile per preprocessing e arricchimento query:

```python
class IntelligentQueryProcessor:
    """
    Processore intelligente query con NLP avanzato e context enhancement
    """
    
    def __init__(self):
        self.nlp = spacy.load("it_core_news_sm")
        self.financial_ner = FinancialEntityRecognizer()
        self.query_expander = QueryExpansionEngine()
        self.spelling_corrector = SpellingCorrector()
        
    async def process_query(self, raw_query: str, context: QueryContext = None) -> ProcessedQuery:
        """
        Preprocessing completo query con:
        1. Spelling correction e normalization
        2. Named entity recognition finanziaria
        3. Query expansion con sinonimi e acronimi
        4. Context integration
        5. Intent signal extraction
        """
        
        # STEP 1: Basic cleaning e normalization
        cleaned_query = self._clean_and_normalize(raw_query)
        
        # STEP 2: Spelling correction
        corrected_query = await self.spelling_corrector.correct_query(cleaned_query)
        
        # STEP 3: NER processing
        doc = self.nlp(corrected_query)
        
        # Standard entities
        standard_entities = self._extract_standard_entities(doc)
        
        # Financial entities
        financial_entities = await self.financial_ner.extract_entities(corrected_query)
        
        # STEP 4: Query expansion
        expanded_terms = await self.query_expander.expand_query(
            corrected_query, standard_entities, financial_entities
        )
        
        # STEP 5: Context integration
        contextualized_query = self._integrate_context(
            corrected_query, expanded_terms, context
        )
        
        # STEP 6: Intent signals extraction
        intent_signals = self._extract_intent_signals(doc, financial_entities)
        
        return ProcessedQuery(
            original=raw_query,
            cleaned=cleaned_query,
            corrected=corrected_query,
            text=contextualized_query,
            entities={**standard_entities, **financial_entities},
            expanded_terms=expanded_terms,
            intent_signals=intent_signals,
            processing_metadata={
                'corrections_made': corrected_query != cleaned_query,
                'entities_found': len(standard_entities) + len(financial_entities),
                'expansion_terms': len(expanded_terms),
                'context_applied': context is not None
            }
        )
    
    def _extract_intent_signals(self, doc, financial_entities: Dict) -> Dict[str, float]:
        """
        Estrazione segnali intent da analisi linguistica
        
        Segnali rilevanti:
        - Question words (cosa, come, quando, perché)
        - Verb patterns (calcola, mostra, confronta)
        - Temporal markers (quest'anno, precedente)
        - Quantitative markers (quanto, quanti)
        - Comparative markers (maggiore, minore, rispetto a)
        """
        
        intent_signals = {}
        
        # Question word analysis
        question_words = {
            'what': ['cosa', 'che', 'quale'],
            'how': ['come', 'in che modo'],
            'when': ['quando', 'in che periodo'],
            'why': ['perché', 'per quale motivo'],
            'where': ['dove', 'in quale'],
            'how_much': ['quanto', 'quanti', 'quale importo']
        }
        
        for intent_type, words in question_words.items():
            signal_strength = sum(1 for token in doc if token.lemma_.lower() in words)
            if signal_strength > 0:
                intent_signals[f'question_{intent_type}'] = signal_strength / len(doc)
        
        # Action verb analysis
        action_verbs = {
            'calculate': ['calcola', 'determina', 'computa'],
            'compare': ['confronta', 'compara', 'paragona'],
            'analyze': ['analizza', 'esamina', 'studia'],
            'show': ['mostra', 'visualizza', 'presenta'],
            'explain': ['spiega', 'illustra', 'chiarisci']
        }
        
        for action_type, verbs in action_verbs.items():
            signal_strength = sum(1 for token in doc if token.lemma_.lower() in verbs)
            if signal_strength > 0:
                intent_signals[f'action_{action_type}'] = signal_strength / len(doc)
        
        # Temporal signal analysis
        temporal_patterns = [
            r'quest[oa]\s+anno',
            r'anno\s+precedente',
            r'ultim[aoi]\s+\d+\s+ann[io]',
            r'\d{4}',  # Year mentions
            r'trimestre',
            r'semestre'
        ]
        
        temporal_score = 0
        for pattern in temporal_patterns:
            matches = re.findall(pattern, doc.text.lower())
            temporal_score += len(matches)
        
        if temporal_score > 0:
            intent_signals['temporal_context'] = temporal_score / len(doc.text.split())
        
        # Financial context strength
        if financial_entities:
            financial_strength = len(financial_entities) / len(doc)
            intent_signals['financial_context'] = financial_strength
        
        return intent_signals
```

### 2. Query Expansion Engine (`services/query_expansion.py`)

Sistema per espansione automatica query con sinonimi e context business:

```python
class QueryExpansionEngine:
    """
    Engine per espansione intelligente query con ontologia business
    """
    
    def __init__(self):
        self.business_ontology = self._load_business_ontology()
        self.financial_synonyms = self._load_financial_synonym_dict()
        self.acronym_expander = AcronymExpander()
        self.semantic_similarity = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def expand_query(self, query: str, entities: Dict, financial_entities: Dict) -> QueryExpansion:
        """
        Espansione multi-layer query:
        1. Synonym expansion con ontologia business
        2. Acronym expansion automatica
        3. Semantic expansion con embeddings
        4. Financial term disambiguation  
        5. Context-aware term weighting
        """
        
        expansion_result = QueryExpansion(original_query=query)
        
        # LAYER 1: Business synonym expansion
        business_expansions = await self._expand_with_business_synonyms(
            query, entities, financial_entities
        )
        expansion_result.add_expansions('business_synonyms', business_expansions)
        
        # LAYER 2: Acronym expansion
        acronym_expansions = await self.acronym_expander.expand_acronyms(query)
        expansion_result.add_expansions('acronyms', acronym_expansions)
        
        # LAYER 3: Semantic similarity expansion
        semantic_expansions = await self._expand_with_semantic_similarity(query)
        expansion_result.add_expansions('semantic', semantic_expansions)
        
        # LAYER 4: Financial term disambiguation
        disambiguated_terms = await self._disambiguate_financial_terms(
            query, financial_entities
        )
        expansion_result.add_expansions('disambiguated', disambiguated_terms)
        
        # LAYER 5: Context weighting
        weighted_expansions = self._apply_context_weighting(expansion_result)
        
        return weighted_expansions
    
    async def _expand_with_business_synonyms(self, query: str, entities: Dict, financial_entities: Dict) -> List[ExpansionTerm]:
        """
        Espansione con sinonimi business utilizzando ontologia finanziaria
        """
        
        expansions = []
        query_tokens = query.lower().split()
        
        # Ricerca sinonimi per ogni token significativo
        for token in query_tokens:
            if len(token) > 3:  # Skip stop words corti
                
                # Ricerca in ontologia business
                business_synonyms = self._find_business_synonyms(token)
                
                for synonym in business_synonyms:
                    # Calcola relevance score basato su context
                    relevance = self._calculate_synonym_relevance(
                        token, synonym, entities, financial_entities
                    )
                    
                    if relevance > 0.6:  # Threshold per qualità
                        expansions.append(ExpansionTerm(
                            original=token,
                            expanded=synonym,
                            type='business_synonym',
                            relevance=relevance,
                            source='business_ontology'
                        ))
        
        return expansions
    
    def _find_business_synonyms(self, term: str) -> List[str]:
        """
        Ricerca sinonimi in ontologia business finanziaria
        
        Ontologia strutturata per categorie:
        - revenue_terms: [ricavi, fatturato, revenues, sales]
        - profit_terms: [utile, profitto, profit, earnings]
        - debt_terms: [debito, debt, liabilities, passività]
        - asset_terms: [attivo, assets, patrimonio]
        """
        
        synonyms = []
        
        # Ricerca diretta in categorie ontologiche
        for category, terms in self.business_ontology.items():
            if term.lower() in [t.lower() for t in terms]:
                # Aggiungi tutti gli altri termini della categoria
                category_synonyms = [t for t in terms if t.lower() != term.lower()]
                synonyms.extend(category_synonyms)
        
        # Ricerca fuzzy per match parziali
        for category, terms in self.business_ontology.items():
            for ontology_term in terms:
                similarity = fuzz.ratio(term.lower(), ontology_term.lower()) / 100.0
                if 0.8 <= similarity < 1.0:  # High similarity ma non exact match
                    synonyms.append(ontology_term)
        
        return list(set(synonyms))  # Remove duplicates
    
    async def _expand_with_semantic_similarity(self, query: str) -> List[ExpansionTerm]:
        """
        Espansione semantica utilizzando embeddings e similarity search
        """
        
        # Generate embedding for query
        query_embedding = self.semantic_similarity.encode([query])
        
        # Pre-computed embeddings per common business terms
        business_term_embeddings = self._get_precomputed_business_embeddings()
        
        semantic_expansions = []
        
        for term, term_embedding in business_term_embeddings.items():
            similarity = cosine_similarity(query_embedding, [term_embedding])[0][0]
            
            # Threshold per relevance semantica
            if similarity > 0.7:
                semantic_expansions.append(ExpansionTerm(
                    original=query,
                    expanded=term,
                    type='semantic_similarity',
                    relevance=similarity,
                    source='sentence_transformer'
                ))
        
        # Sort by semantic similarity
        return sorted(semantic_expansions, key=lambda x: x.relevance, reverse=True)[:10]
```

---

## Algoritmi di Retrieval e Ranking

### 1. Hybrid Retrieval Engine (`src/application/services/hybrid_retrieval.py`)

Sistema di retrieval che combina multiple strategie per massimizzare recall e precision:

```python
class AdvancedHybridRetrieval:
    """
    Sistema di retrieval ibrido enterprise con multiple strategie parallele
    """
    
    def __init__(self):
        # BM25 per keyword matching
        self.bm25_retriever = BM25Retriever()
        
        # Dense retrieval per semantic matching  
        self.dense_retriever = DenseRetriever()
        
        # Cross-encoder per reranking
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-2-v2')
        
        # Filtri specializzati
        self.temporal_filter = TemporalContextFilter()
        self.financial_filter = FinancialRelevanceFilter()
        
        # Configurazione pesi
        self.retrieval_weights = {
            'bm25': 0.3,
            'dense': 0.4, 
            'cross_encoder': 0.3
        }
    
    async def retrieve_relevant_docs(self, 
                                   processed_query: ProcessedQuery, 
                                   query_intent: QueryIntent,
                                   top_k: int = 10) -> RetrievalResult:
        """
        Retrieval multi-stage con fusion intelligente:
        
        STAGE 1: Parallel Retrieval
        - BM25 keyword search
        - Dense semantic search  
        - Filtered search (temporal, financial)
        
        STAGE 2: Result Fusion
        - Reciprocal Rank Fusion (RRF)
        - Score normalization
        - Duplicate removal
        
        STAGE 3: Reranking
        - CrossEncoder reranking
        - Intent-aware scoring
        - Quality filtering
        """
        
        start_time = time.time()
        
        # STAGE 1: Parallel Retrieval Strategy
        retrieval_tasks = [
            self._bm25_retrieval(processed_query, top_k * 2),
            self._dense_retrieval(processed_query, top_k * 2),
            self._filtered_retrieval(processed_query, query_intent, top_k)
        ]
        
        # Execute parallel retrieval
        bm25_results, dense_results, filtered_results = await asyncio.gather(
            *retrieval_tasks, return_exceptions=True
        )
        
        # Handle potential exceptions
        bm25_results = bm25_results if not isinstance(bm25_results, Exception) else []
        dense_results = dense_results if not isinstance(dense_results, Exception) else []
        filtered_results = filtered_results if not isinstance(filtered_results, Exception) else []
        
        # STAGE 2: Result Fusion
        fused_results = await self._fuse_retrieval_results(
            bm25_results, dense_results, filtered_results, processed_query
        )
        
        # STAGE 3: Cross-Encoder Reranking
        reranked_results = await self._crossencoder_rerank(
            processed_query.text, fused_results[:top_k * 3], top_k
        )
        
        # STAGE 4: Intent-Aware Post-Processing
        final_results = await self._intent_aware_filtering(
            reranked_results, query_intent
        )
        
        return RetrievalResult(
            query=processed_query.text,
            documents=final_results[:top_k],
            total_candidates=len(fused_results),
            retrieval_time=time.time() - start_time,
            retrieval_stats=self._calculate_retrieval_stats(
                bm25_results, dense_results, filtered_results, final_results
            )
        )
    
    async def _fuse_retrieval_results(self, 
                                    bm25_results: List, 
                                    dense_results: List, 
                                    filtered_results: List,
                                    query: ProcessedQuery) -> List[DocumentResult]:
        """
        Fusione intelligente risultati con Reciprocal Rank Fusion e score normalization
        """
        
        # Collect all unique documents
        all_documents = {}
        
        # Process BM25 results
        for rank, doc in enumerate(bm25_results):
            doc_id = doc.id
            if doc_id not in all_documents:
                all_documents[doc_id] = DocumentResult(
                    id=doc_id,
                    content=doc.content,
                    metadata=doc.metadata,
                    scores={}
                )
            
            # RRF score for BM25
            all_documents[doc_id].scores['bm25_rrf'] = 1.0 / (60 + rank + 1)
            all_documents[doc_id].scores['bm25_raw'] = doc.score
        
        # Process Dense results
        for rank, doc in enumerate(dense_results):
            doc_id = doc.id
            if doc_id not in all_documents:
                all_documents[doc_id] = DocumentResult(
                    id=doc_id,
                    content=doc.content,
                    metadata=doc.metadata,
                    scores={}
                )
            
            # RRF score for dense retrieval
            all_documents[doc_id].scores['dense_rrf'] = 1.0 / (60 + rank + 1)
            all_documents[doc_id].scores['dense_raw'] = doc.score
        
        # Process Filtered results (bonus scoring)
        filtered_doc_ids = {doc.id for doc in filtered_results}
        for doc_id in filtered_doc_ids:
            if doc_id in all_documents:
                all_documents[doc_id].scores['filtered_bonus'] = 0.1
        
        # Calculate fused scores
        for doc in all_documents.values():
            bm25_rrf = doc.scores.get('bm25_rrf', 0)
            dense_rrf = doc.scores.get('dense_rrf', 0)
            filtered_bonus = doc.scores.get('filtered_bonus', 0)
            
            # Weighted fusion score
            doc.fused_score = (
                self.retrieval_weights['bm25'] * bm25_rrf +
                self.retrieval_weights['dense'] * dense_rrf +
                filtered_bonus
            )
        
        # Sort by fused score
        return sorted(all_documents.values(), key=lambda x: x.fused_score, reverse=True)
    
    async def _crossencoder_rerank(self, 
                                 query: str, 
                                 candidates: List[DocumentResult], 
                                 top_k: int) -> List[DocumentResult]:
        """
        Reranking con CrossEncoder per rilevanza query-document
        """
        
        if not candidates:
            return []
        
        # Prepare query-document pairs for cross-encoder
        query_doc_pairs = [
            [query, doc.content[:512]]  # Limit context per performance
            for doc in candidates
        ]
        
        # Cross-encoder scoring
        cross_scores = self.cross_encoder.predict(query_doc_pairs)
        
        # Update document scores
        for doc, cross_score in zip(candidates, cross_scores):
            doc.scores['cross_encoder'] = cross_score
            
            # Final score combining fusion and cross-encoder
            doc.final_score = (
                0.7 * doc.fused_score +
                0.3 * cross_score
            )
        
        # Sort by final score
        return sorted(candidates, key=lambda x: x.final_score, reverse=True)[:top_k]
```

### 2. Intent-Aware Filtering

Sistema di filtering basato sull'intent della query per risultati più pertinenti:

```python
class IntentAwareFilter:
    """
    Filtro intelligente basato su intent recognition per massimizzare relevance
    """
    
    async def filter_by_intent(self, documents: List[DocumentResult], query_intent: QueryIntent) -> List[DocumentResult]:
        """
        Filtraggio documenti basato su intent recognition
        """
        
        filtered_docs = []
        
        for doc in documents:
            # Intent-specific relevance scoring
            intent_relevance = self._calculate_intent_relevance(doc, query_intent)
            
            # Update document score with intent factor
            doc.scores['intent_relevance'] = intent_relevance
            doc.final_score = doc.final_score * (1 + intent_relevance * 0.2)
            
            # Apply intent-specific filters
            if self._passes_intent_filters(doc, query_intent):
                filtered_docs.append(doc)
        
        return sorted(filtered_docs, key=lambda x: x.final_score, reverse=True)
    
    def _calculate_intent_relevance(self, doc: DocumentResult, intent: QueryIntent) -> float:
        """
        Calcola rilevanza documento rispetto all'intent della query
        """
        
        relevance_score = 0.0
        
        # Financial intent matching
        if intent.financial_domain:
            financial_keywords = self._extract_financial_keywords(doc.content)
            domain_match = self._match_financial_domain(financial_keywords, intent.financial_domain)
            relevance_score += domain_match * 0.4
        
        # Temporal intent matching
        if intent.primary == 'TEMPORAL' or 'temporal_context' in intent.sub_intents:
            temporal_markers = self._extract_temporal_markers(doc.content)
            temporal_relevance = self._evaluate_temporal_relevance(temporal_markers, intent)
            relevance_score += temporal_relevance * 0.3
        
        # Action intent matching
        if intent.primary in ['ANALYTICAL', 'COMPARATIVE']:
            analytical_content = self._identify_analytical_content(doc.content)
            analytical_relevance = self._evaluate_analytical_relevance(analytical_content, intent)
            relevance_score += analytical_relevance * 0.3
        
        return min(relevance_score, 1.0)  # Cap at 1.0
```

---

## Generazione Risposte Contextual

### 1. Contextual Response Generator (`services/response_generator.py`)

Generatore di risposte che utilizza contesto recuperato per creare risposte accurate:

```python
class ContextualResponseGenerator:
    """
    Generatore risposte context-aware con LLM enterprise e validation
    """
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.prompt_template_manager = PromptTemplateManager()
        self.response_validator = ResponseValidator()
        self.citation_generator = CitationGenerator()
        
    async def generate_contextual_answer(self, 
                                       query: ProcessedQuery,
                                       context: ResponseContext,
                                       intent: QueryIntent) -> GeneratedAnswer:
        """
        Generazione risposta contextual multi-step:
        1. Template selection basato su intent
        2. Context organization e chunking  
        3. LLM answer generation
        4. Response validation e quality check
        5. Citation generation e source attribution
        6. Factual accuracy verification
        """
        
        # STEP 1: Select appropriate prompt template
        prompt_template = self.prompt_template_manager.select_template(intent, query)
        
        # STEP 2: Organize context for optimal LLM consumption
        organized_context = await self._organize_context_for_llm(
            context, intent, query
        )
        
        # STEP 3: Generate structured prompt
        structured_prompt = await self._build_structured_prompt(
            query, organized_context, prompt_template, intent
        )
        
        # STEP 4: LLM Generation with parameters tuned for intent
        generation_params = self._get_intent_specific_params(intent)
        
        raw_answer = await self.llm_service.generate_completion(
            prompt=structured_prompt,
            **generation_params
        )
        
        # STEP 5: Response validation
        validation_result = await self.response_validator.validate_response(
            query=query.text,
            answer=raw_answer,
            context=organized_context,
            intent=intent
        )
        
        # STEP 6: Citation generation
        citations = await self.citation_generator.generate_citations(
            answer=raw_answer,
            source_documents=context.documents,
            validation_result=validation_result
        )
        
        # STEP 7: Final answer assembly
        final_answer = await self._assemble_final_answer(
            raw_answer, citations, validation_result, query, intent
        )
        
        return GeneratedAnswer(
            text=final_answer.text,
            confidence=validation_result.confidence_score,
            citations=citations,
            validation_metadata=validation_result.metadata,
            generation_metadata={
                'template_used': prompt_template.name,
                'context_chunks': len(organized_context.chunks),
                'generation_params': generation_params,
                'processing_time': time.time() - start_time
            }
        )
    
    async def _organize_context_for_llm(self, 
                                      context: ResponseContext, 
                                      intent: QueryIntent,
                                      query: ProcessedQuery) -> OrganizedContext:
        """
        Organizzazione intelligente contesto per massimizzare LLM effectiveness
        """
        
        # Priority ranking dei documenti
        prioritized_docs = self._prioritize_documents_by_intent(
            context.documents, intent
        )
        
        # Context chunking intelligente
        context_chunks = []
        current_length = 0
        max_context_length = 4000  # Tokens disponibili per context
        
        for doc in prioritized_docs:
            # Estrai chunk più rilevanti dal documento
            relevant_chunks = self._extract_relevant_chunks(doc, query, intent)
            
            for chunk in relevant_chunks:
                if current_length + len(chunk.text) > max_context_length:
                    break
                
                context_chunks.append(ContextChunk(
                    text=chunk.text,
                    source=doc.metadata,
                    relevance_score=chunk.relevance,
                    chunk_type=chunk.type
                ))
                current_length += len(chunk.text)
        
        # Organizzazione per tipo di contenuto
        organized_chunks = self._organize_chunks_by_type(context_chunks, intent)
        
        return OrganizedContext(
            chunks=organized_chunks,
            total_length=current_length,
            primary_sources=self._identify_primary_sources(context_chunks),
            context_summary=self._generate_context_summary(organized_chunks)
        )
    
    def _get_intent_specific_params(self, intent: QueryIntent) -> Dict:
        """
        Parametri LLM specifici per tipo di intent
        """
        
        base_params = {
            'max_tokens': 800,
            'temperature': 0.3,
            'top_p': 0.9,
            'frequency_penalty': 0.1
        }
        
        # Intent-specific adjustments
        if intent.primary == 'ANALYTICAL':
            base_params.update({
                'temperature': 0.2,  # Lower for factual accuracy
                'max_tokens': 1200   # More space for analysis
            })
            
        elif intent.primary == 'COMPARATIVE':
            base_params.update({
                'temperature': 0.25,
                'max_tokens': 1000,
                'top_p': 0.85       # Slightly more focused
            })
            
        elif intent.primary == 'SUMMARIZATION':
            base_params.update({
                'temperature': 0.4,  # Slightly higher for creativity
                'max_tokens': 600    # Concise summaries
            })
            
        elif intent.primary == 'EXPLORATORY':
            base_params.update({
                'temperature': 0.5,  # Higher for creative exploration
                'max_tokens': 1000,
                'top_p': 0.95
            })
        
        return base_params
    
    async def _build_structured_prompt(self, 
                                     query: ProcessedQuery,
                                     context: OrganizedContext,
                                     template: PromptTemplate,
                                     intent: QueryIntent) -> str:
        """
        Costruzione prompt strutturato per ottimizzare LLM response
        """
        
        # Base template con context injection
        prompt_parts = []
        
        # System role definition
        prompt_parts.append(template.system_role)
        
        # Context information
        prompt_parts.append("=== INFORMAZIONI DI CONTESTO ===")
        
        # Organize context by priority and type
        for chunk in context.chunks:
            chunk_header = f"[Fonte: {chunk.source.get('filename', 'N/A')} - Rilevanza: {chunk.relevance_score:.2f}]"
            prompt_parts.append(f"{chunk_header}\n{chunk.text}\n")
        
        # Query and instructions
        prompt_parts.append("=== DOMANDA UTENTE ===")
        prompt_parts.append(query.text)
        
        # Intent-specific instructions
        intent_instructions = template.get_intent_instructions(intent)
        if intent_instructions:
            prompt_parts.append("=== ISTRUZIONI SPECIFICHE ===")
            prompt_parts.append(intent_instructions)
        
        # Response format guidelines
        prompt_parts.append(template.response_format)
        
        return "\n\n".join(prompt_parts)
```

### 2. Response Validation System

Sistema di validazione per assicurare qualità e accuratezza delle risposte:

```python
class ResponseValidator:
    """
    Validatore multi-layer per qualità e accuratezza risposte
    """
    
    def __init__(self):
        self.factual_checker = FactualAccuracyChecker()
        self.relevance_scorer = RelevanceScorer() 
        self.completeness_assessor = CompletenessAssessor()
        self.consistency_checker = ConsistencyChecker()
    
    async def validate_response(self, 
                              query: str, 
                              answer: str, 
                              context: OrganizedContext,
                              intent: QueryIntent) -> ValidationResult:
        """
        Validazione completa risposta con multiple dimensioni di qualità:
        
        1. Factual Accuracy: Verifica accuratezza rispetto alle fonti
        2. Relevance: Allineamento con query e intent
        3. Completeness: Completezza risposta rispetto alla domanda
        4. Consistency: Coerenza interna e con contesto
        5. Citation Quality: Qualità e accuratezza citazioni
        """
        
        validation_results = {}
        
        # 1. Factual Accuracy Check
        factual_score = await self.factual_checker.check_factual_accuracy(
            answer, context.chunks
        )
        validation_results['factual_accuracy'] = factual_score
        
        # 2. Query Relevance Assessment
        relevance_score = await self.relevance_scorer.score_relevance(
            query, answer, intent
        )
        validation_results['query_relevance'] = relevance_score
        
        # 3. Completeness Assessment
        completeness_score = await self.completeness_assessor.assess_completeness(
            query, answer, intent, context
        )
        validation_results['completeness'] = completeness_score
        
        # 4. Internal Consistency Check
        consistency_score = await self.consistency_checker.check_consistency(
            answer, context
        )
        validation_results['consistency'] = consistency_score
        
        # 5. Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(validation_results)
        
        # 6. Generate quality recommendations
        quality_recommendations = self._generate_quality_recommendations(
            validation_results, overall_confidence
        )
        
        return ValidationResult(
            confidence_score=overall_confidence,
            dimension_scores=validation_results,
            recommendations=quality_recommendations,
            validation_metadata={
                'validation_timestamp': datetime.utcnow().isoformat(),
                'validation_version': '2.0',
                'context_chunks_validated': len(context.chunks)
            }
        )
    
    async def _check_factual_accuracy(self, answer: str, source_chunks: List[ContextChunk]) -> float:
        """
        Verifica accuratezza fattuale utilizzando entailment e fact checking
        """
        
        # Estrai claims fattuale dalla risposta
        claims = self._extract_factual_claims(answer)
        
        accuracy_scores = []
        
        for claim in claims:
            # Find supporting evidence in context
            supporting_evidence = self._find_supporting_evidence(claim, source_chunks)
            
            if supporting_evidence:
                # Entailment check: does context support this claim?
                entailment_score = await self._calculate_entailment_score(
                    claim, supporting_evidence
                )
                accuracy_scores.append(entailment_score)
            else:
                # No supporting evidence found
                accuracy_scores.append(0.0)
        
        # Overall accuracy is average of individual claim accuracies
        return sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.0
    
    def _extract_factual_claims(self, answer: str) -> List[str]:
        """
        Estrazione claims fattuali dalla risposta per validation
        """
        
        # Use spaCy per sentence segmentation
        doc = nlp(answer)
        sentences = [sent.text for sent in doc.sents]
        
        factual_claims = []
        
        for sentence in sentences:
            # Check se la frase contiene claims fattuali
            if self._contains_factual_content(sentence):
                factual_claims.append(sentence.strip())
        
        return factual_claims
    
    def _contains_factual_content(self, sentence: str) -> bool:
        """
        Determina se una frase contiene contenuto fattuale verificabile
        """
        
        # Patterns che indicano contenuto fattuale
        factual_patterns = [
            r'\d+[.,]?\d*\s*%',          # Percentages
            r'\d+[.,]?\d*\s*(milioni?|miliardi?|migliaia?)',  # Monetary amounts
            r'nel\s+\d{4}',              # Year references
            r'è\s+pari\s+a',             # Equality statements
            r'(aumentato|diminuito|cresciuto)',  # Change indicators
            r'(secondo|come\s+riportato|in\s+base\s+a)'  # Attribution phrases
        ]
        
        return any(re.search(pattern, sentence.lower()) for pattern in factual_patterns)
```

---

## Ottimizzazioni Performance

### 1. Query Result Caching

Sistema di cache intelligente per query frequenti:

```python
class IntelligentQueryCache:
    """
    Cache system ottimizzato per query RAG con invalidation intelligente
    """
    
    def __init__(self):
        # Multi-tier cache architecture
        self.memory_cache = TTLCache(maxsize=500, ttl=1800)  # 30 min
        self.redis_cache = redis.Redis(host='localhost', port=6379, db=1)
        
        # Semantic similarity threshold per cache hits
        self.similarity_threshold = 0.85
        
        # Query embedding model per semantic caching
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Pre-computed embeddings per common queries
        self.query_embeddings_cache = {}
    
    async def get_cached_response(self, query: str, context_hash: str) -> Optional[EnterpriseResponse]:
        """
        Recupero risposta da cache con semantic similarity matching
        """
        
        # Try exact match first
        exact_cache_key = self._generate_cache_key(query, context_hash)
        
        # L1: Memory cache
        if exact_cache_key in self.memory_cache:
            logger.debug(f"Exact cache hit (memory): {query[:50]}...")
            return self.memory_cache[exact_cache_key]
        
        # L2: Redis cache
        try:
            redis_result = self.redis_cache.get(exact_cache_key)
            if redis_result:
                logger.debug(f"Exact cache hit (redis): {query[:50]}...")
                cached_response = pickle.loads(redis_result)
                # Promote to memory cache
                self.memory_cache[exact_cache_key] = cached_response
                return cached_response
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
        
        # L3: Semantic similarity matching
        semantic_match = await self._find_semantic_match(query, context_hash)
        if semantic_match:
            logger.debug(f"Semantic cache hit: {query[:50]}...")
            return semantic_match
        
        return None
    
    async def _find_semantic_match(self, query: str, context_hash: str) -> Optional[EnterpriseResponse]:
        """
        Ricerca match semantico per query simili
        """
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])
        
        # Search through cached query embeddings
        for cached_key, cached_embedding in self.query_embeddings_cache.items():
            similarity = cosine_similarity([query_embedding[0]], [cached_embedding])[0][0]
            
            if similarity >= self.similarity_threshold:
                # Check se il context hash è compatibile
                if self._is_context_compatible(cached_key, context_hash):
                    # Retrieve cached response
                    try:
                        cached_response = self.redis_cache.get(cached_key)
                        if cached_response:
                            response = pickle.loads(cached_response)
                            # Update response metadata for semantic match
                            response.semantic_cache_hit = True
                            response.semantic_similarity = similarity
                            return response
                    except Exception as e:
                        logger.warning(f"Semantic cache retrieval error: {e}")
        
        return None
    
    async def cache_response(self, query: str, context_hash: str, response: EnterpriseResponse):
        """
        Cache response con embedding storage per semantic matching
        """
        
        cache_key = self._generate_cache_key(query, context_hash)
        
        # Store in memory cache
        self.memory_cache[cache_key] = response
        
        # Store in Redis with TTL
        try:
            serialized_response = pickle.dumps(response)
            self.redis_cache.setex(cache_key, 3600, serialized_response)  # 1 hour TTL
        except Exception as e:
            logger.warning(f"Redis cache storage error: {e}")
        
        # Store query embedding per semantic matching
        query_embedding = self.embedding_model.encode([query])
        self.query_embeddings_cache[cache_key] = query_embedding[0]
        
        # Limit embedding cache size
        if len(self.query_embeddings_cache) > 1000:
            # Remove oldest entries
            oldest_keys = list(self.query_embeddings_cache.keys())[:100]
            for key in oldest_keys:
                del self.query_embeddings_cache[key]
```

### 2. Batch Query Processing

Sistema per processamento efficiente di query multiple:

```python
class BatchQueryProcessor:
    """
    Processore batch per query multiple con ottimizzazioni parallel processing
    """
    
    def __init__(self, rag_engine: EnhancedRAGEngine):
        self.rag_engine = rag_engine
        self.max_concurrent_queries = 5
        self.batch_semaphore = asyncio.Semaphore(self.max_concurrent_queries)
    
    async def process_query_batch(self, queries: List[str], context: QueryContext = None) -> BatchQueryResult:
        """
        Processamento batch ottimizzato con:
        1. Query similarity clustering
        2. Shared context optimization
        3. Parallel processing con rate limiting
        4. Result aggregation e statistics
        """
        
        start_time = time.time()
        
        # STEP 1: Query preprocessing e clustering
        processed_queries = await self._preprocess_query_batch(queries)
        
        # STEP 2: Similarity clustering per shared retrieval
        query_clusters = await self._cluster_similar_queries(processed_queries)
        
        # STEP 3: Parallel processing con semaphore
        cluster_tasks = []
        for cluster in query_clusters:
            task = self._process_query_cluster(cluster, context)
            cluster_tasks.append(task)
        
        # Execute with controlled concurrency
        cluster_results = await asyncio.gather(*cluster_tasks, return_exceptions=True)
        
        # STEP 4: Result consolidation
        all_results = []
        for cluster_result in cluster_results:
            if isinstance(cluster_result, Exception):
                logger.error(f"Cluster processing error: {cluster_result}")
                continue
            all_results.extend(cluster_result)
        
        # STEP 5: Batch statistics
        batch_stats = self._calculate_batch_statistics(all_results, start_time)
        
        return BatchQueryResult(
            results=all_results,
            total_queries=len(queries),
            processing_time=time.time() - start_time,
            statistics=batch_stats
        )
    
    async def _cluster_similar_queries(self, queries: List[ProcessedQuery]) -> List[QueryCluster]:
        """
        Clustering query simili per ottimizzare retrieval condiviso
        """
        
        # Generate embeddings per tutte le query
        query_texts = [q.text for q in queries]
        embeddings = self.rag_engine.embedding_model.encode(query_texts)
        
        # Hierarchical clustering basato su similarity
        similarity_matrix = cosine_similarity(embeddings)
        
        clusters = []
        processed = set()
        similarity_threshold = 0.75
        
        for i, query in enumerate(queries):
            if i in processed:
                continue
            
            # Start new cluster
            cluster = QueryCluster(primary_query=query)
            cluster.add_query(query, 1.0)  # Primary query has similarity 1.0
            processed.add(i)
            
            # Find similar queries
            for j in range(i + 1, len(queries)):
                if j in processed:
                    continue
                
                similarity = similarity_matrix[i][j]
                if similarity >= similarity_threshold:
                    cluster.add_query(queries[j], similarity)
                    processed.add(j)
            
            clusters.append(cluster)
        
        return clusters
    
    async def _process_query_cluster(self, cluster: QueryCluster, context: QueryContext) -> List[EnterpriseResponse]:
        """
        Processamento ottimizzato cluster con shared retrieval
        """
        
        async with self.batch_semaphore:
            # Use primary query per retrieval condiviso
            shared_retrieval = await self.rag_engine.hybrid_retrieval.retrieve_relevant_docs(
                cluster.primary_query, 
                query_intent=None,  # Will be determined per query
                top_k=15  # Larger pool per cluster
            )
            
            # Process each query in cluster
            cluster_results = []
            
            for query_item in cluster.queries:
                try:
                    # Use shared retrieval con query-specific reranking
                    reranked_docs = await self._rerank_for_specific_query(
                        query_item.query, shared_retrieval.documents
                    )
                    
                    # Generate response con reranked context
                    response = await self.rag_engine.response_generator.generate_contextual_answer(
                        query_item.query,
                        ResponseContext(documents=reranked_docs[:10]),
                        query_intent=await self.rag_engine._recognize_query_intent(query_item.query)
                    )
                    
                    cluster_results.append(response)
                    
                except Exception as e:
                    logger.error(f"Error processing query in cluster: {e}")
                    # Create error response
                    error_response = self.rag_engine._create_error_response(
                        uuid.uuid4().hex, query_item.query.text, str(e)
                    )
                    cluster_results.append(error_response)
            
            return cluster_results
```

---

## Conclusioni

Il sistema di Question & Answering rappresenta l'interfaccia principale tra utente e knowledge base enterprise. L'architettura sofisticata garantisce:

**Caratteristiche principali:**
- **Comprehension Multi-Layer**: Intent recognition, entity extraction, context analysis
- **Hybrid Retrieval**: BM25 + Dense + CrossEncoder per massimizzare recall/precision
- **Contextual Generation**: LLM responses calibrate su intent e context specifico
- **Quality Assurance**: Validation multi-dimensionale per accuracy e relevance
- **Performance**: Caching intelligente e batch processing per scalabilità

**Tecnologie Core:**
- **NLP**: spaCy, Transformers per query understanding
- **Retrieval**: BM25, Dense embeddings, CrossEncoder reranking  
- **Generation**: OpenAI GPT con prompt engineering avanzato
- **Validation**: Entailment checking, factual verification
- **Caching**: Multi-tier con semantic similarity matching

Il sistema garantisce risposte accurate, tracciate e validate, supportando use case enterprise complessi con performance ottimali e observability completa.