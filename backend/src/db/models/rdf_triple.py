"""
RDF Triple storage model with multi-tenant and versioning support.

This model stores RDF triples in PostgreSQL for persistent storage of the
Jena knowledge graph. It provides:
- Multi-tenant isolation via graph_id
- Version tracking for rollback
- Pipeline run tracking
"""

from datetime import datetime
from typing import Optional


class RDFTriple:
    """
    RDF triple storage with multi-tenant and versioning support.

    This is a lightweight class that works with raw psycopg2 instead of
    SQLAlchemy ORM to match the existing PostgreSQLClient pattern.

    Attributes:
        id: Primary key
        subject: RDF triple subject URI
        predicate: RDF triple predicate URI
        object: RDF triple object (URI or literal value)
        object_type: Type of object (uri, literal, bnode)
        language_tag: Language tag for literal values (e.g., 'en')
        datatype_uri: Datatype URI for typed literals
        graph_id: Tenant/organization identifier for isolation
        version: Version number for tracking changes
        pipeline_run_id: Optional pipeline run identifier
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "rdf_triples"

    def __init__(
        self,
        subject: str,
        predicate: str,
        object: str,
        object_type: str = "uri",
        language_tag: Optional[str] = None,
        datatype_uri: Optional[str] = None,
        graph_id: str = "global",
        version: int = 1,
        pipeline_run_id: Optional[str] = None,
        id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.subject = subject
        self.predicate = predicate
        self.object = object
        self.object_type = object_type
        self.language_tag = language_tag
        self.datatype_uri = datatype_uri
        self.graph_id = graph_id
        self.version = version
        self.pipeline_run_id = pipeline_run_id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for insertion."""
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "object_type": self.object_type,
            "language_tag": self.language_tag,
            "datatype_uri": self.datatype_uri,
            "graph_id": self.graph_id,
            "version": self.version,
            "pipeline_run_id": self.pipeline_run_id
        }

    @classmethod
    def from_row(cls, row: dict) -> "RDFTriple":
        """Create instance from database row."""
        return cls(
            id=row.get("id"),
            subject=row["subject"],
            predicate=row["predicate"],
            object=row["object"],
            object_type=row.get("object_type", "uri"),
            language_tag=row.get("language_tag"),
            datatype_uri=row.get("datatype_uri"),
            graph_id=row.get("graph_id", "global"),
            version=row.get("version", 1),
            pipeline_run_id=row.get("pipeline_run_id"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )


# SQL for creating the table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rdf_triples (
    id BIGSERIAL PRIMARY KEY,
    subject VARCHAR(512) NOT NULL,
    predicate VARCHAR(512) NOT NULL,
    object TEXT NOT NULL,
    object_type VARCHAR(50) DEFAULT 'uri',
    language_tag VARCHAR(10),
    datatype_uri VARCHAR(512),
    graph_id VARCHAR(256) NOT NULL DEFAULT 'global',
    version INT DEFAULT 1,
    pipeline_run_id VARCHAR(256),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_rdf_subject ON rdf_triples(subject);
CREATE INDEX IF NOT EXISTS idx_rdf_predicate ON rdf_triples(predicate);
CREATE INDEX IF NOT EXISTS idx_rdf_graph ON rdf_triples(graph_id);
CREATE INDEX IF NOT EXISTS idx_rdf_subject_predicate ON rdf_triples(subject, predicate);
CREATE INDEX IF NOT EXISTS idx_rdf_graph_version ON rdf_triples(graph_id, version);
"""


# SQL for dropping the table (used in migrations)
DROP_TABLE_SQL = """
DROP TABLE IF EXISTS rdf_triples CASCADE;
"""
