#!/bin/bash
#
# Run end-to-end accuracy tests for Mantrix Axis AI
#
# Usage:
#   ./run_accuracy_tests.sh <jwt_token>
#   ./run_accuracy_tests.sh <jwt_token> --quick     # Quick standalone test
#   ./run_accuracy_tests.sh <jwt_token> --sql       # SQL generation tests only
#   ./run_accuracy_tests.sh <jwt_token> --kg        # Knowledge graph tests only
#   ./run_accuracy_tests.sh <jwt_token> --vector    # Vector search tests only
#   ./run_accuracy_tests.sh <jwt_token> --all       # All tests with verbose output
#
# Environment variables:
#   AUTH_TOKEN - JWT token (alternative to command line)
#   API_URL    - API base URL (default: http://localhost:8000/api/v1)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  MANTRIX AXIS AI - ACCURACY TEST RUNNER${NC}"
echo -e "${BLUE}================================================${NC}"

# Get token from argument or environment
TOKEN="${1:-$AUTH_TOKEN}"
MODE="${2:---all}"

if [ -z "$TOKEN" ]; then
    echo -e "${RED}Error: No JWT token provided${NC}"
    echo ""
    echo "Usage: $0 <jwt_token> [--quick|--sql|--kg|--vector|--all]"
    echo ""
    echo "Or set AUTH_TOKEN environment variable:"
    echo "  export AUTH_TOKEN='your_jwt_token_here'"
    echo "  $0"
    exit 1
fi

# Export token for tests
export AUTH_TOKEN="$TOKEN"
export API_URL="${API_URL:-http://localhost:8000/api/v1}"

echo -e "${YELLOW}API URL:${NC} $API_URL"
echo -e "${YELLOW}Token:${NC} ${TOKEN:0:30}..."
echo ""

# Activate virtual environment if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo -e "${GREEN}Virtual environment activated${NC}"
fi

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found. Install with: pip install pytest httpx${NC}"
    exit 1
fi

# Ensure test results directory exists
mkdir -p test_results

case "$MODE" in
    --quick)
        echo -e "\n${BLUE}Running quick standalone test...${NC}\n"
        python tests/e2e/test_endpoint_accuracy.py --token "$TOKEN" --url "$API_URL"
        ;;
    --sql)
        echo -e "\n${BLUE}Running SQL generation accuracy tests...${NC}\n"
        pytest tests/e2e/test_endpoint_accuracy.py -v -s -k "TestSQLGenerationAccuracy" \
            --tb=short --no-header -q
        ;;
    --kg)
        echo -e "\n${BLUE}Running Knowledge Graph tests...${NC}\n"
        pytest tests/e2e/test_endpoint_accuracy.py -v -s -k "TestKnowledgeGraphVerification" \
            --tb=short --no-header -q
        ;;
    --vector)
        echo -e "\n${BLUE}Running Vector Search tests...${NC}\n"
        pytest tests/e2e/test_endpoint_accuracy.py -v -s -k "TestVectorSearchVerification" \
            --tb=short --no-header -q
        ;;
    --cache)
        echo -e "\n${BLUE}Running Cache tests...${NC}\n"
        pytest tests/e2e/test_endpoint_accuracy.py -v -s -k "TestCacheVerification" \
            --tb=short --no-header -q
        ;;
    --connectors)
        echo -e "\n${BLUE}Running Connector tests...${NC}\n"
        pytest tests/e2e/test_endpoint_accuracy.py -v -s -k "TestConnectorHealth" \
            --tb=short --no-header -q
        ;;
    --errors)
        echo -e "\n${BLUE}Running Error handling tests...${NC}\n"
        pytest tests/e2e/test_endpoint_accuracy.py -v -s -k "TestErrorHandling" \
            --tb=short --no-header -q
        ;;
    --all|*)
        echo -e "\n${BLUE}Running all accuracy tests...${NC}\n"
        pytest tests/e2e/test_endpoint_accuracy.py -v -s \
            --tb=short \
            --junitxml=test_results/accuracy_results.xml \
            2>&1 | tee test_results/accuracy_test_output.log
        ;;
esac

# Check exit code
EXIT_CODE=$?

echo ""
echo -e "${BLUE}================================================${NC}"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed (exit code: $EXIT_CODE)${NC}"
fi
echo -e "${BLUE}================================================${NC}"

# Show latest report if exists
LATEST_REPORT=$(ls -t test_results/accuracy_report_*.json 2>/dev/null | head -1)
if [ -n "$LATEST_REPORT" ]; then
    echo -e "\n${YELLOW}Latest report:${NC} $LATEST_REPORT"
    echo -e "${YELLOW}View with:${NC} cat $LATEST_REPORT | python -m json.tool"
fi

exit $EXIT_CODE
