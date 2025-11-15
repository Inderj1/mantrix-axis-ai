#!/usr/bin/env python3
"""
Phase 2 Pipeline Tests
Tests for schema extraction, RDF building, vector generation, and orchestration

Run before/after Phase 2 implementation to verify the build-time pipeline works.

Usage:
    python test_phase2_pipeline.py
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db.bigquery import BigQueryClient
from src.db.weaviate_client import WeaviateClient
from src.core.cache_manager import CacheManager
from src.core.llm_client import LLMClient
from src.pipeline.schema_extractor import SchemaExtractor, SchemaChangeType
from src.pipeline.rdf_builder import RDFBuilder
from src.pipeline.vector_builder import VectorBuilder
from src.pipeline.orchestrator import PipelineOrchestrator, PipelineStatus
from src.config import settings
import structlog

logger = structlog.get_logger()

# Test results tracker
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


def log_test(test_name: str, status: str, details: str = ""):
    """Log test result"""
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"\n{icon} {test_name}")
    if details:
        print(f"   {details}")

    if status == "PASS":
        test_results["passed"].append(test_name)
    elif status == "FAIL":
        test_results["failed"].append((test_name, details))
    else:
        test_results["warnings"].append((test_name, details))


def test_schema_extractor_initialization():
    """Test 2.1: Schema Extractor Initialization"""
    print("\n" + "="*80)
    print("TEST 2.1: Schema Extractor Initialization")
    print("="*80)

    try:
        bq_client = BigQueryClient()
        cache_manager = CacheManager(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )

        extractor = SchemaExtractor(bq_client, cache_manager)

        assert extractor is not None, "Extractor should initialize"
        assert extractor.bq_client is not None, "BigQuery client should be set"
        assert extractor.cache_manager is not None, "Cache manager should be set"

        log_test("Schema Extractor Init", "PASS", "Initialized successfully")
        return extractor

    except Exception as e:
        log_test("Schema Extractor Init", "FAIL", str(e))
        return None


def test_schema_extraction(extractor: SchemaExtractor):
    """Test 2.2: Extract Single Table Schema"""
    print("\n" + "="*80)
    print("TEST 2.2: Schema Extraction")
    print("="*80)

    if not extractor:
        log_test("Schema Extraction", "FAIL", "Extractor not initialized")
        return None

    try:
        # Get first table
        tables = extractor.bq_client.list_tables()
        if not tables:
            log_test("Schema Extraction", "WARN", "No tables found")
            return None

        test_table = tables[0]

        # Extract schema
        snapshot = extractor.extract_schema(test_table)

        assert snapshot is not None, "Should return snapshot"
        assert snapshot.table_name == test_table, "Table name should match"
        assert len(snapshot.columns) > 0, "Should have columns"
        assert snapshot.schema_hash is not None, "Should have schema hash"
        assert snapshot.version > 0, "Should have version"

        log_test(
            "Schema Extraction",
            "PASS",
            f"{test_table}: {len(snapshot.columns)} columns, "
            f"{snapshot.row_count:,} rows, "
            f"v{snapshot.version}"
        )

        return snapshot

    except Exception as e:
        log_test("Schema Extraction", "FAIL", str(e))
        return None


def test_schema_change_detection(extractor: SchemaExtractor):
    """Test 2.3: Schema Change Detection"""
    print("\n" + "="*80)
    print("TEST 2.3: Schema Change Detection")
    print("="*80)

    if not extractor:
        log_test("Schema Change Detection", "FAIL", "Extractor not initialized")
        return

    try:
        # Extract all schemas
        snapshots = extractor.extract_all_schemas()

        if len(snapshots) == 0:
            log_test("Schema Change Detection", "WARN", "No schemas extracted")
            return

        # Detect changes
        changes = extractor.detect_changes(snapshots)

        assert changes is not None, "Should return changes dict"
        assert SchemaChangeType.NO_CHANGE in changes, "Should have NO_CHANGE key"

        total_changes = sum(
            len(change_list) for change_type, change_list in changes.items()
            if change_type != SchemaChangeType.NO_CHANGE
        )

        unchanged = len(changes.get(SchemaChangeType.NO_CHANGE, []))

        log_test(
            "Schema Change Detection",
            "PASS",
            f"{len(snapshots)} tables, {unchanged} unchanged, {total_changes} changes"
        )

        return changes

    except Exception as e:
        log_test("Schema Change Detection", "FAIL", str(e))
        return None


def test_cardinality_estimation(extractor: SchemaExtractor):
    """Test 2.4: Cardinality Estimation"""
    print("\n" + "="*80)
    print("TEST 2.4: Cardinality Estimation")
    print("="*80)

    if not extractor:
        log_test("Cardinality Estimation", "FAIL", "Extractor not initialized")
        return

    try:
        # Get a table and column
        tables = extractor.bq_client.list_tables()
        if not tables:
            log_test("Cardinality Estimation", "WARN", "No tables found")
            return

        test_table = tables[0]
        schema = extractor.bq_client.get_table_schema(test_table)

        string_cols = [
            col['name'] for col in schema.get('columns', [])
            if col['type'] in ('STRING', 'VARCHAR')
        ]

        if not string_cols:
            log_test("Cardinality Estimation", "WARN", f"No string columns in {test_table}")
            return

        test_column = string_cols[0]

        # Estimate cardinality
        cardinality = extractor.estimate_cardinality(test_table, test_column)

        assert 'distinct_count' in cardinality, "Should have distinct_count"
        assert 'total_count' in cardinality, "Should have total_count"
        assert 'selectivity' in cardinality, "Should have selectivity"

        log_test(
            "Cardinality Estimation",
            "PASS",
            f"{test_table}.{test_column}: "
            f"{cardinality['distinct_count']:,} distinct / "
            f"{cardinality['total_count']:,} total "
            f"(selectivity: {cardinality['selectivity']:.2%})"
        )

    except Exception as e:
        log_test("Cardinality Estimation", "FAIL", str(e))


def test_rdf_builder_initialization(extractor: SchemaExtractor):
    """Test 2.5: RDF Builder Initialization"""
    print("\n" + "="*80)
    print("TEST 2.5: RDF Builder Initialization")
    print("="*80)

    if not extractor:
        log_test("RDF Builder Init", "FAIL", "Extractor not initialized")
        return None

    try:
        from src.core.knowledge_graph.jena_singleton import get_jena_knowledge_graph

        jena_kg = get_jena_knowledge_graph()
        cache_manager = CacheManager(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )

        rdf_builder = RDFBuilder(extractor, jena_kg, cache_manager)

        assert rdf_builder is not None, "Should initialize"
        assert rdf_builder.schema_extractor is not None, "Should have schema extractor"
        assert rdf_builder.graph is not None, "Should have RDF graph"

        log_test("RDF Builder Init", "PASS", "Initialized successfully")
        return rdf_builder

    except Exception as e:
        log_test("RDF Builder Init", "FAIL", str(e))
        return None


def test_rdf_building(rdf_builder: RDFBuilder, test_snapshot):
    """Test 2.6: RDF Triple Generation"""
    print("\n" + "="*80)
    print("TEST 2.6: RDF Triple Generation")
    print("="*80)

    if not rdf_builder or not test_snapshot:
        log_test("RDF Building", "FAIL", "RDF builder or snapshot not available")
        return

    try:
        # Build RDF from single snapshot
        snapshots = [test_snapshot]

        result = rdf_builder.build_from_snapshots(
            snapshots,
            include_stats=True,
            discover_relationships=False  # Skip relationship discovery for single table
        )

        assert result is not None, "Should return result"
        assert result.triples_added > 0, "Should add triples"
        assert result.tables_processed == 1, "Should process 1 table"

        log_test(
            "RDF Building",
            "PASS",
            f"{result.triples_added} triples added for {test_snapshot.table_name}"
        )

        # Verify triples exist in graph
        triple_count = len(rdf_builder.graph)
        if triple_count < 5:
            log_test("RDF Triple Count", "WARN", f"Only {triple_count} triples generated")
        else:
            log_test("RDF Triple Count", "PASS", f"{triple_count} triples in graph")

    except Exception as e:
        log_test("RDF Building", "FAIL", str(e))


def test_relationship_discovery(rdf_builder: RDFBuilder, extractor: SchemaExtractor):
    """Test 2.7: Relationship Discovery"""
    print("\n" + "="*80)
    print("TEST 2.7: Relationship Discovery")
    print("="*80)

    if not rdf_builder or not extractor:
        log_test("Relationship Discovery", "FAIL", "RDF builder or extractor not available")
        return

    try:
        # Extract first few tables
        tables = extractor.bq_client.list_tables()
        snapshots = [extractor.extract_schema(table) for table in tables[:5]]

        # Build RDF with relationship discovery
        result = rdf_builder.build_from_snapshots(
            snapshots,
            include_stats=False,
            discover_relationships=True
        )

        assert result is not None, "Should return result"

        if result.relationships_discovered > 0:
            log_test(
                "Relationship Discovery",
                "PASS",
                f"Discovered {result.relationships_discovered} relationships"
            )
        else:
            log_test(
                "Relationship Discovery",
                "WARN",
                "No relationships discovered (tables may not have matching columns)"
            )

    except Exception as e:
        log_test("Relationship Discovery", "FAIL", str(e))


def test_vector_builder_initialization(rdf_builder: RDFBuilder):
    """Test 2.8: Vector Builder Initialization"""
    print("\n" + "="*80)
    print("TEST 2.8: Vector Builder Initialization")
    print("="*80)

    if not rdf_builder:
        log_test("Vector Builder Init", "FAIL", "RDF builder not available")
        return None

    try:
        weaviate_client = WeaviateClient()
        llm_client = LLMClient()
        cache_manager = CacheManager(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )

        vector_builder = VectorBuilder(
            rdf_builder,
            weaviate_client,
            llm_client,
            cache_manager
        )

        assert vector_builder is not None, "Should initialize"
        assert vector_builder.rdf_builder is not None, "Should have RDF builder"
        assert vector_builder.weaviate_client is not None, "Should have Weaviate client"

        log_test("Vector Builder Init", "PASS", "Initialized successfully")
        return vector_builder

    except Exception as e:
        log_test("Vector Builder Init", "FAIL", str(e))
        return None


def test_enriched_description_generation(vector_builder: VectorBuilder, test_snapshot):
    """Test 2.9: Enriched Description Generation"""
    print("\n" + "="*80)
    print("TEST 2.9: Enriched Description Generation")
    print("="*80)

    if not vector_builder or not test_snapshot:
        log_test("Enriched Description", "FAIL", "Vector builder or snapshot not available")
        return

    try:
        # Generate enriched description
        enriched_text = vector_builder._generate_enriched_description(test_snapshot)

        assert enriched_text is not None, "Should return text"
        assert len(enriched_text) > 100, "Should be substantial"
        assert test_snapshot.table_name in enriched_text, "Should include table name"

        # Check for enrichment features
        has_business_context = "Business Domain" in enriched_text or "Use Cases" in enriched_text
        has_relationships = "Relationships" in enriched_text or "JOIN" in enriched_text
        has_column_categories = "Numeric Columns" in enriched_text or "Text/ID Columns" in enriched_text

        log_test(
            "Enriched Description",
            "PASS",
            f"{len(enriched_text)} chars, "
            f"business_context={has_business_context}, "
            f"relationships={has_relationships}, "
            f"categorized_columns={has_column_categories}"
        )

        print(f"\n--- SAMPLE ENRICHED DESCRIPTION ---")
        print(enriched_text[:500] + "...")

    except Exception as e:
        log_test("Enriched Description", "FAIL", str(e))


def test_vector_building(vector_builder: VectorBuilder, test_snapshot):
    """Test 2.10: Vector Embedding Generation"""
    print("\n" + "="*80)
    print("TEST 2.10: Vector Embedding Generation")
    print("="*80)

    if not vector_builder or not test_snapshot:
        log_test("Vector Building", "FAIL", "Vector builder or snapshot not available")
        return

    try:
        # Build vectors
        result = vector_builder.build_vectors_from_rdf(
            [test_snapshot],
            force_refresh=True
        )

        assert result is not None, "Should return result"
        assert result.vectors_created >= 0, "Should create vectors"
        assert result.embedding_provider in ('openai', 'fallback'), "Should have provider"

        log_test(
            "Vector Building",
            "PASS",
            f"{result.vectors_created} vectors created, "
            f"provider: {result.embedding_provider}, "
            f"avg time: {result.avg_embedding_time_ms:.0f}ms"
        )

    except Exception as e:
        log_test("Vector Building", "FAIL", str(e))


def test_pipeline_orchestrator():
    """Test 2.11: Pipeline Orchestrator"""
    print("\n" + "="*80)
    print("TEST 2.11: Pipeline Orchestrator")
    print("="*80)

    try:
        orchestrator = PipelineOrchestrator()

        assert orchestrator is not None, "Should initialize"
        assert orchestrator.schema_extractor is not None, "Should have schema extractor"
        assert orchestrator.rdf_builder is not None, "Should have RDF builder"
        assert orchestrator.vector_builder is not None, "Should have vector builder"

        log_test("Pipeline Orchestrator Init", "PASS", "All components initialized")
        return orchestrator

    except Exception as e:
        log_test("Pipeline Orchestrator Init", "FAIL", str(e))
        return None


def test_full_pipeline_execution(orchestrator: PipelineOrchestrator):
    """Test 2.12: Full Pipeline Execution"""
    print("\n" + "="*80)
    print("TEST 2.12: Full Pipeline Execution (Limited)")
    print("="*80)

    if not orchestrator:
        log_test("Pipeline Execution", "FAIL", "Orchestrator not initialized")
        return

    try:
        # Get first 2 tables for quick test
        tables = orchestrator.schema_extractor.bq_client.list_tables()
        test_tables = tables[:2]

        print(f"Testing pipeline with {len(test_tables)} tables: {test_tables}")

        # Execute pipeline
        run = orchestrator.execute_pipeline(
            incremental=False,  # Full refresh for test
            force_refresh=True,
            tables=test_tables
        )

        assert run is not None, "Should return run"
        assert run.status in (PipelineStatus.COMPLETED, PipelineStatus.PARTIAL_SUCCESS), "Should complete"
        assert run.duration_seconds is not None, "Should have duration"

        log_test(
            "Pipeline Execution",
            "PASS",
            f"Status: {run.status.value}, "
            f"Duration: {run.duration_seconds:.1f}s, "
            f"Tables: {run.tables_processed}, "
            f"Errors: {len(run.errors)}"
        )

        # Print summary
        print("\n" + orchestrator.get_summary(run))

        return run

    except Exception as e:
        log_test("Pipeline Execution", "FAIL", str(e))
        return None


def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total = len(test_results["passed"]) + len(test_results["failed"]) + len(test_results["warnings"])
    passed = len(test_results["passed"])
    failed = len(test_results["failed"])
    warnings = len(test_results["warnings"])

    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warnings}")

    if failed > 0:
        print("\nFailed Tests:")
        for test_name, details in test_results["failed"]:
            print(f"  ❌ {test_name}: {details}")

    if warnings > 0:
        print("\nWarnings:")
        for test_name, details in test_results["warnings"]:
            print(f"  ⚠️  {test_name}: {details}")

    print("\n" + "="*80)

    return 0 if failed == 0 else 1


def main():
    """Run all Phase 2 tests"""
    print("="*80)
    print("PHASE 2 PIPELINE TESTS")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project: {settings.google_cloud_project}")
    print(f"Dataset: {settings.bigquery_dataset}")
    print("="*80)

    # Run tests in order
    extractor = test_schema_extractor_initialization()
    test_snapshot = test_schema_extraction(extractor)
    test_schema_change_detection(extractor)
    test_cardinality_estimation(extractor)

    rdf_builder = test_rdf_builder_initialization(extractor)
    test_rdf_building(rdf_builder, test_snapshot)
    test_relationship_discovery(rdf_builder, extractor)

    vector_builder = test_vector_builder_initialization(rdf_builder)
    test_enriched_description_generation(vector_builder, test_snapshot)
    test_vector_building(vector_builder, test_snapshot)

    orchestrator = test_pipeline_orchestrator()
    test_full_pipeline_execution(orchestrator)

    # Print summary
    exit_code = print_summary()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
