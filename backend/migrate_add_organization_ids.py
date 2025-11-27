#!/usr/bin/env python3
"""
Migration script to add organization IDs to existing data.

This script:
1. Updates MongoDB connector configurations with organization_id
2. Re-indexes RDF triples with new namespace format (org_id + database_type + table_name)
3. Re-indexes Weaviate vectors with organization and database metadata

Usage:
    python migrate_add_organization_ids.py [--org-id=<org_id>] [--dry-run]
"""

import os
import sys
import argparse
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog
from pymongo import MongoClient
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import settings
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.multi_db_schema_extractor import MultiDatabaseSchemaExtractor
from src.pipeline.rdf_builder import RDFBuilder
from src.pipeline.vector_builder import VectorBuilder
from src.core.knowledge_graph.jena_singleton import get_jena_knowledge_graph
from src.db.weaviate_client import WeaviateClient

# Load environment variables
load_dotenv()

# Configure logging
logger = structlog.get_logger()

class OrganizationMigrator:
    """Migrate existing data to include organization IDs."""

    def __init__(self, default_org_id: str = 'default', dry_run: bool = False):
        """
        Initialize migrator.

        Args:
            default_org_id: Default organization ID to use for existing data
            dry_run: If True, only show what would be changed without making changes
        """
        self.default_org_id = default_org_id
        self.dry_run = dry_run

        # Initialize clients
        self.mongo_client = MongoClient(settings.mongodb_url)
        self.db = self.mongo_client['mantrix_axis_ai']
        self.connectors_collection = self.db['database_connectors']

        # Initialize components
        self.weaviate_client = WeaviateClient()
        self.knowledge_graph = get_jena_knowledge_graph()

        logger.info(
            "Migrator initialized",
            organization_id=default_org_id,
            dry_run=dry_run
        )

    def migrate_mongodb_connectors(self):
        """Add organization_id to existing MongoDB connector configurations."""
        logger.info("Starting MongoDB connector migration")

        # Find connectors without organization_id
        connectors = list(self.connectors_collection.find(
            {"organization_id": {"$exists": False}}
        ))

        if not connectors:
            logger.info("No connectors need migration")
            return

        logger.info(f"Found {len(connectors)} connectors to migrate")

        for connector in connectors:
            connector_id = connector['_id']
            connector_name = connector.get('name', 'Unknown')

            if self.dry_run:
                logger.info(
                    "[DRY RUN] Would update connector",
                    connector_id=str(connector_id),
                    name=connector_name,
                    organization_id=self.default_org_id
                )
            else:
                # Update connector with organization_id
                result = self.connectors_collection.update_one(
                    {"_id": connector_id},
                    {
                        "$set": {
                            "organization_id": self.default_org_id,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

                if result.modified_count > 0:
                    logger.info(
                        "Updated connector",
                        connector_id=str(connector_id),
                        name=connector_name,
                        organization_id=self.default_org_id
                    )
                else:
                    logger.warning(
                        "Failed to update connector",
                        connector_id=str(connector_id),
                        name=connector_name
                    )

        logger.info(
            "MongoDB connector migration complete",
            migrated_count=len(connectors)
        )

    def clear_existing_rdf_data(self):
        """Clear existing RDF data (without namespace prefixes)."""
        if self.dry_run:
            logger.info("[DRY RUN] Would clear existing RDF data")
            return

        logger.info("Clearing existing RDF data")

        try:
            # Clear all existing triples
            # Note: In production, you might want to be more selective
            query = """
            DELETE WHERE {
                ?s ?p ?o
            }
            """
            self.knowledge_graph.update(query)
            logger.info("Cleared existing RDF data")
        except Exception as e:
            logger.error(f"Failed to clear RDF data: {e}")

    def clear_existing_vectors(self):
        """Clear existing Weaviate vectors."""
        if self.dry_run:
            logger.info("[DRY RUN] Would clear existing Weaviate vectors")
            return

        logger.info("Clearing existing Weaviate vectors")

        try:
            # Delete existing TableSchema class and recreate
            self.weaviate_client.client.schema.delete_class("TableSchema")
            self.weaviate_client.create_schema()
            logger.info("Cleared and recreated Weaviate schema")
        except Exception as e:
            logger.warning(f"Failed to clear Weaviate vectors: {e}")

    async def reindex_all_databases(self):
        """Re-index all databases with organization context."""
        logger.info("Starting database re-indexing")

        if self.dry_run:
            logger.info("[DRY RUN] Would re-index all databases with organization context")
            # Show what would be indexed
            connectors = list(self.connectors_collection.find({"enabled": True}))
            for connector in connectors:
                logger.info(
                    "[DRY RUN] Would index database",
                    name=connector.get('name'),
                    type=connector.get('connector_type'),
                    organization_id=connector.get('organization_id', self.default_org_id)
                )
            return

        try:
            # Create pipeline orchestrator
            orchestrator = PipelineOrchestrator()

            # Execute full pipeline (will use updated connector configs)
            logger.info("Executing pipeline to re-index all databases")
            await orchestrator.execute_pipeline_async()

            logger.info("Database re-indexing complete")
        except Exception as e:
            logger.error(f"Failed to re-index databases: {e}")
            raise

    def verify_migration(self):
        """Verify the migration was successful."""
        logger.info("Verifying migration")

        # Check MongoDB connectors
        connectors_without_org = self.connectors_collection.count_documents(
            {"organization_id": {"$exists": False}}
        )
        connectors_with_org = self.connectors_collection.count_documents(
            {"organization_id": {"$exists": True}}
        )

        logger.info(
            "MongoDB verification",
            with_org_id=connectors_with_org,
            without_org_id=connectors_without_org
        )

        # Check RDF data (sample query)
        try:
            query = f"""
            PREFIX fin: <http://example.com/finance#>

            SELECT (COUNT(?table) as ?count)
            WHERE {{
                ?table a fin:Table_{self.default_org_id}_bigquery_* .
            }}
            """
            results = self.knowledge_graph.query(query)
            if results:
                logger.info(
                    "RDF verification",
                    namespaced_tables=results[0].get('count', 0)
                )
        except Exception as e:
            logger.warning(f"RDF verification failed: {e}")

        # Check Weaviate vectors
        try:
            # Search for any table with organization context
            test_query = "customer"
            test_embedding = self.weaviate_client.llm_client.generate_embedding(test_query)
            results = self.weaviate_client.search_similar_tables(
                test_embedding,
                limit=1,
                organization_id=self.default_org_id
            )

            logger.info(
                "Weaviate verification",
                can_search_with_org=len(results) > 0
            )
        except Exception as e:
            logger.warning(f"Weaviate verification failed: {e}")

        return connectors_without_org == 0

    async def run_migration(self):
        """Run the complete migration."""
        logger.info("Starting organization ID migration")
        start_time = datetime.utcnow()

        try:
            # Step 1: Update MongoDB connectors
            self.migrate_mongodb_connectors()

            # Step 2: Clear old data (optional, be careful in production!)
            if not self.dry_run:
                response = input("\nDo you want to clear existing RDF/vector data? This will re-index everything. (y/N): ")
                if response.lower() == 'y':
                    self.clear_existing_rdf_data()
                    self.clear_existing_vectors()

                    # Step 3: Re-index all databases
                    await self.reindex_all_databases()
                else:
                    logger.warning("Skipping re-indexing. Existing data may not have organization context.")

            # Step 4: Verify migration
            success = self.verify_migration()

            elapsed = (datetime.utcnow() - start_time).total_seconds()

            if success:
                logger.info(
                    "Migration completed successfully",
                    elapsed_seconds=elapsed
                )
            else:
                logger.warning(
                    "Migration completed with warnings",
                    elapsed_seconds=elapsed
                )

            return success

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate existing data to include organization IDs"
    )
    parser.add_argument(
        '--org-id',
        type=str,
        default='default',
        help='Default organization ID to use for existing data (default: "default")'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making any changes'
    )

    args = parser.parse_args()

    # Create migrator
    migrator = OrganizationMigrator(
        default_org_id=args.org_id,
        dry_run=args.dry_run
    )

    # Run migration
    try:
        success = asyncio.run(migrator.run_migration())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()