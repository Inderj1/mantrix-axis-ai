-- Migration: Create RDF Triples Table
-- Description: PostgreSQL-backed RDF triple store for persistent Jena knowledge graph
-- Date: 2025-12-04
-- Author: Mantrix Axis AI

-- Purpose: Store RDF triples in PostgreSQL to persist across container restarts in AWS ECS.
-- This solves the issue where the Jena RDF knowledge graph is lost when containers restart
-- because the container filesystem is read-only.

-- Create the rdf_triples table
CREATE TABLE IF NOT EXISTS rdf_triples (
    id BIGSERIAL PRIMARY KEY,

    -- Triple components
    subject VARCHAR(512) NOT NULL,
    predicate VARCHAR(512) NOT NULL,
    object TEXT NOT NULL,

    -- Object metadata
    object_type VARCHAR(50) DEFAULT 'uri',  -- uri, literal, bnode
    language_tag VARCHAR(10),                -- for literal@en
    datatype_uri VARCHAR(512),               -- for typed literals

    -- Multi-tenant & versioning
    graph_id VARCHAR(256) NOT NULL DEFAULT 'global',  -- org_id or "global"
    version INT DEFAULT 1,
    pipeline_run_id VARCHAR(256),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_rdf_subject ON rdf_triples(subject);
CREATE INDEX IF NOT EXISTS idx_rdf_predicate ON rdf_triples(predicate);
CREATE INDEX IF NOT EXISTS idx_rdf_graph ON rdf_triples(graph_id);
CREATE INDEX IF NOT EXISTS idx_rdf_subject_predicate ON rdf_triples(subject, predicate);
CREATE INDEX IF NOT EXISTS idx_rdf_graph_version ON rdf_triples(graph_id, version);

-- Add comment for documentation
COMMENT ON TABLE rdf_triples IS 'RDF triple storage for persistent Jena knowledge graph with multi-tenant isolation';
COMMENT ON COLUMN rdf_triples.subject IS 'RDF triple subject URI';
COMMENT ON COLUMN rdf_triples.predicate IS 'RDF triple predicate URI';
COMMENT ON COLUMN rdf_triples.object IS 'RDF triple object (URI or literal value)';
COMMENT ON COLUMN rdf_triples.object_type IS 'Type of object: uri, literal, or bnode';
COMMENT ON COLUMN rdf_triples.graph_id IS 'Tenant/organization identifier for multi-tenant isolation';
COMMENT ON COLUMN rdf_triples.version IS 'Version number for tracking changes and rollback';
COMMENT ON COLUMN rdf_triples.pipeline_run_id IS 'Pipeline run identifier for tracking which pipeline created the triples';

-- Grant permissions (adjust as needed for your environment)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON rdf_triples TO mantrix_app;
-- GRANT USAGE, SELECT ON SEQUENCE rdf_triples_id_seq TO mantrix_app;
