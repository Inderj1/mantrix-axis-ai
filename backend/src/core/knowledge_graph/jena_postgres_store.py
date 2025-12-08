"""
PostgreSQL-backed RDF triple store with versioning and multi-tenant support.

This module provides persistent storage for RDF triples in PostgreSQL,
enabling the Jena knowledge graph to survive container restarts in AWS ECS.

Features:
- Persistent storage in PostgreSQL (already have RDS)
- Multi-tenant isolation via graph_id column
- Version tracking for rollback capability
- Bulk operations for pipeline efficiency
- RDFLib-compatible interface

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                      Query Time                              │
│                                                              │
│  ┌─────────┐    cache miss    ┌────────────┐                │
│  │  Redis  │ ───────────────► │ PostgreSQL │                │
│  │ (hot)   │ ◄─────────────── │ (primary)  │                │
│  │  24hr   │    populate      │  (persist) │                │
│  └─────────┘                  └────────────┘                │
└─────────────────────────────────────────────────────────────┘
"""

import os
import structlog
from typing import Optional, List, Dict, Any, Iterator
from contextlib import contextmanager
from datetime import datetime

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.term import Node

from src.db.postgresql_client import PostgreSQLClient
from src.db.models.rdf_triple import RDFTriple, CREATE_TABLE_SQL

logger = structlog.get_logger()

# Singleton instance
_postgres_store: Optional["JenaPostgresStore"] = None


