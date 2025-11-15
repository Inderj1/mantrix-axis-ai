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
        try:
            self.client = self._initialize_client()
            self._ensure_collection_exists()
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
        """Create the TableSchemas collection if it doesn't exist."""
        try:
            if self.client.collections.exists(self.collection_name):
                logger.info(f"Collection {self.collection_name} already exists")
                # Check if we need to recreate due to dimension change
                try:
                    collection = self.client.collections.get(self.collection_name)
                    # If collection exists and is accessible, keep it
                    return
                except Exception:
                    # If there's an issue, delete and recreate
                    logger.info("Deleting existing collection due to configuration change")
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
            
            combined_text = f"""
            Table: {schema['table_name']}
            Dataset: {schema['dataset']}
            Description: {schema.get('description', 'No description')}
            Columns: {', '.join(columns_text)}
            Row Count: {schema.get('row_count', 'Unknown')}
            """
            
            import json
            collection = self.client.collections.get(self.collection_name)
            
            data_object = {
                "table_name": schema["table_name"],
                "dataset": schema["dataset"],
                "project": schema["project"],
                "description": schema.get("description", ""),
                "columns": json.dumps(schema["columns"]),
                "row_count": schema.get("row_count", 0),
                "combined_text": combined_text.strip()
            }
            
            collection.data.insert(
                properties=data_object,
                vector=embedding
            )
            
            logger.info(f"Indexed schema for table {schema['table_name']}")
        except Exception as e:
            logger.error(f"Failed to index schema: {e}")
            raise
    
    def search_similar_tables(self, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Search for tables similar to the query."""
        try:
            collection = self.client.collections.get(self.collection_name)
            
            response = collection.query.near_vector(
                near_vector=query_embedding,
                limit=limit,
                return_metadata=wvc.query.MetadataQuery(distance=True)
            )
            
            results = []
            for item in response.objects:
                import json
                result = {
                    "table_name": item.properties["table_name"],
                    "dataset": item.properties["dataset"],
                    "project": item.properties["project"],
                    "description": item.properties["description"],
                    "columns": json.loads(item.properties["columns"]),
                    "row_count": item.properties["row_count"],
                    "distance": item.metadata.distance if item.metadata else None
                }
                results.append(result)
            
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
    
    def close(self):
        """Close the Weaviate client connection."""
        if self.client:
            self.client.close()