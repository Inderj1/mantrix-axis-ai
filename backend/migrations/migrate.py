#!/usr/bin/env python3
"""
Database Migration Script for RDF Triples Table

This script can be run directly or imported and called from the application.
It's designed to be idempotent - safe to run multiple times.

Usage:
    python migrate.py                    # Run all pending migrations
    python migrate.py --check            # Check if migrations are needed
    python migrate.py --rollback         # Rollback last migration (destructive!)

Environment Variables:
    POSTGRES_HOST     - Database host
    POSTGRES_PORT     - Database port (default: 5432)
    POSTGRES_USER     - Database username
    POSTGRES_PASSWORD - Database password
    POSTGRES_DATABASE - Database name
"""

import os
import sys
import argparse
from pathlib import Path

# Add backend/src to path for imports
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

from src.db.postgresql_client import PostgreSQLClient
from src.db.models.rdf_triple import CREATE_TABLE_SQL, DROP_TABLE_SQL


def get_db_client() -> PostgreSQLClient:
    """Create a PostgreSQL client using environment variables."""
    return PostgreSQLClient(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        database=os.getenv("POSTGRES_DATABASE", "mantrix")
    )


def check_table_exists(client: PostgreSQLClient, table_name: str) -> bool:
    """Check if a table exists in the database."""
    query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = %s
        )
    """
    result = client.execute_query(query, (table_name,))
    return result[0]['exists'] if result else False


def get_table_count(client: PostgreSQLClient, table_name: str) -> int:
    """Get the row count of a table."""
    try:
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = client.execute_query(query)
        return result[0]['count'] if result else 0
    except Exception:
        return 0


def run_migration(client: PostgreSQLClient) -> bool:
    """
    Run the RDF triples table migration.

    Returns:
        True if migration was applied, False if already exists
    """
    table_name = "rdf_triples"

    if check_table_exists(client, table_name):
        print(f"[INFO] Table '{table_name}' already exists. Skipping migration.")
        count = get_table_count(client, table_name)
        print(f"[INFO] Current row count: {count}")
        return False

    print(f"[INFO] Creating table '{table_name}'...")

    try:
        # Execute the CREATE TABLE SQL
        client.execute_query(CREATE_TABLE_SQL)
        print(f"[SUCCESS] Table '{table_name}' created successfully!")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create table: {e}")
        raise


def run_rollback(client: PostgreSQLClient) -> bool:
    """
    Rollback the RDF triples table migration (destructive!).

    Returns:
        True if rollback was applied, False if table didn't exist
    """
    table_name = "rdf_triples"

    if not check_table_exists(client, table_name):
        print(f"[INFO] Table '{table_name}' does not exist. Nothing to rollback.")
        return False

    count = get_table_count(client, table_name)

    if count > 0:
        confirm = input(f"[WARNING] Table has {count} rows. Type 'DELETE' to confirm rollback: ")
        if confirm != "DELETE":
            print("[INFO] Rollback cancelled.")
            return False

    print(f"[INFO] Dropping table '{table_name}'...")

    try:
        client.execute_query(DROP_TABLE_SQL)
        print(f"[SUCCESS] Table '{table_name}' dropped successfully!")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to drop table: {e}")
        raise


def check_migration_status(client: PostgreSQLClient) -> dict:
    """
    Check the current migration status.

    Returns:
        Dictionary with migration status information
    """
    table_name = "rdf_triples"
    exists = check_table_exists(client, table_name)

    status = {
        "table_name": table_name,
        "exists": exists,
        "row_count": 0,
        "needs_migration": not exists
    }

    if exists:
        status["row_count"] = get_table_count(client, table_name)

    return status


def ensure_rdf_table_exists() -> bool:
    """
    Ensure the RDF triples table exists.

    This function is designed to be called on application startup.
    It's idempotent and safe to call multiple times.

    Returns:
        True if table exists (created or already existed)
    """
    try:
        client = get_db_client()

        if not client.test_connection():
            print("[WARNING] Could not connect to PostgreSQL. Skipping RDF table check.")
            return False

        if not check_table_exists(client, "rdf_triples"):
            print("[INFO] RDF triples table not found. Running migration...")
            run_migration(client)

        return True

    except Exception as e:
        print(f"[ERROR] Failed to ensure RDF table exists: {e}")
        return False


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Run database migrations for RDF triples table"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check migration status without making changes"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration (destructive!)"
    )

    args = parser.parse_args()

    # Create database client
    print("[INFO] Connecting to PostgreSQL...")
    client = get_db_client()

    if not client.test_connection():
        print("[ERROR] Could not connect to PostgreSQL. Check your environment variables.")
        sys.exit(1)

    print("[INFO] Connected successfully!")

    if args.check:
        # Just check status
        status = check_migration_status(client)
        print(f"\nMigration Status:")
        print(f"  Table: {status['table_name']}")
        print(f"  Exists: {status['exists']}")
        print(f"  Row Count: {status['row_count']}")
        print(f"  Needs Migration: {status['needs_migration']}")

    elif args.rollback:
        # Rollback migration
        run_rollback(client)

    else:
        # Run migration
        run_migration(client)


if __name__ == "__main__":
    main()
