# GCP Service Account Setup Guide

Complete guide for setting up Google Cloud Platform service accounts for Mantrix Axis AI production deployment.

## Table of Contents
- [Quick Start](#quick-start)
- [Manual Setup](#manual-setup)
- [Required IAM Roles](#required-iam-roles)
- [Testing & Validation](#testing--validation)
- [Production Deployment](#production-deployment)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Automated Setup (Recommended)

```bash
cd backend

# Make the setup script executable
chmod +x setup_service_account.sh

# Run the setup script
./setup_service_account.sh
```

The script will:
1. Create a service account
2. Grant necessary BigQuery permissions
3. Generate and download a JSON key file
4. Update your `.env` file
5. Set secure file permissions

### Verify Setup

```bash
# Activate virtual environment
source venv/bin/activate

# Install python-dotenv if not already installed
pip install python-dotenv

# Run validation tests
python test_gcp_credentials.py
```

---

## Manual Setup

### 1. Prerequisites

- GCP account with project admin access
- `gcloud` CLI installed and authenticated
- Project ID (e.g., `arizona-poc`)

Install gcloud CLI:
```bash
# macOS
brew install --cask google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate
gcloud auth login
```

### 2. Create Service Account

```bash
# Set your project
export PROJECT_ID="arizona-poc"
gcloud config set project $PROJECT_ID

# Create service account
export SA_NAME="mantrix-axis-ai-prod"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create $SA_NAME \
  --display-name="Mantrix Axis AI Production" \
  --description="Service account for Mantrix Axis AI production deployment"
```

### 3. Grant IAM Roles

```bash
# BigQuery Data Viewer - Read table data and metadata
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.dataViewer"

# BigQuery Job User - Execute queries
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.jobUser"

# BigQuery Read Session User - Use Storage Read API for faster queries
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.readSessionUser"
```

### 4. Create and Download Key

```bash
# Create credentials directory
mkdir -p credentials

# Generate key file
gcloud iam service-accounts keys create credentials/gcp-key-prod.json \
  --iam-account=$SA_EMAIL

# Set secure permissions (readable only by owner)
chmod 600 credentials/gcp-key-prod.json
```

### 5. Configure Environment

Add to your `.env` file:
```bash
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/backend/credentials/gcp-key-prod.json
GOOGLE_CLOUD_PROJECT=arizona-poc
BIGQUERY_DATASET=copa_export_copa_data_000000000000
```

---

## Required IAM Roles

### Minimum Required (Read-Only Access)

| Role | Purpose | Permissions |
|------|---------|-------------|
| `roles/bigquery.dataViewer` | Read table data and metadata | `bigquery.tables.getData`<br>`bigquery.tables.get`<br>`bigquery.datasets.get` |
| `roles/bigquery.jobUser` | Run queries and jobs | `bigquery.jobs.create`<br>`bigquery.jobs.get` |
| `roles/bigquery.readSessionUser` | Use Storage Read API | `bigquery.readsessions.create`<br>`bigquery.readsessions.getData` |

### Optional Roles

| Role | When Needed | Purpose |
|------|-------------|---------|
| `roles/storage.objectViewer` | Using Cloud Storage | Read files from GCS buckets |
| `roles/bigquery.dataEditor` | Creating/modifying tables | Write data to BigQuery (usually not needed) |
| `roles/logging.logWriter` | Custom logging | Write to Cloud Logging |

### Grant Role to Service Account

```bash
# Syntax
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA_EMAIL" \
  --role="ROLE_NAME"

# Example
gcloud projects add-iam-policy-binding arizona-poc \
  --member="serviceAccount:mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"
```

### Grant Role for Specific Dataset (More Restrictive)

```bash
# Get dataset reference
bq show --format=prettyjson \
  ${PROJECT_ID}:${DATASET_ID} > /tmp/dataset.json

# Add IAM policy for dataset
bq update \
  --source /tmp/dataset.json \
  ${PROJECT_ID}:${DATASET_ID}
```

---

## Testing & Validation

### Run Validation Script

```bash
cd backend
source venv/bin/activate
python test_gcp_credentials.py
```

Expected output:
```
=================================================
GCP Credentials Validation
=================================================

1. Checking GOOGLE_APPLICATION_CREDENTIALS...
   ✓ Found: /path/to/credentials/gcp-key-prod.json

2. Checking credentials file exists...
   ✓ File exists

3. Checking file permissions...
   ✓ Permissions are secure (600)

4. Loading service account credentials...
   ✓ Credentials loaded successfully
   Service Account: mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com
   Project ID: arizona-poc

5. Testing BigQuery connection...
   ✓ BigQuery client created
   Using project: arizona-poc

6. Testing dataset access...
   ✓ Can access dataset: arizona-poc.copa_export_copa_data_000000000000
   Dataset location: US
   Tables in dataset: 42

7. Testing query execution...
   ✓ Can execute queries

8. Testing table query...
   ✓ Can query tables in dataset

=================================================
✅ ALL TESTS PASSED!
=================================================
```

### Manual Test

```python
from google.cloud import bigquery
import os

# Load credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/key.json'

# Create client
client = bigquery.Client(project='arizona-poc')

# Test query
query = """
SELECT COUNT(*) as count
FROM `arizona-poc.copa_export_copa_data_000000000000.your_table`
"""

results = client.query(query).result()
for row in results:
    print(f"Count: {row.count}")
```

---

## Production Deployment

### Option 1: Docker Container

```yaml
# docker-compose.yml
services:
  api:
    environment:
      GOOGLE_APPLICATION_CREDENTIALS: /app/credentials/gcp-key.json
    volumes:
      - ./credentials/gcp-key-prod.json:/app/credentials/gcp-key.json:ro
    # Read-only mount for security
```

### Option 2: Kubernetes Secret

```bash
# Create secret from key file
kubectl create secret generic gcp-credentials \
  --from-file=key.json=credentials/gcp-key-prod.json

# Use in deployment
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
    env:
    - name: GOOGLE_APPLICATION_CREDENTIALS
      value: /var/secrets/google/key.json
    volumeMounts:
    - name: gcp-credentials
      mountPath: /var/secrets/google
      readOnly: true
  volumes:
  - name: gcp-credentials
    secret:
      secretName: gcp-credentials
```

### Option 3: GKE Workload Identity (Best for GKE)

```bash
# 1. Enable Workload Identity
gcloud container clusters update CLUSTER_NAME \
  --workload-pool=PROJECT_ID.svc.id.goog

# 2. Create Kubernetes service account
kubectl create serviceaccount mantrix-app-sa

# 3. Bind to GCP service account
gcloud iam service-accounts add-iam-policy-binding \
  $SA_EMAIL \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/mantrix-app-sa]"

# 4. Annotate K8s service account
kubectl annotate serviceaccount mantrix-app-sa \
  iam.gke.io/gcp-service-account=$SA_EMAIL

# 5. Use in deployment (no credentials file needed!)
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: mantrix-app-sa
  containers:
  - name: app
    # GOOGLE_APPLICATION_CREDENTIALS not needed!
```

### Option 4: Cloud Run

```bash
# Deploy to Cloud Run with service account
gcloud run deploy mantrix-axis-ai \
  --image gcr.io/PROJECT_ID/mantrix-axis-ai \
  --service-account $SA_EMAIL \
  --region us-central1
```

---

## Security Best Practices

### 1. Key Management

```bash
# ✅ DO: Set restrictive file permissions
chmod 600 credentials/*.json

# ✅ DO: Use environment variables
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

# ❌ DON'T: Commit keys to git
# Already protected in .gitignore

# ❌ DON'T: Share keys between environments
# Use separate keys for dev/staging/prod
```

### 2. Key Rotation

```bash
# List existing keys
gcloud iam service-accounts keys list \
  --iam-account=$SA_EMAIL

# Create new key
gcloud iam service-accounts keys create credentials/gcp-key-new.json \
  --iam-account=$SA_EMAIL

# Update application to use new key
# Then delete old key
gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=$SA_EMAIL
```

**Rotation Schedule:**
- Production: Every 90 days
- Development: Every 180 days
- Set calendar reminders!

### 3. Least Privilege

```bash
# ✅ DO: Grant minimum required roles
# Only bigquery.dataViewer, bigquery.jobUser, bigquery.readSessionUser

# ❌ DON'T: Grant broad permissions
# Avoid: roles/owner, roles/editor, roles/bigquery.admin

# ✅ DO: Use dataset-level permissions when possible
# More restrictive than project-level
```

### 4. Monitoring & Auditing

```bash
# View service account activity
gcloud logging read \
  "protoPayload.authenticationInfo.principalEmail=$SA_EMAIL" \
  --limit 50 \
  --format json

# Set up alerts for unusual activity
# Cloud Console > Logging > Logs-based Metrics
```

### 5. Secret Management (Production)

Use Google Secret Manager instead of files:

```bash
# Store key in Secret Manager
gcloud secrets create mantrix-gcp-key \
  --data-file=credentials/gcp-key-prod.json

# Grant access to service account
gcloud secrets add-iam-policy-binding mantrix-gcp-key \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

# Access in application
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
name = f"projects/PROJECT_ID/secrets/mantrix-gcp-key/versions/latest"
response = client.access_secret_version(request={"name": name})
credentials_json = response.payload.data.decode("UTF-8")
```

---

## Troubleshooting

### Error: "Permission denied"

```
google.api_core.exceptions.PermissionDenied: 403 Permission denied
```

**Solutions:**
1. Verify service account has required roles:
   ```bash
   gcloud projects get-iam-policy $PROJECT_ID \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount:$SA_EMAIL"
   ```

2. Check dataset-level permissions:
   ```bash
   bq show --format=prettyjson $PROJECT_ID:$DATASET_ID
   ```

3. Ensure key is not expired:
   ```bash
   gcloud iam service-accounts keys list --iam-account=$SA_EMAIL
   ```

### Error: "File not found"

```
FileNotFoundError: File /path/to/key.json was not found
```

**Solutions:**
1. Use absolute path in `GOOGLE_APPLICATION_CREDENTIALS`
2. Check file exists: `ls -la credentials/`
3. Verify path in `.env` file

### Error: "Invalid credentials"

```
google.auth.exceptions.DefaultCredentialsError: File /path/to/key.json is not a valid service account credential file
```

**Solutions:**
1. Verify JSON file is valid: `cat credentials/gcp-key.json | jq`
2. Re-download key from GCP Console
3. Check file isn't corrupted: `file credentials/gcp-key.json`

### Error: "Timeout" or "Connection refused"

```
ConnectionRefused: [Errno 111] Connection refused
```

**Solutions:**
1. Check network connectivity
2. Verify firewall rules allow egress to `*.googleapis.com`
3. Try with VPN disabled (corporate networks may block)

### Test Queries Failing

```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG

# Test with gcloud CLI directly
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) FROM `arizona-poc.copa_export_copa_data_000000000000.BKPF`'

# Check quotas
gcloud compute project-info describe --project=$PROJECT_ID
```

---

## Additional Resources

- [GCP Service Accounts Documentation](https://cloud.google.com/iam/docs/service-accounts)
- [BigQuery IAM Roles](https://cloud.google.com/bigquery/docs/access-control)
- [Best Practices for Service Accounts](https://cloud.google.com/iam/docs/best-practices-service-accounts)
- [Workload Identity for GKE](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)

---

## Quick Reference

### Common Commands

```bash
# List service accounts
gcloud iam service-accounts list

# Describe service account
gcloud iam service-accounts describe $SA_EMAIL

# List keys
gcloud iam service-accounts keys list --iam-account=$SA_EMAIL

# Test authentication
gcloud auth activate-service-account --key-file=credentials/gcp-key.json
gcloud auth list

# Revoke authentication
gcloud auth revoke $SA_EMAIL
```

### Environment Variables

```bash
# Required
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials/gcp-key-prod.json
GOOGLE_CLOUD_PROJECT=arizona-poc
BIGQUERY_DATASET=copa_export_copa_data_000000000000

# Optional
BIGQUERY_QUERY_TIMEOUT_SECONDS=60
DEFAULT_QUERY_TIMEOUT_SECONDS=60
```

---

## Support

For issues or questions:
1. Run validation script: `python test_gcp_credentials.py`
2. Check logs: `tail -f logs/backend.log`
3. Review this guide's troubleshooting section
4. Contact DevOps team with error details
