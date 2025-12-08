#!/bin/bash
# Run RDF Triples Migration on AWS RDS PostgreSQL
#
# This script runs the migration using AWS CLI and psql or direct connection.
# It supports both local development and AWS ECS deployment scenarios.
#
# Usage:
#   ./run_migration.sh                    # Uses environment variables
#   ./run_migration.sh --aws-profile prod # Uses AWS profile for RDS credentials
#
# Environment Variables:
#   POSTGRES_HOST     - RDS endpoint (e.g., mydb.xxx.us-east-1.rds.amazonaws.com)
#   POSTGRES_PORT     - PostgreSQL port (default: 5432)
#   POSTGRES_USER     - Database username
#   POSTGRES_PASSWORD - Database password
#   POSTGRES_DATABASE - Database name
#   AWS_PROFILE       - AWS CLI profile (optional)
#   AWS_REGION        - AWS region (default: us-east-1)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATION_FILE="$SCRIPT_DIR/001_create_rdf_triples.sql"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
AWS_PROFILE_ARG=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --aws-profile)
            AWS_PROFILE_ARG="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--aws-profile PROFILE]"
            echo ""
            echo "Runs the RDF triples migration on PostgreSQL."
            echo ""
            echo "Options:"
            echo "  --aws-profile PROFILE  AWS CLI profile to use for credentials"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            echo_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set AWS profile if provided
if [ -n "$AWS_PROFILE_ARG" ]; then
    export AWS_PROFILE="$AWS_PROFILE_ARG"
    echo_info "Using AWS profile: $AWS_PROFILE"
fi

# Get database connection parameters
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DATABASE:-mantrix}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo_info "Database connection:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  User: $DB_USER"
echo "  Database: $DB_NAME"

# Check if migration file exists
if [ ! -f "$MIGRATION_FILE" ]; then
    echo_error "Migration file not found: $MIGRATION_FILE"
    exit 1
fi

echo_info "Migration file: $MIGRATION_FILE"

# Function to run migration with psql
run_with_psql() {
    echo_info "Running migration with psql..."

    if [ -n "$POSTGRES_PASSWORD" ]; then
        export PGPASSWORD="$POSTGRES_PASSWORD"
    fi

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION_FILE"

    unset PGPASSWORD
}

# Function to run migration via AWS RDS Data API (for Aurora Serverless)
run_with_rds_data_api() {
    echo_info "Running migration with AWS RDS Data API..."

    # This requires Aurora Serverless v2 with Data API enabled
    # and appropriate IAM permissions

    local cluster_arn="$RDS_CLUSTER_ARN"
    local secret_arn="$RDS_SECRET_ARN"

    if [ -z "$cluster_arn" ] || [ -z "$secret_arn" ]; then
        echo_error "RDS Data API requires RDS_CLUSTER_ARN and RDS_SECRET_ARN"
        return 1
    fi

    # Read migration file
    local sql_content=$(cat "$MIGRATION_FILE")

    aws rds-data execute-statement \
        --resource-arn "$cluster_arn" \
        --secret-arn "$secret_arn" \
        --database "$DB_NAME" \
        --sql "$sql_content" \
        --region "$AWS_REGION"
}

# Function to run migration via ECS Exec (for running inside ECS)
run_with_ecs_exec() {
    echo_info "Running migration via ECS Exec..."

    local cluster="$ECS_CLUSTER"
    local service="$ECS_SERVICE"
    local container="${ECS_CONTAINER:-backend}"

    if [ -z "$cluster" ] || [ -z "$service" ]; then
        echo_error "ECS Exec requires ECS_CLUSTER and ECS_SERVICE environment variables"
        return 1
    fi

    # Get a running task
    local task_arn=$(aws ecs list-tasks \
        --cluster "$cluster" \
        --service-name "$service" \
        --desired-status RUNNING \
        --query 'taskArns[0]' \
        --output text \
        --region "$AWS_REGION")

    if [ "$task_arn" == "None" ] || [ -z "$task_arn" ]; then
        echo_error "No running tasks found for service $service"
        return 1
    fi

    echo_info "Found task: $task_arn"

    # Execute migration command inside container
    aws ecs execute-command \
        --cluster "$cluster" \
        --task "$task_arn" \
        --container "$container" \
        --interactive \
        --command "psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f /app/migrations/001_create_rdf_triples.sql" \
        --region "$AWS_REGION"
}

# Determine which method to use
if [ -n "$RDS_CLUSTER_ARN" ] && [ -n "$RDS_SECRET_ARN" ]; then
    # Use RDS Data API (Aurora Serverless)
    run_with_rds_data_api
elif [ -n "$ECS_CLUSTER" ] && [ -n "$ECS_SERVICE" ]; then
    # Use ECS Exec
    run_with_ecs_exec
elif command -v psql &> /dev/null; then
    # Use psql directly
    run_with_psql
else
    echo_error "No suitable method found to run migration."
    echo "Options:"
    echo "  1. Install psql and set POSTGRES_* environment variables"
    echo "  2. Set RDS_CLUSTER_ARN and RDS_SECRET_ARN for Aurora Serverless Data API"
    echo "  3. Set ECS_CLUSTER and ECS_SERVICE for ECS Exec"
    exit 1
fi

echo_info "Migration completed successfully!"

# Verify the table was created
echo_info "Verifying migration..."

if command -v psql &> /dev/null && [ -n "$POSTGRES_PASSWORD" ]; then
    export PGPASSWORD="$POSTGRES_PASSWORD"

    result=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'rdf_triples';" 2>/dev/null)

    unset PGPASSWORD

    if [ "$(echo $result | tr -d ' ')" == "1" ]; then
        echo_info "Table 'rdf_triples' created successfully!"

        # Show table info
        export PGPASSWORD="$POSTGRES_PASSWORD"
        echo ""
        echo "Table structure:"
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\d rdf_triples"
        unset PGPASSWORD
    else
        echo_warn "Could not verify table creation"
    fi
fi
