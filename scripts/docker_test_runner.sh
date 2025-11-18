#!/bin/bash
# Docker Test Runner - Automated Full Stack Testing
# Starts Docker services, waits for health, runs all tests, and reports results

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.test.yml"
WAIT_TIMEOUT=180  # 3 minutes max wait for services
CHECK_INTERVAL=5   # Check every 5 seconds

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}=========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "ℹ $1"
}

# Cleanup function
cleanup() {
    if [ "$CLEANUP_ON_EXIT" = "true" ]; then
        print_header "Cleaning Up"
        docker compose -f $COMPOSE_FILE down
        print_success "Services stopped"
    fi
}

trap cleanup EXIT

# ============================================================================
# STEP 1: Pre-flight Checks
# ============================================================================
print_header "Pre-flight Checks"

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi
print_success "Docker is running"

# Check Docker Compose version
if ! docker compose version > /dev/null 2>&1; then
    print_error "Docker Compose V2 is required. Please update Docker Desktop."
    exit 1
fi
print_success "Docker Compose V2 available"

# Check .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found"
    print_info "Please create .env file (see QUICK_START_DOCKER.md)"
    exit 1
fi
print_success ".env file found"

# Check required environment variables
if ! grep -q "ANTHROPIC_API_KEY=" .env || grep -q "ANTHROPIC_API_KEY=$" .env; then
    print_warning "ANTHROPIC_API_KEY not set in .env"
    print_info "Some tests may fail without API key"
fi

if ! grep -q "OPENAI_API_KEY=" .env || grep -q "OPENAI_API_KEY=$" .env; then
    print_warning "OPENAI_API_KEY not set in .env"
fi

if ! grep -q "GOOGLE_CLOUD_PROJECT=" .env || grep -q "GOOGLE_CLOUD_PROJECT=$" .env; then
    print_warning "GOOGLE_CLOUD_PROJECT not set in .env"
fi

# Check GCP credentials file
if [ ! -f "credentials/gcp-key.json" ]; then
    print_warning "GCP credentials file not found at credentials/gcp-key.json"
    print_info "BigQuery tests will fail"
fi

# ============================================================================
# STEP 2: Start Docker Services
# ============================================================================
print_header "Starting Docker Services"

# Stop any existing containers
print_info "Stopping existing containers..."
docker compose -f $COMPOSE_FILE down > /dev/null 2>&1 || true

# Build API image
print_info "Building API image (this may take 5-10 minutes on first run)..."
if docker compose -f $COMPOSE_FILE build api; then
    print_success "API image built"
else
    print_error "Failed to build API image"
    exit 1
fi

# Start all services
print_info "Starting all services..."
if docker compose -f $COMPOSE_FILE up -d; then
    print_success "Services started"
else
    print_error "Failed to start services"
    exit 1
fi

# ============================================================================
# STEP 3: Wait for Services to be Healthy
# ============================================================================
print_header "Waiting for Services to be Healthy"

print_info "This may take up to 3 minutes..."
print_info "Services: API, PostgreSQL, Redis, MongoDB, Weaviate, Neo4j"

elapsed=0
all_healthy=false

while [ $elapsed -lt $WAIT_TIMEOUT ]; do
    # Get service status
    services_status=$(docker compose -f $COMPOSE_FILE ps --format json 2>/dev/null | jq -r '.[] | "\(.Service):\(.Health)"' 2>/dev/null || echo "")

    if [ -z "$services_status" ]; then
        print_info "Waiting for services to start... (${elapsed}s)"
        sleep $CHECK_INTERVAL
        elapsed=$((elapsed + CHECK_INTERVAL))
        continue
    fi

    # Check if all services are healthy
    unhealthy_count=$(echo "$services_status" | grep -v "healthy" | wc -l)

    if [ "$unhealthy_count" -eq 0 ]; then
        all_healthy=true
        break
    fi

    # Show status
    echo "$services_status" | while read line; do
        service=$(echo "$line" | cut -d: -f1)
        health=$(echo "$line" | cut -d: -f2)
        if [ "$health" = "healthy" ]; then
            print_info "  $service: ${GREEN}healthy${NC}"
        else
            print_info "  $service: ${YELLOW}$health${NC}"
        fi
    done

    sleep $CHECK_INTERVAL
    elapsed=$((elapsed + CHECK_INTERVAL))
done

if [ "$all_healthy" = "false" ]; then
    print_error "Services did not become healthy within ${WAIT_TIMEOUT} seconds"
    print_info "Checking logs..."
    docker compose -f $COMPOSE_FILE logs --tail=50 api
    exit 1
