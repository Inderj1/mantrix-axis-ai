#!/bin/bash
# Service Account Setup Script for Mantrix Axis AI Production
# This script helps you create and configure a GCP service account with proper permissions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "GCP Service Account Setup for Production"
echo "=========================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
echo -e "${YELLOW}Step 1: Project Configuration${NC}"
read -p "Enter your GCP Project ID (default: arizona-poc): " PROJECT_ID
PROJECT_ID=${PROJECT_ID:-arizona-poc}

# Verify project exists
if ! gcloud projects describe "$PROJECT_ID" &> /dev/null; then
    echo -e "${RED}Error: Project '$PROJECT_ID' not found or you don't have access${NC}"
    echo "Available projects:"
    gcloud projects list
    exit 1
fi

echo -e "${GREEN}✓ Using project: $PROJECT_ID${NC}"
gcloud config set project "$PROJECT_ID"

# Service account details
echo ""
echo -e "${YELLOW}Step 2: Service Account Details${NC}"
read -p "Enter service account name (default: mantrix-axis-ai-prod): " SA_NAME
SA_NAME=${SA_NAME:-mantrix-axis-ai-prod}
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

read -p "Enter service account display name (default: Mantrix Axis AI Production): " SA_DISPLAY_NAME
SA_DISPLAY_NAME=${SA_DISPLAY_NAME:-Mantrix Axis AI Production}

# Create service account
echo ""
echo -e "${YELLOW}Step 3: Creating Service Account${NC}"
if gcloud iam service-accounts describe "$SA_EMAIL" &> /dev/null; then
    echo -e "${YELLOW}Service account already exists: $SA_EMAIL${NC}"
    read -p "Do you want to continue and update permissions? (y/n): " CONTINUE
    if [[ $CONTINUE != "y" ]]; then
        exit 0
    fi
else
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="$SA_DISPLAY_NAME" \
        --description="Service account for Mantrix Axis AI production deployment"
    echo -e "${GREEN}✓ Service account created: $SA_EMAIL${NC}"
fi

# Grant BigQuery permissions
echo ""
echo -e "${YELLOW}Step 4: Granting BigQuery Permissions${NC}"

ROLES=(
    "roles/bigquery.dataViewer"
    "roles/bigquery.jobUser"
    "roles/bigquery.readSessionUser"
)

for ROLE in "${ROLES[@]}"; do
    echo "  Adding role: $ROLE"
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$ROLE" \
        --condition=None \
        > /dev/null 2>&1
done

echo -e "${GREEN}✓ BigQuery permissions granted${NC}"

# Optional: Grant additional permissions
echo ""
echo -e "${YELLOW}Step 5: Optional Additional Permissions${NC}"
read -p "Do you need Google Cloud Storage access? (y/n): " NEED_STORAGE
if [[ $NEED_STORAGE == "y" ]]; then
    read -p "Enter GCS bucket name (or press Enter to grant project-wide access): " BUCKET_NAME
    if [[ -z "$BUCKET_NAME" ]]; then
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$SA_EMAIL" \
            --role="roles/storage.objectViewer" \
            > /dev/null 2>&1
        echo -e "${GREEN}✓ Storage Object Viewer granted (project-wide)${NC}"
    else
        gsutil iam ch "serviceAccount:$SA_EMAIL:roles/storage.objectViewer" "gs://$BUCKET_NAME"
        echo -e "${GREEN}✓ Storage access granted for bucket: $BUCKET_NAME${NC}"
    fi
fi

# Create and download key
echo ""
echo -e "${YELLOW}Step 6: Creating Service Account Key${NC}"
mkdir -p credentials
KEY_FILE="credentials/gcp-key-${SA_NAME}.json"

if [[ -f "$KEY_FILE" ]]; then
    echo -e "${YELLOW}Warning: Key file already exists: $KEY_FILE${NC}"
    read -p "Do you want to create a new key? (This will create a second key) (y/n): " CREATE_NEW
    if [[ $CREATE_NEW != "y" ]]; then
        echo "Using existing key file"
    else
        KEY_FILE="credentials/gcp-key-${SA_NAME}-$(date +%Y%m%d-%H%M%S).json"
        gcloud iam service-accounts keys create "$KEY_FILE" \
            --iam-account="$SA_EMAIL"
        echo -e "${GREEN}✓ New key created: $KEY_FILE${NC}"
    fi
else
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="$SA_EMAIL"
    echo -e "${GREEN}✓ Key created: $KEY_FILE${NC}"
fi

# Update .env file
echo ""
echo -e "${YELLOW}Step 7: Updating .env File${NC}"
ENV_FILE=".env"

if [[ -f "$ENV_FILE" ]]; then
    # Create backup
    cp "$ENV_FILE" "${ENV_FILE}.backup-$(date +%Y%m%d-%H%M%S)"
    echo -e "${GREEN}✓ Backup created: ${ENV_FILE}.backup-$(date +%Y%m%d-%H%M%S)${NC}"

    # Check if GOOGLE_APPLICATION_CREDENTIALS is commented out
    if grep -q "^# GOOGLE_APPLICATION_CREDENTIALS=" "$ENV_FILE"; then
        # Uncomment and update
        FULL_PATH="$(pwd)/$KEY_FILE"
        # For macOS sed
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^# GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=$FULL_PATH|" "$ENV_FILE"
        else
            sed -i "s|^# GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=$FULL_PATH|" "$ENV_FILE"
        fi
        echo -e "${GREEN}✓ Updated .env file with credentials path${NC}"
    else
        echo ""
        echo -e "${YELLOW}Please manually add this to your .env file:${NC}"
        echo "GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/$KEY_FILE"
    fi
fi

# Security reminder
echo ""
echo -e "${RED}=========================================="
echo "SECURITY REMINDERS"
echo "==========================================${NC}"
echo "1. ⚠️  NEVER commit $KEY_FILE to git"
echo "2. ⚠️  Add credentials/ to .gitignore"
echo "3. ⚠️  Rotate keys every 90 days"
echo "4. ⚠️  Use Secret Manager in production deployments"
echo "5. ⚠️  Limit key file permissions: chmod 600 $KEY_FILE"
echo ""

# Set proper permissions
chmod 600 "$KEY_FILE"
echo -e "${GREEN}✓ Set secure permissions on key file (600)${NC}"

# Summary
echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo "Service Account: $SA_EMAIL"
echo "Key File: $KEY_FILE"
echo ""
echo "Next steps:"
echo "1. Test the credentials with: python test_gcp_credentials.py"
echo "2. Update your production environment with the key file path"
echo "3. For Docker, mount the credentials directory as a volume"
echo ""
