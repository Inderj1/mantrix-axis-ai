# Conversation Context Architecture

## Overview
Enable the system to understand and respond to follow-up questions by maintaining conversation context.

## Current State
✅ **Implemented:**
- `Conversation` model with message history
- `Message` model with `sql`, `results`, `metadata` fields
- `conversationId` field in `QueryRequest`
- MongoDB storage for conversations
- `ConversationContextManager` class for follow-up detection and context extraction
- Context retrieval and usage in SQL generation
- Follow-up question detection (6 patterns)
- Context-aware LLM prompting
- Table/column tracking in message metadata (tables_used, columns_selected, limit)

## Architecture Design

### 1. Enhanced Message Metadata
Store additional context in `Message.metadata`:
```python
{
    "tables_used": ["customer_master_analysis", "sales_order_cockpit_export"],
    "columns_selected": ["Customer", "revenue", "customer_name"],
    "filters_applied": [],
    "aggregations": ["SUM", "COUNT"],
    "limit": 5,
    "order_by": ["revenue DESC"]
}
```

### 2. Context Retrieval Flow
```
User Query → Check conversationId → Retrieve last N messages → Extract context → Generate SQL
```

### 3. Follow-up Question Detection
Detect follow-up patterns:
- "add [column]" / "include [column]"
- "show more details"
- "filter by [condition]"
- "sort by [column]"
- "expand to top [N]"
- "with [additional info]"

### 4. Context-Aware SQL Generation

**Input:**
```python
{
    "question": "add customer name",
    "conversationId": "conv-123",
    "context": {
        "previous_query": "Show top 5 customers by revenue",
        "previous_sql": "SELECT Customer, revenue FROM ...",
        "tables_used": ["customer_master_analysis"],
        "columns_selected": ["Customer", "revenue"]
    }
}
```

**LLM Prompt Enhancement:**
```
Previous Query: "Show top 5 customers by revenue"
Previous SQL: SELECT Customer, revenue FROM customer_master_analysis...
Previous Tables: customer_master_analysis
Previous Columns: Customer, revenue

New Request: "add customer name"

INSTRUCTIONS:
- This is a follow-up question to modify the previous query
- Keep the same base query structure (WHERE, LIMIT, ORDER BY)
- ADD ONLY the requested column: customer_name
- Join with sales_order_cockpit_export to get customer names
- Result should have: Customer, revenue, customer_name
```

## Implementation Plan

### Step 1: Enhance Message Model ✅
Add `tables_used` and `columns_selected` to metadata.

### Step 2: Create Context Manager
```python
class ConversationContextManager:
    def get_context(self, conversation_id: str, limit: int = 3) -> Dict
    def is_follow_up(self, question: str) -> bool
    def extract_context_from_message(self, message: Message) -> Dict
```

### Step 3: Update SQL Generator
```python
def generate_sql(..., conversation_context: Optional[Dict] = None):
    if conversation_context and self.is_follow_up(query):
        # Use context-aware prompt
        prompt = self._build_followup_prompt(query, conversation_context)
    else:
        # Use standard prompt
        prompt = self._build_user_prompt(...)
```

### Step 4: Update API Endpoint
```python
@router.post("/query")
async def process_query(request: QueryRequest, mongodb: MongoDBClient):
    context = None
    if request.conversationId:
        # Retrieve conversation context
        conversation = await mongodb.get_conversation(request.conversationId)
        context = extract_recent_context(conversation.messages, limit=3)

    result = generator.generate_and_execute(request.question, context=context)

    # Save message with enhanced metadata
    await mongodb.add_message(request.conversationId, message)
```

## Follow-up Question Patterns

### Pattern 1: Add Column
- **Query:** "add customer name"
- **Detection:** Starts with "add", "include", "show also"
- **Action:** Keep previous SELECT, add new column with appropriate JOIN

### Pattern 2: Change Filter
- **Query:** "only customers with revenue > $1M"
- **Detection:** Keywords: "only", "filter", "where", "with"
- **Action:** Keep previous SELECT, add/modify WHERE clause

### Pattern 3: Change Sorting
- **Query:** "sort by profit instead"
- **Detection:** "sort by", "order by", "ranked by"
- **Action:** Keep previous query, modify ORDER BY

### Pattern 4: Change Limit
- **Query:** "show top 10 instead"
- **Detection:** "top [N]", "expand to", "show more"
- **Action:** Keep previous query, modify LIMIT

### Pattern 5: Add Aggregation
- **Query:** "group by region"
- **Detection:** "group by", "by [dimension]"
- **Action:** Add GROUP BY, adjust SELECT for aggregations

## Benefits

✅ **User Experience:**
- Natural conversation flow
- No need to repeat full context
- Faster iteration on queries

✅ **Query Precision:**
- Maintains previous query structure
- Only modifies requested parts
- Prevents unintended column additions

✅ **Context Awareness:**
- Understands user intent across messages
- Builds on previous results
- Reduces query ambiguity

## Testing Strategy

### Test Case 1: Add Column
1. Query: "Show top 5 customers by revenue"
2. Result: Customer, revenue (2 columns)
3. Follow-up: "add customer name"
4. Expected: Customer, revenue, customer_name (3 columns, same 5 customers)

### Test Case 2: Change Filter
1. Query: "Show all customers"
2. Follow-up: "only customers in California"
3. Expected: Same columns, filtered by location

### Test Case 3: Change Aggregation
1. Query: "Show customers with revenue"
2. Follow-up: "group by state"
3. Expected: State-level aggregation instead of customer-level

### Test Case 4: Multiple Follow-ups
1. Query: "Show top 10 customers by revenue"
2. Follow-up: "add margin"
3. Follow-up: "only customers with margin > 20%"
4. Expected: Top 10 customers, revenue + margin, filtered by margin

## Rollout Plan

1. **Phase 1:** Context retrieval and storage ✅ COMPLETED
2. **Phase 2:** Follow-up detection and context manager ✅ COMPLETED
3. **Phase 3:** Context-aware prompting ✅ COMPLETED
4. **Phase 4:** Frontend integration ⏳ IN PROGRESS (Track conversation state)
5. **Phase 5:** Advanced patterns 📋 PLANNED (Multi-turn context, semantic understanding)
