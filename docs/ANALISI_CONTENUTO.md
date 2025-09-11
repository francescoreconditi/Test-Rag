# Analisi Contenuto - Documentazione Tecnica Dettagliata

## Indice
1. [Panoramica del Sistema di Analisi](#panoramica-del-sistema-di-analisi)
2. [Architettura Enterprise per l'Analisi](#architettura-enterprise-per-lanalisi)
3. [Pipeline di Analisi Completa](#pipeline-di-analisi-completa)
4. [Analisi del Codice Sorgente](#analisi-del-codice-sorgente)
5. [Componenti Specializzati](#componenti-specializzati)
6. [Intelligenza Artificiale nell'Analisi](#intelligenza-artificiale-nellanalisi)
7. [Performance e Ottimizzazioni](#performance-e-ottimizzazioni)

---

## Panoramica del Sistema di Analisi

Il sistema di analisi contenuto rappresenta il cuore dell'intelligence del sistema RAG Enterprise. È progettato per estrarre, normalizzare e arricchire informazioni da documenti eterogenei, trasformandoli in knowledge strutturata interrogabile attraverso linguaggio naturale.

### Architettura Multi-Layer

```
[Documento Originale]
         ↓
[Document Classification & Routing]
         ↓
[Content Extraction & Parsing]
         ↓
[Data Normalization & Cleaning]
         ↓
[Ontology Mapping & Semantic Enrichment]
         ↓
[Financial Validation & Business Rules]
         ↓
[Provenance Tracking & Lineage]
         ↓
[Dimensional Storage & Indexing]
```

---

## Architettura Enterprise per l'Analisi

### Enterprise Orchestrator (`src/application/services/enterprise_orchestrator.py`)

Il componente centrale che coordina l'intera pipeline di analisi enterprise:

```python
class EnterpriseOrchestrator:
    """
    Orchestratore principale per analisi contenuto enterprise
    
    Coordina 6 fasi principali:
    1. Document Classification
    2. Hybrid Retrieval Setup
    3. Data Normalization
    4. Ontology Mapping
    5. Financial Validation
    6. Dimensional Storage
    """
    
    async def analyze_document_enterprise(self, file_path: str, query: str = None) -> EnterpriseResponse:
        """
        Analisi completa documento con pipeline enterprise
        
        Args:
            file_path: Percorso del documento da analizzare
            query: Query opzionale per analisi mirata
            
        Returns:
            EnterpriseResponse: Risultato con metadati completi e provenance
        """
        start_time = time.time()
        analysis_context = AnalysisContext()
        
        try:
            # FASE 1: Document Classification
            doc_type = await self._classify_document(file_path)
            analysis_context.add_step("classification", doc_type)
            
            # FASE 2: Content Extraction
            extracted_content = await self._extract_content_by_type(file_path, doc_type)
            analysis_context.add_step("extraction", len(extracted_content))
            
            # FASE 3: Data Normalization
            normalized_data = await self._normalize_data(extracted_content)
            analysis_context.add_step("normalization", normalized_data.stats)
            
            # FASE 4: Semantic Enrichment
            enriched_content = await self._apply_ontology_mapping(normalized_data)
            analysis_context.add_step("enrichment", enriched_content.mapped_entities)
            
            # FASE 5: Business Validation
            validation_results = await self._validate_business_rules(enriched_content)
            analysis_context.add_step("validation", validation_results)
            
            # FASE 6: Dimensional Storage
            storage_result = await self._store_dimensional_facts(enriched_content)
            analysis_context.add_step("storage", storage_result.fact_count)
            
            # Compilazione response finale
            return self._compile_enterprise_response(
                analysis_context, 
                time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Enterprise analysis failed: {e}")
            return self._create_error_response(e, analysis_context)
```

---

## Pipeline di Analisi Completa

### 1. Document Classification (`src/application/services/document_router.py`)

Il primo step determina la strategia di analisi basata sul tipo di contenuto:

```python
class IntelligentDocumentRouter:
    """
    Router intelligente per classificazione automatica documenti
    """
    
    def __init__(self):
        self.content_analyzers = {
            'structured': StructuredContentAnalyzer(),
            'unstructured': UnstructuredContentAnalyzer(), 
            'hybrid': HybridContentAnalyzer()
        }
    
    async def classify_and_route(self, file_path: str) -> DocumentAnalysisResult:
        """
        Classificazione intelligente basata su:
        1. Estensione file
        2. Content analysis
        3. Structure detection
        4. ML-based classification
        """
        # Analisi preliminare file
        file_info = self._analyze_file_structure(file_path)
        
        # ML Classification per contenuto ambiguo
        if file_info.confidence < 0.8:
            ml_classification = await self._ml_classify_content(file_path)
            file_info = self._merge_classifications(file_info, ml_classification)
        
        # Routing a analyzer specifico
        analyzer = self.content_analyzers[file_info.document_type]
        
        return await analyzer.analyze(file_path, file_info)
    
    def _analyze_file_structure(self, file_path: str) -> FileStructureInfo:
        """
        Analisi struttura file multi-dimensionale:
        - Formato e encoding
        - Presenza tabelle/form strutturate
        - Densità testo vs dati
        - Presence grafica/immagini
        """
        extension = Path(file_path).suffix.lower()
        file_size = os.path.getsize(file_path)
        
        # Quick content sampling per large files
        sample_content = self._get_content_sample(file_path, max_size=1024*10)
        
        # Pattern recognition
        structure_patterns = {
            'table_indicators': len(re.findall(r'\t|,|\|', sample_content)),
            'numeric_density': len(re.findall(r'\d+[.,]\d+', sample_content)) / len(sample_content),
            'text_paragraphs': len(re.findall(r'\n\s*\n', sample_content)),
            'structured_markers': len(re.findall(r':|;|\{|\}|\[|\]', sample_content))
        }
        
        # Classification logic
        confidence = self._calculate_classification_confidence(structure_patterns)
        
        return FileStructureInfo(
            extension=extension,
            file_size=file_size,
            structure_patterns=structure_patterns,
            document_type=self._determine_document_type(structure_patterns),
            confidence=confidence
        )
```

### 2. Content Extraction Specializzato

#### A. Structured Content Analyzer

```python
class StructuredContentAnalyzer:
    """
    Analizzatore specializzato per contenuto strutturato (CSV, Excel)
    """
    
    async def analyze(self, file_path: str, file_info: FileStructureInfo) -> AnalysisResult:
        """
        Analisi profonda dati strutturati con:
        1. Schema detection automatica
        2. Data quality assessment
        3. Relationship discovery
        4. Statistical profiling
        """
        
        # Caricamento dati con schema inference
        data_loader = StructuredDataLoader()
        dataset = await data_loader.load_with_schema_detection(file_path)
        
        # Profiling statistico colonne
        column_profiles = {}
        for column in dataset.columns:
            profile = self._profile_column(dataset[column])
            column_profiles[column] = profile
        
        # Relationship discovery tra colonne
        relationships = self._discover_relationships(dataset, column_profiles)
        
        # Data quality assessment
        quality_metrics = self._assess_data_quality(dataset, column_profiles)
        
        # Business pattern recognition
        business_patterns = self._identify_business_patterns(dataset, column_profiles)
        
        return StructuredAnalysisResult(
            schema=dataset.schema,
            column_profiles=column_profiles,
            relationships=relationships,
            quality_metrics=quality_metrics,
            business_patterns=business_patterns,
            raw_data=dataset
        )
    
    def _profile_column(self, series: pd.Series) -> ColumnProfile:
        """
        Profiling completo singola colonna:
        - Distribuzione valori
        - Pattern temporali
        - Outlier detection
        - Data type suggestions
        """
        profile = ColumnProfile()
        
        # Basic statistics
        profile.basic_stats = {
            'count': len(series),
            'unique': series.nunique(),
            'null_count': series.isnull().sum(),
            'null_percentage': series.isnull().sum() / len(series) * 100
        }
        
        # Type inference con confidence
        profile.inferred_type = self._infer_column_type(series)
        
        # Pattern analysis
        if profile.inferred_type == 'numeric':
            profile.numeric_stats = {
                'mean': series.mean(),
                'median': series.median(),
                'std': series.std(),
                'outliers': self._detect_outliers(series)
            }
        
        elif profile.inferred_type == 'temporal':
            profile.temporal_stats = {
                'date_range': (series.min(), series.max()),
                'frequency': self._detect_temporal_frequency(series),
                'seasonality': self._detect_seasonality(series)
            }
        
        elif profile.inferred_type == 'categorical':
            profile.categorical_stats = {
                'categories': series.value_counts().to_dict(),
                'cardinality': series.nunique(),
                'top_categories': series.value_counts().head(10).to_dict()
            }
        
        return profile
    
    def _discover_relationships(self, dataset: pd.DataFrame, profiles: Dict) -> List[Relationship]:
        """
        Scoperta automatica relazioni tra colonne:
        - Correlazioni statistiche
        - Functional dependencies
        - Hierarchical relationships
        - Foreign key candidates
        """
        relationships = []
        
        # Correlazione numerica
        numeric_columns = [col for col, prof in profiles.items() 
                          if prof.inferred_type == 'numeric']
        
        if len(numeric_columns) > 1:
            correlation_matrix = dataset[numeric_columns].corr()
            
            for i, col1 in enumerate(numeric_columns):
                for j, col2 in enumerate(numeric_columns[i+1:], i+1):
                    correlation = correlation_matrix.loc[col1, col2]
                    
                    if abs(correlation) > 0.7:  # Strong correlation
                        relationships.append(Relationship(
                            type='correlation',
                            source_column=col1,
                            target_column=col2,
                            strength=abs(correlation),
                            metadata={'correlation_value': correlation}
                        ))
        
        # Functional dependencies
        for col1 in dataset.columns:
            for col2 in dataset.columns:
                if col1 != col2:
                    dependency_strength = self._calculate_functional_dependency(
                        dataset[col1], dataset[col2]
                    )
                    
                    if dependency_strength > 0.9:
                        relationships.append(Relationship(
                            type='functional_dependency',
                            source_column=col1,
                            target_column=col2,
                            strength=dependency_strength
                        ))
        
        return relationships
```

#### B. Unstructured Content Analyzer

```python
class UnstructuredContentAnalyzer:
    """
    Analizzatore per contenuto non strutturato (PDF, Word, Text)
    """
    
    def __init__(self):
        self.nlp_processor = spacy.load("it_core_news_sm")  # Modello italiano
        self.financial_ner = FinancialEntityRecognizer()
        self.topic_modeler = TopicModelingEngine()
    
    async def analyze(self, file_path: str, file_info: FileStructureInfo) -> AnalysisResult:
        """
        Analisi NLP completa per testo non strutturato:
        1. Entity Recognition (finanziaria + generale)
        2. Topic Modeling e classificazione tematica
        3. Sentiment Analysis
        4. Key phrase extraction
        5. Document summarization
        6. Language detection e statistics
        """
        
        # Estrazione testo con OCR fallback
        text_content = await self._extract_text_content(file_path)
        
        # Preprocessing e cleaning
        cleaned_text = self._preprocess_text(text_content)
        
        # NLP Analysis Pipeline
        analysis_results = {}
        
        # 1. Named Entity Recognition
        entities = await self._extract_entities(cleaned_text)
        analysis_results['entities'] = entities
        
        # 2. Topic Modeling
        topics = await self._identify_topics(cleaned_text)
        analysis_results['topics'] = topics
        
        # 3. Financial Information Extraction
        financial_data = await self._extract_financial_information(cleaned_text)
        analysis_results['financial_data'] = financial_data
        
        # 4. Document Structure Analysis
        structure = await self._analyze_document_structure(text_content)
        analysis_results['structure'] = structure
        
        # 5. Key Information Extraction
        key_info = await self._extract_key_information(cleaned_text, entities)
        analysis_results['key_information'] = key_info
        
        return UnstructuredAnalysisResult(
            original_text=text_content,
            cleaned_text=cleaned_text,
            analysis_results=analysis_results,
            language_stats=self._calculate_language_stats(cleaned_text)
        )
    
    async def _extract_entities(self, text: str) -> Dict[str, List[Entity]]:
        """
        Estrazione entità multi-layer:
        - Standard NER (Persone, Luoghi, Organizzazioni)
        - Financial NER (Metrie finanziarie, Importi, Date)
        - Custom business entity recognition
        """
        entities = {
            'persons': [],
            'organizations': [],
            'locations': [],
            'financial_metrics': [],
            'dates': [],
            'monetary_amounts': [],
            'percentages': []
        }
        
        # Standard NER con spaCy
        doc = self.nlp_processor(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                entities['persons'].append(Entity(
                    text=ent.text,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=ent._.confidence if hasattr(ent._, 'confidence') else 0.8
                ))
            # Similar logic for other standard entities...
        
        # Financial NER specializzato
        financial_entities = await self.financial_ner.extract_financial_entities(text)
        entities.update(financial_entities)
        
        return entities
    
    async def _extract_financial_information(self, text: str) -> FinancialAnalysis:
        """
        Estrazione informazioni finanziarie specializzate:
        - Bilanci e statement finanziari
        - KPI e metriche performance
        - Trend e variazioni temporali
        - Forecast e proiezioni
        """
        financial_analyzer = FinancialTextAnalyzer()
        
        # Identificazione sezioni finanziarie
        financial_sections = financial_analyzer.identify_financial_sections(text)
        
        # Estrazione dati strutturati da testo
        extracted_data = {}
        
        for section in financial_sections:
            section_data = financial_analyzer.extract_structured_data(section)
            extracted_data[section.type] = section_data
        
        # Validazione coerenza dati estratti
        validation_results = financial_analyzer.validate_financial_coherence(extracted_data)
        
        return FinancialAnalysis(
            sections=financial_sections,
            extracted_data=extracted_data,
            validation_results=validation_results,
            confidence_score=financial_analyzer.calculate_confidence(extracted_data)
        )
```

### 3. Data Normalization (`src/application/services/data_normalizer.py`)

Componente cruciale per standardizzare dati eterogenei:

```python
class EnterpriseDataNormalizer:
    """
    Normalizzatore enterprise per dati multi-formato e multi-locale
    """
    
    def __init__(self):
        self.locale_handlers = {
            'it_IT': ItalianLocaleHandler(),
            'en_US': EnglishLocaleHandler(),
            'en_GB': BritishLocaleHandler()
        }
        self.currency_converter = CurrencyConverter()
        self.date_parser = FlexibleDateParser()
        self.number_parser = MultiLocaleNumberParser()
    
    async def normalize_data(self, raw_data: Any, context: NormalizationContext) -> NormalizedData:
        """
        Normalizzazione completa dati con:
        1. Locale detection e standardizzazione
        2. Currency conversion e standardizzazione
        3. Date/time normalization
        4. Unit conversion (migliaia, milioni, miliardi)
        5. Text normalization (encoding, case, spacing)
        """
        
        normalized_result = NormalizedData()
        
        # Auto-detection locale predominante
        detected_locale = self._detect_primary_locale(raw_data)
        locale_handler = self.locale_handlers.get(detected_locale, self.locale_handlers['en_US'])
        
        # Normalizzazione per tipo di dato
        for field_name, field_value in raw_data.items():
            if field_value is None or field_value == '':
                normalized_result.add_field(field_name, None, 'null_value')
                continue
            
            # Numeric normalization
            if self._is_numeric_field(field_value):
                normalized_value = await self._normalize_numeric(
                    field_value, locale_handler, context
                )
                normalized_result.add_field(field_name, normalized_value, 'numeric')
            
            # Date normalization
            elif self._is_date_field(field_value):
                normalized_value = await self._normalize_date(
                    field_value, locale_handler, context
                )
                normalized_result.add_field(field_name, normalized_value, 'date')
            
            # Currency normalization  
            elif self._is_currency_field(field_value):
                normalized_value = await self._normalize_currency(
                    field_value, locale_handler, context
                )
                normalized_result.add_field(field_name, normalized_value, 'currency')
            
            # Text normalization
            else:
                normalized_value = await self._normalize_text(
                    field_value, locale_handler, context
                )
                normalized_result.add_field(field_name, normalized_value, 'text')
        
        # Post-processing validation
        validation_results = await self._validate_normalization(normalized_result)
        normalized_result.set_validation_results(validation_results)
        
        return normalized_result
    
    async def _normalize_numeric(self, value: str, locale_handler, context) -> NumericValue:
        """
        Normalizzazione numerica avanzata:
        - Italian format: 1.234.567,89 → 1234567.89
        - Scale detection: 123K → 123000, 45M → 45000000
        - Percentage handling: 15% → 0.15
        - Range parsing: 100-200 → Range(100, 200)
        """
        
        # Scale detection e conversion
        scale_multiplier = 1
        if re.search(r'[KkMmBbGg](?:\b|$)', str(value)):
            scale_matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*([KkMmBbGg])', str(value))
            if scale_matches:
                number_part, scale_part = scale_matches[0]
                scale_multiplier = self._get_scale_multiplier(scale_part.upper())
                value = number_part
        
        # Locale-specific parsing
        parsed_number = locale_handler.parse_number(value)
        
        # Apply scale
        final_value = parsed_number * scale_multiplier
        
        return NumericValue(
            original=value,
            normalized=final_value,
            scale=scale_multiplier,
            locale=locale_handler.locale_code,
            confidence=self._calculate_numeric_confidence(value)
        )
    
    def _get_scale_multiplier(self, scale_indicator: str) -> int:
        """Mapping scala numeriche"""
        scale_map = {
            'K': 1_000,           # Thousands
            'M': 1_000_000,       # Millions
            'B': 1_000_000_000,   # Billions
            'G': 1_000_000_000    # Billions (alternative)
        }
        return scale_map.get(scale_indicator, 1)
```

### 4. Ontology Mapping (`src/application/services/ontology_mapper.py`)

Sistema di mapping semantico per standardizzazione business terminology:

```python
class FinancialOntologyMapper:
    """
    Mapper ontologia finanziaria con supporto fuzzy matching e ML
    """
    
    def __init__(self):
        self.ontology_data = self._load_ontology_definitions()
        self.fuzzy_matcher = RapidFuzz()
        self.semantic_similarity = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Pre-compute embeddings per canonical metrics
        self.canonical_embeddings = self._precompute_canonical_embeddings()
    
    def _load_ontology_definitions(self) -> Dict:
        """
        Caricamento definizioni ontologia da YAML configurazione
        
        Struttura ontologia:
        canonical_metrics:
          ricavi_totali:
            synonyms: [fatturato, revenues, total_revenues, ricavi]
            category: income_statement  
            data_type: currency
            validation_rules: [positive_value]
            
          margine_operativo_lordo:
            synonyms: [ebitda, mol, gross_operating_margin]
            calculation: ricavi_totali - costi_operativi
            category: profitability
        """
        ontology_path = Path("config/financial_ontology.yaml")
        
        with open(ontology_path, 'r', encoding='utf-8') as f:
            ontology_data = yaml.safe_load(f)
        
        # Costruzione indici per ricerca rapida
        self.synonym_index = self._build_synonym_index(ontology_data)
        self.category_index = self._build_category_index(ontology_data)
        
        return ontology_data
    
    async def map_to_canonical_metrics(self, raw_metrics: List[str]) -> MappingResult:
        """
        Mapping batch metriche raw a canonical metrics con confidence scoring
        """
        mapping_results = []
        
        for raw_metric in raw_metrics:
            # Multi-layer matching approach
            matches = []
            
            # 1. Exact synonym match
            exact_match = self._find_exact_synonym_match(raw_metric)
            if exact_match:
                matches.append(MatchResult(
                    canonical_metric=exact_match,
                    confidence=1.0,
                    match_type='exact_synonym'
                ))
            
            # 2. Fuzzy string matching
            fuzzy_matches = self._fuzzy_match_synonyms(raw_metric, threshold=0.8)
            matches.extend(fuzzy_matches)
            
            # 3. Semantic similarity matching
            semantic_matches = await self._semantic_similarity_match(raw_metric, threshold=0.75)
            matches.extend(semantic_matches)
            
            # 4. Pattern-based matching
            pattern_matches = self._pattern_based_match(raw_metric)
            matches.extend(pattern_matches)
            
            # Consolidamento e ranking matches
            best_match = self._rank_and_select_best_match(matches)
            
            mapping_results.append(MetricMapping(
                raw_metric=raw_metric,
                canonical_metric=best_match.canonical_metric if best_match else None,
                confidence=best_match.confidence if best_match else 0.0,
                alternatives=matches[:5],  # Top 5 alternative matches
                mapping_metadata=self._generate_mapping_metadata(raw_metric, matches)
            ))
        
        return MappingResult(
            mappings=mapping_results,
            overall_confidence=self._calculate_overall_confidence(mapping_results),
            unmapped_metrics=[m for m in mapping_results if m.canonical_metric is None]
        )
    
    def _fuzzy_match_synonyms(self, raw_metric: str, threshold: float = 0.8) -> List[MatchResult]:
        """
        Fuzzy matching contro tutti i sinonimi nell'ontologia
        """
        matches = []
        
        for canonical_metric, definition in self.ontology_data['canonical_metrics'].items():
            for synonym in definition.get('synonyms', []):
                # Fuzzy matching con RapidFuzz
                similarity = fuzz.ratio(raw_metric.lower(), synonym.lower()) / 100.0
                
                if similarity >= threshold:
                    matches.append(MatchResult(
                        canonical_metric=canonical_metric,
                        confidence=similarity,
                        match_type='fuzzy_synonym',
                        matched_synonym=synonym,
                        metadata={'fuzzy_score': similarity}
                    ))
        
        return sorted(matches, key=lambda x: x.confidence, reverse=True)
    
    async def _semantic_similarity_match(self, raw_metric: str, threshold: float = 0.75) -> List[MatchResult]:
        """
        Semantic matching usando embeddings pre-computati
        """
        matches = []
        
        # Generate embedding for raw metric
        raw_embedding = self.semantic_similarity.encode([raw_metric])
        
        # Compare with pre-computed canonical embeddings
        for canonical_metric, canonical_embedding in self.canonical_embeddings.items():
            similarity = cosine_similarity([raw_embedding[0]], [canonical_embedding])[0][0]
            
            if similarity >= threshold:
                matches.append(MatchResult(
                    canonical_metric=canonical_metric,
                    confidence=similarity,
                    match_type='semantic_similarity',
                    metadata={'semantic_score': similarity}
                ))
        
        return sorted(matches, key=lambda x: x.confidence, reverse=True)
```

### 5. Financial Validation (`src/domain/value_objects/guardrails.py`)

Sistema di validazione business rules per coerenza finanziaria:

```python
class FinancialValidationEngine:
    """
    Engine di validazione regole business finanziarie
    """
    
    def __init__(self):
        self.validation_rules = self._load_validation_rules()
        self.tolerance_levels = {
            'strict': 0.01,      # 1% tolerance
            'moderate': 0.05,    # 5% tolerance  
            'lenient': 0.10      # 10% tolerance
        }
    
    def validate_financial_coherence(self, financial_data: Dict, tolerance_level: str = 'moderate') -> ValidationResult:
        """
        Validazione completa coerenza finanziaria con multiple rules
        
        Validazioni implementate:
        1. Balance Sheet Equation: Assets = Liabilities + Equity
        2. PFN Coherence: PFN = Gross Debt - Cash
        3. Income Statement Logic: Net Income = Revenues - Expenses
        4. Cash Flow Consistency: Operating + Investing + Financing = Net Change
        5. Ratio Bounds: Financial ratios within reasonable ranges
        """
        
        validation_results = ValidationResult()
        tolerance = self.tolerance_levels[tolerance_level]
        
        # 1. Balance Sheet Validation
        bs_validation = self._validate_balance_sheet_equation(financial_data, tolerance)
        validation_results.add_check('balance_sheet_equation', bs_validation)
        
        # 2. PFN Validation
        pfn_validation = self._validate_pfn_coherence(financial_data, tolerance)
        validation_results.add_check('pfn_coherence', pfn_validation)
        
        # 3. Income Statement Validation
        is_validation = self._validate_income_statement_logic(financial_data, tolerance)
        validation_results.add_check('income_statement_logic', is_validation)
        
        # 4. Cross-Statement Validation
        cross_validation = self._validate_cross_statement_consistency(financial_data, tolerance)
        validation_results.add_check('cross_statement_consistency', cross_validation)
        
        # 5. Ratio Validation
        ratio_validation = self._validate_financial_ratios(financial_data)
        validation_results.add_check('financial_ratios', ratio_validation)
        
        # 6. Temporal Consistency (se disponibili dati multi-periodo)
        if self._has_temporal_data(financial_data):
            temporal_validation = self._validate_temporal_consistency(financial_data)
            validation_results.add_check('temporal_consistency', temporal_validation)
        
        return validation_results
    
    def _validate_balance_sheet_equation(self, data: Dict, tolerance: float) -> ValidationCheck:
        """
        Validazione equazione fondamentale bilancio: Attivo = Passivo + Patrimonio Netto
        """
        try:
            # Estrazione valori chiave
            total_assets = self._extract_metric_value(data, ['attivo_totale', 'total_assets'])
            total_liabilities = self._extract_metric_value(data, ['passivo_totale', 'total_liabilities'])  
            shareholders_equity = self._extract_metric_value(data, ['patrimonio_netto', 'shareholders_equity'])
            
            if any(v is None for v in [total_assets, total_liabilities, shareholders_equity]):
                return ValidationCheck(
                    status='skipped',
                    message="Insufficient data for balance sheet validation",
                    severity='warning'
                )
            
            # Calcolo discrepancy
            expected_assets = total_liabilities + shareholders_equity
            discrepancy = abs(total_assets - expected_assets)
            relative_error = discrepancy / total_assets if total_assets != 0 else float('inf')
            
            # Validation logic
            if relative_error <= tolerance:
                return ValidationCheck(
                    status='passed',
                    message=f"Balance sheet equation valid (error: {relative_error:.2%})",
                    severity='info',
                    metadata={
                        'total_assets': total_assets,
                        'total_liabilities': total_liabilities,
                        'shareholders_equity': shareholders_equity,
                        'discrepancy': discrepancy,
                        'relative_error': relative_error
                    }
                )
            else:
                return ValidationCheck(
                    status='failed',
                    message=f"Balance sheet equation violated (error: {relative_error:.2%})",
                    severity='error',
                    suggestions=[
                        "Verify completeness of assets and liabilities",
                        "Check for hidden reserves or off-balance items",
                        "Review data extraction accuracy"
                    ],
                    metadata={
                        'discrepancy': discrepancy,
                        'relative_error': relative_error,
                        'tolerance_used': tolerance
                    }
                )
                
        except Exception as e:
            return ValidationCheck(
                status='error',
                message=f"Balance sheet validation failed: {str(e)}",
                severity='error'
            )
    
    def _validate_pfn_coherence(self, data: Dict, tolerance: float) -> ValidationCheck:
        """
        Validazione coerenza Posizione Finanziaria Netta: PFN = Debito Lordo - Cassa
        """
        try:
            # Estrazione componenti PFN
            pfn_declared = self._extract_metric_value(data, [
                'posizione_finanziaria_netta', 'pfn', 'net_financial_position'
            ])
            gross_debt = self._extract_metric_value(data, [
                'debito_finanziario_lordo', 'gross_debt', 'total_debt'
            ])
            cash_equivalents = self._extract_metric_value(data, [
                'disponibilita_liquide', 'cash_and_equivalents', 'cash'
            ])
            
            if pfn_declared is None:
                # Calcolo PFN se non dichiarata esplicitamente
                if gross_debt is not None and cash_equivalents is not None:
                    calculated_pfn = gross_debt - cash_equivalents
                    return ValidationCheck(
                        status='calculated',
                        message=f"PFN calculated: {calculated_pfn:,.2f}",
                        severity='info',
                        metadata={'calculated_pfn': calculated_pfn}
                    )
                else:
                    return ValidationCheck(
                        status='skipped',
                        message="Insufficient data for PFN validation",
                        severity='warning'
                    )
            
            # Validazione PFN vs componenti
            if gross_debt is not None and cash_equivalents is not None:
                calculated_pfn = gross_debt - cash_equivalents
                discrepancy = abs(pfn_declared - calculated_pfn)
                relative_error = discrepancy / abs(pfn_declared) if pfn_declared != 0 else float('inf')
                
                if relative_error <= tolerance:
                    return ValidationCheck(
                        status='passed',
                        message=f"PFN coherence validated (error: {relative_error:.2%})",
                        severity='info'
                    )
                else:
                    return ValidationCheck(
                        status='failed',
                        message=f"PFN coherence violation (error: {relative_error:.2%})",
                        severity='warning',
                        suggestions=[
                            "Review gross debt calculation completeness",
                            "Verify cash equivalents include all liquid assets",
                            "Check for restricted cash or pledged assets"
                        ]
                    )
            
        except Exception as e:
            return ValidationCheck(
                status='error',
                message=f"PFN validation error: {str(e)}",
                severity='error'
            )
```

---

## Componenti Specializzati

### 1. Hybrid Retrieval System (`src/application/services/hybrid_retrieval.py`)

Sistema di retrieval ibrido che combina ricerca keyword e semantica:

```python
class HybridRetrievalEngine:
    """
    Engine di retrieval ibrido BM25 + Embeddings + Reranking
    """
    
    def __init__(self):
        self.bm25_index = None
        self.vector_store = None
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-2-v2')
        
        # Weighting configuration
        self.weights = {
            'bm25': 0.3,
            'semantic': 0.5,
            'cross_encoder': 0.2
        }
    
    async def hybrid_search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Ricerca ibrida multi-stage:
        1. BM25 keyword search
        2. Semantic vector search  
        3. CrossEncoder reranking
        4. Score fusion e ranking finale
        """
        
        # Stage 1: BM25 Retrieval
        bm25_results = await self._bm25_search(query, top_k * 2)
        
        # Stage 2: Semantic Search
        semantic_results = await self._semantic_search(query, top_k * 2)
        
        # Stage 3: Result Fusion
        fused_results = self._fuse_search_results(bm25_results, semantic_results)
        
        # Stage 4: CrossEncoder Reranking
        reranked_results = await self._cross_encoder_rerank(query, fused_results, top_k)
        
        return reranked_results
    
    def _fuse_search_results(self, bm25_results: List, semantic_results: List) -> List[SearchResult]:
        """
        Fusione intelligente risultati con Reciprocal Rank Fusion (RRF)
        """
        # Combine unique documents from both result sets
        all_docs = {}
        
        # Process BM25 results
        for rank, result in enumerate(bm25_results):
            doc_id = result.document_id
            if doc_id not in all_docs:
                all_docs[doc_id] = SearchResult(
                    document_id=doc_id,
                    content=result.content,
                    metadata=result.metadata
                )
            
            # RRF score for BM25
            all_docs[doc_id].scores['bm25'] = result.score
            all_docs[doc_id].scores['bm25_rrf'] = 1.0 / (60 + rank + 1)
        
        # Process semantic results
        for rank, result in enumerate(semantic_results):
            doc_id = result.document_id
            if doc_id not in all_docs:
                all_docs[doc_id] = SearchResult(
                    document_id=doc_id,
                    content=result.content,
                    metadata=result.metadata
                )
            
            # RRF score for semantic
            all_docs[doc_id].scores['semantic'] = result.score
            all_docs[doc_id].scores['semantic_rrf'] = 1.0 / (60 + rank + 1)
        
        # Calculate fused score
        for doc in all_docs.values():
            bm25_rrf = doc.scores.get('bm25_rrf', 0)
            semantic_rrf = doc.scores.get('semantic_rrf', 0)
            
            # Weighted RRF fusion
            doc.fused_score = (
                self.weights['bm25'] * bm25_rrf +
                self.weights['semantic'] * semantic_rrf
            )
        
        # Sort by fused score
        return sorted(all_docs.values(), key=lambda x: x.fused_score, reverse=True)
```

### 2. Table Analyzer (`src/application/services/table_analyzer.py`)

Analizzatore specializzato per tabelle estratte da documenti:

```python
class IntelligentTableAnalyzer:
    """
    Analizzatore intelligente per tabelle con riconoscimento semantico
    """
    
    def __init__(self):
        self.column_classifier = ColumnSemanticClassifier()
        self.relation_detector = TableRelationDetector()
        self.financial_pattern_recognizer = FinancialPatternRecognizer()
    
    async def analyze_table(self, table_data: pd.DataFrame, context: AnalysisContext) -> TableAnalysis:
        """
        Analisi completa tabella con:
        1. Classificazione semantica colonne
        2. Riconoscimento pattern finanziari
        3. Estrazione relazioni e dipendenze
        4. Quality assessment e suggerimenti
        """
        
        analysis_result = TableAnalysis()
        
        # 1. Semantic Column Classification
        column_semantics = {}
        for column_name in table_data.columns:
            semantic_type = await self.column_classifier.classify_column(
                column_name, table_data[column_name], context
            )
            column_semantics[column_name] = semantic_type
        
        analysis_result.column_semantics = column_semantics
        
        # 2. Financial Pattern Recognition
        financial_patterns = self.financial_pattern_recognizer.identify_patterns(
            table_data, column_semantics
        )
        analysis_result.financial_patterns = financial_patterns
        
        # 3. Table Structure Analysis
        structure_info = self._analyze_table_structure(table_data)
        analysis_result.structure_info = structure_info
        
        # 4. Data Quality Assessment
        quality_metrics = self._assess_table_quality(table_data, column_semantics)
        analysis_result.quality_metrics = quality_metrics
        
        # 5. Business Intelligence Extraction
        bi_insights = self._extract_business_insights(table_data, financial_patterns)
        analysis_result.business_insights = bi_insights
        
        return analysis_result
    
    def _analyze_table_structure(self, df: pd.DataFrame) -> TableStructureInfo:
        """
        Analisi struttura tabella:
        - Header detection e multi-level headers
        - Footer detection (totali, note)
        - Section identification
        - Merged cell detection
        """
        structure = TableStructureInfo()
        
        # Multi-level header detection
        if self._has_multilevel_headers(df):
            structure.header_levels = self._extract_header_hierarchy(df)
        
        # Total/subtotal row detection
        total_rows = self._identify_total_rows(df)
        structure.total_rows = total_rows
        
        # Section boundaries
        sections = self._identify_table_sections(df)
        structure.sections = sections
        
        # Data sparsity analysis
        sparsity_metrics = self._calculate_sparsity_metrics(df)
        structure.sparsity_metrics = sparsity_metrics
        
        return structure
    
    def _extract_business_insights(self, df: pd.DataFrame, patterns: List[FinancialPattern]) -> List[BusinessInsight]:
        """
        Estrazione insights business da analisi tabella
        """
        insights = []
        
        for pattern in patterns:
            if pattern.type == 'income_statement':
                # Calculate key financial ratios
                if 'revenues' in pattern.identified_columns and 'net_income' in pattern.identified_columns:
                    profit_margin = self._calculate_profit_margin(df, pattern)
                    if profit_margin:
                        insights.append(BusinessInsight(
                            type='profitability_ratio',
                            description=f"Profit margin: {profit_margin:.2%}",
                            value=profit_margin,
                            significance='high' if profit_margin > 0.15 else 'medium'
                        ))
            
            elif pattern.type == 'balance_sheet':
                # Analyze financial position
                if 'total_assets' in pattern.identified_columns and 'total_equity' in pattern.identified_columns:
                    leverage_ratio = self._calculate_leverage_ratio(df, pattern)
                    if leverage_ratio:
                        insights.append(BusinessInsight(
                            type='leverage_analysis',
                            description=f"Debt-to-equity ratio: {leverage_ratio:.2f}",
                            value=leverage_ratio,
                            significance='high' if leverage_ratio > 2.0 else 'medium'
                        ))
        
        return insights
```

---

## Intelligenza Artificiale nell'Analisi

### 1. ML-Enhanced Content Classification

```python
class MLContentClassifier:
    """
    Classificatore ML per tipo di contenuto e rilevanza business
    """
    
    def __init__(self):
        self.content_classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
        
        self.business_categories = [
            "financial_statement",
            "balance_sheet", 
            "income_statement",
            "cash_flow_statement",
            "management_discussion",
            "market_analysis",
            "risk_assessment",
            "strategic_plan",
            "operational_metrics",
            "regulatory_compliance"
        ]
    
    async def classify_content(self, text: str) -> ContentClassification:
        """
        Classificazione ML del contenuto con confidence scoring
        """
        
        # Zero-shot classification
        classification_result = self.content_classifier(text, self.business_categories)
        
        # Extract top predictions
        top_predictions = []
        for label, score in zip(classification_result['labels'], classification_result['scores']):
            if score > 0.1:  # Threshold per rilevanza
                top_predictions.append(CategoryPrediction(
                    category=label,
                    confidence=score,
                    relevance=self._calculate_business_relevance(label, score)
                ))
        
        # Content complexity analysis
        complexity_score = self._analyze_content_complexity(text)
        
        # Financial content density
        financial_density = self._calculate_financial_density(text)
        
        return ContentClassification(
            primary_category=top_predictions[0] if top_predictions else None,
            all_predictions=top_predictions,
            complexity_score=complexity_score,
            financial_density=financial_density,
            processing_recommendations=self._generate_processing_recommendations(
                top_predictions, complexity_score, financial_density
            )
        )
```

### 2. Advanced Topic Modeling

```python
class AdvancedTopicModeling:
    """
    Topic modeling avanzato con BERTopic e custom financial topics
    """
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.topic_model = BERTopic(
            embedding_model=self.embedding_model,
            nr_topics="auto",
            min_topic_size=5
        )
        self.financial_topics = self._load_financial_topic_seeds()
    
    async def extract_topics(self, documents: List[str]) -> TopicAnalysis:
        """
        Estrazione topic con guided topic modeling per domini finanziari
        """
        
        # Preprocessing documents
        cleaned_docs = [self._preprocess_document(doc) for doc in documents]
        
        # Guided topic modeling con seed topics finanziari
        topics, probabilities = self.topic_model.fit_transform(
            cleaned_docs,
            y=self._get_financial_guidance_labels(cleaned_docs)
        )
        
        # Topic information extraction
        topic_info = self.topic_model.get_topic_info()
        
        # Financial relevance scoring
        financial_relevance = {}
        for topic_id in topic_info['Topic']:
            if topic_id != -1:  # Skip outlier topic
                topic_words = self.topic_model.get_topic(topic_id)
                relevance_score = self._calculate_financial_relevance(topic_words)
                financial_relevance[topic_id] = relevance_score
        
        # Topic-document mapping
        topic_document_mapping = self._create_topic_document_mapping(
            topics, probabilities, documents
        )
        
        return TopicAnalysis(
            topics=topic_info,
            financial_relevance=financial_relevance,
            document_mapping=topic_document_mapping,
            model_metadata={
                'num_topics': len(topic_info),
                'outlier_documents': len([t for t in topics if t == -1]),
                'avg_coherence': self._calculate_topic_coherence(topic_info)
            }
        )
```

---

## Performance e Ottimizzazioni

### 1. Caching Strategy Avanzato

```python
class AdvancedAnalysisCache:
    """
    Sistema di cache multi-layer per analisi contenuto
    """
    
    def __init__(self):
        # Memory cache per risultati frequenti
        self.memory_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour TTL
        
        # Redis cache per sharing cross-processo
        self.redis_client = redis.Redis(host='localhost', port=6379, db=2)
        
        # File system cache per risultati pesanti
        self.fs_cache = FileSystemCache('.cache/analysis', default_timeout=86400)  # 24 hours
    
    async def get_cached_analysis(self, content_hash: str, analysis_type: str) -> Optional[Any]:
        """
        Recupero analisi da cache multi-layer con fallback strategy
        """
        cache_key = f"{analysis_type}:{content_hash}"
        
        # L1 Cache: Memory
        if cache_key in self.memory_cache:
            logger.debug(f"Cache hit (memory): {cache_key}")
            return self.memory_cache[cache_key]
        
        # L2 Cache: Redis
        try:
            redis_result = self.redis_client.get(cache_key)
            if redis_result:
                logger.debug(f"Cache hit (redis): {cache_key}")
                result = pickle.loads(redis_result)
                # Promote to memory cache
                self.memory_cache[cache_key] = result
                return result
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
        
        # L3 Cache: File System
        try:
            fs_result = self.fs_cache.get(cache_key)
            if fs_result:
                logger.debug(f"Cache hit (filesystem): {cache_key}")
                # Promote to higher levels
                self.memory_cache[cache_key] = fs_result
                try:
                    self.redis_client.setex(
                        cache_key, 
                        3600,  # 1 hour in Redis
                        pickle.dumps(fs_result)
                    )
                except Exception:
                    pass
                return fs_result
        except Exception as e:
            logger.warning(f"Filesystem cache error: {e}")
        
        return None
    
    async def cache_analysis_result(self, content_hash: str, analysis_type: str, result: Any):
        """
        Memorizzazione risultato analisi su tutti i layer di cache
        """
        cache_key = f"{analysis_type}:{content_hash}"
        
        # Store in all cache layers
        self.memory_cache[cache_key] = result
        
        try:
            self.redis_client.setex(
                cache_key,
                3600,  # 1 hour
                pickle.dumps(result)
            )
        except Exception as e:
            logger.warning(f"Redis cache storage error: {e}")
        
        try:
            self.fs_cache.set(cache_key, result)
        except Exception as e:
            logger.warning(f"Filesystem cache storage error: {e}")
```

### 2. Parallel Analysis Pipeline

```python
class ParallelAnalysisPipeline:
    """
    Pipeline parallelizzata per analisi multi-documento
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def analyze_documents_batch(self, documents: List[DocumentInfo]) -> BatchAnalysisResult:
        """
        Analisi batch parallelizzata con load balancing
        """
        
        # Raggruppamento documenti per tipo per ottimizzare risorse
        doc_groups = self._group_documents_by_type(documents)
        
        # Parallelizzazione per gruppo
        analysis_tasks = []
        for doc_type, doc_list in doc_groups.items():
            if len(doc_list) > 1:
                # Parallel processing per gruppo omogeneo
                task = self._parallel_analyze_group(doc_type, doc_list)
            else:
                # Single document analysis
                task = self._analyze_single_document(doc_list[0])
            
            analysis_tasks.append(task)
        
        # Esecuzione parallela di tutti i task
        group_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Consolidamento risultati
        consolidated_results = self._consolidate_analysis_results(group_results)
        
        return BatchAnalysisResult(
            total_documents=len(documents),
            successful_analyses=len([r for r in group_results if not isinstance(r, Exception)]),
            failed_analyses=len([r for r in group_results if isinstance(r, Exception)]),
            results=consolidated_results,
            processing_time=time.time() - start_time,
            performance_metrics=self._calculate_batch_performance_metrics(group_results)
        )
    
    async def _parallel_analyze_group(self, doc_type: str, documents: List[DocumentInfo]) -> List[AnalysisResult]:
        """
        Analisi parallelizzata gruppo omogeneo di documenti
        """
        
        # Ottimizzazione analyzer per tipo specifico
        analyzer = self._get_optimized_analyzer(doc_type)
        
        # Chunking per batch processing
        batch_size = self._calculate_optimal_batch_size(doc_type, len(documents))
        batches = [documents[i:i+batch_size] for i in range(0, len(documents), batch_size)]
        
        # Parallel batch processing
        batch_tasks = [
            asyncio.create_task(analyzer.analyze_batch(batch))
            for batch in batches
        ]
        
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Flatten results
        all_results = []
        for batch_result in batch_results:
            all_results.extend(batch_result)
        
        return all_results
```

---

## Conclusioni

Il sistema di analisi contenuto rappresenta una pipeline sofisticata che trasforma documenti non strutturati in knowledge strutturata e interrogabile. L'architettura enterprise multi-layer garantisce:

**Punti di forza principali:**
- **Intelligenza Multi-Modale**: Combina NLP, ML e regole business per analisi completa
- **Scalabilità**: Processamento parallelo e caching avanzato
- **Precisione**: Validazione business rules e ontology mapping
- **Resilienza**: Fallback automatici e gestione errori robusta
- **Osservabilità**: Monitoring completo con metriche performance

**Tecnologie Core:**
- **NLP**: spaCy, Transformers, BERTopic per analisi linguistica
- **ML**: Classification, entity recognition, semantic similarity
- **Business Logic**: Financial validation, ontology mapping, data normalization
- **Performance**: Caching multi-layer, parallel processing, optimization

La documentazione tecnica evidenzia come ogni componente contribuisce alla trasformazione di documenti grezzi in insight business azionabili attraverso una pipeline enterprise robusta e scalabile.