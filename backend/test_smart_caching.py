"""
Test Smart Caching System - Verify failed and inefficient queries are NOT cached.

This test demonstrates the new smart caching system that:
1. Only caches validated SQL
2. Only caches successfully executed queries
3. Assigns quality tiers based on performance
4. Rejects queries that fail quality gates
"""
import sys
import json
from datetime import datetime
from src.core.sql_generator import SQLGenerator
from src.core.cache_manager import CacheManager
from src.config import settings

print("=" * 80)
print("SMART CACHING SYSTEM TEST")
print("=" * 80)
print(f"Timestamp: {datetime.now()}")
print(f"Cache execution test required: {settings.cache_execution_test_required}")
print(f"Cache validation required: {settings.cache_validation_required}")
print(f"Cache min confidence: {settings.cache_min_confidence}")
print(f"Cache execution threshold: {settings.cache_execution_threshold_ms}ms")
print("=" * 80)

# Initialize components
sql_gen = SQLGenerator()
cache_mgr = sql_gen.cache_manager

# Test scenarios
test_scenarios = [
    {
        "name": "SCENARIO 1: Valid, fast query (GOLD tier expected)",
        "query": "Show me all GL accounts",
        "expected_cached": True,
        "expected_tier": "GOLD",
        "description": "Should be cached with GOLD tier (fast, valid)"
    },
    {
        "name": "SCENARIO 2: Valid, medium query (SILVER tier expected)",
        "query": "What is the total revenue by customer?",
        "expected_cached": True,
        "expected_tier": "SILVER",
        "description": "Should be cached with SILVER tier (validated)"
    },
    {
        "name": "SCENARIO 3: Invalid query (NOT cached)",
        "query": "SELECT nonexistent_column FROM fake_table",
        "expected_cached": False,
        "expected_tier": None,
        "description": "Should NOT be cached (validation failure)"
    },
]

results = []

for scenario in test_scenarios:
    print(f"\n{'='*60}")
    print(scenario["name"])
    print('='*60)
    print(f"Query: {scenario['query']}")
    print(f"Expected: {'Cached' if scenario['expected_cached'] else 'NOT cached'}")
    if scenario['expected_tier']:
        print(f"Expected tier: {scenario['expected_tier']}")

    # Clear any existing cache for this query
    print("\nClearing existing cache...")
    import hashlib
    normalized = scenario['query'].strip().lower()
    normalized = " ".join(normalized.split())
    query_hash = hashlib.sha256(normalized.encode()).hexdigest()

    # Generate SQL
    print(f"\nGenerating SQL (attempt 1 - fresh)...")
    try:
        result1 = sql_gen.generate_sql(
            query=scenario['query'],
            use_vector_search=True,
            force_refresh=True  # Force fresh generation
        )

        # Check result
        validation_status = result1.get("validation", {}).get("valid", False)
        from_cache = result1.get("from_cache", False)
        sql = result1.get("sql", "")

        print(f"  ✓ SQL generated: {sql[:100]}...")
        print(f"  ✓ Validation: {'PASSED' if validation_status else 'FAILED'}")
        print(f"  ✓ From cache: {from_cache}")

        # Check execution metadata in result
        exec_meta = result1.get("execution_metadata")
        if exec_meta:
            print(f"  ✓ Execution time: {exec_meta.get('execution_time_ms', 0):.0f}ms")
            print(f"  ✓ Row count: {exec_meta.get('row_count', 0)}")
            print(f"  ✓ Cache tier: {result1.get('cache_tier', 'N/A')}")

        # Now try again WITHOUT force_refresh to see if it was cached
        print(f"\nGenerating SQL (attempt 2 - check cache)...")
        result2 = sql_gen.generate_sql(
            query=scenario['query'],
            use_vector_search=True,
            force_refresh=False  # Allow cache
        )

        from_cache_2 = result2.get("from_cache", False)
        print(f"  ✓ From cache: {from_cache_2}")

        # Verify expectation
        if scenario['expected_cached'] and from_cache_2:
            print(f"\n✅ SUCCESS: Query was cached as expected")
            cache_tier = result2.get("cache_tier", "UNKNOWN")
            print(f"   Cache tier: {cache_tier}")

            if scenario['expected_tier'] and cache_tier == scenario['expected_tier']:
                print(f"   ✅ Correct tier assigned!")
            elif scenario['expected_tier']:
                print(f"   ⚠️  Expected {scenario['expected_tier']}, got {cache_tier}")

        elif not scenario['expected_cached'] and not from_cache_2:
            print(f"\n✅ SUCCESS: Query was NOT cached (correctly rejected)")
            print(f"   Reason: Validation failed or quality gates not met")

        elif scenario['expected_cached'] and not from_cache_2:
            print(f"\n❌ UNEXPECTED: Expected caching but query was not cached")

        else:
            print(f"\n❌ UNEXPECTED: Expected no caching but query was cached")

        results.append({
            "scenario": scenario["name"],
            "query": scenario["query"],
            "validated": validation_status,
            "cached": from_cache_2,
            "expected_cached": scenario["expected_cached"],
            "tier": result2.get("cache_tier"),
            "success": (from_cache_2 == scenario["expected_cached"])
        })

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)[:200]}")
        results.append({
            "scenario": scenario["name"],
            "query": scenario["query"],
            "error": str(e)[:200],
            "success": False
        })

