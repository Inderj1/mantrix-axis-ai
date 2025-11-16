#!/bin/bash
# Test runner script for Mantrix Axis AI
# Provides convenient commands to run different test categories

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Default to all tests if no argument provided
TEST_TYPE="${1:-all}"

echo -e "${BLUE}===========================================================${NC}"
echo -e "${BLUE}  Mantrix Axis AI - Test Runner${NC}"
echo -e "${BLUE}===========================================================${NC}"
echo ""

case "$TEST_TYPE" in
    unit)
        echo -e "${GREEN}Running Unit Tests (fast, isolated)...${NC}"
        pytest tests/unit/ -v
        ;;
    
    integration)
        echo -e "${GREEN}Running Integration Tests (multi-component)...${NC}"
        pytest tests/integration/ -v
        ;;
    
    e2e)
        echo -e "${GREEN}Running End-to-End Tests (full workflows)...${NC}"
        pytest tests/e2e/ -v
        ;;
    
    ui)
        echo -e "${GREEN}Running UI Tests (Playwright)...${NC}"
        pytest tests/ui/ -v
        ;;
    
    fast)
        echo -e "${GREEN}Running Fast Tests (unit only)...${NC}"
        pytest tests/unit/ -v --duration=10
        ;;
    
    slow)
        echo -e "${YELLOW}Running Slow Tests (integration + e2e)...${NC}"
        pytest tests/integration/ tests/e2e/ -v
        ;;
    
    all)
        echo -e "${GREEN}Running All Tests...${NC}"
        pytest tests/ -v
        ;;
    
    smart-caching)
        echo -e "${GREEN}Running Smart Caching Tests...${NC}"
        # Run as Python script (has custom output)
        cd tests/e2e && python test_smart_caching.py
        ;;
    
    complex-queries)
        echo -e "${GREEN}Running Complex Query Tests...${NC}"
        # Run as Python script (has custom output)
        cd tests/e2e && python test_complex_queries.py
        ;;
    
    pipeline)
        echo -e "${GREEN}Running Full Pipeline Test...${NC}"
        # Run as Python script (has custom output)
        cd tests/e2e && python test_full_pipeline_accuracy.py
        ;;
    
    coverage)
        echo -e "${GREEN}Running Tests with Coverage...${NC}"
        pytest tests/ -v --cov=src --cov-report=html:test_results/coverage --cov-report=term-missing
        echo -e "${BLUE}Coverage report: test_results/coverage/index.html${NC}"
        ;;
    
    benchmark)
        echo -e "${YELLOW}Running Benchmarks...${NC}"
        python benchmarks/benchmark_technical_limits.py
        ;;
    
    help)
        echo "Usage: ./run_tests.sh [TEST_TYPE]"
        echo ""
        echo "Test Types:"
        echo "  unit              - Run unit tests only (fast)"
        echo "  integration       - Run integration tests"
        echo "  e2e               - Run end-to-end tests"
        echo "  ui                - Run UI tests (Playwright)"
        echo "  fast              - Run only fast tests"
        echo "  slow              - Run slow tests (integration + e2e)"
        echo "  all               - Run all tests (default)"
        echo "  smart-caching     - Run smart caching validation"
        echo "  complex-queries   - Run complex query tests"
        echo "  pipeline          - Run full pipeline test"
        echo "  coverage          - Run tests with coverage report"
        echo "  benchmark         - Run performance benchmarks"
        echo "  help              - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh unit"
        echo "  ./run_tests.sh e2e"
        echo "  ./run_tests.sh coverage"
        ;;
    
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}===========================================================${NC}"
echo -e "${GREEN}Tests complete!${NC}"
echo -e "${BLUE}===========================================================${NC}"
