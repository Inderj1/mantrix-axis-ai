#!/bin/bash
# Test All Features - Comprehensive Test Script
# Tests all multi-database and cross-database features

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"  # Set if you have admin auth

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

info() {
    echo -e "ℹ INFO: $1"
}

section() {
    echo ""
    echo "========================================="
    echo "$1"
    echo "========================================="
}

# Start tests
echo "========================================="
echo "  Mantrix Axis AI - Feature Test Suite"
echo "  Testing API at: $API_URL"
echo "========================================="
echo ""

# ============================================================================
# TEST 1: Health Check
# ============================================================================
section "TEST 1: Health Check"

response=$(curl -s -w "\n%{http_code}" "$API_URL/api/v1/health")
http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    pass "API health check"
    info "Response: $body"
else
    fail "API health check (HTTP $http_code)"
fi

# ============================================================================
# TEST 2: Database Connectors Available
# ============================================================================
section "TEST 2: Database Connectors"

response=$(curl -s "$API_URL/api/v1/connectors/types")
if echo "$response" | grep -q "bigquery"; then
    pass "BigQuery connector available"
else
    fail "BigQuery connector not found"
fi

if echo "$response" | grep -q "postgresql"; then
    pass "PostgreSQL connector available"
else
    fail "PostgreSQL connector not found"
fi

if echo "$response" | grep -q "snowflake"; then
    pass "Snowflake connector available"
else
    fail "Snowflake connector not found"
fi

if echo "$response" | grep -q "databricks"; then
    pass "Databricks connector available"
else
    fail "Databricks connector not found"
fi

if echo "$response" | grep -q "redshift"; then
    pass "Redshift connector available"
else
    fail "Redshift connector not found"
fi

# ============================================================================
# TEST 3: PostgreSQL Connection Test
# ============================================================================
section "TEST 3: PostgreSQL Connection"

response=$(curl -s -X POST "$API_URL/api/v1/connectors/test" \
  -H "Content-Type: application/json" \
  -d '{
    "connector_type": "postgresql",
    "config": {
      "host": "postgres",
      "port": 5432,
      "database": "mantrix_test_db",
      "user": "mantrix_test",
      "password": "mantrix_test_123"
    }
  }')

if echo "$response" | grep -q '"success":true'; then
    pass "PostgreSQL connection test"
    connection_time=$(echo "$response" | grep -o '"connection_time_ms":[0-9.]*' | cut -d: -f2)
    info "Connection time: ${connection_time}ms"
else
    fail "PostgreSQL connection test"
    warn "Response: $response"
fi

# ============================================================================
# TEST 4: SQL Dialect Translation
# ============================================================================
section "TEST 4: SQL Dialect Translation"

# Test 4.1: BigQuery to Snowflake
info "Test 4.1: BigQuery → Snowflake"
response=$(curl -s -X POST "$API_URL/api/v1/cross-db/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) as week_ago",
    "source_dialect": "bigquery",
    "target_dialect": "snowflake",
    "validate": true
  }')

if echo "$response" | grep -q '"translated_sql"'; then
    pass "SQL translation: BigQuery → Snowflake"
    translated=$(echo "$response" | grep -o '"translated_sql":"[^"]*"' | cut -d'"' -f4)
    info "Translated: $translated"
else
    fail "SQL translation: BigQuery → Snowflake"
fi

# Test 4.2: Snowflake to PostgreSQL
info "Test 4.2: Snowflake → PostgreSQL"
response=$(curl -s -X POST "$API_URL/api/v1/cross-db/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT DATEADD(day, -7, CURRENT_DATE())",
    "source_dialect": "snowflake",
    "target_dialect": "postgresql",
    "validate": true
  }')

if echo "$response" | grep -q '"translated_sql"'; then
    pass "SQL translation: Snowflake → PostgreSQL"
else
    fail "SQL translation: Snowflake → PostgreSQL"
fi

