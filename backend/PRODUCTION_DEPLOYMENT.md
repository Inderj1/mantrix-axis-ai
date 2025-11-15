# Production Deployment Guide - Without Service Account Keys

Your organization has the `constraints/iam.disableServiceAccountKeyCreation` policy enabled, which **prevents creating service account JSON key files**. This is a **security best practice** that prevents key leakage and theft.

## Quick Summary

✅ **Local Development**: Use Application Default Credentials (ADC) - your user account
✅ **Production**: Use platform-native service account attachment (NO key files needed!)

---

## Table of Contents
- [Understanding the Constraint](#understanding-the-constraint)
- [Local Development Setup](#local-development-setup)
- [Production Options](#production-options)
  - [Option 1: Cloud Run (Easiest)](#option-1-cloud-run-easiest)
  - [Option 2: GKE with Workload Identity (Best Practice)](#option-2-gke-with-workload-identity-best-practice)
  - [Option 3: Compute Engine / VM](#option-3-compute-engine--vm)
  - [Option 4: Non-GCP with Workload Identity Federation](#option-4-non-gcp-with-workload-identity-federation)
- [Service Account Already Created](#service-account-already-created)
- [Deployment Examples](#deployment-examples)

---

## Understanding the Constraint

### What is `constraints/iam.disableServiceAccountKeyCreation`?

This is an **Organization Policy** that prevents creating downloadable JSON key files for service accounts.

**Why it's good:**
- ✅ Prevents key theft and leakage
- ✅ Eliminates key rotation burden
- ✅ Forces use of better authentication methods
- ✅ Meets compliance requirements (SOC2, ISO27001)

**Impact:**
- ❌ Can't use `gcloud iam service-accounts keys create`
- ✅ Can still use service accounts via platform attachment
- ✅ Can still use Application Default Credentials for local dev

### Service Account Already Created

During setup, we successfully created:
- **Service Account**: `mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com`
- **Permissions Granted**:
  - `roles/bigquery.dataViewer` - Read table data
  - `roles/bigquery.jobUser` - Execute queries
  - `roles/bigquery.readSessionUser` - Fast reads via Storage API

We just can't create a JSON key file for it. Instead, we'll **attach** it to compute resources.

---

## Local Development Setup

### ✅ Already Completed

You've already set this up! Your local environment uses:

```bash
# Your user credentials (not a service account)
GOOGLE_APPLICATION_CREDENTIALS=/Users/jay/.config/gcloud/application_default_credentials.json
```

### How It Works

1. You authenticated with: `gcloud auth application-default login`
2. This created credentials at `~/.config/gcloud/application_default_credentials.json`
3. These are **your user credentials** with your GCP permissions
4. The BigQuery client automatically uses these credentials

### Refresh When Expired

ADC credentials expire after ~1 hour. To refresh:

```bash
gcloud auth application-default login
```

---

## Production Options

### Option 1: Cloud Run (Easiest)

**Best for:** Serverless deployments, auto-scaling applications

Cloud Run can **attach the service account directly** to your container - no keys needed!

#### Step 1: Build and Push Image

```bash
cd /Users/jay/Workspace/Cloudmantra_code/mantrix-axis-ai

# Build Docker image
docker build -t gcr.io/arizona-poc/mantrix-axis-ai:latest .

# Push to Google Container Registry
docker push gcr.io/arizona-poc/mantrix-axis-ai:latest
```

#### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy mantrix-axis-ai \
  --image gcr.io/arizona-poc/mantrix-axis-ai:latest \
  --platform managed \
  --region us-central1 \
  --service-account mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=arizona-poc,BIGQUERY_DATASET=copa_export_copa_data_000000000000,ANTHROPIC_API_KEY=your-key"
```

**Key flags:**
- `--service-account`: Attaches our service account (NO key file needed!)
- `--set-env-vars`: Pass environment variables
- **DO NOT** set `GOOGLE_APPLICATION_CREDENTIALS` - Cloud Run provides it automatically!

#### Step 3: Update Your Dockerfile (if needed)

Make sure your Dockerfile **does NOT require** `GOOGLE_APPLICATION_CREDENTIALS`:

```dockerfile
# Good - no GOOGLE_APPLICATION_CREDENTIALS needed
FROM python:3.9-slim

WORKDIR /app
COPY backend/ /app/

RUN pip install -r requirements.txt

# Don't set GOOGLE_APPLICATION_CREDENTIALS here!
# Cloud Run provides it automatically

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Option 2: GKE with Workload Identity (Best Practice)

**Best for:** Kubernetes deployments, multi-service architectures

Workload Identity lets Kubernetes pods **impersonate GCP service accounts** without keys.

#### Step 1: Enable Workload Identity on Cluster

```bash
# For new cluster
gcloud container clusters create mantrix-cluster \
  --region us-central1 \
  --workload-pool=arizona-poc.svc.id.goog \
  --enable-ip-alias

# For existing cluster
gcloud container clusters update YOUR_CLUSTER_NAME \
  --region us-central1 \
  --workload-pool=arizona-poc.svc.id.goog
```

#### Step 2: Create Kubernetes Service Account

```bash
kubectl create namespace mantrix-prod

kubectl create serviceaccount mantrix-app-ksa \
  --namespace mantrix-prod
```

#### Step 3: Bind K8s SA to GCP SA

```bash
# Allow K8s service account to impersonate GCP service account
gcloud iam service-accounts add-iam-policy-binding \
  mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:arizona-poc.svc.id.goog[mantrix-prod/mantrix-app-ksa]"

# Annotate K8s service account
kubectl annotate serviceaccount mantrix-app-ksa \
  --namespace mantrix-prod \
  iam.gke.io/gcp-service-account=mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com
```

#### Step 4: Deploy Application

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mantrix-axis-ai
  namespace: mantrix-prod
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mantrix-axis-ai
  template:
    metadata:
      labels:
        app: mantrix-axis-ai
    spec:
      serviceAccountName: mantrix-app-ksa  # Use K8s service account
      containers:
      - name: api
        image: gcr.io/arizona-poc/mantrix-axis-ai:latest
        ports:
        - containerPort: 8000
        env:
        - name: GOOGLE_CLOUD_PROJECT
          value: "arizona-poc"
        - name: BIGQUERY_DATASET
          value: "copa_export_copa_data_000000000000"
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: mantrix-secrets
              key: anthropic-api-key
        # DO NOT set GOOGLE_APPLICATION_CREDENTIALS!
        # Workload Identity provides it automatically
```

Apply:
```bash
kubectl apply -f deployment.yaml
```

---

### Option 3: Compute Engine / VM

**Best for:** VM-based deployments, legacy applications

Compute Engine VMs can **attach service accounts** directly.

#### Step 1: Create VM with Service Account

```bash
gcloud compute instances create mantrix-vm \
  --zone us-central1-a \
  --machine-type n1-standard-2 \
  --service-account mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com \
  --scopes cloud-platform \
  --image-family ubuntu-2204-lts \
  --image-project ubuntu-os-cloud
```

#### Step 2: SSH and Deploy

```bash
gcloud compute ssh mantrix-vm --zone us-central1-a

# On the VM
git clone https://github.com/your-repo/mantrix-axis-ai.git
cd mantrix-axis-ai/backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables (NO GOOGLE_APPLICATION_CREDENTIALS!)
export GOOGLE_CLOUD_PROJECT=arizona-poc
export BIGQUERY_DATASET=copa_export_copa_data_000000000000

# Run application
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**Important:** Do NOT set `GOOGLE_APPLICATION_CREDENTIALS` on the VM. The Google Cloud client libraries will automatically use the VM's attached service account.

#### Step 3: Update Existing VM

If you have an existing VM:

```bash
gcloud compute instances stop mantrix-vm --zone us-central1-a

gcloud compute instances set-service-account mantrix-vm \
  --zone us-central1-a \
  --service-account mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com \
  --scopes cloud-platform

gcloud compute instances start mantrix-vm --zone us-central1-a
```

---

### Option 4: Non-GCP with Workload Identity Federation

**Best for:** AWS, Azure, on-premises, or other cloud providers

Workload Identity Federation lets **external workloads** authenticate to GCP without keys.

#### Example: AWS EKS to GCP BigQuery

```bash
# 1. Create Workload Identity Pool
gcloud iam workload-identity-pools create aws-pool \
  --location="global" \
  --display-name="AWS Pool"

# 2. Create AWS Provider
gcloud iam workload-identity-pools providers create-aws aws-provider \
  --location="global" \
  --workload-identity-pool="aws-pool" \
  --account-id="YOUR_AWS_ACCOUNT_ID"

# 3. Grant access to service account
gcloud iam service-accounts add-iam-policy-binding \
  mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/aws-pool/*"

# 4. Get configuration file
gcloud iam workload-identity-pools create-cred-config \
  projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/aws-pool/providers/aws-provider \
  --service-account=mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com \
  --output-file=aws-config.json \
  --aws
```

Then in your AWS environment:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/aws-config.json
```

[Full Guide](https://cloud.google.com/iam/docs/workload-identity-federation-with-other-clouds)

---

## Deployment Examples

### Docker Compose (Development/Testing Only)

For local testing with multiple services:

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      GOOGLE_CLOUD_PROJECT: arizona-poc
      BIGQUERY_DATASET: copa_export_copa_data_000000000000
      # Use ADC from host
      GOOGLE_APPLICATION_CREDENTIALS: /root/.config/gcloud/application_default_credentials.json
    volumes:
      # Mount your ADC credentials
      - ~/.config/gcloud:/root/.config/gcloud:ro
```

**Note:** This works for local testing but NOT for production!

### Environment Variables

**Local Development (.env):**
```bash
GOOGLE_APPLICATION_CREDENTIALS=/Users/jay/.config/gcloud/application_default_credentials.json
GOOGLE_CLOUD_PROJECT=arizona-poc
BIGQUERY_DATASET=copa_export_copa_data_000000000000
```

**Production (Cloud Run / GKE / Compute Engine):**
```bash
# DO NOT SET GOOGLE_APPLICATION_CREDENTIALS!
# The platform provides it automatically

GOOGLE_CLOUD_PROJECT=arizona-poc
BIGQUERY_DATASET=copa_export_copa_data_000000000000
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
REDIS_HOST=10.x.x.x
MONGODB_URL=mongodb://...
```

---

## Verification

### Test Production Authentication

After deploying, verify the service account is working:

```bash
# Cloud Run
gcloud run services describe mantrix-axis-ai \
  --region us-central1 \
  --format="value(spec.template.spec.serviceAccountName)"

# GKE Pod
kubectl exec -it POD_NAME -- python3 -c "
import google.auth
credentials, project = google.auth.default()
print(f'Using project: {project}')
print(f'Credentials type: {type(credentials).__name__}')
"

# Compute Engine VM
gcloud compute ssh mantrix-vm -- \
  'curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email'
```

Expected output: `mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com`

---

## Common Issues & Solutions

### Issue: "Could not automatically determine credentials"

**Cause:** `GOOGLE_APPLICATION_CREDENTIALS` is set but file doesn't exist on the container/VM

**Solution:**
- **Cloud Run/GKE/Compute Engine:** Remove `GOOGLE_APPLICATION_CREDENTIALS` environment variable entirely
- The platform automatically provides credentials via metadata server

### Issue: "Permission denied" in production

**Cause:** Service account lacks required roles

**Solution:**
```bash
# Verify roles
gcloud projects get-iam-policy arizona-poc \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com"

# Add missing role
gcloud projects add-iam-policy-binding arizona-poc \
  --member="serviceAccount:mantrix-axis-ai-prod@arizona-poc.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"
```

### Issue: "Service account not found" when deploying

**Cause:** Service account doesn't exist or wrong project

**Solution:**
```bash
# List service accounts
gcloud iam service-accounts list --project arizona-poc

# If missing, create it
gcloud iam service-accounts create mantrix-axis-ai-prod \
  --display-name="Mantrix Axis AI Production" \
  --project arizona-poc
```

---

## Best Practices Summary

### ✅ DO

- Use Application Default Credentials for local development
- Attach service accounts to compute resources in production
- Use Workload Identity for GKE
- Use Cloud Run for serverless deployments
- Keep `GOOGLE_APPLICATION_CREDENTIALS` unset in production
- Use Secret Manager for API keys

### ❌ DON'T

- Don't request exemption from the org policy (defeats security)
- Don't set `GOOGLE_APPLICATION_CREDENTIALS` in production containers
- Don't share your ADC credentials (`~/.config/gcloud/`) with others
- Don't commit credentials to git (already protected by `.gitignore`)
- Don't use ADC credentials in production environments

---

## Migration Checklist

- [ ] Local development using ADC ✅ (Already done!)
- [ ] Service account created with permissions ✅ (Already done!)
- [ ] Choose production platform (Cloud Run / GKE / Compute Engine)
- [ ] Update Dockerfile to not require `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Deploy with service account attached
- [ ] Verify authentication works in production
- [ ] Update CI/CD pipelines
- [ ] Document deployment process for team

---

## Additional Resources

- [Workload Identity (GKE)](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Cloud Run Service Identity](https://cloud.google.com/run/docs/securing/service-identity)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
- [Best Practices for Service Accounts](https://cloud.google.com/iam/docs/best-practices-service-accounts)

---

## Questions?

**For local development issues:**
- Run: `python test_gcp_credentials.py`
- Check: `gcloud auth application-default login`

**For production deployment:**
- See deployment examples above for your platform
- Contact DevOps team for platform-specific guidance
