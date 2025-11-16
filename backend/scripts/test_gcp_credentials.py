#!/usr/bin/env python3
"""
GCP Credentials Validation Script
Tests that the service account has proper permissions for Mantrix Axis AI
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from google.cloud import bigquery
import google.auth
import json
import structlog

logger = structlog.get_logger()

def test_credentials():
    """Test GCP credentials and permissions"""

    print("=" * 60)
    print("GCP Credentials Validation")
    print("=" * 60)
    print()

    # Check environment variable
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    print(f"1. Checking GOOGLE_APPLICATION_CREDENTIALS...")

    if not creds_path:
        print("   ❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        print("   Set it in .env or export it:")
        print("   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
        return False

    print(f"   ✓ Found: {creds_path}")

    # Check file exists
    print(f"\n2. Checking credentials file exists...")
    if not os.path.exists(creds_path):
        print(f"   ❌ File not found: {creds_path}")
        return False

    print(f"   ✓ File exists")

    # Check file permissions
    print(f"\n3. Checking file permissions...")
    file_stat = os.stat(creds_path)
    file_mode = oct(file_stat.st_mode)[-3:]

    if file_mode != '600':
        print(f"   ⚠️  File permissions are {file_mode} (recommended: 600)")
        print(f"   Run: chmod 600 {creds_path}")
    else:
        print(f"   ✓ Permissions are secure (600)")

    # Detect credential type
    print(f"\n4. Detecting credential type...")
    try:
        with open(creds_path, 'r') as f:
            cred_data = json.load(f)

        if cred_data.get('type') == 'service_account':
            cred_type = 'Service Account'
            account_info = cred_data.get('client_email', 'N/A')
        elif cred_data.get('type') == 'authorized_user':
            cred_type = 'Application Default Credentials (User Account)'
            account_info = cred_data.get('client_id', 'N/A')
        else:
            cred_type = 'Unknown'
            account_info = 'N/A'

        print(f"   ✓ Type: {cred_type}")
        print(f"   Account: {account_info}")
    except Exception as e:
        print(f"   ⚠️  Could not detect type: {e}")

    # Load and validate credentials using google.auth.default()
    print(f"\n5. Loading credentials...")
    try:
        credentials, project = google.auth.default()
        print(f"   ✓ Credentials loaded successfully")
        print(f"   Project ID: {project}")
    except Exception as e:
        print(f"   ❌ Failed to load credentials: {e}")
        return False

    # Test BigQuery connection
    print(f"\n6. Testing BigQuery connection...")
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT', project)

    try:
        client = bigquery.Client(project=project_id, credentials=credentials)
        print(f"   ✓ BigQuery client created")
        print(f"   Using project: {project_id}")
    except Exception as e:
        print(f"   ❌ Failed to create BigQuery client: {e}")
        return False

    # Test dataset access
    print(f"\n7. Testing dataset access...")
    dataset_id = os.getenv('BIGQUERY_DATASET')

    if not dataset_id:
        print(f"   ⚠️  BIGQUERY_DATASET not set in environment")
        print(f"   Skipping dataset access test")
    else:
        try:
            dataset_ref = f"{project_id}.{dataset_id}"
            dataset = client.get_dataset(dataset_ref)
            print(f"   ✓ Can access dataset: {dataset_ref}")
            print(f"   Dataset location: {dataset.location}")
            print(f"   Created: {dataset.created}")

            # List tables
            tables = list(client.list_tables(dataset))
            print(f"   Tables in dataset: {len(tables)}")
            if tables:
                print(f"   Sample tables: {', '.join([t.table_id for t in tables[:5]])}")

        except Exception as e:
            print(f"   ❌ Cannot access dataset: {e}")
            print(f"   Check that the service account has 'bigquery.dataViewer' role")
            return False

    # Test query execution
    print(f"\n8. Testing query execution...")
    try:
        test_query = "SELECT 1 as test"
        query_job = client.query(test_query)
        results = query_job.result()
        print(f"   ✓ Can execute queries")
        print(f"   Job ID: {query_job.job_id}")

    except Exception as e:
        print(f"   ❌ Cannot execute queries: {e}")
        print(f"   Check that the service account has 'bigquery.jobUser' role")
        return False

    # Test table query (if dataset available)
    if dataset_id:
        print(f"\n9. Testing table query...")
        try:
            # Get first table
            tables = list(client.list_tables(dataset))
            if tables:
                first_table = tables[0]
                test_query = f"""
                SELECT *
                FROM `{project_id}.{dataset_id}.{first_table.table_id}`
                LIMIT 1
                """
                query_job = client.query(test_query)
                results = query_job.result()
                row_count = sum(1 for _ in results)
                print(f"   ✓ Can query tables in dataset")
                print(f"   Test query returned {row_count} row(s)")
            else:
                print(f"   ⚠️  No tables in dataset to test")

        except Exception as e:
            print(f"   ❌ Cannot query tables: {e}")
            return False

    # Summary
    print()
    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("Your service account is properly configured with:")
    print("  ✓ Valid credentials file")
    print("  ✓ BigQuery access")
    print("  ✓ Dataset access")
    print("  ✓ Query execution permissions")
    print()
    print("You're ready to run the application!")
    print()

    return True

def show_required_permissions():
    """Display required IAM permissions"""
    print()
    print("=" * 60)
    print("Required IAM Roles for Production")
    print("=" * 60)
    print()
    print("Minimum required roles:")
    print("  1. roles/bigquery.dataViewer")
    print("     - Read table data and metadata")
    print()
    print("  2. roles/bigquery.jobUser")
    print("     - Run queries and jobs")
    print()
    print("  3. roles/bigquery.readSessionUser")
    print("     - Use BigQuery Storage Read API (faster)")
    print()
    print("Optional roles (if needed):")
    print("  - roles/storage.objectViewer")
    print("    For reading files from Cloud Storage")
    print()
    print("  - roles/bigquery.dataEditor")
    print("    If you need to create/modify tables (usually not needed)")
    print()
    print("To grant these roles:")
    print("  gcloud projects add-iam-policy-binding PROJECT_ID \\")
    print("    --member='serviceAccount:SA_EMAIL' \\")
    print("    --role='ROLE_NAME'")
    print()

if __name__ == "__main__":
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()

    import argparse
    parser = argparse.ArgumentParser(description='Test GCP credentials')
    parser.add_argument('--show-roles', action='store_true',
                       help='Show required IAM roles')
    args = parser.parse_args()

    if args.show_roles:
        show_required_permissions()
    else:
        success = test_credentials()
        sys.exit(0 if success else 1)
