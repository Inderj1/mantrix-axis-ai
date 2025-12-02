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
from src.core.cross_database_validator import CrossDatabaseValidator
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
from src.db.connector_factory import ConnectorFactory
from src.db.weaviate_client import WeaviateClient
from src.config import settings

logger = structlog.get_logger()


class SQLGenerator:
    def __init__(
        self,
        database_type: str = None,
        database_config: Optional[Dict[str, Any]] = None,
        organization_id: str = None
    ):
        """Initialize SQL Generator with multi-database support.

        Args:
            database_type: Type of database ('bigquery', 'snowflake', 'postgresql', 'redshift', 'databricks')
                          If None, auto-detects from organization's enabled connectors
            database_config: Database-specific configuration (optional)
            organization_id: Organization ID for multi-tenancy
        """
        self.organization_id = organization_id or getattr(settings, 'default_org_id', 'default')
        # Store connector IDs for Weaviate filtering
        self.connector_ids = []

        # Auto-detect database type if not specified
        if database_type is None:
            database_type = self._detect_database_type()

        # Store database type and config
        self.database_type = database_type
        self.database_config = database_config or {}

        # Validate database type against supported types
        from src.db.connector_factory import ConnectorFactory
        supported_types = ConnectorFactory.get_supported_types()
        if database_type not in supported_types:
            raise ValueError(
                f"Unsupported database type: {database_type}. "
                f"Supported types: {', '.join(supported_types)}"
            )

        logger.info(f"Initializing SQL Generator for database type: {database_type}")

        # Initialize LLM and vector clients
        self.llm_client = LLMClient()
        self.vector_client = WeaviateClient()
        self.optimizer = QueryOptimizer()
        self.suggestion_service = QuerySuggestionService()

        # Create database client using connector factory
        if database_config:
            # Use provided configuration
            db_config = database_config
        else:
            # Try to load organization's enabled connector from MongoDB
            logger.info(f"Looking up {database_type} connector for organization: {self.organization_id}")
            db_config = self._load_org_connector_config(self.organization_id, database_type)
            if not db_config:
                # No fallback - raise error if no connector configured
                error_msg = (
                    f"No enabled {database_type} connector found for organization '{self.organization_id}'. "
                    f"Please configure a {database_type} connector in the Database Configuration page."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

        # IMPORTANT: Update self.database_config with the loaded config
        # This ensures LLM gets the correct project/dataset
        self.database_config = db_config
        logger.info(f"Database config set: project={db_config.get('project_id')}, dataset={db_config.get('dataset_id')}")

        # Create connector via factory
        self.db_client = ConnectorFactory.create_connector(
            connector_type=database_type,
            config=db_config
        )

        # Connect to the database
        self.db_client.connect()

        # Get database capabilities for dialect-specific handling
        self.db_capabilities = self.db_client.get_capabilities()
        logger.info(f"Database client initialized: {self.db_capabilities.database_name}")

        # Keep bq_client reference for backward compatibility (will be removed in later tasks)
        self.bq_client = self.db_client

        # Load ALL enabled connector IDs for Weaviate filtering
        # This ensures schemas from all enabled connectors are searchable
        self._refresh_connector_ids()

        # Log initialization summary (helpful for debugging multi-connector scenarios)
        logger.info(
            "SQLGenerator initialized",
            organization_id=self.organization_id,
            primary_database_type=self.database_type,
            connector_ids_count=len(self.connector_ids),
            is_bigquery=(self.database_type == 'bigquery')
        )

        # Initialize cross-database validator
        self.cross_db_validator = CrossDatabaseValidator(organization_id=self.organization_id)

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

        # Initialize format normalizer (requires db_client and cache_manager)
        try:
            self.format_normalizer = FormatNormalizer(
                db_client=self.db_client,
                cache_manager=self.cache_manager,
                database_qualifier=self._get_database_qualifier(),
                schema_qualifier=self._get_schema_qualifier()
            )
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
                # Pass organization and database context to query resolver
                from src.core.knowledge_graph.jena_query_resolver import JenaQueryResolver
                self.kg_query_resolver = JenaQueryResolver(
                    graph_client=self.knowledge_graph,
                    organization_id=self.organization_id,
                    database_type=self.database_type
                )
                # Note: GraphTraversalEngine might need updating for Jena
                # self.kg_traversal = GraphTraversalEngine(self.knowledge_graph)
                logger.info("Jena/RDF knowledge graph components initialized (Redis-cached, org-aware)")
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
                    db_client=self.db_client,
                    cache_manager=self.cache_manager,
                    database_qualifier=self._get_database_qualifier(),
                    schema_qualifier=self._get_schema_qualifier()
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

    def _detect_database_type(self) -> str:
        """
        Auto-detect database type from organization's enabled connectors.

        Looks up MongoDB to find what connector types are enabled for this org.

        Returns:
            Database type string (e.g., 'bigquery', 'snowflake')

        Raises:
            ValueError: If no enabled connectors found for the organization
        """
        try:
            from pymongo import MongoClient

            mongo_client = MongoClient(settings.mongodb_url)
            db = mongo_client[settings.mongodb_database]
            collection = db["database_connectors"]

            # Find first enabled connector for this organization
            connector = collection.find_one({
                "organization_id": self.organization_id,
                "enabled_for_chat": True,
                "status": {"$in": ["connected", "active"]}
            })

            if connector:
                db_type = connector.get("connector_type")
                logger.info(
                    f"Auto-detected database type '{db_type}' for organization '{self.organization_id}' "
                    f"(connector: {connector.get('name')})"
                )
                return db_type

            # No connector found - raise clear error
            error_msg = (
                f"No enabled database connector found for organization '{self.organization_id}'. "
                f"Please configure and enable a database connector in the Database Configuration page."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        except ValueError:
            raise  # Re-raise ValueError as-is
        except Exception as e:
            logger.error(f"Error detecting database type: {e}")
            raise ValueError(f"Failed to detect database type for organization '{self.organization_id}': {e}")

    def _load_org_connector_config(self, organization_id: str, database_type: str) -> Optional[Dict[str, Any]]:
        """
        Load connector config for an organization from MongoDB.

        Args:
            organization_id: Organization ID to look up
            database_type: Type of database connector

        Returns:
            Config dict with OAuth credentials if applicable, or None if not found
        """
        try:
            from pymongo import MongoClient
            from src.config import settings

            # Connect to MongoDB synchronously (we're in __init__)
            mongo_client = MongoClient(settings.mongodb_url)
            db = mongo_client[settings.mongodb_database]
            collection = db["database_connectors"]

            logger.info(f"Looking up {database_type} connector for organization: {organization_id}")

            # Find enabled connector for this org and database type
            connector = collection.find_one({
                "organization_id": organization_id,
                "connector_type": database_type,
                "enabled_for_chat": True,
                "status": {"$in": ["connected", "active"]}
            })

            if not connector:
                logger.warning(f"No enabled {database_type} connector found for org {organization_id}")
                return None

            # Store connector_id for Weaviate filtering
            connector_id = str(connector.get("_id"))
            if connector_id and connector_id not in self.connector_ids:
                self.connector_ids.append(connector_id)
                logger.info(f"Added connector_id {connector_id} to filter list")

            # Build config from connector
            logger.info(f"Found connector: id={connector_id}, name={connector.get('name')}, org={connector.get('organization_id')}, "
                       f"auth_method={connector.get('config', {}).get('auth_method')}, "
                       f"has_oauth_credentials={bool(connector.get('oauth_credentials'))}")
            config = connector.get("config", {}).copy()

            # For OAuth connectors, decrypt credentials
            # Note: Token refresh happens automatically in BigQuery client via google-auth
            if config.get("auth_method") == "oauth" and connector.get("oauth_credentials"):
                try:
                    from src.core.google_oauth_service import get_google_oauth_service
                    oauth_service = get_google_oauth_service()
                    decrypted_creds = oauth_service.decrypt_tokens(connector["oauth_credentials"])
                    config["oauth_credentials"] = decrypted_creds
                    logger.info(f"Loaded OAuth config for {database_type} connector in org {organization_id}")
                except Exception as e:
                    logger.error(f"Failed to decrypt OAuth credentials: {e}")
                    return None
            else:
                logger.info(f"Loaded {config.get('auth_method', 'default')} config for {database_type} connector in org {organization_id}")

            logger.info(f"Returning config with keys: {list(config.keys())}")
            return config

        except Exception as e:
            logger.error(f"Error loading connector config for org {organization_id}: {e}")
            return None

    def _refresh_connector_ids(self) -> List[str]:
        """
        Refresh the list of enabled connector IDs for this organization.

        This loads ALL enabled connectors across ALL database types to enable
        multi-connector semantic search. The connector_ids filter in Weaviate
        maintains security by only returning tables from enabled connectors.

        Returns:
            List of enabled connector IDs
        """
        try:
            from pymongo import MongoClient

            mongo_client = MongoClient(settings.mongodb_url)
            db = mongo_client[settings.mongodb_database]
            collection = db["database_connectors"]

            # Find ALL enabled connectors for this organization (across ALL database types)
            # This enables multi-connector semantic search while connector_ids filter
            # maintains security isolation
            connectors = collection.find({
                "organization_id": self.organization_id,
                # REMOVED: "connector_type": self.database_type - load ALL types
                "enabled_for_chat": True,
                "status": {"$in": ["connected", "active"]}
            })

            # Update connector_ids list and build connector_id → database_type mapping
            self.connector_ids = []
            self.connector_db_types: Dict[str, str] = {}
            connector_details = []
            for connector in connectors:
                connector_id = str(connector.get("_id"))
                connector_name = connector.get("connector_name", "unnamed")
                connector_type = connector.get("connector_type", "unknown")
                if connector_id:
                    self.connector_ids.append(connector_id)
                    self.connector_db_types[connector_id] = connector_type
                    connector_details.append(f"{connector_name}({connector_type})")

            # Comprehensive logging for multi-connector debugging
            unique_db_types = list(set(self.connector_db_types.values()))
            logger.info(
                "Connector refresh completed",
                organization_id=self.organization_id,
                connector_count=len(self.connector_ids),
                connector_ids=self.connector_ids,
                database_types=unique_db_types,
                connector_details=connector_details,
                is_multi_database=(len(unique_db_types) > 1),
                includes_bigquery=('bigquery' in unique_db_types),
                includes_snowflake=('snowflake' in unique_db_types)
            )

            return self.connector_ids

        except Exception as e:
            logger.warning(f"Failed to refresh connector_ids: {e}")
            return self.connector_ids  # Return existing list on error

    def _determine_target_database(
        self,
        tables_used: List[str],
        schemas: List[Dict[str, Any]]
    ) -> str:
        """
        Determine which database the query targets based on tables used.

        When multi-connector search is enabled, the LLM may generate SQL using
        tables from different databases. This method detects which database
        the query actually targets for proper execution routing.

        Args:
            tables_used: List of table names from the generated SQL
            schemas: List of schema dictionaries from vector search (each has database_type)

        Returns:
            Database type string ('bigquery', 'snowflake', 'federated', etc.)

        Raises:
            ValueError: If query uses tables from multiple databases without federation
        """
        db_types_used = set()

        for table in tables_used:
            for schema in schemas:
                if schema.get('table_name') == table:
                    db_types_used.add(schema.get('database_type', self.database_type))
                    break

        if len(db_types_used) == 0:
            # No tables matched - use default database type
            return self.database_type

        if len(db_types_used) == 1:
            # All tables from same database - use that database
            return list(db_types_used)[0]

        # Cross-database query detected
        logger.warning(f"Cross-database query detected: {db_types_used}")

        # Use existing CrossDatabaseValidator for detailed analysis
        if hasattr(self, 'cross_db_validator') and self.cross_db_validator:
            table_db_map = {s['table_name']: s.get('database_type') for s in schemas}
            validation = self.cross_db_validator.validate_query(
                query="",  # We don't have SQL here yet, just table info
                selected_databases=list(db_types_used),
                table_database_map=table_db_map
            )
            if validation.can_execute_federated:
                logger.info("Cross-database query can be executed federally")
                return 'federated'

        # Can't execute cross-database query
        raise ValueError(
            f"Query uses tables from multiple databases ({', '.join(sorted(db_types_used))}). "
            "Please ask about tables from a single database, or explicitly request cross-database federation."
        )

    def _get_connector_for_database(self, db_type: str):
        """
        Get or create a database connector for a specific database type.

        This enables dynamic connector selection when the target database
        differs from the initially configured database (multi-connector scenarios).

        Args:
            db_type: Database type ('bigquery', 'snowflake', 'postgresql', etc.)

        Returns:
            Database connector instance

        Raises:
            ValueError: If no enabled connector found for the database type
        """
        # If target matches current connector, use it
        if db_type == self.database_type and self.db_client:
            return self.db_client

        # Check connector pool
        if not hasattr(self, '_connector_pool'):
            self._connector_pool = {}

        if db_type in self._connector_pool:
            return self._connector_pool[db_type]

        # Load connector config for this database type
        db_config = self._load_org_connector_config(self.organization_id, db_type)
        if not db_config:
            raise ValueError(
                f"No enabled {db_type} connector for organization '{self.organization_id}'. "
                f"Please configure a {db_type} connector in the Database Configuration page."
            )

        # Create and connect
        connector = ConnectorFactory.create_connector(db_type, config=db_config)
        connector.connect()
        self._connector_pool[db_type] = connector

        logger.info(f"Created dynamic connector for {db_type}")
        return connector

    def _detect_multi_connector_scenario(self, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect if query requires cross-connector execution.

        Uses connector_id (not database_type) because user might have:
        - Two BigQuery projects (same type, different connectors)
        - Two Snowflake accounts (same type, different connectors)

        Args:
            schemas: List of table schemas from vector search

        Returns:
            Dictionary with multi-connector detection results:
            - is_multi_connector: bool
            - connector_ids: list of connector IDs involved
            - schemas_by_connector: dict mapping connector_id to schemas
            - connector_metadata: dict mapping connector_id to metadata
            - has_different_db_types: bool (True if different SQL dialects needed)
        """
        connector_ids = set(s.get('connector_id') for s in schemas if s.get('connector_id'))

        if len(connector_ids) <= 1:
            return {
                "is_multi_connector": False,
                "connector_ids": list(connector_ids),
                "database_types": list(set(s.get('database_type') for s in schemas if s.get('database_type')))
            }

        # Group schemas by connector_id
        schemas_by_connector = {}
        connector_metadata = {}  # connector_id -> {database_type, project, dataset, ...}

        for schema in schemas:
            conn_id = schema.get('connector_id', 'unknown')
            if conn_id not in schemas_by_connector:
                schemas_by_connector[conn_id] = []
                connector_metadata[conn_id] = {
                    "database_type": schema.get('database_type'),
                    "project": schema.get('project'),
                    "dataset": schema.get('dataset')
                }
            schemas_by_connector[conn_id].append(schema)

        # Check if different database types are involved (affects SQL dialect)
        db_types = set(m['database_type'] for m in connector_metadata.values() if m.get('database_type'))
        has_different_db_types = len(db_types) > 1

        logger.info(
            "Multi-connector scenario detected",
            connector_count=len(connector_ids),
            connector_ids=list(connector_ids),
            database_types=list(db_types),
            has_different_db_types=has_different_db_types
        )

        return {
            "is_multi_connector": True,
            "connector_ids": list(connector_ids),
            "schemas_by_connector": schemas_by_connector,
            "connector_metadata": connector_metadata,
            "has_different_db_types": has_different_db_types
        }

    def _load_connector_config_by_id(self, connector_id: str) -> Optional[Dict[str, Any]]:
        """
        Load connector config by connector_id from MongoDB.

        Args:
            connector_id: MongoDB _id of the connector

        Returns:
            Config dict with database_type and connection settings, or None if not found
        """
        try:
            from pymongo import MongoClient
            from bson import ObjectId

            mongo_client = MongoClient(settings.mongodb_url)
            db = mongo_client[settings.mongodb_database]
            collection = db["database_connectors"]

            # Find connector by ID
            connector = collection.find_one({
                "_id": ObjectId(connector_id),
                "organization_id": self.organization_id,
                "enabled_for_chat": True,
                "status": {"$in": ["connected", "active"]}
            })

            if not connector:
                logger.warning(f"Connector {connector_id} not found or not enabled")
                return None

            # Build config including database_type
            config = connector.get("config", {}).copy()
            config["database_type"] = connector.get("connector_type")
            config["connector_id"] = connector_id
            config["connector_name"] = connector.get("name", "")

            # Handle OAuth credentials if applicable
            if config.get("auth_method") == "oauth" and connector.get("oauth_credentials"):
                try:
                    from src.core.google_oauth_service import get_google_oauth_service
                    oauth_service = get_google_oauth_service()
                    decrypted_creds = oauth_service.decrypt_tokens(connector["oauth_credentials"])
                    config["oauth_credentials"] = decrypted_creds
                except Exception as e:
                    logger.error(f"Failed to decrypt OAuth credentials for connector {connector_id}: {e}")
                    return None

            logger.info(f"Loaded config for connector {connector_id} (type: {config['database_type']})")
            return config

        except Exception as e:
            logger.error(f"Error loading connector config by ID {connector_id}: {e}")
            return None

    async def _execute_cross_connector_query(
        self,
        llm_result: Dict[str, Any],
        connector_metadata: Dict[str, Dict[str, Any]],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute cross-connector query using CrossDatabaseExecutor.

        Takes the LLM-generated connector_queries and join_specification,
        builds an ExecutionPlan, and executes via CrossDatabaseExecutor.

        Args:
            llm_result: Result from LLMClient.generate_cross_connector_sql()
            connector_metadata: Dict mapping connector_id -> {database_type, project, dataset}
            user_id: User ID for permissions

        Returns:
            Dict with results, row_count, connectors_used, etc.
        """
        from src.core.cross_database_executor import get_cross_database_executor
        from src.core.federated_query_planner import (
            ExecutionPlan, ExecutionStrategy, QueryStep, TableReference
        )

        logger.info(
            "Executing cross-connector query",
            connector_count=len(llm_result.get("connector_queries", {})),
            join_type=llm_result.get("join_specification", {}).get("type")
        )

        connector_queries = llm_result.get("connector_queries", {})
        join_spec = llm_result.get("join_specification", {})

        if not connector_queries:
            return {
                "error": "No connector queries provided",
                "is_cross_connector": True,
                "success": False
            }

        # Load configs for each connector
        database_configs = {}
        steps = []
        tables_by_database = {}
        step_num = 1

        for connector_id, query_info in connector_queries.items():
            # Load connector config
            config = self._load_connector_config_by_id(connector_id)
            if not config:
                return {
                    "error": f"Could not load config for connector {connector_id}",
                    "is_cross_connector": True,
                    "success": False
                }

            db_type = config["database_type"]
            database_configs[db_type] = config

            # Build query step
            steps.append(QueryStep(
                step_number=step_num,
                database_type=db_type,
                sql=query_info["sql"],
                description=f"Execute query on {db_type} connector {connector_id}",
                estimated_cost=1.0
            ))

            # Track tables
            if db_type not in tables_by_database:
                tables_by_database[db_type] = []
            for table in query_info.get("tables_used", []):
                tables_by_database[db_type].append(TableReference(
                    database_type=db_type,
                    full_name=table,
                    table=table
                ))

            step_num += 1

        # Determine execution strategy
        if join_spec and join_spec.get("type") in ["INNER", "LEFT", "RIGHT", "FULL"]:
            strategy = ExecutionStrategy.DISTRIBUTED
        elif join_spec and join_spec.get("type") in ["UNION", "UNION_ALL"]:
            strategy = ExecutionStrategy.DISTRIBUTED
        else:
            strategy = ExecutionStrategy.DISTRIBUTED

        # Determine primary database (first one in the list)
        primary_db = list(database_configs.keys())[0]

        # Build execution plan
        plan = ExecutionPlan(
            strategy=strategy,
            primary_database=primary_db,
            databases_involved=list(database_configs.keys()),
            tables_by_database=tables_by_database,
            steps=steps,
            metadata={
                "join_specification": join_spec,
                "connector_queries": connector_queries
            }
        )

        # Execute via CrossDatabaseExecutor
        try:
            executor = get_cross_database_executor()
            # skip_permission_check=True because connector access was already verified
            # (only enabled connectors for this user/org reach this point)
            result = await executor.execute_plan(
                plan=plan,
                user_id=user_id,
                organization_id=self.organization_id,
                database_configs=database_configs,
                skip_permission_check=True
            )

            # Convert DataFrame to dict records
            rows = result.data.to_dict('records') if result.data is not None else []

            return {
                "rows": rows,
                "row_count": result.rows_returned,
                "is_cross_connector": True,
                "success": True,
                "connectors_used": list(connector_queries.keys()),
                "database_types_used": result.databases_accessed,
                "execution_time_seconds": result.execution_time_seconds,
                "warnings": result.warnings,
                "explanation": llm_result.get("explanation", "")
            }

        except Exception as e:
            logger.error(f"Cross-connector execution failed: {e}")
            return {
                "error": str(e),
                "is_cross_connector": True,
                "success": False,
                "connectors_used": list(connector_queries.keys())
            }

    def _get_database_qualifier(self) -> Optional[str]:
        """Get database-level qualifier (project for BigQuery, database for others).

        Returns:
            Database qualifier string or None
        """
        if self.database_type == 'bigquery':
            return getattr(self.db_client, 'project_id', None)
        elif self.database_type in ['snowflake', 'databricks']:
            return getattr(self.db_client, 'database', None)
        elif self.database_type in ['postgresql', 'redshift']:
            return getattr(self.db_client, 'database', None)
        return None

    def _get_schema_qualifier(self) -> Optional[str]:
        """Get schema/dataset qualifier.

        Returns:
            Schema qualifier string or None
        """
        if self.database_type == 'bigquery':
            return getattr(self.db_client, 'dataset_id', None)
        else:
            return getattr(self.db_client, 'schema', None)

    def _get_full_qualifier(self) -> str:
        """Get full database qualifier for cache keys and logging.

        Returns:
            Formatted qualifier (e.g., 'project:dataset' for BigQuery, 'database:schema' for others)
        """
        db_qual = self._get_database_qualifier()
        schema_qual = self._get_schema_qualifier()

        if db_qual and schema_qual:
            return f"{db_qual}:{schema_qual}"
        elif schema_qual:
            return schema_qual
        elif db_qual:
            return db_qual
        return "default"

    def _get_dialect_guide(self) -> str:
        """Get database-specific SQL syntax guidelines for LLM.

        Returns:
            String containing SQL dialect-specific guidelines
        """
        guides = {
            'bigquery': """
**BigQuery SQL Dialect:**
- Use backticks for identifiers: `project.dataset.table`
- Date formatting: FORMAT_DATE('%Y-%m-%d', date_column)
- String concatenation: CONCAT(str1, str2) or ||
- Current timestamp: CURRENT_TIMESTAMP()
- Date arithmetic: DATE_ADD(date, INTERVAL 1 DAY)
- Window functions: Use OVER (PARTITION BY ... ORDER BY ...)
- Arrays: ARRAY_AGG(), UNNEST()
- Structs: STRUCT(field1, field2)
- Supports standard SQL with extensions
            """,
            'snowflake': """
**Snowflake SQL Dialect:**
- Three-part names: database.schema.table (no backticks needed)
- Date formatting: TO_CHAR(date_column, 'YYYY-MM-DD')
- String concatenation: CONCAT(str1, str2) or ||
- Current timestamp: CURRENT_TIMESTAMP() or SYSDATE()
- Date arithmetic: DATEADD(DAY, 1, date)
- Window functions: Use OVER (PARTITION BY ... ORDER BY ...)
- Semi-structured data: VARIANT type with : accessor
- JSON: PARSE_JSON(), object:field syntax
- Case-insensitive by default (identifiers are uppercase unless quoted)
            """,
            'postgresql': """
**PostgreSQL SQL Dialect:**
- Schema-qualified names: schema.table (or just table if in search_path)
- Date formatting: TO_CHAR(date_column, 'YYYY-MM-DD')
- String concatenation: CONCAT(str1, str2) or ||
- Current timestamp: CURRENT_TIMESTAMP or NOW()
- Date arithmetic: date + INTERVAL '1 day'
- Window functions: Use OVER (PARTITION BY ... ORDER BY ...)
- Case-insensitive search: ILIKE operator
- JSON: jsonb type with -> and ->> operators
- Supports CTEs, window functions, recursive queries
            """,
            'redshift': """
**Amazon Redshift SQL Dialect:**
- Similar to PostgreSQL but with some limitations
- Schema-qualified names: schema.table
- Date formatting: TO_CHAR(date_column, 'YYYY-MM-DD')
- String concatenation: || or CONCAT
- No recursive CTEs
- Limited window function support compared to PostgreSQL
- SUPER type for semi-structured data (JSON-like)
- DISTKEY and SORTKEY for optimization (optional in queries)
            """,
            'databricks': """
**Databricks SQL Dialect (Spark SQL):**
- Three-part names: catalog.schema.table
- Date formatting: DATE_FORMAT(date_column, 'yyyy-MM-dd')
- String concatenation: CONCAT(str1, str2) or ||
- Current timestamp: CURRENT_TIMESTAMP() or NOW()
- Date arithmetic: DATE_ADD(date, 1)
- Window functions: Use OVER (PARTITION BY ... ORDER BY ...)
- Delta Lake features: TIME TRAVEL, MERGE, OPTIMIZE
- Java-style date patterns: 'yyyy-MM-dd HH:mm:ss'
- Supports Spark SQL with Delta Lake extensions
            """
        }
        return guides.get(self.database_type, "")

    def _index_schemas(self):
        """Index all table schemas in the vector database."""
        try:
            logger.info(f"Indexing {self.db_capabilities.database_name} table schemas...")
            schemas = self.db_client.get_dataset_schema()

            for schema in schemas:
                # Cache schema if caching is enabled
                if self.cache_manager and settings.cache_schema_enabled:
                    self.cache_manager.cache_schema(
                        self._get_database_qualifier(),
                        self._get_schema_qualifier(),
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
        conversation_context: Optional[Dict[str, Any]] = None,
        persona_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate SQL from natural language query.

        Args:
            query: Natural language query
            use_vector_search: Whether to use vector search for table selection
            max_tables: Maximum number of tables to consider
            auto_optimize: Whether to apply query optimization
            force_refresh: Force cache refresh
            conversation_context: Context from previous conversation messages
            persona_context: User persona context from user profile (role, prompt additions)

        Raises:
            ValueError: If no connector is configured for the organization
        """
        # CRITICAL: Require connector configuration - no hardcoded fallback
        if not self.connector_ids:
            raise ValueError(
                "No database connector configured. Please configure a connector in Database Settings "
                "and enable it for chat queries."
            )

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

                            # Pass organization and database context to JoinPathFinder
                            finder = JoinPathFinder(
                                self.knowledge_graph,
                                organization_id=self.organization_id,
                                database_type=self.database_type
                            )
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
                
                # Final fallback: get all schemas from current connector
                if not relevant_schemas:
                    try:
                        all_schemas = self.db_client.get_dataset_schema()
                        relevant_schemas = all_schemas[:max_tables]
                    except Exception as e:
                        logger.warning(f"Fallback schema fetch failed: {e}")
                        relevant_schemas = []
            
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

            # ============================================================
            # MULTI-CONNECTOR DETECTION
            # Check if query involves multiple connectors BEFORE LLM call
            # ============================================================
            multi_conn_info = self._detect_multi_connector_scenario(relevant_schemas)

            if multi_conn_info["is_multi_connector"]:
                logger.info(
                    "Multi-connector query detected - using cross-connector LLM flow",
                    connector_ids=multi_conn_info["connector_ids"],
                    has_different_db_types=multi_conn_info["has_different_db_types"]
                )

                # Use cross-connector LLM method instead of standard generate_sql
                cross_conn_result = self.llm_client.generate_cross_connector_sql(
                    user_query=processed_query,
                    schemas_by_connector=multi_conn_info["schemas_by_connector"],
                    connector_metadata=multi_conn_info["connector_metadata"],
                    financial_context=financial_context,
                    business_context=enhanced_context,
                    conversation_context=conversation_context
                )

                # Mark result for downstream cross-connector handling
                cross_conn_result["_multi_connector_info"] = multi_conn_info
                cross_conn_result["from_cache"] = False

                # If LLM decided single connector is sufficient, continue with normal flow
                if not cross_conn_result.get("requires_cross_connector"):
                    single_connector_id = cross_conn_result.get("single_connector_id")
                    logger.info(
                        f"LLM determined single connector sufficient: {single_connector_id}"
                    )
                    # Filter schemas to just the single connector and continue normal flow
                    if single_connector_id:
                        relevant_schemas = [
                            s for s in relevant_schemas
                            if s.get("connector_id") == single_connector_id
                        ]
                        # Update database config for the selected connector
                        selected_meta = multi_conn_info["connector_metadata"].get(single_connector_id, {})
                        if selected_meta.get("database_type"):
                            self.database_type = selected_meta["database_type"]
                            # FIX: Also update database_config with connector's location info
                            # This ensures the LLM prompt uses correct table qualification
                            self.database_config = {
                                "database_type": selected_meta["database_type"],
                                "project_id": selected_meta.get("project", selected_meta.get("database", "")),
                                "dataset_id": selected_meta.get("dataset", selected_meta.get("schema", "")),
                            }
                            logger.info(
                                f"Updated database_config for {single_connector_id}",
                                database_type=self.database_type,
                                project_id=self.database_config.get("project_id"),
                                dataset_id=self.database_config.get("dataset_id")
                            )
                else:
                    # Multi-connector query - return result for cross-connector execution
                    logger.info(
                        "Returning cross-connector result for execution",
                        connector_queries=list(cross_conn_result.get("connector_queries", {}).keys())
                    )
                    return cross_conn_result

            # ============================================================
            # SINGLE-CONNECTOR FLOW (standard path)
            # ============================================================

            # Prepare kwargs for LLM client
            llm_kwargs = {}

            # Add database dialect information (CRITICAL for multi-database support)
            llm_kwargs["database_type"] = self.database_type
            llm_kwargs["database_name"] = self.db_capabilities.database_name
            llm_kwargs["dialect_guide"] = self._get_dialect_guide()
            # Pass connector's database config so LLM uses correct project/dataset
            llm_kwargs["database_config"] = self.database_config
            logger.info(f"Using database_config for LLM: project={self.database_config.get('project_id')}, dataset={self.database_config.get('dataset_id')}")

            if financial_context:
                llm_kwargs["financial_context"] = financial_context
            if enhanced_context:
                llm_kwargs["business_context"] = enhanced_context
            if join_hints:
                llm_kwargs["join_hints"] = join_hints
            if conversation_context:
                llm_kwargs["conversation_context"] = conversation_context
            if persona_context:
                llm_kwargs["persona_context"] = persona_context

            logger.info(f"Generating SQL for {self.db_capabilities.database_name} (dialect: {self.database_type})")
            
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
                    force_refresh=force_refresh,
                    connector_ids=self.connector_ids if self.connector_ids else None
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

            # Detect target database from tables used in generated SQL (multi-connector support)
            tables_used = result.get("tables_used", [])
            if tables_used and relevant_schemas:
                try:
                    target_db_type = self._determine_target_database(tables_used, relevant_schemas)
                    result["target_database_type"] = target_db_type
                    logger.info(f"Target database determined: {target_db_type}")

                    # If target DB differs from current connector, update LLM kwargs for dialect
                    if target_db_type != self.database_type and target_db_type != 'federated':
                        logger.info(f"Target database ({target_db_type}) differs from primary ({self.database_type})")
                        result["requires_alternate_connector"] = True
                except ValueError as e:
                    # Cross-database query that can't be executed
                    logger.warning(f"Cross-database detection: {e}")
                    result["cross_database_error"] = str(e)
            else:
                # Default to current database type
                result["target_database_type"] = self.database_type

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
            # Use target database connector for validation (multi-connector support)
            # IMPORTANT: Always use the correct connector for the target database type
            # No fallback to avoid validating BigQuery SQL against Snowflake (or vice versa)
            target_db_type = result.get("target_database_type", self.database_type)
            if target_db_type and target_db_type != 'federated':
                validation_connector = self._get_connector_for_database(target_db_type)
                logger.info(f"Using {target_db_type} connector for validation")
            else:
                validation_connector = self.db_client
                logger.info(f"Using default connector for validation (federated or no target type)")

            validation = None
            if self.cache_manager and settings.cache_validation_enabled:
                validation = self.cache_manager.get_validation(result["sql"])

            if validation is None:
                validation = validation_connector.validate_query(result["sql"])
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
                    
                    # Re-validate optimized query (using target database connector)
                    result["validation"] = validation_connector.validate_query(result["sql"])

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

                        # Re-validate normalized query (using target database connector)
                        result["validation"] = validation_connector.validate_query(result["sql"])
                    else:
                        result["format_normalized"] = False
                except Exception as e:
                    logger.warning(f"Format normalization failed: {e}. Using original query.")
                    result["format_normalized"] = False

            # Add industry context to result
            if settings.enable_industry_features:
                result["industry"] = settings.industry
                result["industry_terms_translated"] = processed_query != query
            
            # Add query suggestions (context-aware, including error-specific suggestions)
            execution_error = result.get("execution", {}).get("error") or result.get("error")
            improvements = self.suggestion_service.suggest_query_improvements(
                query,
                result.get("sql", ""),
                result.get("execution", {}).get("performance_stats"),
                execution_error=execution_error  # Pass error for context-aware suggestions
            )
            if improvements:
                result["suggestions"] = improvements

            # SMART CACHING: Cache after validation and test execution (if not from cache)
            if (
                self.cache_manager
                and settings.cache_sql_enabled
                and not result.get("from_cache", False)
                and not force_refresh
            ):
                try:
                    # Get validation status
                    validation_status = result.get("validation", {}).get("valid", False)
                    error_details = result.get("validation", {}).get("error") if not validation_status else None

                    # Test execution if required and query is valid
                    execution_time_ms = 0
                    row_count = 0

                    if settings.cache_execution_test_required and validation_status and result.get("sql"):
                        try:
                            # Quick test execution with LIMIT 1 for performance
                            import time
                            test_sql = result["sql"]

                            # Add LIMIT 1 if not already limited for testing
                            if "LIMIT" not in test_sql.upper():
                                test_sql += " LIMIT 1"

                            start_time = time.time()
                            # Use target database connector for test execution (multi-connector support)
                            test_results = validation_connector.execute_query(test_sql)
                            execution_time_ms = (time.time() - start_time) * 1000
                            row_count = len(test_results) if test_results else 0

                            logger.debug(f"Test execution: {execution_time_ms:.0f}ms, {row_count} rows")

                        except Exception as exec_error:
                            # Test execution failed
                            error_details = str(exec_error)
                            validation_status = False
                            logger.warning(f"Test execution failed: {error_details[:100]}...")

                    # Get confidence score from result (if available)
                    confidence_score = result.get("confidence_score")

                    # Generate cache key
                    normalized_query = query.strip().lower()
                    normalized_query = " ".join(normalized_query.split())

                    table_names = sorted(result.get("tables_used", []))
                    import hashlib
                    query_hash = hashlib.sha256(normalized_query.encode()).hexdigest()
                    table_hash = hashlib.sha256(",".join(table_names).encode()).hexdigest()
                    cache_key = f"sql:{query_hash}:{table_hash}"

                    # Attempt to cache with quality gates
                    cached = self.cache_manager.cache_validated_sql(
                        key=cache_key,
                        result=result,
                        query=normalized_query,
                        execution_time_ms=execution_time_ms,
                        row_count=row_count,
                        validation_status=validation_status,
                        error_details=error_details,
                        confidence_score=confidence_score
                    )

                    if not cached:
                        logger.info(f"Query not cached - failed quality gates")
                    else:
                        logger.debug(f"Query cached with smart caching v2.0")

                except Exception as cache_error:
                    logger.error(f"Smart caching failed: {cache_error}")

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
        """
        Check if vector DB needs reindexing based on cache expiration.

        DISABLED: This was causing 30+ second delays on every query by fetching
        all schemas from the database. Schema indexing should only happen:
        1. When user clicks "Sync" in the Database Connectors UI
        2. During the scheduled pipeline (daily at 2am)

        The vector DB (Weaviate) persists schemas, so they don't need to be
        re-indexed on every query.
        """
        # Skip reindex check during query time - rely on manual sync or scheduled pipeline
        logger.debug("Skipping reindex check during query (use manual sync or pipeline)")
        return

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

            # Note: connector_ids refresh is now handled by sql_generator_singleton module
            # which invalidates this instance when connectors change

            # Check Weaviate search cache first
            if self.cache_manager and settings.cache_weaviate_enabled:
                cached_results = self.cache_manager.get_weaviate_search(
                    query_embedding,
                    self.organization_id,
                    self.connector_ids,
                    adjusted_limit
                )
                if cached_results:
                    logger.info(
                        "Weaviate cache HIT",
                        tables_found=len(cached_results),
                        organization_id=self.organization_id
                    )
                    # Apply table selection logic to cached results
                    return self._select_tables_by_relevance(cached_results, query, limit)

            # Search for similar tables with adjusted limit, filtered by organization and connector
            # NOTE: database_type filter REMOVED to enable multi-connector semantic search
            # The connector_ids filter maintains security by only returning tables from enabled connectors
            # Each returned table has its database_type property for target DB detection
            logger.info(
                "Starting multi-connector vector search",
                organization_id=self.organization_id,
                primary_database_type=self.database_type,
                connector_ids=self.connector_ids,
                connector_db_types=getattr(self, 'connector_db_types', {}),
                adjusted_limit=adjusted_limit,
                is_bigquery=(self.database_type == 'bigquery')
            )

            # Use per-connector search when multiple connectors are enabled
            # This ensures results from ALL databases are represented, not just the one
            # with the highest semantic similarity
            if len(self.connector_ids) > 1:
                similar_tables = self._per_connector_vector_search(
                    query_embedding=query_embedding,
                    total_limit=adjusted_limit,
                    organization_id=self.organization_id
                )
            else:
                # Single connector - use original search
                similar_tables = self.vector_client.search_similar_tables(
                    query_embedding,
                    limit=adjusted_limit,
                    organization_id=self.organization_id,
                    connector_ids=self.connector_ids if self.connector_ids else None
                )

            # Cache the Weaviate search results
            if self.cache_manager and settings.cache_weaviate_enabled and similar_tables:
                self.cache_manager.cache_weaviate_search(
                    query_embedding,
                    self.organization_id,
                    self.connector_ids,
                    adjusted_limit,
                    similar_tables
                )

            # Log which databases the results came from
            if similar_tables:
                db_types_found = set(t.get('database_type', 'unknown') for t in similar_tables)
                table_names = [t.get('table_name', 'unknown') for t in similar_tables[:5]]
                logger.info(
                    "Vector search completed",
                    organization_id=self.organization_id,
                    tables_found=len(similar_tables),
                    database_types_found=list(db_types_found),
                    sample_tables=table_names,
                    is_bigquery=(self.database_type == 'bigquery')
                )

            # Analyze if multiple tables are needed based on similarity scores
            tables_to_return = self._select_tables_by_relevance(similar_tables, query, limit)
            
            return tables_to_return
        except Exception as e:
            logger.warning(f"Vector search failed, falling back to all tables: {e}")
            # Fallback to getting all schemas
            return self.bq_client.get_dataset_schema()[:limit]

    def _per_connector_vector_search(
        self,
        query_embedding: List[float],
        total_limit: int,
        organization_id: str
    ) -> List[Dict[str, Any]]:
        """
        Perform vector search separately for each connector, then merge results.

        This ensures that results from ALL enabled databases are represented,
        even if one database has higher semantic similarity scores overall.

        Args:
            query_embedding: The query vector embedding
            total_limit: Total number of results to return
            organization_id: Organization ID for filtering

        Returns:
            Merged and deduplicated list of table schemas from all connectors
        """
        all_tables = []
        connector_count = len(self.connector_ids)

        # Calculate per-connector limit - ensure at least 3 results per connector
        # to have meaningful representation from each database
        per_connector_limit = max(3, total_limit // connector_count)

        logger.info(
            "Starting per-connector vector search",
            connector_count=connector_count,
            per_connector_limit=per_connector_limit,
            total_limit=total_limit,
            organization_id=organization_id
        )

        # Search each connector separately
        for connector_id in self.connector_ids:
            db_type = self.connector_db_types.get(connector_id, 'unknown')
            try:
                connector_results = self.vector_client.search_similar_tables(
                    query_embedding,
                    limit=per_connector_limit,
                    connector_id=connector_id,  # Single connector search
                    organization_id=organization_id
                )

                tables_found = len(connector_results) if connector_results else 0
                logger.info(
                    f"Per-connector search completed for {db_type}",
                    connector_id=connector_id,
                    database_type=db_type,
                    tables_found=tables_found,
                    sample_tables=[t.get('table_name') for t in (connector_results or [])[:3]]
                )

                if connector_results:
                    all_tables.extend(connector_results)

            except Exception as e:
                logger.warning(
                    f"Vector search failed for connector {connector_id}: {e}",
                    connector_id=connector_id,
                    database_type=db_type
                )

        # Deduplicate by (table_name, connector_id) - same table from same connector
        seen = set()
        deduplicated = []
        for table in all_tables:
            key = (table.get('table_name'), table.get('connector_id'))
            if key not in seen:
                seen.add(key)
                deduplicated.append(table)

        # Sort by distance (similarity) - lower distance = more similar
        deduplicated.sort(key=lambda t: t.get('distance', float('inf')))

        # Cap to total_limit
        final_results = deduplicated[:total_limit]

        # Log summary
        db_types_found = list(set(t.get('database_type', 'unknown') for t in final_results))
        logger.info(
            "Per-connector search completed",
            total_tables_found=len(final_results),
            database_types_found=db_types_found,
            all_connectors_represented=(len(db_types_found) >= connector_count),
            sample_tables=[t.get('table_name') for t in final_results[:5]]
        )

        return final_results

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
    
    def execute_query(self, sql: str, target_database_type: str = None) -> Dict[str, Any]:
        """Execute SQL query and return results.

        Args:
            sql: The SQL query to execute
            target_database_type: Optional database type to execute on. If not provided,
                                  uses the primary connector (self.db_client)
        """
        try:
            # Log query execution context (helpful for debugging non-BigQuery scenarios)
            logger.info(
                "Executing query",
                organization_id=self.organization_id,
                primary_database_type=self.database_type,
                target_database_type=target_database_type or self.database_type,
                is_bigquery=(self.database_type == 'bigquery'),
                sql_preview=sql[:100] if sql else None
            )

            # Get the appropriate connector for execution (multi-connector support)
            if target_database_type and target_database_type != self.database_type and target_database_type != 'federated':
                try:
                    db_connector = self._get_connector_for_database(target_database_type)
                    logger.info(
                        "Using dynamic connector for query execution",
                        target_database_type=target_database_type,
                        organization_id=self.organization_id
                    )
                except ValueError as e:
                    logger.warning(f"Could not get connector for {target_database_type}, using default: {e}")
                    db_connector = self.db_client
            else:
                db_connector = self.db_client
                logger.debug(
                    "Using primary connector for query execution",
                    database_type=self.database_type,
                    organization_id=self.organization_id
                )

            # Validate first
            validation = db_connector.validate_query(sql)
            if not validation["valid"]:
                # Try to correct the SQL if validation failed
                if self.llm_client:
                    correction_result = self.llm_client.correct_sql_error(
                        sql,
                        validation['error'],
                        db_connector.get_dataset_schema()[:5]  # Provide some schema context
                    )

                    if correction_result.get("correction_applied") and correction_result.get("sql"):
                        # Try the corrected SQL
                        logger.info("Attempting to execute corrected SQL")
                        sql = correction_result["sql"]
                        validation = db_connector.validate_query(sql)

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
            execution_result = db_connector.execute_query(sql)
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