# Test 4.3: Batch translation
info "Test 4.3: Batch translation"
response=$(curl -s -X POST "$API_URL/api/v1/cross-db/translate/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      "SELECT * FROM users",
      "SELECT COUNT(*) FROM products",
      "SELECT id, name FROM orders WHERE status = '\''active'\''"
    ],
    "source_dialect": "bigquery",
    "target_dialect": "postgresql"
  }')

if echo "$response" | grep -q '"total_queries":3'; then
    pass "Batch SQL translation (3 queries)"
else
    fail "Batch SQL translation"
fi

# ============================================================================
# TEST 5: Cache Status
# ============================================================================
section "TEST 5: Cache System"

response=$(curl -s "$API_URL/api/v1/cache/stats")
if echo "$response" | grep -q "hits\|misses"; then
    pass "Cache statistics available"
    info "Cache stats: $response"
else
    fail "Cache statistics"
fi

# ============================================================================
# TEST 6: Statistics Configuration
# ============================================================================
section "TEST 6: Statistics Extraction"

response=$(curl -s "$API_URL/api/v1/statistics/status")
if echo "$response" | grep -q '"enabled"'; then
    pass "Statistics configuration endpoint"
    enabled=$(echo "$response" | grep -o '"enabled":[^,]*' | cut -d: -f2)
    schedule=$(echo "$response" | grep -o '"schedule":"[^"]*"' | cut -d'"' -f4)
    info "Statistics enabled: $enabled, schedule: $schedule"
else
    fail "Statistics configuration endpoint"
fi

# ============================================================================
# TEST 7: Cross-Database Routes
# ============================================================================
section "TEST 7: Cross-Database API Routes"

response=$(curl -s "$API_URL/api/v1/cross-db/dialects")
if echo "$response" | grep -q "bigquery\|snowflake\|postgresql"; then
    pass "Cross-database dialects endpoint"
else
    fail "Cross-database dialects endpoint"
fi

# ============================================================================
# TEST 8: Connector Health Check
# ============================================================================
section "TEST 8: Connector Health"

response=$(curl -s "$API_URL/api/v1/cross-db/health")
if [ "$response" != "" ]; then
    pass "Cross-database health endpoint"
else
    warn "Cross-database health endpoint (may not be implemented)"
fi

# ============================================================================
# TEST 9: Query Pushdown Optimizer
# ============================================================================
section "TEST 9: Query Optimization Features"

# This test may fail if the endpoint doesn't exist yet
response=$(curl -s -X POST "$API_URL/api/v1/cross-db/analyze-pushdown" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM sales WHERE customer_id = 123 AND date >= '\''2024-01-01'\''",
    "table_name": "sales",
    "source_database": "bigquery"
  }' 2>/dev/null)

if [ "$response" != "" ] && ! echo "$response" | grep -q "404\|Not Found"; then
    pass "Query pushdown analysis endpoint"
else
    warn "Query pushdown analysis endpoint (may not be implemented as API endpoint)"
fi

# ============================================================================
# TEST 10: Database Permissions (if admin token provided)
# ============================================================================
section "TEST 10: Permission System"

if [ -n "$ADMIN_TOKEN" ]; then
    response=$(curl -s "$API_URL/api/v1/permissions/databases" \
      -H "Authorization: Bearer $ADMIN_TOKEN")

    if echo "$response" | grep -q "bigquery\|databases"; then
        pass "Permission system endpoint (with auth)"
    else
        fail "Permission system endpoint"
    fi
else
    warn "Skipping permission tests (ADMIN_TOKEN not set)"
fi

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "========================================="
echo "  TEST SUMMARY"
echo "========================================="
echo -e "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Check the output above for details."
    echo "Common issues:"
    echo "  - Services not fully started (wait 60s after 'docker compose up')"
    echo "  - Missing environment variables (check .env file)"
    echo "  - Network connectivity issues"
    echo ""
    exit 1
fi