fi

print_success "All services are healthy!"

# ============================================================================
# STEP 4: Run Automated Tests
# ============================================================================
print_header "Running Automated Feature Tests"

if [ -x ./scripts/test_all_features.sh ]; then
    if ./scripts/test_all_features.sh; then
        print_success "Feature tests passed"
    else
        print_error "Feature tests failed"
        TEST_FAILED=true
    fi
else
    print_warning "Test script not executable: ./scripts/test_all_features.sh"
fi

# ============================================================================
# STEP 5: Run Unit Tests (Optional)
# ============================================================================
print_header "Running Unit Tests (Optional)"

read -p "Run unit tests inside Docker? This may take 5-10 minutes. [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Running pytest..."
    if docker compose -f $COMPOSE_FILE exec api pytest /app/tests/ -v --tb=short; then
        print_success "Unit tests passed"
    else
        print_error "Unit tests failed"
        TEST_FAILED=true
    fi
else
    print_info "Skipping unit tests"
fi

# ============================================================================
# STEP 6: Service Information
# ============================================================================
print_header "Service Information"

echo ""
echo "All services are running and accessible:"
echo ""
echo "  ${GREEN}API (Backend)${NC}:"
echo "    URL: http://localhost:8000"
echo "    Docs: http://localhost:8000/docs"
echo "    Health: http://localhost:8000/api/v1/health"
echo ""
echo "  ${GREEN}Databases${NC}:"
echo "    PostgreSQL: localhost:5433 (user: mantrix_test, db: mantrix_test_db)"
echo "    Redis: localhost:6379"
echo "    MongoDB: localhost:27017"
echo "    Weaviate: http://localhost:8082"
echo "    Neo4j: http://localhost:7474 (user: neo4j, password: test_password_123)"
echo ""
echo "  ${GREEN}Management UIs${NC} (optional, start with --profile tools):"
echo "    Adminer (PostgreSQL): http://localhost:8080"
echo "    Redis Commander: http://localhost:8081"
echo "    Mongo Express: http://localhost:8083"
echo ""

# ============================================================================
# STEP 7: Quick Manual Tests
# ============================================================================
print_header "Quick Manual Test Commands"

echo ""
echo "Test database connectors:"
echo "  ${BLUE}curl http://localhost:8000/api/v1/connectors/types${NC}"
echo ""
echo "Test SQL translation:"
echo "  ${BLUE}curl -X POST http://localhost:8000/api/v1/cross-db/translate \\
    -H 'Content-Type: application/json' \\
    -d '{\"sql\":\"SELECT CURRENT_DATE()\",\"source_dialect\":\"bigquery\",\"target_dialect\":\"snowflake\"}'${NC}"
echo ""
echo "View logs:"
echo "  ${BLUE}docker compose -f $COMPOSE_FILE logs -f api${NC}"
echo ""
echo "Stop services:"
echo "  ${BLUE}docker compose -f $COMPOSE_FILE down${NC}"
echo ""

# ============================================================================
# STEP 8: Summary
# ============================================================================
print_header "Test Summary"

if [ "$TEST_FAILED" = "true" ]; then
    echo ""
    print_error "Some tests failed"
    echo ""
    echo "Troubleshooting steps:"
    echo "  1. Check logs: docker compose -f $COMPOSE_FILE logs api"
    echo "  2. Verify .env file has all required API keys"
    echo "  3. Ensure GCP credentials file exists: credentials/gcp-key.json"
    echo "  4. Check service status: docker compose -f $COMPOSE_FILE ps"
    echo ""

    read -p "Keep services running for debugging? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        CLEANUP_ON_EXIT=true
    else
        CLEANUP_ON_EXIT=false
        print_info "Services will keep running. Stop with: docker compose -f $COMPOSE_FILE down"
    fi

    exit 1
else
    echo ""
    print_success "All tests passed!"
    echo ""
    echo -e "${GREEN}✓ Services healthy${NC}"
    echo -e "${GREEN}✓ Feature tests passing${NC}"
    echo -e "${GREEN}✓ Ready for development${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review DEPLOYMENT_PLAN.md for staging deployment"
    echo "  2. Test with your production databases (Snowflake, Databricks, etc.)"
    echo "  3. Run load tests to validate performance"
    echo ""

    read -p "Keep services running? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        CLEANUP_ON_EXIT=true
    else
        CLEANUP_ON_EXIT=false
        print_info "Services will keep running. Stop with: docker compose -f $COMPOSE_FILE down"
    fi

    exit 0
fi
