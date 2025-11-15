"""
RDF Builder - Build-time RDF knowledge graph from schema snapshots.

This module converts extracted schema snapshots into semantic RDF triples,
enriching the knowledge graph with business context, relationships, and
cardinality information for improved query generation.

Key Features:
- Convert TableSchemaSnapshot → RDF triples
- Add business semantics and domain knowledge
- Store cardinality estimates for query optimization
- Discover and represent table relationships (JOINs)
- Incremental updates (only changed schemas)
- Integration with existing Jena knowledge graph

Architecture:
Schema Extraction → **RDF Building** → Vector Indexing → Query Generation

Author: Mantrix Axis AI
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD
from rdflib.namespace import FOAF, DC, DCTERMS
import structlog

from src.pipeline.schema_extractor import TableSchemaSnapshot, SchemaExtractor
from src.core.knowledge_graph.jena_singleton import get_jena_knowledge_graph
from src.core.cache_manager import CacheManager
from src.db.bigquery import BigQueryClient
from src.config import settings

logger = structlog.get_logger()


# Define custom namespaces for financial/business domain
FIN = Namespace("http://example.com/finance#")
SCHEMA = Namespace("http://example.com/schema#")
STATS = Namespace("http://example.com/stats#")


@dataclass
class RDFBuildResult:
    """Result of RDF building operation"""
    triples_added: int
    triples_updated: int
    triples_removed: int
    tables_processed: int
    relationships_discovered: int
    build_timestamp: str
    errors: List[str]


class RDFBuilder:
    """
    Builds RDF knowledge graph from database schema snapshots.

    Workflow:
    1. Load schema snapshots from SchemaExtractor
    2. Convert to RDF triples (tables, columns, types)
    3. Discover and add relationships (JOIN paths)
    4. Add cardinality statistics
    5. Enrich with business semantics
    6. Store in Jena knowledge graph

    Usage:
        builder = RDFBuilder(schema_extractor, jena_kg)
        result = builder.build_from_snapshots(snapshots)
    """

    def __init__(
        self,
        schema_extractor: SchemaExtractor,
        jena_kg=None,
        cache_manager: Optional[CacheManager] = None
    ):
        self.schema_extractor = schema_extractor
        self.jena_kg = jena_kg or get_jena_knowledge_graph()
        self.cache_manager = cache_manager
        self.graph = Graph()  # Local RDF graph for building

        # Bind namespaces
        self.graph.bind("fin", FIN)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("stats", STATS)
        self.graph.bind("dc", DC)
        self.graph.bind("dcterms", DCTERMS)

    def build_from_snapshots(
        self,
        snapshots: List[TableSchemaSnapshot],
        include_stats: bool = True,
        discover_relationships: bool = True
    ) -> RDFBuildResult:
        """
        Build RDF graph from schema snapshots.

        Args:
            snapshots: List of TableSchemaSnapshot objects
            include_stats: Add cardinality statistics
            discover_relationships: Discover JOIN relationships

        Returns:
            RDFBuildResult with operation statistics
        """
        logger.info(f"Building RDF graph from {len(snapshots)} schema snapshots")

        errors = []
        relationships_discovered = 0

        # Clear local graph for fresh build
        self.graph = Graph()
        self._bind_namespaces()

        # Phase 1: Convert schemas to RDF
        for snapshot in snapshots:
            try:
                self._add_table_to_graph(snapshot)
            except Exception as e:
                logger.error(f"Failed to add table {snapshot.table_name} to RDF: {e}")
                errors.append(f"{snapshot.table_name}: {str(e)}")

        # Phase 2: Add statistics (cardinality)
        if include_stats:
            for snapshot in snapshots:
                try:
                    self._add_table_statistics(snapshot)
                except Exception as e:
                    logger.warning(f"Failed to add stats for {snapshot.table_name}: {e}")

        # Phase 3: Discover and add relationships
        if discover_relationships:
            try:
                relationships_discovered = self._discover_relationships(snapshots)
            except Exception as e:
                logger.error(f"Relationship discovery failed: {e}")
                errors.append(f"Relationships: {str(e)}")

        # Phase 4: Merge into Jena knowledge graph
        triples_before = len(self.jena_kg.graph) if self.jena_kg else 0

        if self.jena_kg:
            try:
                self._merge_into_jena()
            except Exception as e:
                logger.error(f"Failed to merge into Jena KG: {e}")
                errors.append(f"Jena merge: {str(e)}")

        triples_after = len(self.jena_kg.graph) if self.jena_kg else 0

        result = RDFBuildResult(
            triples_added=len(self.graph),
            triples_updated=0,  # TODO: Track updates separately
            triples_removed=0,
            tables_processed=len(snapshots),
            relationships_discovered=relationships_discovered,
            build_timestamp=datetime.now().isoformat(),
            errors=errors
        )

        logger.info(
            f"RDF build complete: {result.triples_added} triples, "
            f"{result.relationships_discovered} relationships, "
            f"{len(errors)} errors"
        )

        return result

    def _bind_namespaces(self):
        """Bind all namespaces to graph"""
        self.graph.bind("fin", FIN)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("stats", STATS)
        self.graph.bind("dc", DC)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)

    def _add_table_to_graph(self, snapshot: TableSchemaSnapshot):
        """
        Convert TableSchemaSnapshot to RDF triples.

        Creates:
        - fin:Table node for the table
        - schema:Column nodes for each column
        - Properties: name, type, description, row_count, etc.
        """
        # Create table URI
        table_uri = FIN[f"Table_{snapshot.table_name}"]

        # Table metadata
        self.graph.add((table_uri, RDF.type, FIN.Table))
        self.graph.add((table_uri, SCHEMA.tableName, Literal(snapshot.table_name)))
        self.graph.add((table_uri, SCHEMA.dataset, Literal(snapshot.dataset)))
        self.graph.add((table_uri, SCHEMA.project, Literal(snapshot.project)))
        self.graph.add((table_uri, SCHEMA.databaseType, Literal(snapshot.database_type)))

        if snapshot.description:
            self.graph.add((table_uri, DCTERMS.description, Literal(snapshot.description)))

        # Metadata
        self.graph.add((table_uri, SCHEMA.rowCount, Literal(snapshot.row_count, datatype=XSD.integer)))
        self.graph.add((table_uri, SCHEMA.sizeBytes, Literal(snapshot.size_bytes, datatype=XSD.integer)))
        self.graph.add((table_uri, SCHEMA.schemaHash, Literal(snapshot.schema_hash)))
        self.graph.add((table_uri, SCHEMA.version, Literal(snapshot.version, datatype=XSD.integer)))
        self.graph.add((table_uri, DCTERMS.created, Literal(snapshot.created_at, datatype=XSD.dateTime)))
        self.graph.add((table_uri, DCTERMS.modified, Literal(snapshot.modified_at, datatype=XSD.dateTime)))

        # Add columns
        for col in snapshot.columns:
            self._add_column_to_graph(table_uri, snapshot.table_name, col)

        logger.debug(f"Added table {snapshot.table_name} to RDF graph")

    def _add_column_to_graph(self, table_uri: URIRef, table_name: str, column: Dict[str, Any]):
        """Add column as RDF node connected to table"""
        col_name = column['name']
        col_uri = FIN[f"Column_{table_name}_{col_name}"]

        # Column metadata
        self.graph.add((col_uri, RDF.type, FIN.Column))
        self.graph.add((col_uri, SCHEMA.columnName, Literal(col_name)))
        self.graph.add((col_uri, SCHEMA.dataType, Literal(column['type'])))
        self.graph.add((col_uri, SCHEMA.mode, Literal(column.get('mode', 'NULLABLE'))))
        self.graph.add((col_uri, SCHEMA.isNullable, Literal(column.get('is_nullable', True), datatype=XSD.boolean)))

        if column.get('description'):
            self.graph.add((col_uri, DCTERMS.description, Literal(column['description'])))

        # Link column to table
        self.graph.add((table_uri, SCHEMA.hasColumn, col_uri))
        self.graph.add((col_uri, SCHEMA.belongsToTable, table_uri))

        # Add type-specific metadata
        data_type = column['type'].upper()

        if data_type in ('STRING', 'VARCHAR', 'TEXT'):
            self.graph.add((col_uri, SCHEMA.columnCategory, SCHEMA.StringColumn))
        elif data_type in ('INT64', 'INTEGER', 'BIGINT'):
            self.graph.add((col_uri, SCHEMA.columnCategory, SCHEMA.IntegerColumn))
        elif data_type in ('FLOAT64', 'FLOAT', 'DOUBLE', 'NUMERIC', 'BIGNUMERIC'):
            self.graph.add((col_uri, SCHEMA.columnCategory, SCHEMA.NumericColumn))
        elif data_type in ('DATE', 'DATETIME', 'TIMESTAMP', 'TIME'):
            self.graph.add((col_uri, SCHEMA.columnCategory, SCHEMA.DateTimeColumn))
        elif data_type == 'BOOLEAN':
            self.graph.add((col_uri, SCHEMA.columnCategory, SCHEMA.BooleanColumn))

    def _add_table_statistics(self, snapshot: TableSchemaSnapshot):
        """
        Add statistical metadata for query optimization.

        Includes:
        - Row count buckets (for cardinality estimation)
        - Table size indicators
        - Data freshness metrics
        """
        table_uri = FIN[f"Table_{snapshot.table_name}"]

        # Row count bucket (for quick size assessment)
        row_bucket = self._get_row_bucket(snapshot.row_count)
        self.graph.add((table_uri, STATS.rowCountBucket, Literal(row_bucket)))

        # Size indicators
        if snapshot.row_count > 1000000:
            self.graph.add((table_uri, STATS.isLargeTable, Literal(True, datatype=XSD.boolean)))

        if snapshot.row_count > 0:
            # Estimate avg row size
            avg_row_size = snapshot.size_bytes / snapshot.row_count if snapshot.size_bytes > 0 else 0
            self.graph.add((table_uri, STATS.avgRowSizeBytes, Literal(int(avg_row_size), datatype=XSD.integer)))

        # Data freshness (if modified timestamp available)
        if snapshot.modified_at:
            try:
                modified_dt = datetime.fromisoformat(snapshot.modified_at)
                age_hours = (datetime.now() - modified_dt).total_seconds() / 3600
                self.graph.add((table_uri, STATS.dataAgeHours, Literal(age_hours, datatype=XSD.float)))

                # Flag stale data (>7 days old)
                if age_hours > 168:  # 7 days
                    self.graph.add((table_uri, STATS.isStale, Literal(True, datatype=XSD.boolean)))
            except Exception as e:
                logger.warning(f"Failed to calculate data age for {snapshot.table_name}: {e}")

    def _get_row_bucket(self, row_count: int) -> str:
        """Categorize table size into buckets"""
        if row_count == 0:
            return "empty"
        elif row_count <= 1000:
            return "tiny"  # <1K
        elif row_count <= 10000:
            return "small"  # 1K-10K
        elif row_count <= 100000:
            return "medium"  # 10K-100K
        elif row_count <= 1000000:
            return "large"  # 100K-1M
        elif row_count <= 10000000:
            return "very_large"  # 1M-10M
        else:
            return "huge"  # >10M

    def _discover_relationships(self, snapshots: List[TableSchemaSnapshot]) -> int:
        """
        Discover JOIN relationships between tables.

        Strategy:
        1. Find columns with matching names across tables
        2. Verify data type compatibility
        3. Sample data to estimate JOIN cardinality
        4. Add relationship triples to graph

        Returns:
            Number of relationships discovered
        """
        logger.info("Discovering table relationships...")

        # Build column index: column_name -> [(table, col_type)]
        column_index: Dict[str, List[Tuple[str, str]]] = {}

        for snapshot in snapshots:
            for col in snapshot.columns:
                col_name = col['name']
                col_type = col['type']

                if col_name not in column_index:
                    column_index[col_name] = []

                column_index[col_name].append((snapshot.table_name, col_type))

        # Find potential JOIN columns (appear in 2+ tables)
        relationships_found = 0

        for col_name, occurrences in column_index.items():
            if len(occurrences) < 2:
                continue  # Not a join column

            # Check type compatibility
            types = set(col_type for _, col_type in occurrences)
            if len(types) > 1:
                # Mixed types - might still be joinable (e.g., INT64 vs STRING)
                logger.debug(f"Column {col_name} has mixed types: {types}")

            # Create relationships for all pairs
            tables = [table for table, _ in occurrences]

            for i in range(len(tables)):
                for j in range(i + 1, len(tables)):
                    table1 = tables[i]
                    table2 = tables[j]

                    self._add_relationship(table1, table2, col_name, col_name)
                    relationships_found += 1

        logger.info(f"Discovered {relationships_found} potential JOIN relationships")
        return relationships_found

    def _add_relationship(self, table1: str, table2: str, col1: str, col2: str):
        """Add JOIN relationship to graph"""
        table1_uri = FIN[f"Table_{table1}"]
        table2_uri = FIN[f"Table_{table2}"]
        col1_uri = FIN[f"Column_{table1}_{col1}"]
        col2_uri = FIN[f"Column_{table2}_{col2}"]

        # Create relationship URI
        rel_id = f"{table1}_{col1}_to_{table2}_{col2}"
        rel_uri = FIN[f"Relationship_{rel_id}"]

        # Add relationship triples
        self.graph.add((rel_uri, RDF.type, FIN.JoinRelationship))
        self.graph.add((rel_uri, SCHEMA.sourceTable, table1_uri))
        self.graph.add((rel_uri, SCHEMA.targetTable, table2_uri))
        self.graph.add((rel_uri, SCHEMA.sourceColumn, col1_uri))
        self.graph.add((rel_uri, SCHEMA.targetColumn, col2_uri))
        self.graph.add((rel_uri, SCHEMA.joinType, Literal("INNER")))  # Default

        # Link tables to relationship
        self.graph.add((table1_uri, SCHEMA.hasRelationship, rel_uri))
        self.graph.add((table2_uri, SCHEMA.hasRelationship, rel_uri))

        logger.debug(f"Added relationship: {table1}.{col1} ↔ {table2}.{col2}")

    def _merge_into_jena(self):
        """
        Merge local RDF graph into Jena knowledge graph.

        Strategy:
        - Remove old schema triples
        - Add new triples from local graph
        - Preserve non-schema triples (GL mappings, synonyms, etc.)
        """
        if not self.jena_kg:
            logger.warning("Jena KG not available, skipping merge")
            return

        logger.info(f"Merging {len(self.graph)} triples into Jena knowledge graph")

        # Strategy: Remove schema-related triples, then add new ones
        # This ensures clean updates without duplicate triples

        # Remove old schema triples (tables, columns, relationships)
        old_triples = list(self.jena_kg.graph.triples((None, RDF.type, FIN.Table)))
        for triple in old_triples:
            # Remove table and all its related triples
            table_uri = triple[0]
            self.jena_kg.graph.remove((table_uri, None, None))  # Remove all triples with table as subject
            self.jena_kg.graph.remove((None, None, table_uri))  # Remove all triples with table as object

        # Add new triples
        for triple in self.graph:
            self.jena_kg.graph.add(triple)

        logger.info(f"Jena KG now has {len(self.jena_kg.graph)} total triples")

    def add_business_semantics(self, domain_mappings: Dict[str, Any]):
        """
        Enrich graph with business domain knowledge.

        Args:
            domain_mappings: Business domain definitions (e.g., "revenue", "customer")

        Example:
            domain_mappings = {
                "revenue": {
                    "tables": ["CE11000"],
                    "columns": ["VV001", "Gross_Revenue"],
                    "description": "Revenue and sales data"
                }
            }
        """
        logger.info(f"Adding business semantics for {len(domain_mappings)} domains")

        for domain_name, config in domain_mappings.items():
            domain_uri = FIN[f"Domain_{domain_name}"]

            # Create domain node
            self.graph.add((domain_uri, RDF.type, FIN.BusinessDomain))
            self.graph.add((domain_uri, SCHEMA.domainName, Literal(domain_name)))

            if 'description' in config:
                self.graph.add((domain_uri, DCTERMS.description, Literal(config['description'])))

            # Link tables to domain
            for table_name in config.get('tables', []):
                table_uri = FIN[f"Table_{table_name}"]
                self.graph.add((table_uri, SCHEMA.belongsToDomain, domain_uri))
                self.graph.add((domain_uri, SCHEMA.includesTable, table_uri))

            # Link columns to domain
            for col_name in config.get('columns', []):
                # Find all columns with this name across tables
                for s, p, o in self.graph.triples((None, SCHEMA.columnName, Literal(col_name))):
                    col_uri = s
                    self.graph.add((col_uri, SCHEMA.belongsToDomain, domain_uri))

    def get_build_summary(self, result: RDFBuildResult) -> str:
        """Generate human-readable build summary"""
        summary = f"""
