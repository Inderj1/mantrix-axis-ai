from typing import List, Dict, Any, Optional
import weaviate
import weaviate.classes as wvc
from weaviate.classes.config import Property, DataType
import structlog
from src.config import settings

logger = structlog.get_logger()


class WeaviateClient:
    def __init__(self):
        self.client = None
        self.collection_name = "TableSchemas"
        self.query_collection_name = "OptimizedQuery"  # NEW: For query performance tracking
        try:
            self.client = self._initialize_client()
            self._ensure_collection_exists()
            self._ensure_query_collection_exists()  # NEW: Create query collection
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client during construction: {e}")
            # Don't raise here, let methods handle the None client
    
    def _initialize_client(self) -> weaviate.Client:
        """Initialize Weaviate client."""
        try:
            # Simple connection without gRPC for compatibility
            # Extract host and port from URL
            url_without_protocol = settings.weaviate_url.replace("http://", "").replace("https://", "")
            if ":" in url_without_protocol:
                host, port_str = url_without_protocol.split(":", 1)
                port = int(port_str)
            else:
                host = url_without_protocol
                port = 8080
            
            logger.info(f"Connecting to Weaviate at {host}:{port}")
            
            client = weaviate.connect_to_local(
                host=host,
                port=port,
                grpc_port=50051,
                skip_init_checks=True
            )
            logger.info("Weaviate client initialized")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}")
            raise
    
    def _ensure_collection_exists(self):
        """Create the TableSchemas collection if it doesn't exist or schema is outdated."""
        # Required properties that must exist in the collection
        required_properties = {
            "table_name", "dataset", "project", "description", "columns",
            "row_count", "combined_text", "schema_version", "schema_hash",
            "column_count", "database_type", "organization_id", "connector_id",
            "created_at", "modified_at", "indexed_at", "business_domains",
            "has_relationships", "column_names"
        }

        try:
            if self.client.collections.exists(self.collection_name):
                # Check if schema has all required properties
                try:
                    collection = self.client.collections.get(self.collection_name)
                    config = collection.config.get()
                    existing_properties = {prop.name for prop in config.properties}
                    missing_properties = required_properties - existing_properties

                    if missing_properties:
                        logger.warning(
                            f"Collection {self.collection_name} missing properties: {missing_properties}. Recreating."
                        )
                        self.client.collections.delete(self.collection_name)
                    else:
                        logger.info(f"Collection {self.collection_name} exists with correct schema")
                        return
                except Exception as e:
                    # If there's an issue checking, delete and recreate
                    logger.info(f"Deleting existing collection due to error: {e}")
                    self.client.collections.delete(self.collection_name)
            
            # Get embedding dimension from service
            from src.core.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            vector_dimension = embedding_service.dimension
            
            self.client.collections.create(
                name=self.collection_name,
                properties=[
                    Property(name="table_name", data_type=DataType.TEXT),
                    Property(name="dataset", data_type=DataType.TEXT),
                    Property(name="project", data_type=DataType.TEXT),
                    Property(name="description", data_type=DataType.TEXT),
                    Property(name="columns", data_type=DataType.TEXT),  # JSON string
                    Property(name="row_count", data_type=DataType.INT),
                    Property(name="combined_text", data_type=DataType.TEXT),  # For semantic search
                    Property(name="schema_version", data_type=DataType.INT),
                    Property(name="schema_hash", data_type=DataType.TEXT),
                    Property(name="column_count", data_type=DataType.INT),
                    Property(name="database_type", data_type=DataType.TEXT),
                    Property(name="organization_id", data_type=DataType.TEXT),  # Add organization ID
                    Property(name="connector_id", data_type=DataType.TEXT),  # Connector ID for filtering
                    Property(name="created_at", data_type=DataType.TEXT),
                    Property(name="modified_at", data_type=DataType.TEXT),
                    Property(name="indexed_at", data_type=DataType.TEXT),
                    Property(name="business_domains", data_type=DataType.TEXT),  # JSON string
                    Property(name="has_relationships", data_type=DataType.BOOL),
                    Property(name="column_names", data_type=DataType.TEXT),  # JSON string
                ],
                vectorizer_config=wvc.config.Configure.Vectorizer.none(),
                vector_index_config=wvc.config.Configure.VectorIndex.hnsw(
                    distance_metric=wvc.config.VectorDistances.COSINE,
                    vector_cache_max_objects=100000,
                    quantizer=wvc.config.Configure.VectorIndex.Quantizer.bq()
                )
            )
            logger.info(f"Created collection {self.collection_name} with {vector_dimension}D vectors")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise

    def _ensure_query_collection_exists(self):
        """
        Create the OptimizedQuery collection for query performance tracking.

        This collection stores historical query performance data to enable
        intelligent optimization decisions based on past executions.
        """
        try:
            if self.client.collections.exists(self.query_collection_name):
                logger.info(f"Collection {self.query_collection_name} already exists")
                return

            # Get embedding dimension from service
            from src.core.embeddings import EmbeddingService
            embedding_service = EmbeddingService()
            vector_dimension = embedding_service.dimension

            self.client.collections.create(
                name=self.query_collection_name,
                properties=[
                    # Query identification
                    Property(name="sql_text", data_type=DataType.TEXT),
                    Property(name="query_hash", data_type=DataType.TEXT),  # For deduplication

                    # Performance metrics
                    Property(name="execution_time_ms", data_type=DataType.NUMBER),
                    Property(name="rows_returned", data_type=DataType.INT),
                    Property(name="data_transferred_mb", data_type=DataType.NUMBER),

                    # Strategy information
                    Property(name="strategy_used", data_type=DataType.TEXT),  # STAGING_TABLE, MOVE_TO_PRIMARY, etc.
                    Property(name="pushdown_applied", data_type=DataType.BOOL),
                    Property(name="filters_pushed", data_type=DataType.INT),

                    # Database context
                    Property(name="source_database", data_type=DataType.TEXT),
                    Property(name="target_database", data_type=DataType.TEXT),
                    Property(name="tables_involved", data_type=DataType.TEXT),  # JSON array

                    # JOIN information
                    Property(name="join_type", data_type=DataType.TEXT),  # INNER, LEFT, etc.
                    Property(name="join_columns", data_type=DataType.TEXT),  # JSON object

                    # Outcome
                    Property(name="success", data_type=DataType.BOOL),
                    Property(name="error_message", data_type=DataType.TEXT),

                    # Metadata
                    Property(name="timestamp", data_type=DataType.TEXT),
                    Property(name="user_id", data_type=DataType.TEXT),
                    Property(name="organization_id", data_type=DataType.TEXT),
                ],
                vectorizer_config=wvc.config.Configure.Vectorizer.none(),
                vector_index_config=wvc.config.Configure.VectorIndex.hnsw(
                    distance_metric=wvc.config.VectorDistances.COSINE,
                    vector_cache_max_objects=100000,
                    quantizer=wvc.config.Configure.VectorIndex.Quantizer.bq()
                )
            )

            logger.info(f"Created OptimizedQuery collection with {vector_dimension}D vectors")

        except Exception as e:
            logger.error(f"Failed to create OptimizedQuery collection: {e}")
            # Don't raise - allow system to function without query tracking

    def index_table_schema(self, schema: Dict[str, Any], embedding: List[float]):
        """Index a table schema with its embedding."""
        try:
            # Create combined text for better semantic search
            columns_text = []
            for col in schema["columns"]:
                col_desc = f"{col['name']} ({col['type']})"
                if col.get("description"):
                    col_desc += f": {col['description']}"
                columns_text.append(col_desc)
            
            # Support both BigQuery (dataset/project) and Snowflake/PostgreSQL/etc (schema/database) field names
            dataset_name = schema.get("dataset", schema.get("schema", ""))
            project_name = schema.get("project", schema.get("database", ""))

            combined_text = f"""
            Table: {schema['table_name']}
            Dataset: {dataset_name}
            Project: {project_name}
            Description: {schema.get('description', 'No description')}
            Columns: {', '.join(columns_text)}
            Row Count: {schema.get('row_count', 'Unknown')}
            """
            
            import json
            collection = self.client.collections.get(self.collection_name)
            
            data_object = {
                "table_name": schema["table_name"],
                "dataset": dataset_name,
                "project": project_name,
                "description": schema.get("description", ""),
                "columns": json.dumps(schema["columns"]),
                "row_count": schema.get("row_count", 0),
                "combined_text": combined_text.strip(),
                "database_type": schema.get("source_database_type", schema.get("database_type", "bigquery")),
                "organization_id": schema.get("organization_id", "default"),
                "connector_id": schema.get("connector_id", "")
            }
            
            collection.data.insert(
                properties=data_object,
                vector=embedding
            )
            
            logger.info(f"Indexed schema for table {schema['table_name']}")
        except Exception as e:
            logger.error(f"Failed to index schema: {e}")
            raise
    
    def search_similar_tables(
        self,
        query_embedding: List[float],
        limit: int = 5,
        database_type: str = None,
        organization_id: str = None,
        enabled_databases: List[str] = None,
        connector_id: str = None,
        connector_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for tables similar to the query with optional filtering.

        Args:
            query_embedding: The query vector
            limit: Maximum number of results
            database_type: Filter by specific database type
            organization_id: Filter by organization ID
            enabled_databases: List of enabled database types to filter by
            connector_id: Filter by specific connector ID
            connector_ids: Filter by list of connector IDs (use for multiple enabled connectors)
        """
        try:
            import json
            collection = self.client.collections.get(self.collection_name)

            # Build filter conditions
            filters = None
            logger.info(f"Vector search filters: connector_id={connector_id}, connector_ids={connector_ids}, "
                       f"database_type={database_type}, organization_id={organization_id}")
            if organization_id or database_type or enabled_databases or connector_id or connector_ids:
                filter_conditions = []

                # Connector ID filter (highest priority - most specific)
                if connector_id:
                    filter_conditions.append(
                        wvc.query.Filter.by_property("connector_id").equal(connector_id)
                    )
                elif connector_ids:  # Multiple connector IDs
                    filter_conditions.append(
                        wvc.query.Filter.by_property("connector_id").contains_any(connector_ids)
                    )

                # Organization filter
                if organization_id:
                    filter_conditions.append(
                        wvc.query.Filter.by_property("organization_id").equal(organization_id)
                    )

                # Database type filter
                if database_type:
                    filter_conditions.append(
                        wvc.query.Filter.by_property("database_type").equal(database_type)
                    )
                elif enabled_databases:  # Use enabled databases list if no specific database
                    filter_conditions.append(
                        wvc.query.Filter.by_property("database_type").contains_any(enabled_databases)
                    )

                # Combine filters with AND
                if len(filter_conditions) == 1:
                    filters = filter_conditions[0]
                else:
                    filters = filter_conditions[0]
                    for condition in filter_conditions[1:]:
                        filters = filters & condition

            # Specify which properties to return to avoid None values
            response = collection.query.near_vector(
                near_vector=query_embedding,
                filters=filters,  # Apply filters (Weaviate v4 uses 'filters' not 'where')
                limit=limit,
                return_metadata=wvc.query.MetadataQuery(distance=True),
                return_properties=[
                    "table_name",
                    "dataset",
                    "project",
                    "description",
                    "columns",
                    "row_count",
                    "combined_text",
                    "database_type",
                    "organization_id",
                    "connector_id",
                    "business_domains",
                    "has_relationships"
                ]
            )

            results = []
            for item in response.objects:
                # Safe property access with None checks
                columns_json = item.properties.get("columns")
                columns = []
                if columns_json:
                    try:
                        columns = json.loads(columns_json)
                    except (json.JSONDecodeError, TypeError) as parse_error:
                        logger.warning(f"Failed to parse columns for {item.properties.get('table_name')}: {parse_error}")
                        columns = []

                # Parse business_domains if stored as JSON string
                business_domains_raw = item.properties.get("business_domains", [])
                if isinstance(business_domains_raw, str):
                    try:
                        business_domains = json.loads(business_domains_raw)
                    except (json.JSONDecodeError, TypeError):
                        business_domains = []
                else:
                    business_domains = business_domains_raw if business_domains_raw else []

                result = {
                    "table_name": item.properties.get("table_name", "unknown"),
                    "dataset": item.properties.get("dataset", ""),
                    "project": item.properties.get("project", ""),
                    "description": item.properties.get("description", ""),
                    "columns": columns,
                    "row_count": item.properties.get("row_count", 0),
                    "distance": item.metadata.distance if item.metadata else None,
                    "connector_id": item.properties.get("connector_id", ""),
                    "database_type": item.properties.get("database_type", "bigquery"),
                    "business_domains": business_domains,
                    "has_relationships": item.properties.get("has_relationships", False)
                }
                results.append(result)

            logger.info(f"Vector search found {len(results)} similar tables")
            if len(results) == 0:
                # Debug: check total count in collection
                try:
                    aggregate = collection.aggregate.over_all(total_count=True)
                    logger.warning(f"Vector search returned 0 results but collection has {aggregate.total_count} total objects")
                except Exception as agg_err:
                    logger.warning(f"Could not get collection count: {agg_err}")
            return results
        except Exception as e:
            logger.error(f"Failed to search tables: {e}")
            raise
    
    def delete_all_schemas(self):
        """Delete all schemas from the collection."""
        try:
            collection = self.client.collections.get(self.collection_name)
            collection.data.delete_many(where=wvc.query.Filter.by_property("table_name").like("*"))
            logger.info("Deleted all schemas")
        except Exception as e:
            logger.error(f"Failed to delete schemas: {e}")
            raise

    def recreate_collection(self):
        """
        Delete and recreate the TableSchemas collection with the current schema.

        Use this when the collection schema is outdated (e.g., missing connector_id property).
        """
        try:
            # Delete existing collection
            if self.client.collections.exists(self.collection_name):
                self.client.collections.delete(self.collection_name)
                logger.info(f"Deleted existing collection {self.collection_name}")

            # Recreate with current schema
            self._ensure_collection_exists()
            logger.info(f"Recreated collection {self.collection_name} with updated schema")
            return True
        except Exception as e:
            logger.error(f"Failed to recreate collection: {e}")
            raise

    def delete_schemas_by_connector(self, connector_id: str) -> int:
        """
        Delete all schemas belonging to a specific connector.

        Args:
            connector_id: The ID of the connector whose schemas should be deleted

        Returns:
            Number of schemas deleted
        """
        try:
            collection = self.client.collections.get(self.collection_name)
            result = collection.data.delete_many(
                where=wvc.query.Filter.by_property("connector_id").equal(connector_id)
            )
            deleted_count = result.successful if hasattr(result, 'successful') else 0
            logger.info(f"Deleted {deleted_count} schemas for connector {connector_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete schemas for connector {connector_id}: {e}")
            raise

    def get_schema_count_by_connector(self, connector_id: str) -> int:
        """
        Get the count of schemas for a specific connector.

        Args:
            connector_id: The ID of the connector

        Returns:
            Number of schemas indexed for this connector
        """
        try:
            collection = self.client.collections.get(self.collection_name)
            response = collection.aggregate.over_all(
                filters=wvc.query.Filter.by_property("connector_id").equal(connector_id),
                total_count=True
            )
            return response.total_count if response.total_count else 0
        except Exception as e:
            logger.error(f"Failed to count schemas for connector {connector_id}: {e}")
            return 0

    def get_table_by_name(
        self,
        table_name: str,
        organization_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a table by exact name and return its metadata including row_count.

        Args:
            table_name: The table name to look up (case-insensitive)
            organization_id: Optional organization ID filter

        Returns:
            Dict with table metadata including row_count, or None if not found
        """
        try:
            collection = self.client.collections.get(self.collection_name)

            # Build filter
            filters = wvc.query.Filter.by_property("table_name").equal(table_name.upper())
            if organization_id:
                filters = filters & wvc.query.Filter.by_property("organization_id").equal(organization_id)

            # Query by exact name match
            response = collection.query.fetch_objects(
                filters=filters,
                limit=1,
                return_properties=["table_name", "row_count", "dataset", "project", "database_type"]
            )

            if response.objects:
                item = response.objects[0]
                return {
                    "table_name": item.properties.get("table_name", ""),
                    "row_count": item.properties.get("row_count", 0),
                    "dataset": item.properties.get("dataset", ""),
                    "project": item.properties.get("project", ""),
                    "database_type": item.properties.get("database_type", "")
                }
            return None
        except Exception as e:
            logger.debug(f"Failed to get table {table_name}: {e}")
            return None

    def record_query_performance(
        self,
        sql_text: str,
        sql_embedding: List[float],
        execution_time_ms: float,
        rows_returned: int,
        data_transferred_mb: float,
        strategy_used: str,
        pushdown_applied: bool = False,
        filters_pushed: int = 0,
        source_database: Optional[str] = None,
        target_database: Optional[str] = None,
        tables_involved: Optional[List[str]] = None,
        join_type: Optional[str] = None,
        join_columns: Optional[Dict[str, str]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ):
        """
        Record query performance data for optimization learning.

        Args:
            sql_text: The SQL query text
            sql_embedding: Vector embedding of the query
            execution_time_ms: Execution time in milliseconds
            rows_returned: Number of rows returned
            data_transferred_mb: Data transferred in MB
            strategy_used: Execution strategy (STAGING_TABLE, MOVE_TO_PRIMARY, etc.)
            pushdown_applied: Whether pushdown optimization was applied
            filters_pushed: Number of filters pushed to source
            source_database: Source database type
            target_database: Target database type
            tables_involved: List of table names
            join_type: Type of JOIN (INNER, LEFT, etc.)
            join_columns: JOIN column mapping
            success: Whether query succeeded
            error_message: Error message if failed
            user_id: User ID
            organization_id: Organization ID
        """
        try:
            import json
            import hashlib
            from datetime import datetime

            # Generate query hash for deduplication
            query_hash = hashlib.sha256(sql_text.encode()).hexdigest()[:16]

            collection = self.client.collections.get(self.query_collection_name)

            properties = {
                "sql_text": sql_text[:10000],  # Limit text length
                "query_hash": query_hash,
                "execution_time_ms": execution_time_ms,
                "rows_returned": rows_returned,
                "data_transferred_mb": data_transferred_mb,
                "strategy_used": strategy_used,
                "pushdown_applied": pushdown_applied,
                "filters_pushed": filters_pushed,
                "source_database": source_database or "",
                "target_database": target_database or "",
                "tables_involved": json.dumps(tables_involved or []),
                "join_type": join_type or "",
                "join_columns": json.dumps(join_columns or {}),
                "success": success,
                "error_message": error_message or "",
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id or "",
                "organization_id": organization_id or ""
            }

            collection.data.insert(
                properties=properties,
                vector=sql_embedding
            )

            logger.debug(
                f"Recorded query performance: {execution_time_ms:.0f}ms, "
                f"strategy={strategy_used}, success={success}"
            )

        except Exception as e:
            logger.error(f"Failed to record query performance: {e}")
            # Don't raise - query tracking failure shouldn't break main flow

    def search_similar_queries(
        self,
        query_embedding: List[float],
        limit: int = 10,
        only_successful: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for historically similar queries for optimization hints.

        Args:
            query_embedding: Vector embedding of the query
            limit: Maximum number of results
            only_successful: Only return successful queries

        Returns:
            List of similar query executions with performance metrics
        """
        try:
            import json

            collection = self.client.collections.get(self.query_collection_name)

            # Build filter for successful queries
            filters = None
            if only_successful:
                filters = wvc.query.Filter.by_property("success").equal(True)

            response = collection.query.near_vector(
                near_vector=query_embedding,
                limit=limit,
                filters=filters,
                return_metadata=wvc.query.MetadataQuery(distance=True),
                return_properties=[
                    "sql_text",
                    "execution_time_ms",
                    "rows_returned",
                    "data_transferred_mb",
                    "strategy_used",
                    "pushdown_applied",
                    "filters_pushed",
                    "source_database",
                    "target_database",
                    "tables_involved",
                    "join_type",
                    "timestamp",
                    "success"
                ]
            )

            results = []
            for item in response.objects:
                props = item.properties

                # Parse JSON fields
                tables_involved = []
                if props.get("tables_involved"):
                    try:
                        tables_involved = json.loads(props["tables_involved"])
                    except (json.JSONDecodeError, TypeError):
                        pass

                result = {
                    "sql_text": props.get("sql_text", ""),
                    "execution_time_ms": props.get("execution_time_ms", 0),
                    "rows_returned": props.get("rows_returned", 0),
                    "data_transferred_mb": props.get("data_transferred_mb", 0),
                    "strategy_used": props.get("strategy_used", ""),
                    "pushdown_applied": props.get("pushdown_applied", False),
                    "filters_pushed": props.get("filters_pushed", 0),
                    "source_database": props.get("source_database", ""),
                    "target_database": props.get("target_database", ""),
                    "tables_involved": tables_involved,
                    "join_type": props.get("join_type", ""),
                    "timestamp": props.get("timestamp", ""),
                    "success": props.get("success", True),
                    "distance": item.metadata.distance if item.metadata else None
                }
                results.append(result)

            logger.debug(f"Found {len(results)} similar historical queries")
            return results

        except Exception as e:
            logger.error(f"Failed to search similar queries: {e}")
            return []  # Return empty list on error

    def get_optimization_hints(
        self,
        query_embedding: List[float],
        confidence_threshold: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """
        Get optimization hints from similar historical queries.

        Args:
            query_embedding: Vector embedding of the query
            confidence_threshold: Minimum confidence (0-1) to return hints

        Returns:
            Dictionary with optimization recommendations or None
        """
        try:
            similar_queries = self.search_similar_queries(
                query_embedding,
                limit=10,
                only_successful=True
            )

            if not similar_queries:
                return None

            # Calculate confidence based on distance and sample size
            # Distance < 0.2 = very similar queries
            very_similar = [q for q in similar_queries if q.get('distance', 1.0) < 0.2]

            if not very_similar:
                return None

            # Find most common successful strategy
            strategies = [q['strategy_used'] for q in very_similar if q['strategy_used']]
            if not strategies:
                return None

            from collections import Counter
            strategy_counts = Counter(strategies)
            recommended_strategy = strategy_counts.most_common(1)[0][0]

            # Calculate average performance
            avg_time = sum(q['execution_time_ms'] for q in very_similar) / len(very_similar)
            avg_data_transfer = sum(q['data_transferred_mb'] for q in very_similar) / len(very_similar)

            # Confidence based on sample size and distance
            confidence = min(len(very_similar) / 10.0, 1.0)  # Max confidence at 10+ samples

            if confidence < confidence_threshold:
                return None

            return {
                'recommended_strategy': recommended_strategy,
                'expected_time_ms': avg_time,
                'expected_data_transfer_mb': avg_data_transfer,
                'confidence': confidence,
                'sample_size': len(very_similar),
                'strategy_distribution': dict(strategy_counts)
            }

        except Exception as e:
            logger.error(f"Failed to get optimization hints: {e}")
            return None

    def close(self):
        """Close the Weaviate client connection."""
        if self.client:
            self.client.close()