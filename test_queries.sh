#!/bin/bash

# Test script for documenting query responses
API_URL="http://localhost:8000/api/v1/query"
USER_ID="test_user_$(date +%s)"
RESULTS_FILE="TEST_RESULTS.md"

# Function to test a query and append to results
test_query() {
    local query_name="$1"
    local query_text="$2"
    local query_num="$3"

    echo ""
    echo "=========================================="
    echo "Testing: $query_name"
    echo "=========================================="

    # Make API request
    response=$(curl -s -X POST "$API_URL" \
      -H "Content-Type: application/json" \
      -d "{
        \"query\": \"$query_text\",
        \"user_id\": \"$USER_ID\",
        \"execute\": true
      }")

    # Extract key information
    sql=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('sql', 'N/A'))" 2>/dev/null || echo "ERROR")
    explanation=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('explanation', 'N/A'))" 2>/dev/null || echo "ERROR")
    row_count=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); exec=data.get('execution', {}); print(len(exec.get('results', [])) if exec else 0)" 2>/dev/null || echo "0")
    error=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('error', 'None'))" 2>/dev/null || echo "PARSE_ERROR")

    # Append to results file
    {
        echo ""
        echo "## Query $query_num: $query_name"
        echo ""
        echo "**Query Text:**"
        echo "\`\`\`"
        echo "$query_text"
        echo "\`\`\`"
        echo ""
        echo "**Status:** $([ "$error" = "None" ] && echo "✅ SUCCESS" || echo "❌ FAILED")"
        echo ""
        echo "**Results:** $row_count rows returned"
        echo ""
        echo "**Explanation:**"
        echo "$explanation"
        echo ""
        echo "**Generated SQL:**"
        echo "\`\`\`sql"
        echo "$sql" | head -50
        echo "\`\`\`"
        echo ""
        if [ "$error" != "None" ]; then
            echo "**Error:**"
            echo "\`\`\`"
            echo "$error"
            echo "\`\`\`"
            echo ""
        fi
        echo "---"
        echo ""
    } >> "$RESULTS_FILE"

    echo "✓ Documented in $RESULTS_FILE"
    sleep 2
}

# Clear/create results file
cat > "$RESULTS_FILE" <<EOF
# Query Testing Results
## Test Session: $(date +"%Y-%m-%d %H:%M:%S")

### Test Plan
Testing queries for:
1. Context maintenance (beer portfolio analysis)
2. Sales inventory queries (4 queries)
3. Sales performance queries (2 queries)

---

EOF

echo "Starting query tests..."
echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Context Maintenance Tests
test_query "Beer Portfolio Performance" \
  "how's my beer product portfolio been doing over the year (show details)" \
  "1"

test_query "Customer Segment Targeting" \
  "based on the above which customer segment should be targeted for product promotion (show details)" \
  "2"

# Sales Inventory Tests
test_query "Delivered Quantity by Material and Plant" \
  "Show me the total Delivered Quantity by Material and Plant for each month over the last 6 months" \
  "3"

test_query "Aging Inventory - Open Orders" \
  "List open sales orders older than 60 days where Delivered Quantity is 0 and Net Value is greater than 1000" \
  "4"

test_query "Inventory Movement by Plant" \
  "Give me Delivered Quantity by Plant and month for the last 6 months" \
  "5"

test_query "Declining Delivery Trend" \
  "Show me Materials where Delivered Quantity in the last month is at least 20% lower than the average of the previous 3 months" \
  "6"

# Sales Performance Tests
test_query "Sales by Product and Region" \
  "What is the total sales amount by product and region for the last 12 months?" \
  "7"

test_query "Top Customers by Value and Volume" \
  "Which customers have ordered the most (by value and volume) in the last quarter?" \
  "8"

echo ""
echo "=========================================="
echo "All tests completed!"
echo "Results saved to: $RESULTS_FILE"
echo "=========================================="