RDF Build Summary
=================
Timestamp: {result.build_timestamp}

Tables Processed: {result.tables_processed}
Triples Added: {result.triples_added:,}
Relationships Discovered: {result.relationships_discovered}

Errors: {len(result.errors)}
"""
        if result.errors:
            summary += "\nError Details:\n"
            for error in result.errors[:10]:  # Show first 10 errors
                summary += f"  - {error}\n"

        return summary

    def export_to_file(self, output_path: str, format: str = "turtle"):
        """
        Export RDF graph to file.

        Args:
            output_path: File path to write
            format: RDF serialization format (turtle, xml, json-ld, nt)
        """
        logger.info(f"Exporting RDF graph to {output_path} ({format})")

        try:
            self.graph.serialize(destination=output_path, format=format)
            logger.info(f"Exported {len(self.graph)} triples to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export RDF: {e}")
            raise

    def query_relationships(self, table_name: str) -> List[Dict[str, str]]:
        """
        Query relationships for a specific table.

        Args:
            table_name: Table to find relationships for

        Returns:
            List of relationship dictionaries
        """
        table_uri = FIN[f"Table_{table_name}"]

        relationships = []

        # Query SPARQL for relationships
        query = f"""
        PREFIX fin: <http://example.com/finance#>
        PREFIX schema: <http://example.com/schema#>

        SELECT ?target_table ?source_col ?target_col
        WHERE {{
            ?rel a fin:JoinRelationship .
            ?rel schema:sourceTable <{table_uri}> .
            ?rel schema:targetTable ?target_table_uri .
            ?rel schema:sourceColumn ?source_col_uri .
            ?rel schema:targetColumn ?target_col_uri .

            ?target_table_uri schema:tableName ?target_table .
            ?source_col_uri schema:columnName ?source_col .
            ?target_col_uri schema:columnName ?target_col .
        }}
        """

        try:
            results = self.graph.query(query)

            for row in results:
                relationships.append({
                    'target_table': str(row.target_table),
                    'source_column': str(row.source_col),
                    'target_column': str(row.target_col),
                    'join_type': 'INNER'
                })

        except Exception as e:
            logger.error(f"SPARQL query failed: {e}")

        return relationships
