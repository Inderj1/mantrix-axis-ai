# Multi-Connector Per Database Type

## Current Behavior (Resolved)

The system enforces **ONE enabled connector per database type per organization**.

When a user enables a new connector for chat, any previously enabled connector of the **same type** is automatically deactivated. A warning notification is shown to inform the user.

## Implementation Details

### Enforcement Location

**File:** `connector_routes.py:toggle_connector_for_chat()` (lines ~946-968)

```python
# Per-type uniqueness: Only one connector per database type can be enabled
# Auto-deactivate any other connector of same type when enabling
deactivated_connector_name = None
if is_enabling:
    connector_type = connector.get('connector_type')
    existing_enabled = await collection.find_one({
        "organization_id": organization_id,
        "connector_type": connector_type,
        "enabled_for_chat": True,
        "_id": {"$ne": ObjectId(connector_id)}  # Exclude self
    })

    if existing_enabled:
        # Auto-deactivate the existing connector of same type
        await collection.update_one(
            {"_id": existing_enabled["_id"]},
            {"$set": {"enabled_for_chat": False, "updated_at": ...}}
        )
        deactivated_connector_name = existing_enabled.get("name")
```

### User Experience

When enabling a connector that would conflict with an existing one:

1. The existing connector is automatically disabled
2. The new connector is enabled
3. A warning notification appears: `"Project A" was automatically disabled (only one bigquery connector can be active at a time)`
4. The UI refreshes to show the updated states

### Behavior Summary

| Scenario | Action |
|----------|--------|
| Enable BigQuery-A (no other BigQuery enabled) | Enable normally |
| Enable BigQuery-B (BigQuery-A already enabled) | Auto-disable BigQuery-A, enable BigQuery-B, show warning |
| Enable Snowflake-A (BigQuery-A enabled) | Enable normally (different types, no conflict) |
| Disable any connector | Disable normally |

## Why This Approach?

### Previous Problem

MongoDB's `find_one()` returns the **first matching document** with no guaranteed ordering. If multiple connectors of the same type were enabled, query execution was non-deterministic.

### Solution Benefits

1. **Deterministic**: `find_one()` always returns the single enabled connector
2. **Simple**: No complex routing logic needed
3. **Clear UX**: User sees which connector was deactivated
4. **Backward Compatible**: No API changes needed for queries

## Multi-Database Support

Organizations can still have **multiple databases of different types** enabled simultaneously:

- 1 BigQuery connector
- 1 Snowflake connector
- 1 PostgreSQL connector

This allows cross-database queries while maintaining deterministic connector selection within each type.

## Cache Isolation (Still Implemented)

Cache isolation remains in place to ensure correctness:

```python
# Validation cache uses connector_id in key
hash_input = f"{sql}:{database_type}:{connector_id}"
key = f"validation:{sha256(hash_input)}"
```

This ensures that when switching between connectors of the same type, cached data from the previous connector won't be incorrectly used.

## Testing

```python
# Test 1: Enable BigQuery-A
response = toggle_connector(bigquery_a_id, enabled=True)
assert response["enabled_for_chat"] == True
assert "deactivated_connector" not in response

# Test 2: Enable BigQuery-B (should auto-disable BigQuery-A)
response = toggle_connector(bigquery_b_id, enabled=True)
assert response["enabled_for_chat"] == True
assert response["deactivated_connector"] == "BigQuery-A"

# Verify BigQuery-A is now disabled
bigquery_a = get_connector(bigquery_a_id)
assert bigquery_a["enabled_for_chat"] == False
```

## File References

- `backend/src/api/connector_routes.py` - Toggle endpoint with per-type enforcement
- `frontend/src/components/controlcenter/DatabaseToggleCard.jsx` - UI with warning notification
- `backend/src/core/sql_generator.py` - SQL generation (benefits from deterministic selection)
- `backend/src/core/cache_manager.py` - Cache with connector_id isolation

---

**Last Updated:** December 2025
**Status:** Resolved - Single connector per type enforced with auto-deactivation