class JenaPostgresStore:
    """
    PostgreSQL-backed RDF store that implements RDFLib-compatible interface.

    Features:
    - Persistent storage in PostgreSQL
    - Multi-tenant isolation via graph_id
    - Version tracking for rollback
    - Bulk operations for pipeline efficiency
    """

    def __init__(self, graph_id: str = "global"):
        """
        Initialize the PostgreSQL RDF store.

        Args:
            graph_id: Tenant/organization identifier for isolation
        """
        self.graph_id = graph_id
        self._graph: Optional[Graph] = None
        self._loaded = False
        self._db_client = PostgreSQLClient()
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """Create the rdf_triples table if it doesn't exist."""
        try:
            self._db_client.execute_query(CREATE_TABLE_SQL)
            logger.debug("RDF triples table ensured")
        except Exception as e:
            logger.error(f"Failed to create rdf_triples table: {e}")
            raise

    @property
    def graph(self) -> Graph:
        """Lazy-load graph from PostgreSQL."""
        if not self._loaded:
            self._load_from_postgres()
        return self._graph

    def _load_from_postgres(self) -> None:
        """Load all triples for this graph_id from PostgreSQL."""
        logger.info(f"Loading RDF graph from PostgreSQL for graph_id={self.graph_id}")

        self._graph = Graph()

        try:
            query = """
                SELECT subject, predicate, object, object_type, language_tag, datatype_uri
                FROM rdf_triples
                WHERE graph_id = %s
            """
            results = self._db_client.execute_query(query, (self.graph_id,))

            for row in results:
                subject = self._parse_node(row['subject'], "uri")
                predicate = URIRef(row['predicate'])
                obj = self._parse_node(
                    row['object'],
                    row.get('object_type', 'uri'),
                    row.get('language_tag'),
                    row.get('datatype_uri')
                )
                self._graph.add((subject, predicate, obj))

            self._loaded = True
            logger.info(f"Loaded {len(self._graph)} triples from PostgreSQL")

        except Exception as e:
            logger.error(f"Failed to load RDF from PostgreSQL: {e}")
            self._graph = Graph()
            self._loaded = True  # Mark as loaded to prevent retry loops

    def _parse_node(
        self,
        value: str,
        node_type: str,
        lang: Optional[str] = None,
        datatype: Optional[str] = None
    ) -> Node:
        """Parse a stored value back into an RDFLib node."""
        if node_type == "uri":
            return URIRef(value)
        elif node_type == "bnode":
            return BNode(value)
        elif node_type == "literal":
            if lang:
                return Literal(value, lang=lang)
            elif datatype:
                return Literal(value, datatype=URIRef(datatype))
            return Literal(value)
        return URIRef(value)

    def _get_node_type(self, node: Node) -> str:
        """Determine the type of an RDFLib node."""
        if isinstance(node, URIRef):
            return "uri"
        elif isinstance(node, BNode):
            return "bnode"
        elif isinstance(node, Literal):
            return "literal"
        return "uri"

    def save_graph(
        self,
        graph: Graph,
        pipeline_run_id: Optional[str] = None,
        replace: bool = True
    ) -> int:
        """
        Save an RDFLib graph to PostgreSQL.

        Args:
            graph: RDFLib Graph to save
            pipeline_run_id: Optional pipeline run identifier for versioning
            replace: If True, delete existing triples first

        Returns:
            Number of triples saved
        """
        logger.info(f"Saving {len(graph)} triples to PostgreSQL for graph_id={self.graph_id}")

        try:
            if replace:
                # Delete existing triples for this graph
                delete_query = "DELETE FROM rdf_triples WHERE graph_id = %s"
                self._db_client.execute_query(delete_query, (self.graph_id,))
                logger.info(f"Deleted existing triples for graph_id={self.graph_id}")

            # Bulk insert new triples
            insert_query = """
                INSERT INTO rdf_triples
                    (subject, predicate, object, object_type, language_tag, datatype_uri, graph_id, pipeline_run_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            count = 0
            batch_size = 1000
            batch = []

            for s, p, o in graph:
                obj_type = self._get_node_type(o)
                lang_tag = getattr(o, 'language', None) if isinstance(o, Literal) else None
                dtype_uri = str(o.datatype) if isinstance(o, Literal) and o.datatype else None

                batch.append((
                    str(s),
                    str(p),
                    str(o),
                    obj_type,
                    lang_tag,
                    dtype_uri,
                    self.graph_id,
                    pipeline_run_id
                ))
                count += 1

                # Execute batch when full
                if len(batch) >= batch_size:
                    self._execute_batch_insert(insert_query, batch)
                    batch = []

            # Insert remaining triples
            if batch:
                self._execute_batch_insert(insert_query, batch)

            # Update local cache
            self._graph = graph
            self._loaded = True

            logger.info(f"Saved {count} triples to PostgreSQL")
            return count

        except Exception as e:
            logger.error(f"Failed to save RDF to PostgreSQL: {e}")
            raise

    def _execute_batch_insert(self, query: str, batch: List[tuple]) -> None:
        """Execute a batch insert using executemany."""
        with self._db_client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, batch)
                conn.commit()

    def add_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        object_type: str = "uri",
        language_tag: Optional[str] = None,
        datatype_uri: Optional[str] = None
    ) -> None:
        """Add a single triple to the store."""
        query = """
            INSERT INTO rdf_triples
                (subject, predicate, object, object_type, language_tag, datatype_uri, graph_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        self._db_client.execute_query(
            query,
            (subject, predicate, obj, object_type, language_tag, datatype_uri, self.graph_id)
        )

        # Update in-memory graph if loaded
        if self._loaded and self._graph:
            s = self._parse_node(subject, "uri")
            p = URIRef(predicate)
            o = self._parse_node(obj, object_type, language_tag, datatype_uri)
            self._graph.add((s, p, o))

    def clear(self) -> int:
        """Delete all triples for this graph_id."""
        try:
            query = "DELETE FROM rdf_triples WHERE graph_id = %s RETURNING id"
            results = self._db_client.execute_query(query, (self.graph_id,))
            deleted = len(results)

            self._graph = Graph()
            self._loaded = True

            logger.info(f"Cleared {deleted} triples from PostgreSQL for graph_id={self.graph_id}")
            return deleted

        except Exception as e:
            logger.error(f"Failed to clear RDF triples: {e}")
            raise

    def get_triple_count(self) -> int:
        """Get count of triples without loading full graph."""
        try:
            query = "SELECT COUNT(*) as count FROM rdf_triples WHERE graph_id = %s"
            results = self._db_client.execute_query(query, (self.graph_id,))
            return results[0]['count'] if results else 0
        except Exception as e:
            logger.error(f"Failed to get triple count: {e}")
            return 0

    def health_check(self) -> Dict[str, Any]:
        """Return health status of PostgreSQL RDF store."""
        try:
            count = self.get_triple_count()
            return {
                "connected": True,
                "triple_count": count,
                "graph_id": self.graph_id,
                "backend": "postgresql"
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "graph_id": self.graph_id,
                "backend": "postgresql"
            }

    def reload(self) -> None:
        """Force reload from PostgreSQL."""
        self._loaded = False
        self._graph = None
        _ = self.graph  # Trigger reload

    def query_triples(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query triples with optional filters.

        Args:
            subject: Filter by subject (optional)
            predicate: Filter by predicate (optional)
            limit: Maximum results to return

        Returns:
            List of triple dictionaries
        """
        query = "SELECT subject, predicate, object, object_type FROM rdf_triples WHERE graph_id = %s"
        params = [self.graph_id]

        if subject:
            query += " AND subject = %s"
            params.append(subject)

        if predicate:
            query += " AND predicate = %s"
            params.append(predicate)

        query += " LIMIT %s"
        params.append(limit)

        return self._db_client.execute_query(query, tuple(params))


def get_postgres_store(graph_id: str = "global") -> JenaPostgresStore:
    """
    Get a JenaPostgresStore instance.

    Args:
        graph_id: Tenant/organization identifier (default: "global")

    Returns:
        JenaPostgresStore instance
    """
    global _postgres_store

    if _postgres_store is None or _postgres_store.graph_id != graph_id:
        _postgres_store = JenaPostgresStore(graph_id=graph_id)

    return _postgres_store


def get_postgres_graph(graph_id: str = "global") -> Graph:
    """
    Factory function to get a PostgreSQL-backed RDF graph.

    Args:
        graph_id: Tenant/organization identifier (default: "global")

    Returns:
        RDFLib Graph loaded from PostgreSQL
    """
    store = get_postgres_store(graph_id)
    return store.graph


def save_graph_to_postgres(
    graph: Graph,
    graph_id: str = "global",
    pipeline_run_id: Optional[str] = None
) -> int:
    """
    Save an RDFLib graph to PostgreSQL.

    Args:
        graph: RDFLib Graph to save
        graph_id: Tenant/organization identifier
        pipeline_run_id: Optional pipeline run identifier

    Returns:
        Number of triples saved
    """
    store = JenaPostgresStore(graph_id=graph_id)
    return store.save_graph(graph, pipeline_run_id=pipeline_run_id)
