from typing import List, Dict, Any, Optional
import structlog
import time
from src.core.llm_client import LLMClient
from src.core.query_optimizer import QueryOptimizer
from src.core.industry_configs import IndustryConfigManager
from src.core.cache_manager import CacheManager
from src.core.query_suggestions import QuerySuggestionService
from src.core.format_normalizer import FormatNormalizer
from src.core.financial_hierarchy import HierarchyLevel, financial_hierarchy
from src.core.financial_semantic_parser import financial_parser, QueryIntent, QueryType
from src.core.metrics_precalculation import FinancialMetricsPreCalculator
from src.core.precalc_integration import PreCalcIntegrator, PreCalcRegistry, QueryDecomposer
from src.core.table_registry import table_registry, TableDomain
from src.core.business_config import (
    BusinessConfigManager, 
    mapping_registry,
    QueryContextEnhancer
)
try:
    from src.core.knowledge_graph import GraphTraversalEngine
    from src.core.knowledge_graph.jena_singleton import (
        get_jena_knowledge_graph,
        get_jena_query_resolver
    )
    KNOWLEDGE_GRAPH_AVAILABLE = True
except ImportError as e:
    import traceback
    print(f"❌ KNOWLEDGE GRAPH IMPORT FAILED: {e}")
    traceback.print_exc()
    KNOWLEDGE_GRAPH_AVAILABLE = False
    GraphTraversalEngine = None
    get_jena_knowledge_graph = lambda redis_client=None: None
    get_jena_query_resolver = lambda: None
from src.db.bigquery import BigQueryClient
from src.db.weaviate_client import WeaviateClient
from src.config import settings

logger = structlog.get_logger()


