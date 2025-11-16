"""
Clear SQL cache entries from Redis to remove stale SQL with wrong column names.
"""
import redis
import json

print("=" * 80)
print("CLEARING SQL CACHE FROM REDIS")
print("=" * 80)

# Connect to Redis
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Pattern to match SQL cache keys
patterns = [
    "sql:*",           # All SQL cache entries
    "embedding:*",     # Embedding cache (might be related)
    "query:*"          # Query cache if exists
]

total_deleted = 0

for pattern in patterns:
    print(f"\nSearching for keys matching: {pattern}")

    # Find all matching keys
    keys = list(redis_client.scan_iter(match=pattern, count=100))

    if keys:
        print(f"Found {len(keys)} keys")

        # Show a few examples
        for key in keys[:5]:
            try:
                value = redis_client.get(key)
                if value:
                    # Try to parse as JSON to see what's cached
                    try:
                        data = json.loads(value)
                        if isinstance(data, dict) and 'sql' in data:
                            sql_preview = data['sql'][:100]
                            print(f"  - {key}: SQL starts with: {sql_preview}...")
                    except:
                        print(f"  - {key}: {value[:100] if value else 'empty'}...")
            except Exception as e:
                print(f"  - {key}: Error reading: {e}")

        if len(keys) > 5:
            print(f"  ... and {len(keys) - 5} more")

        # Delete all matching keys
        for key in keys:
            redis_client.delete(key)

        print(f"✅ Deleted {len(keys)} keys matching {pattern}")
        total_deleted += len(keys)
    else:
        print(f"No keys found matching {pattern}")

print("\n" + "=" * 80)
print(f"CACHE CLEANUP COMPLETE")
print(f"Total keys deleted: {total_deleted}")
print("=" * 80)

# Also check if there's a specific cache flush command
print("\nChecking for cache configuration...")
try:
    # Try to flush just the SQL cache namespace if it exists
    info = redis_client.info()
    print(f"Redis DB has {info.get('db0', {}).get('keys', 0)} total keys")
except Exception as e:
    print(f"Could not get Redis info: {e}")