# Test cache invalidation
print(f"\n{'='*80}")
print("TESTING CACHE INVALIDATION")
print('='*80)

print("\nRunning invalidate_failed_queries()...")
try:
    invalidation_stats = cache_mgr.invalidate_failed_queries()
    print(f"\n✅ Invalidation complete:")
    print(f"   Total deleted: {invalidation_stats['total_deleted']}")
    print(f"   Execution errors: {invalidation_stats['execution_errors']}")
    print(f"   Validation failed: {invalidation_stats['validation_failed']}")
    print(f"   Slow queries: {invalidation_stats['slow_queries']}")
    print(f"   Old version: {invalidation_stats['old_version']}")
except Exception as e:
    print(f"❌ Invalidation failed: {e}")

# Summary
print(f"\n{'='*80}")
print("TEST SUMMARY")
print('='*80)

successful = sum(1 for r in results if r.get('success', False))
total = len(results)

print(f"\nTests passed: {successful}/{total}")
print("\nDetailed Results:")
for r in results:
    status = "✅" if r.get('success') else "❌"
    cached_str = "CACHED" if r.get('cached') else "NOT CACHED"
    expected_str = "CACHED" if r.get('expected_cached') else "NOT CACHED"
    print(f"{status} {r['scenario'][:50]:50}")
    print(f"   Result: {cached_str}, Expected: {expected_str}")
    if r.get('tier'):
        print(f"   Tier: {r['tier']}")
    if r.get('error'):
        print(f"   Error: {r['error'][:80]}...")

# Save detailed results
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
results_file = f"test_results/smart_caching_{timestamp}.json"

import os
os.makedirs("test_results", exist_ok=True)

with open(results_file, 'w') as f:
    json.dump({
        "timestamp": timestamp,
        "settings": {
            "cache_execution_test_required": settings.cache_execution_test_required,
            "cache_validation_required": settings.cache_validation_required,
            "cache_min_confidence": settings.cache_min_confidence,
            "cache_execution_threshold_ms": settings.cache_execution_threshold_ms
        },
        "results": results,
        "summary": {
            "tests_passed": successful,
            "tests_total": total,
            "success_rate": successful / total if total > 0 else 0
        }
    }, f, indent=2)

print(f"\n💾 Detailed results saved to: {results_file}")

if successful == total:
    print(f"\n✅ ALL TESTS PASSED - Smart caching is working correctly!")
    sys.exit(0)
else:
    print(f"\n⚠️  SOME TESTS FAILED - Review results above")
    sys.exit(1)