class SQLGenerator:
    def __init__(self):
        self.llm_client = LLMClient()
        self.bq_client = BigQueryClient()
        self.vector_client = WeaviateClient()
        self.optimizer = QueryOptimizer()
        self.suggestion_service = QuerySuggestionService()
        self.format_normalizer = None  # Will be initialized after cache_manager
        
        # Initialize cache manager
        self.cache_manager = None
        if settings.cache_enabled:
            try:
                self.cache_manager = CacheManager(
                    redis_url=settings.redis_url,
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    decode_responses=settings.redis_decode_responses,
                    max_connections=settings.redis_max_connections
                )
                # Update TTL settings from config
                self.cache_manager.TTL_SQL_FREQUENT = settings.cache_ttl_sql_frequent
                self.cache_manager.TTL_SQL_INFREQUENT = settings.cache_ttl_sql_infrequent
                self.cache_manager.TTL_SCHEMA = settings.cache_ttl_schema
                self.cache_manager.TTL_EMBEDDING = settings.cache_ttl_embedding
                self.cache_manager.TTL_VALIDATION = settings.cache_ttl_validation
                self.cache_manager.TTL_RESULT = settings.cache_ttl_result
                self.cache_manager.TTL_SESSION = settings.cache_ttl_session
                logger.info("Cache manager initialized successfully")
                # Update suggestion service with cache manager
                self.suggestion_service.cache_manager = self.cache_manager
            except Exception as e:
                logger.warning(f"Failed to initialize cache manager: {e}. Running without cache.")
                self.cache_manager = None

        # Initialize format normalizer (requires bq_client and cache_manager)
        try:
            self.format_normalizer = FormatNormalizer(self.bq_client, self.cache_manager)
            logger.info("Format normalizer initialized - JOIN accuracy fix enabled")
        except Exception as e:
            logger.warning(f"Failed to initialize format normalizer: {e}. Running without format normalization.")
            self.format_normalizer = None

        # Industry configuration
        self.industry_manager = IndustryConfigManager()
        if settings.enable_industry_features:
            self.industry_manager.set_active_industry(settings.industry)
            logger.info(f"Industry features enabled for: {settings.industry}")
        
        
        # Initialize financial components
        self.financial_parser = financial_parser
        self.financial_hierarchy = financial_hierarchy
        # Enable financial features
        self.enable_financial_features = True  # settings.enable_industry_features and hasattr(settings, 'enable_financial_hierarchy')
        
        # Initialize business configuration
        self.business_config_manager = BusinessConfigManager(
            cache_manager=self.cache_manager,
            weaviate_client=self.vector_client
        )
        self.query_enhancer = QueryContextEnhancer()
        
        # Initialize knowledge graph components (using Jena/RDF singleton)
        self.knowledge_graph = None
        self.kg_query_resolver = None
        self.kg_traversal = None
        try:
            # Pass Redis client from cache manager if available
            redis_client = None
            if self.cache_manager and hasattr(self.cache_manager, 'redis'):
                redis_client = self.cache_manager.redis
                
            if KNOWLEDGE_GRAPH_AVAILABLE:
                self.knowledge_graph = get_jena_knowledge_graph(redis_client)
                self.kg_query_resolver = get_jena_query_resolver()
                # Note: GraphTraversalEngine might need updating for Jena
                # self.kg_traversal = GraphTraversalEngine(self.knowledge_graph)
                logger.info("Jena/RDF knowledge graph components initialized (Redis-cached)")
            else:
                self.knowledge_graph = None
                self.kg_query_resolver = None
                logger.info("Knowledge graph not available - continuing without it")
        except Exception as e:
            logger.warning(f"Failed to initialize Jena knowledge graph: {e}. Running without KG enhancement.")
        
        # Load default client configuration
        client_id = getattr(settings, 'client_id', 'arizona_beverages')
        dataset_id = settings.bigquery_dataset
        try:
            config = self.business_config_manager.load_client_config(client_id, dataset_id)
            self.business_config_manager.set_active_config(client_id, dataset_id)
            
            # Register mappings in the registry
            if config.gl_mappings:
                mapping_registry.register_gl_mapping(client_id, config.gl_mappings.mappings)
                logger.info(f"Registered {len(config.gl_mappings.mappings)} GL mappings for {client_id}")
            
            if config.material_hierarchy:
                mapping_registry.register_material_hierarchy(client_id, config.material_hierarchy)
                logger.info(f"Registered material hierarchy for {client_id}")
            
            # Refresh the dynamic hierarchy to use the new mappings
            if config.gl_mappings or config.material_hierarchy:
                from src.core.dynamic_financial_hierarchy import refresh_dynamic_hierarchy
                refresh_dynamic_hierarchy(client_id)
                logger.info(f"Refreshed dynamic hierarchy for {client_id}")
                
        except Exception as e:
            logger.warning(f"Failed to load business configuration: {e}")
        
        # Initialize pre-calculation integration
        self.precalc_integrator = None
        if self.cache_manager and self.enable_financial_features:
            try:
                precalculator = FinancialMetricsPreCalculator(
                    bq_client=self.bq_client,
                    cache_manager=self.cache_manager
                )
                registry = PreCalcRegistry(precalculator)
                decomposer = QueryDecomposer(registry, self.financial_parser)
                self.precalc_integrator = PreCalcIntegrator(decomposer, precalculator)
                logger.info("Pre-calculation integration initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize pre-calc integration: {e}")
                self.precalc_integrator = None
        if not hasattr(settings, 'enable_financial_hierarchy'):
            self.enable_financial_features = True  # Enable by default
        
        # Set LLM client in suggestion service
        self.suggestion_service.llm_client = self.llm_client
        
        # Skip automatic indexing on startup - will be done lazily on first use
        # self._index_schemas()
    
    def _index_schemas(self):
        """Index all table schemas in the vector database."""
        try:
            logger.info("Indexing BigQuery table schemas...")
            schemas = self.bq_client.get_dataset_schema()
            
            for schema in schemas:
                # Cache schema if caching is enabled
                if self.cache_manager and settings.cache_schema_enabled:
                    self.cache_manager.cache_schema(
                        self.bq_client.project_id,
                        self.bq_client.dataset_id,
                        schema['table_name'],
                        schema
                    )
                
                # Generate embedding for the schema
                schema_text = self._schema_to_text(schema)
                
                # Check cache for embedding first
                embedding = None
                if self.cache_manager and settings.cache_embedding_enabled:
                    embedding = self.cache_manager.get_embedding(schema_text)
                
                if embedding is None:
                    embedding = self.llm_client.generate_embedding(schema_text)
                    # Cache the embedding
                    if self.cache_manager and settings.cache_embedding_enabled:
                        self.cache_manager.cache_embedding(schema_text, embedding)
                
                # Index in vector database
                self.vector_client.index_table_schema(schema, embedding)
            
            logger.info(f"Indexed {len(schemas)} table schemas")
        except Exception as e:
            logger.error(f"Failed to index schemas: {e}")
            # Continue even if indexing fails
    
    def _schema_to_text(self, schema: Dict[str, Any]) -> str:
        """Convert schema to text for embedding generation."""
        parts = [
            f"Table: {schema['table_name']}",
            f"Description: {schema.get('description', 'No description')}"
        ]
        
        for col in schema['columns']:
            col_text = f"{col['name']} {col['type']}"
            if col.get('description'):
                col_text += f" - {col['description']}"
            parts.append(col_text)
        
        return "\n".join(parts)
    
    def generate_sql(
        self,
        query: str,
        use_vector_search: bool = True,
        max_tables: int = 5,
        auto_optimize: bool = True,
        force_refresh: bool = False,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate SQL from natural language query.

        Args:
            query: Natural language query
            use_vector_search: Whether to use vector search for table selection
            max_tables: Maximum number of tables to consider
            auto_optimize: Whether to apply query optimization
            force_refresh: Force cache refresh
            conversation_context: Context from previous conversation messages
        """
        logger.info(f">>> SQL Generator: Starting generation for query: {query}")
        if conversation_context:
            logger.info(f"Using conversation context with {len(conversation_context.get('previous_sql', ''))} chars of previous SQL")
        try:
            # Apply financial hierarchy parsing if enabled
            financial_context = None
            parsed_query = None
            if self.enable_financial_features:
                parsed_query = self.financial_parser.parse_query(query)
                if isinstance(parsed_query, dict):
                    financial_context = self.financial_parser.generate_context_for_llm(parsed_query)
                    
                    # Log the parsed financial context
                    hierarchy_level_value = parsed_query.get("hierarchy_level")
                    if hierarchy_level_value:
                        hierarchy_level_value = hierarchy_level_value.value
                    
                    logger.info(
                        "Financial query parsed",
                        hierarchy_level=hierarchy_level_value,
                        query_type=parsed_query.get("query_type", QueryType.GENERAL).value if hasattr(parsed_query.get("query_type"), "value") else str(parsed_query.get("query_type")),
                        intent=parsed_query.get("intent", QueryIntent.METRIC_CALCULATION).value if hasattr(parsed_query.get("intent"), "value") else str(parsed_query.get("intent")),
                        metrics=[m.metric_name for m in parsed_query.get("metrics", [])]
                    )
                    
                    # For L1 metrics with predefined formulas, we can potentially bypass schema search
                    if (parsed_query.get("hierarchy_level") == HierarchyLevel.L1_METRIC and 
                        parsed_query.get("metrics") and 
                        parsed_query["metrics"][0].metric_code):
                        
                        # Check if we can use a predefined formula from Jena
                        metric_code = parsed_query["metrics"][0].metric_code
                        if self.kg_query_resolver:
                            try:
                                metric_formula = self.kg_query_resolver.get_metric_formula(metric_code)
                                if metric_formula:
                                    # We'll pass this context to the LLM for formula-based generation
                                    logger.info(f"Using predefined formula for metric: {metric_code} from Jena")
                                    # Add the formula to the context
                                    if 'formulas' not in financial_context:
                                        financial_context['formulas'] = {}
                                    financial_context['formulas'][metric_code] = {
                                        'formula': metric_formula.formula,
                                        'components': metric_formula.formula_components
                                    }
                            except Exception as e:
                                logger.warning(f"Failed to get metric formula from Jena: {e}")
                                # Fall back to hardcoded if Jena fails
                                l1_metrics = getattr(self.financial_hierarchy, 'l1_metrics', None) or {}
                                if metric_code in l1_metrics:
                                    logger.info(f"Using predefined formula for metric: {metric_code} from hardcoded")
                        else:
                            # Fall back to hardcoded if no Jena resolver
                            l1_metrics = getattr(self.financial_hierarchy, 'l1_metrics', None) or {}
                            if metric_code in l1_metrics:
                                logger.info(f"Using predefined formula for metric: {metric_code} from hardcoded")
                else:
                    logger.warning(f"Financial parser returned invalid result: {type(parsed_query)}")
                    financial_context = None
            
            # Apply knowledge graph enhancement if available
            kg_enhanced_context = financial_context
            if self.kg_query_resolver and financial_context:
                try:
                    kg_result = self.kg_query_resolver.resolve_query(query, financial_context)
                    
                    # Enhance context with KG findings
                    if kg_result.synonyms_resolved:
                        logger.info(f"Knowledge graph resolved {len(kg_result.synonyms_resolved)} synonyms")
                        if not kg_enhanced_context:
                            kg_enhanced_context = {}
                        kg_enhanced_context['synonyms_resolved'] = kg_result.synonyms_resolved
                    
                    if kg_result.metrics:
                        logger.info(f"Knowledge graph suggested {len(kg_result.metrics)} metrics")
                        kg_enhanced_context['suggested_metrics'] = [
                            {
                                'code': m.metric_code,
                                'name': m.metric_name,
                                'formula': m.formula,
                                'formula_components': m.formula_components
                            } for m in kg_result.metrics
                        ]
                    
                    if kg_result.confidence_score > 0.5:
                        kg_enhanced_context['kg_confidence'] = kg_result.confidence_score

                    # ALWAYS add SQL template if available (not conditional on confidence)
                    if kg_result.suggested_query:
                        kg_enhanced_context['suggested_query'] = kg_result.suggested_query
                        kg_enhanced_context['kg_suggested_query'] = kg_result.suggested_query  # Keep for backwards compatibility
                        logger.info(f"✅ SQL template from KG added to context (length: {len(kg_result.suggested_query)} chars)")
                    
                    # Add formula components if found
                    for metric in kg_result.metrics:
                        if metric.formula_components:
                            if 'sql_components' not in kg_enhanced_context:
                                kg_enhanced_context['sql_components'] = {}
                            kg_enhanced_context['sql_components'][metric.metric_code] = metric.formula_components
                    
                    # Add GL accounts if found
                    if kg_result.gl_accounts:
                        kg_enhanced_context['gl_accounts'] = [
                            {
                                'account_number': gl.account_number,
                                'description': gl.description,
                                'bucket_code': gl.bucket_code
                            } for gl in kg_result.gl_accounts if gl.is_active
                        ]
                    
                    financial_context = kg_enhanced_context
                except Exception as e:
                    logger.warning(f"Knowledge graph enhancement failed: {e}")
            
            # Apply business configuration enhancements
            enhanced_context = None
            active_config = self.business_config_manager.get_active_config()
            if active_config:
                client_id = active_config.client_id
                enhanced_context = self.query_enhancer.enhance_with_client_mappings(query, client_id)
                
                # Merge with financial context if available
                if financial_context and enhanced_context.get("gl_accounts"):
                    # Use the dynamically resolved GL accounts instead of hardcoded ranges
                    financial_context["gl_accounts"] = enhanced_context["gl_accounts"]
                    financial_context["gl_filter"] = self.query_enhancer.get_gl_filter_sql(
                        enhanced_context["gl_accounts"]
                    )
                    logger.info(f"Using {len(enhanced_context['gl_accounts'])} GL accounts from business config")
            
            # Check for pre-calculated values BEFORE generating SQL
            if self.precalc_integrator and financial_context:
                precalc_result = self.precalc_integrator.check_and_use_precalc(query)
                if precalc_result:
                    logger.info(f"Using pre-calculated values for query: {query}")
                    # Add financial context if available
                    if financial_context:
                        precalc_result["financial_context"] = financial_context
                    return precalc_result
            
            # Apply industry-specific preprocessing
            processed_query = query
            if settings.enable_industry_features and self.industry_manager.active_config:
                # Translate business terms
                processed_query = self.industry_manager.translate_business_terms(query)
                
                # Check for matching templates
                templates = self.industry_manager.get_relevant_templates(query)
                if templates:
                    logger.info(f"Found {len(templates)} matching query templates")
            
            # Get relevant table schemas - ALWAYS use vector search as primary mechanism
            relevant_schemas = None
            join_hints = []
            
            # Primary approach: Use vector search for ALL queries
            if use_vector_search:
                logger.info("Using vector search as primary table selection mechanism")
                relevant_schemas = self._get_relevant_schemas(processed_query, max_tables)
                
                # If multiple tables are selected, add JOIN hints
                if relevant_schemas and len(relevant_schemas) > 1:
                    selected_table_names = [s["table_name"] for s in relevant_schemas]

                    # Try using Jena knowledge graph for intelligent JOIN path finding
                    if self.knowledge_graph:
                        try:
                            from src.core.knowledge_graph.join_path_finder import JoinPathFinder

                            finder = JoinPathFinder(self.knowledge_graph)
                            join_order = finder.recommend_join_order(selected_table_names)

                            # Convert JoinPath objects to join hints
                            for join_path in join_order:
                                join_hints.append({
                                    "source": join_path.source_table,
                                    "target": join_path.target_table,
                                    "keys": [(join_path.join_column, join_path.join_column)],  # Both tables use same column name
                                    "type": join_path.join_type,
                                    "column_type": join_path.column_type
                                })

                            if join_hints:
                                logger.info(f"Jena KG found {len(join_hints)} optimal JOIN paths for {len(selected_table_names)} tables")

                        except Exception as e:
                            logger.warning(f"Jena JOIN path finding failed: {e}, falling back to table_registry")
                            # Fall back to table_registry
                            relationships = table_registry.find_relationships(selected_table_names)
                            for rel in relationships:
                                join_hints.append({
                                    "source": rel.source_table,
                                    "target": rel.target_table,
                                    "keys": rel.join_keys,
                                    "type": rel.join_type
                                })
                    else:
                        # No knowledge graph available, use table_registry
                        logger.info("Using table_registry for JOIN hints (Jena KG not available)")
                        relationships = table_registry.find_relationships(selected_table_names)
                        for rel in relationships:
                            join_hints.append({
                                "source": rel.source_table,
                                "target": rel.target_table,
                                "keys": rel.join_keys,
                                "type": rel.join_type
                            })

                    if join_hints:
                        logger.info(f"Found {len(join_hints)} JOIN relationships for {len(selected_table_names)} tables")
                
                # Add domain metadata to schemas
                for schema in relevant_schemas:
                    schema["domain"] = str(table_registry.classify_table(schema["table_name"]).value)
            
            # Fallback only if vector search is disabled or fails
            if not relevant_schemas:
                logger.info("Vector search disabled or failed, using fallback selection")
                
                # Check if we have financial context for specialized handling
                if financial_context and financial_context.get("hierarchy_level"):
                    relevant_schemas = self._get_financial_schemas(financial_context, max_tables)
                
                # Final fallback: get all schemas
                if not relevant_schemas:
                    all_schemas = self.bq_client.get_dataset_schema()
                    relevant_schemas = all_schemas[:max_tables]
            
            if not relevant_schemas:
                # Get suggestions for the failed query
                suggestions = self.suggestion_service.get_suggestions(query)
                clarifying_questions = self.suggestion_service.get_clarifying_questions(query)
                
                return {
                    "error": "No relevant tables found",
                    "sql": None,
                    "error_details": {
                        "error_type": "data_not_found",
                        "user_friendly_message": "I couldn't find tables matching your query. Please check the table names or try rephrasing.",
                        "suggestions": [s.__dict__ for s in suggestions],
                        "clarifying_questions": clarifying_questions
                    }
                }
            
            # Enhance schemas with industry metadata
            if settings.enable_industry_features and self.industry_manager.active_config:
                relevant_schemas = self._enhance_schemas_with_industry_info(relevant_schemas)

            # Prepare kwargs for LLM client
            llm_kwargs = {}
            if financial_context:
                llm_kwargs["financial_context"] = financial_context
            if enhanced_context:
                llm_kwargs["business_context"] = enhanced_context
            if join_hints:
                llm_kwargs["join_hints"] = join_hints
            if conversation_context:
                llm_kwargs["conversation_context"] = conversation_context
            
            # Debug relevant_schemas before passing to LLM
            logger.info(f"Relevant schemas type: {type(relevant_schemas)}")
            logger.info(f"Relevant schemas count: {len(relevant_schemas) if relevant_schemas else 0}")
            if relevant_schemas and len(relevant_schemas) > 0:
                logger.info(f"First schema type: {type(relevant_schemas[0])}")
                if isinstance(relevant_schemas[0], dict):
                    logger.info(f"First schema keys: {list(relevant_schemas[0].keys())}")
            
            # Try cache first if enabled
            if self.cache_manager and settings.cache_sql_enabled and not force_refresh:
                cached_result, from_cache = self.cache_manager.get_or_generate_sql(
                    query,
                    relevant_schemas,
                    lambda q, s: self.llm_client.generate_sql(processed_query, s, **llm_kwargs),
                    force_refresh=force_refresh
                )
                
                if from_cache:
                    logger.info("Returning cached SQL generation")
                    result = cached_result
                    result["from_cache"] = True
                else:
                    result = cached_result
                    result["from_cache"] = False
            else:
                # Generate SQL using LLM
                result = self.llm_client.generate_sql(processed_query, relevant_schemas, **llm_kwargs)
                result["from_cache"] = False
            
            # Post-process SQL to fix revenue column usage
            logger.info(f"Post-processing check: query contains 'revenue'? {('revenue' in query.lower())}")
            if result.get("sql"):
                logger.info(f"SQL before post-processing (first 200 chars): {result['sql'][:200]}")
                
                # Check if this is a revenue-related query
                is_revenue_query = any(term in query.lower() for term in [
                    'revenue', 'sales', 'income', 'turnover', 'top line'
                ])
                
                if is_revenue_query:
                    original_sql = result["sql"]
                    sql_modified = False
                    
                    # Replace all variations of incorrect revenue patterns
                    if "GL_Amount_in_CC" in original_sql and ">" in original_sql:
                        logger.info("Found GL_Amount_in_CC pattern in revenue query, replacing with Gross_Revenue")
                        
                        # List of replacement patterns (order matters - most specific first)
                        replacements = [
                            # With ROUND
                            ("ROUND(SUM(CASE WHEN GL_Amount_in_CC > 0 THEN GL_Amount_in_CC ELSE 0 END), 2)",
                             "ROUND(SUM(COALESCE(Gross_Revenue, 0)), 2)"),
                            # Without ROUND
                            ("SUM(CASE WHEN GL_Amount_in_CC > 0 THEN GL_Amount_in_CC ELSE 0 END)",
                             "SUM(COALESCE(Gross_Revenue, 0))"),
                            # Just the CASE statement
                            ("CASE WHEN GL_Amount_in_CC > 0 THEN GL_Amount_in_CC ELSE 0 END",
                             "COALESCE(Gross_Revenue, 0)"),
                            # Variations with spacing
                            ("CASE WHEN GL_Amount_in_CC>0 THEN GL_Amount_in_CC ELSE 0 END",
                             "COALESCE(Gross_Revenue, 0)"),
                            # With different numeric formats
                            ("CASE WHEN GL_Amount_in_CC > 0.0 THEN GL_Amount_in_CC ELSE 0.0 END",
                             "COALESCE(Gross_Revenue, 0)")
                        ]
                        
                        for old_pattern, new_pattern in replacements:
                            if old_pattern in result["sql"]:
                                result["sql"] = result["sql"].replace(old_pattern, new_pattern)
                                sql_modified = True
                                logger.info(f"Replaced pattern: {old_pattern[:50]}...")
                        
                        if sql_modified:
                            logger.info(f"SQL after post-processing (first 200 chars): {result['sql'][:200]}")
                            result["explanation"] = "Query correctly uses Gross_Revenue column for revenue calculations (auto-corrected)"
                            result["auto_corrected"] = True
            
            # Validate the generated SQL (with caching)
            validation = None
            if self.cache_manager and settings.cache_validation_enabled:
                validation = self.cache_manager.get_validation(result["sql"])
            
            if validation is None:
                validation = self.bq_client.validate_query(result["sql"])
                # Cache validation result
                if self.cache_manager and settings.cache_validation_enabled and not result.get("error"):
                    self.cache_manager.cache_validation(result["sql"], validation)
            
            result["validation"] = validation
            
            # Apply query optimization if enabled and query is valid
            if auto_optimize and validation.get("valid", False):
                optimization_result = self.optimizer.optimize_query(result["sql"])
                
                # If optimization improved the query, use optimized version
                if optimization_result.get("optimized_sql") and \
                   optimization_result["optimized_sql"] != result["sql"]:
                    
                    result["original_sql"] = result["sql"]
                    result["sql"] = optimization_result["optimized_sql"]
                    result["optimizations"] = result.get("optimizations", []) + optimization_result.get("optimizations_applied", [])
                    result["optimization_suggestions"] = optimization_result.get("suggestions", [])
                    result["optimization_improvement"] = optimization_result.get("improvement", {})
                    
                    # Re-validate optimized query
                    result["validation"] = self.bq_client.validate_query(result["sql"])

            # Apply format normalization for JOIN accuracy (fixes COPA/Cockpit mismatch)
            if self.format_normalizer and validation.get("valid", False):
                try:
                    original_sql = result["sql"]
                    normalized_sql = self.format_normalizer.normalize_join_query(original_sql)

                    if normalized_sql != original_sql:
                        logger.info("Format normalization applied to query - JOIN accuracy improved")
                        result["original_sql_before_normalization"] = original_sql
                        result["sql"] = normalized_sql
                        result["format_normalized"] = True

                        # Re-validate normalized query
                        result["validation"] = self.bq_client.validate_query(result["sql"])
                    else:
                        result["format_normalized"] = False
                except Exception as e:
                    logger.warning(f"Format normalization failed: {e}. Using original query.")
                    result["format_normalized"] = False

            # Add industry context to result
            if settings.enable_industry_features:
                result["industry"] = settings.industry
                result["industry_terms_translated"] = processed_query != query
            
            # Add query suggestions if available
            if not result.get("error"):
                # Get improvement suggestions
                improvements = self.suggestion_service.suggest_query_improvements(
                    query, 
                    result.get("sql", ""),
                    result.get("execution", {}).get("performance_stats")
                )
                if improvements:
                    result["suggestions"] = improvements
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate SQL: {e}")
            
            # Get suggestions for the failed query
            suggestions = self.suggestion_service.get_suggestions(query)
            clarifying_questions = self.suggestion_service.get_clarifying_questions(query)
            
            # Return enhanced error response
            error_response = {
                "error": str(e),
                "sql": None,
                "error_details": {
                    "error_type": "generation_error",
                    "user_friendly_message": "I encountered an error generating the SQL query. Please try rephrasing your question.",
                    "suggestions": [s.__dict__ for s in suggestions],
                    "clarifying_questions": clarifying_questions,
                    "technical_details": str(e)
                }
            }
            
            # If we have error details from LLM client, merge them
            if hasattr(e, 'error_details'):
                error_response["error_details"].update(e.error_details)
            
            return error_response
    
    def _check_and_reindex_if_needed(self):
        """Check if vector DB needs reindexing based on cache expiration."""
        try:
            # Check if we have a timestamp for when schemas were last indexed
            index_timestamp_key = f"schema_index_timestamp:{self.bq_client.project_id}:{self.bq_client.dataset_id}"
            
            if self.cache_manager:
                # Get the last index timestamp from cache
                last_indexed = self.cache_manager.redis_client.get(index_timestamp_key)
                
                if last_indexed is None:
                    # Never indexed or cache expired - need to reindex
                    logger.info("No schema index timestamp found, triggering reindex")
                    self._index_schemas()
                    # Store the timestamp
                    self.cache_manager.redis_client.setex(
                        index_timestamp_key,
                        settings.cache_ttl_schema,  # Use same TTL as schema cache
                        str(time.time())
                    )
                else:
                    # Check if any schemas have been modified since last index
                    last_indexed_time = float(last_indexed)
                    schemas = self.bq_client.get_dataset_schema()
                    
                    # Check if any table was modified after our last index
                    needs_reindex = False
                    for schema in schemas:
                        if 'modified' in schema:
                            # Convert modified timestamp to epoch
                            modified_time = schema['modified'].timestamp() if hasattr(schema['modified'], 'timestamp') else 0
                            if modified_time > last_indexed_time:
                                needs_reindex = True
                                break
                    
                    if needs_reindex:
                        logger.info("Schema changes detected, triggering reindex")
                        self._index_schemas()
                        # Update the timestamp
                        self.cache_manager.redis_client.setex(
                            index_timestamp_key,
                            settings.cache_ttl_schema,
                            str(time.time())
                        )
            else:
                # No cache manager, check if vector DB is empty
                try:
                    # Try a simple search to see if we have any indexed schemas
                    test_embedding = [0.0] * 1536  # Dummy embedding
                    results = self.vector_client.search_similar_tables(test_embedding, limit=1)
                    if not results:
                        logger.info("Vector DB appears empty, triggering reindex")
                        self._index_schemas()
                except:
                    # If search fails, assume we need to index
                    logger.info("Vector DB check failed, triggering reindex")
                    self._index_schemas()
                    
        except Exception as e:
            logger.warning(f"Failed to check/reindex schemas: {e}")
            # Continue without reindexing on error

    def _get_relevant_schemas(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get relevant table schemas using vector search.
        
        Enhanced to intelligently select multiple tables when needed for JOINs.
        """
        try:
            # Check if reindexing is needed (based on cache expiration)
            self._check_and_reindex_if_needed()
            
            # Check cache for embedding first
            query_embedding = None
            if self.cache_manager and settings.cache_embedding_enabled:
                query_embedding = self.cache_manager.get_embedding(query)
            
            if query_embedding is None:
                # Generate embedding for the query
                query_embedding = self.llm_client.generate_embedding(query)
                # Cache the embedding
                if self.cache_manager and settings.cache_embedding_enabled:
                    self.cache_manager.cache_embedding(query, query_embedding)
            
            # Adjust limit based on query complexity indicators
            adjusted_limit = self._determine_search_limit(query, limit)
            
            # Search for similar tables with adjusted limit
            similar_tables = self.vector_client.search_similar_tables(
                query_embedding, 
                limit=adjusted_limit
            )
            
            # Analyze if multiple tables are needed based on similarity scores
            tables_to_return = self._select_tables_by_relevance(similar_tables, query, limit)
            
            return tables_to_return
        except Exception as e:
            logger.warning(f"Vector search failed, falling back to all tables: {e}")
            # Fallback to getting all schemas
            return self.bq_client.get_dataset_schema()[:limit]
    
    def _determine_search_limit(self, query: str, base_limit: int) -> int:
        """Determine search limit based on query complexity.
        
        Returns a higher limit for queries that likely need multiple tables.
        """
        query_lower = query.lower()
        
        # Indicators that multiple tables might be needed
        multi_table_indicators = [
            # JOIN keywords
            "join", "combine", "merge", "together with",
            # Multiple entity references
            "customer and product", "orders and revenue", "delivery and billing",
            # Cross-domain terms
            "revenue by delivery", "margin for orders", "profit and shipment",
            # Aggregation across entities
            "total revenue and order count", "sales with customer details"
        ]
        
        # Check for multi-table indicators
        needs_multiple = any(indicator in query_lower for indicator in multi_table_indicators)
        
        # Also check for explicit mentions of multiple business domains
        domain_count = 0
        domains = ["revenue", "margin", "profit", "order", "delivery", "customer", "product", "inventory"]
        for domain in domains:
            if domain in query_lower:
                domain_count += 1
        
        if needs_multiple or domain_count >= 2:
            # Search for more tables to find potential JOIN candidates
            return min(base_limit * 2, 10)  # Cap at 10 for performance
        
        return base_limit
    
    def _select_tables_by_relevance(self, similar_tables: List[Dict[str, Any]], query: str, limit: int) -> List[Dict[str, Any]]:
        """Select tables based on relevance scores and potential for JOINs.
        
        Uses similarity distances to determine if multiple tables should be included.
        """
        if not similar_tables:
            return []
        
        # Sort by distance (lower is better)
        sorted_tables = sorted(similar_tables, key=lambda x: x.get("distance", 1.0))
        
        # Always include the most relevant table
        selected = [sorted_tables[0]]
        
        if len(sorted_tables) > 1:
            # Get the best match distance as baseline
            best_distance = sorted_tables[0].get("distance", 0.0)
            
            # Threshold for considering additional tables (within 20% of best match)
            threshold = best_distance * 1.2
            
            # Check if query explicitly mentions multiple entities
            query_lower = query.lower()
            needs_join = any(keyword in query_lower for keyword in 
                           ["and", "with", "by", "per", "for each", "join", "combine"])
            
            # Add additional relevant tables
            for table in sorted_tables[1:]:
                if len(selected) >= limit:
                    break
                    
                table_distance = table.get("distance", 1.0)
                
                # Include table if:
                # 1. It's within the relevance threshold
                # 2. Query indicates need for multiple tables
                # 3. Table name suggests different domain than already selected
                if table_distance <= threshold or (needs_join and table_distance <= best_distance * 1.5):
                    # Check if this table adds value (different domain)
                    if self._is_complementary_table(table, selected):
                        selected.append(table)
                        logger.info(f"Selected additional table {table['table_name']} with distance {table_distance}")
        
        return selected
    
    def _is_complementary_table(self, table: Dict[str, Any], selected_tables: List[Dict[str, Any]]) -> bool:
        """Check if a table complements already selected tables (different domain/entity)."""
        table_name = table.get("table_name", "").lower()
        
        # Check if table represents a different entity type
        for selected in selected_tables:
            selected_name = selected.get("table_name", "").lower()
            
            # If tables share significant prefix/suffix, they might be variants of same entity
            if (table_name.startswith(selected_name[:10]) or 
                selected_name.startswith(table_name[:10])):
                return False
            
            # Check for domain differences
            if "copa" in selected_name and "copa" in table_name:
                return False  # Same financial domain
            if "order" in selected_name and "order" in table_name:
                return False  # Same order domain
        
        return True
    
    def _get_multi_domain_schemas(self, query: str, domains: List[str], limit: int) -> Dict[str, Any]:
        """Get relevant schemas for multi-domain queries with relationship hints.
        
        Now uses vector search as primary mechanism, with JOIN hints added when needed.
        """
        try:
            # Use vector search as primary mechanism
            relevant_schemas = self._get_relevant_schemas(query, limit)
            
            if not relevant_schemas:
                return {
                    "schemas": [],
                    "join_hints": [],
                    "requires_join": False,
                    "domains": domains
                }
            
            # Extract table names from selected schemas
            selected_table_names = [s["table_name"] for s in relevant_schemas]
            
            # Add domain metadata to schemas
            for schema in relevant_schemas:
                schema["domain"] = str(table_registry.classify_table(schema["table_name"]).value)
            
            # If multiple tables selected, get JOIN hints
            join_hints = []
            requires_join = len(selected_table_names) > 1
            
            if requires_join:
                # Get relationships between selected tables
                relationships = table_registry.find_relationships(selected_table_names)
                
                # Build join hints from relationships
                for rel in relationships:
                    join_hints.append({
                        "source": rel.source_table,
                        "target": rel.target_table,
                        "keys": rel.join_keys,
                        "type": rel.join_type
                    })
                
                if join_hints:
                    logger.info(f"Found {len(join_hints)} JOIN relationships for {len(selected_table_names)} tables")
                else:
                    logger.info(f"No direct JOIN relationships found for selected tables: {selected_table_names}")
            
            return {
                "schemas": relevant_schemas,
                "join_hints": join_hints,
                "requires_join": requires_join,
                "domains": domains
            }
        except Exception as e:
            logger.warning(f"Multi-domain schema selection failed: {e}")
            # Fallback to basic vector search without JOIN hints
            return {
                "schemas": self._get_relevant_schemas(query, limit),
                "join_hints": [],
                "requires_join": False,
                "domains": domains
            }
    
    def execute_query(self, sql: str) -> Dict[str, Any]:
        """Execute SQL query and return results."""
        try:
            # Validate first
            validation = self.bq_client.validate_query(sql)
            if not validation["valid"]:
                # Try to correct the SQL if validation failed
                if self.llm_client:
                    correction_result = self.llm_client.correct_sql_error(
                        sql,
                        validation['error'],
                        self.bq_client.get_dataset_schema()[:5]  # Provide some schema context
                    )
                    
                    if correction_result.get("correction_applied") and correction_result.get("sql"):
                        # Try the corrected SQL
                        logger.info("Attempting to execute corrected SQL")
                        sql = correction_result["sql"]
                        validation = self.bq_client.validate_query(sql)
                        
                        if not validation["valid"]:
                            # Still invalid after correction
                            return {
                                "error": f"Invalid query even after correction: {validation['error']}",
                                "results": None,
                                "error_details": {
                                    "original_error": validation['error'],
                                    "correction_attempted": True,
                                    "correction_failed": True
                                }
                            }
                    else:
                        return {
                            "error": f"Invalid query: {validation['error']}",
                            "results": None,
                            "error_details": {
                                "validation_error": validation['error'],
                                "correction_attempted": True,
                                "correction_failed": True
                            }
                        }
                else:
                    return {
                        "error": f"Invalid query: {validation['error']}",
                        "results": None
                    }
            
            # Execute query with performance tracking
            start_time = time.time()
            execution_result = self.bq_client.execute_query(sql)
            execution_time = (time.time() - start_time) * 1000  # ms

            # Extract results from the new Dict format
            results = execution_result.get('rows', [])
            total_rows = execution_result.get('total_rows', len(results))
            truncated = execution_result.get('truncated', False)

            return {
                "results": results,
                "row_count": len(results),
                "total_rows": total_rows,
                "truncated": truncated,
                "validation": validation,
                "performance_stats": {
                    "execution_time_ms": execution_time,
                    "bytes_processed": validation.get("bytes_processed", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            
            # Provide enhanced error information
            error_response = {
                "error": str(e),
                "results": None,
                "error_details": {
                    "error_type": "execution_error",
                    "user_friendly_message": "The query couldn't be executed. This might be due to permissions, data availability, or syntax issues.",
                    "technical_details": str(e)
                }
            }
            
            # Add specific handling for common BigQuery errors
            error_str = str(e).lower()
            if "permission" in error_str or "access denied" in error_str:
                error_response["error_details"]["error_type"] = "permission_error"
                error_response["error_details"]["user_friendly_message"] = "You don't have permission to access this data. Please contact your administrator."
            elif "not found" in error_str:
                error_response["error_details"]["error_type"] = "data_not_found"
                error_response["error_details"]["user_friendly_message"] = "The requested table or dataset was not found. Please check the names."
            elif "timeout" in error_str:
                error_response["error_details"]["error_type"] = "timeout"
                error_response["error_details"]["user_friendly_message"] = "The query took too long to execute. Try adding filters to reduce the data processed."
            
            return error_response
    
    def generate_and_execute(self, query: str) -> Dict[str, Any]:
        """Generate SQL from natural language and execute it."""
        # Add detailed logging for revenue queries
        if 'revenue' in query.lower():
            logger.warning(f"REVENUE QUERY DETECTED: {query}")
        
        # Generate SQL
        generation_result = self.generate_sql(query)
        
        if generation_result.get("error") or not generation_result.get("sql"):
            return generation_result
        
        # Log the SQL that will be executed
        logger.info(f"SQL to be executed: {generation_result['sql'][:500]}")
        
        # Extra logging for revenue queries
        if 'revenue' in query.lower():
            if 'GL_Amount_in_CC > 0' in generation_result.get('sql', ''):
                logger.error(f"INCORRECT SQL PATTERN DETECTED IN REVENUE QUERY!")
                logger.error(f"SQL: {generation_result['sql'][:200]}")
            elif 'Gross_Revenue' in generation_result.get('sql', ''):
                logger.warning(f"CORRECT: Revenue query using Gross_Revenue")
        
        # Execute the generated SQL
        execution_result = self.execute_query(generation_result["sql"])
        
        # Log execution details
        if execution_result.get("results"):
            logger.info(f"Execution returned {execution_result.get('row_count', 0)} rows")
            if execution_result["results"] and len(execution_result["results"]) > 0:
                logger.info(f"First row: {execution_result['results'][0]}")
        
        # Combine results
        return {
            **generation_result,
            "execution": execution_result
        }
    
    def optimize_query(self, sql: str) -> Dict[str, Any]:
        """Optimize an existing SQL query using the QueryOptimizer."""
        try:
            return self.optimizer.optimize_query(sql)
        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            return {
                "error": str(e),
                "optimized_sql": None
            }
    
    def _enhance_schemas_with_industry_info(self, schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance table schemas with industry-specific information."""
        if not self.industry_manager.active_config:
            return schemas
        
        enhanced_schemas = []
        table_mappings = {}
        
        # Build mapping of technical names to business info
        for domain in self.industry_manager.active_config.domains:
            for mapping in domain.table_mappings:
                table_mappings[mapping.technical_name.lower()] = mapping
        
        # Enhance each schema
        for schema in schemas:
            enhanced = schema.copy()
            table_name = schema.get("table_name", "").lower()
            
            if table_name in table_mappings:
                mapping = table_mappings[table_name]
                enhanced["business_name"] = mapping.business_name
                enhanced["business_description"] = mapping.description
                enhanced["key_columns"] = mapping.key_columns
                enhanced["common_filters"] = mapping.common_filters
                
            
            enhanced_schemas.append(enhanced)
        
        return enhanced_schemas
    
    def _get_financial_schemas(self, financial_context: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Get relevant schemas for financial queries based on hierarchy level."""
        try:
            # Determine which tables to look for based on hierarchy level
            target_tables = []
            
            # Common GL transaction tables
            gl_tables = ["gl_transactions", "general_ledger", "gl_entries", "journal_entries"]
            
            # For any financial query, we typically need GL transaction data
            target_tables.extend(gl_tables)
            
            # For L1/L2 queries, might also need summary tables
            if financial_context.get("hierarchy_level") in [1, 2]:
                summary_tables = ["gl_summary", "financial_summary", "profit_loss", "income_statement"]
                target_tables.extend(summary_tables)
            
            # For dimension-based queries, add dimension tables
            if financial_context.get("dimensions"):
                for dimension in financial_context["dimensions"]:
                    if dimension == "region":
                        target_tables.extend(["regions", "locations", "geography"])
                    elif dimension == "product":
                        target_tables.extend(["products", "items", "product_master"])
                    elif dimension == "customer":
                        target_tables.extend(["customers", "clients", "customer_master"])
            
            # Get all schemas and filter for financial tables
            all_schemas = self.bq_client.get_dataset_schema()
            financial_schemas = []
            
            for schema in all_schemas:
                table_name = schema.get("table_name", "").lower()
                
                # Check if it's a financial table
                if any(target in table_name for target in target_tables):
                    financial_schemas.append(schema)
                    
                # Also check column names for GL-related fields
                elif any(col["name"].lower() in ["gl_account", "account_number", "gl_code"] 
                        for col in schema.get("columns", [])):
                    financial_schemas.append(schema)
                
                if len(financial_schemas) >= limit:
                    break
            
            # If no financial tables found, try to find tables with amount/revenue columns
            if not financial_schemas:
                for schema in all_schemas[:limit]:
                    if any(col["name"].lower() in ["amount", "revenue", "cost", "expense", "debit", "credit"]
                          for col in schema.get("columns", [])):
                        financial_schemas.append(schema)
            
            logger.info(f"Found {len(financial_schemas)} financial schemas for hierarchy level {financial_context.get('hierarchy_level')}")
            
            return financial_schemas[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get financial schemas: {e}")
            return []
    
    def close(self):
        """Close all connections and clean up resources."""
        try:
            if self.knowledge_graph:
                self.knowledge_graph.close()
                logger.info("Closed knowledge graph connection")
        except Exception as e:
            logger.warning(f"Error closing knowledge graph: {e}")
        
        try:
            if self.cache_manager:
                self.cache_manager.close()
                logger.info("Closed cache manager")
        except Exception as e:
            logger.warning(f"Error closing cache manager: {e}")
        
        try:
            if self.vector_client:
                # WeaviateClient might not have a close method
                pass
        except Exception as e:
            logger.warning(f"Error closing vector client: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()