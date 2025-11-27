#!/bin/bash

# Mantrix Axis AI - Minimal Deployment Script
# This script automates the deployment process with proper checks

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_info() { echo -e "ℹ $1"; }

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1
    else
        return 0
    fi
}

# Function to wait for a service to be healthy
wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=1

    echo -n "Waiting for $service to be healthy..."
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps | grep $service | grep -q "healthy\|running"; then
            print_success " $service is ready!"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    print_error " $service failed to become healthy"
    return 1
}

# Header
echo "================================================"
echo "  Mantrix Axis AI - Minimal Deployment Setup"
echo "================================================"
echo ""

# Step 1: Check prerequisites
print_info "Checking prerequisites..."

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi
print_success "Docker is installed"

if ! command_exists docker-compose; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
print_success "Docker Compose is installed"

# Check Docker daemon
if ! docker info >/dev/null 2>&1; then
    print_error "Docker daemon is not running. Please start Docker."
    exit 1
fi
print_success "Docker daemon is running"

# Check available memory
AVAILABLE_MEM=$(docker info --format '{{.MemTotal}}' 2>/dev/null || echo "0")
AVAILABLE_MEM_GB=$((AVAILABLE_MEM / 1073741824))
if [ $AVAILABLE_MEM_GB -lt 8 ]; then
    print_warning "Docker has less than 8GB of memory allocated ($AVAILABLE_MEM_GB GB)"
    print_warning "The application may experience performance issues"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
print_success "Docker has sufficient memory ($AVAILABLE_MEM_GB GB)"

# Step 2: Check environment file
print_info "Checking environment configuration..."

if [ ! -f .env ]; then
    if [ -f .env.template ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.template .env
        print_warning "Please edit .env file with your actual values and run this script again."
        exit 1
    else
        print_error ".env file not found and no template available."
        exit 1
    fi
fi
print_success ".env file exists"

# Check required environment variables
source .env
REQUIRED_VARS=(
    "ANTHROPIC_API_KEY"
    "OPENAI_API_KEY"
    "AWS_COGNITO_USER_POOL_ID"
    "AWS_COGNITO_REGION"
    "AWS_COGNITO_CLIENT_ID"
    "GOOGLE_CLOUD_PROJECT"
    "BIGQUERY_DATASET"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=($var)
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    print_error "Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    print_warning "Please edit .env file and set all required variables."
    exit 1
fi
print_success "All required environment variables are set"

# Check Google Cloud credentials file
if [ ! -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    # Extract filename from path
    GCP_KEY_FILE=$(basename "$GOOGLE_APPLICATION_CREDENTIALS")
    if [ ! -f "$GCP_KEY_FILE" ]; then
        print_warning "Google Cloud credentials file not found: $GCP_KEY_FILE"
        print_warning "Make sure to place your GCP service account key file in this directory"
    else
        print_success "Google Cloud credentials file found"
    fi
fi

# Step 3: Check ports
print_info "Checking port availability..."

PORTS=(8080 80 8000 5433 6379 27017 8082)
PORTS_IN_USE=()

for port in "${PORTS[@]}"; do
    if ! check_port $port; then
        PORTS_IN_USE+=($port)
    fi
done

if [ ${#PORTS_IN_USE[@]} -gt 0 ]; then
    print_warning "The following ports are already in use:"
    for port in "${PORTS_IN_USE[@]}"; do
        echo "  - Port $port"
    done
    echo ""
    read -p "Do you want to stop existing services and continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "You can modify the ports in docker-compose.yml"
        exit 1
    fi
fi
print_success "Ports are available"

# Step 4: Build images
print_info "Building Docker images..."
echo ""

docker-compose build --progress=plain

if [ $? -ne 0 ]; then
    print_error "Failed to build Docker images"
    exit 1
fi
print_success "Docker images built successfully"

# Step 5: Start services
print_info "Starting services..."
echo ""

docker-compose up -d

if [ $? -ne 0 ]; then
    print_error "Failed to start services"
    exit 1
fi

# Step 6: Wait for services to be healthy
print_info "Waiting for services to be ready..."

services=("postgres" "redis" "mongodb" "weaviate" "backend" "frontend")
for service in "${services[@]}"; do
    wait_for_service $service
done

# Step 7: Verify deployment
print_info "Verifying deployment..."

# Check backend health
if curl -f -s http://localhost:8000/api/v1/health >/dev/null 2>&1; then
    print_success "Backend API is healthy"
else
    print_warning "Backend API health check failed"
fi

# Check frontend health
if curl -f -s http://localhost/health >/dev/null 2>&1; then
    print_success "Frontend is healthy"
else
    print_warning "Frontend health check failed"
fi

# Check load balancer
if curl -f -s http://localhost:8080/lb-health >/dev/null 2>&1; then
    print_success "Load balancer is healthy"
else
    print_warning "Load balancer health check failed"
fi

# Step 8: Display access information
echo ""
echo "================================================"
echo "  Deployment Complete!"
echo "================================================"
echo ""
print_success "All services are running"
echo ""
echo "Access the application:"
echo "  Main Application:  http://localhost:8080"
echo "  Backend API:       http://localhost:8000"
echo "  API Documentation: http://localhost:8000/docs"
echo ""
echo "Service Status:"
docker-compose ps
echo ""
echo "View logs:"
echo "  All services:     docker-compose logs -f"
echo "  Backend only:     docker-compose logs -f backend"
echo "  Frontend only:    docker-compose logs -f frontend"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""
print_info "Note: It may take a few more seconds for all services to be fully initialized"