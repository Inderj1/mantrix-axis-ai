# Query Testing Guide
## Manual Testing Instructions

Frontend URL: **http://localhost:5174**

### Testing Objectives
1. Verify context maintenance between related queries
2. Test sales inventory queries (4 queries)
3. Test sales performance queries (2 queries)
4. Document "Show Details" functionality

---

## Test Suite

### 1. Context Maintenance Test

#### Query 1A: Beer Portfolio Performance
```
how's my beer product portfolio been doing over the year (show details)
```

**Expected Behavior:**
- System should identify beer products in portfolio
- Return year-over-year performance metrics
- "Show Details" should expand to show detailed breakdown

**Document:**
- ✅/❌ Query executed successfully
- ✅/❌ "Show Details" button works
- Number of rows returned: ___
- Any errors or issues: ___

---

#### Query 1B: Customer Segment Targeting (Context Follow-up)
```
based on the above which customer segment should be targeted for product promotion (show details)
```

**Expected Behavior:**
- System should reference previous beer portfolio results
- Analyze customer segments from previous query
- Recommend segments for promotion
- Context should be maintained (no need to restate "beer")

**Document:**
- ✅/❌ Context maintained from previous query
- ✅/❌ System referenced beer portfolio from Query 1A
- ✅/❌ "Show Details" works
- Recommendation provided: ___
- Any errors: ___

---

### 2. Sales Inventory Queries

#### Query 2A: Delivered Quantity by Material/Plant
```
Show me the total Delivered Quantity by Material and Plant for each month over the last 6 months
```

**Purpose:** Identify high-moving vs. slow-moving inventory across locations

**Document:**
- ✅/❌ Query executed
- ✅/❌ "Show Details" works
- ✅/❌ Shows monthly breakdown
- ✅/❌ Groups by Material and Plant
- Number of rows: ___
- Issues: ___

---

#### Query 2B: Aging Inventory - Open Orders
```
List open sales orders older than 60 days where Delivered Quantity is 0 and Net Value is greater than 1000
```

**Purpose:** Detect aging inventory with significant value

**Document:**
- ✅/❌ Query executed
- ✅/❌ "Show Details" works
- ✅/❌ Filters orders > 60 days old
- ✅/❌ Filters Delivered Quantity = 0
- ✅/❌ Filters Net Value > 1000
- Number of rows: ___
- Issues: ___

---

#### Query 2C: Inventory Movement by Plant
```
Give me Delivered Quantity by Plant and month for the last 6 months
```

**Purpose:** Reveal which plants are moving inventory more actively

**Document:**
- ✅/❌ Query executed
- ✅/❌ "Show Details" works
- ✅/❌ Shows monthly trends
- ✅/❌ Groups by Plant
- Number of rows: ___
- Issues: ___

---

#### Query 2D: Declining Delivery Trend
```
Show me Materials where Delivered Quantity in the last month is at least 20% lower than the average of the previous 3 months
```

**Purpose:** Detect materials with declining delivery trends

**Document:**
- ✅/❌ Query executed
- ✅/❌ "Show Details" works
- ✅/❌ Correctly calculates 20% decline threshold
- ✅/❌ Compares last month vs 3-month average
- Number of materials flagged: ___
- Issues: ___

---

### 3. Sales Performance Queries

#### Query 3A: Sales by Product/Region
```
What is the total sales amount by product and region for the last 12 months?
```

**Impact:** Identifies top-performing SKUs for regional optimization

**Document:**
- ✅/❌ Query executed
- ✅/❌ "Show Details" works
- ✅/❌ Groups by Product and Region
- ✅/❌ Covers 12 months
- Number of rows: ___
- Issues: ___

---

#### Query 3B: Top Customers by Value/Volume
```
Which customers have ordered the most (by value and volume) in the last quarter?
```

**Impact:** Enables account targeting for upsell/cross-sell

**Document:**
- ✅/❌ Query executed
- ✅/❌ "Show Details" works
- ✅/❌ Shows both value AND volume
- ✅/❌ Covers last quarter
- Number of customers shown: ___
- Issues: ___

---

## Summary Checklist

### Functionality Tests
- [ ] All 8 queries executed successfully
- [ ] "Show Details" works for all queries
- [ ] Context maintained between Query 1A → 1B
- [ ] No SQL errors or timeouts
- [ ] Results appear within reasonable time (< 30 seconds)

### Query Quality Tests
- [ ] Time filters work correctly (6 months, 12 months, quarter, etc.)
- [ ] Aggregations are correct (SUM, AVG, counts)
- [ ] Filtering logic works (> 60 days, > 1000, 20% decline)
- [ ] GROUP BY logic is correct (Material+Plant, Product+Region, etc.)

### Known Issues from User
User reported:
- Query 1 ("Show Details") not working - Document if still an issue
- Context maintenance to be verified

---

## How to Document Results

1. Copy this file to `TEST_RESULTS_MANUAL.md`
2. Test each query in the frontend (http://localhost:5174)
3. Fill in the checkboxes and document fields
4. Take screenshots if there are visual issues
5. Note any unexpected behavior or errors

---

## Additional Notes Section

Use this section to document any other observations:

- **Performance Issues:** ___
- **UI/UX Issues:** ___
- **Unexpected Behavior:** ___
- **Feature Requests:** ___

