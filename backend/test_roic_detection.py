#!/usr/bin/env python3
"""
Test ROIC metric detection in Jena Query Resolver
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.core.knowledge_graph.jena_query_resolver import JenaQueryResolver
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

def test_roic_detection():
    """Test if ROIC is detected in query"""
    print("=" * 80)
    print("Testing ROIC Metric Detection")
    print("=" * 80)

    # Initialize resolver
    resolver = JenaQueryResolver()

    # Test query
    query = "Give me ROIC analysis of top 10 customers"

    print(f"\n Query: {query}")
    print(f"\n{'=' * 80}\n")

    # Resolve query
    resolved = resolver.resolve_query(query, context={"query_type": "L1"})

    print(f"\n{'=' * 80}")
    print(f"RESOLUTION RESULTS:")
    print(f"{'=' * 80}")
    print(f"Query Type: {resolved.query_type}")
    print(f"Detected Metrics: {len(resolved.metrics)}")

    if resolved.metrics:
        for metric in resolved.metrics:
            print(f"\n  ✓ Metric: {metric.metric_code}")
            print(f"    Name: {metric.metric_name}")
            print(f"    Formula: {metric.formula}")
            print(f"    Components: {len(metric.formula_components)}")
            for comp_name, comp_expr in metric.formula_components.items():
                print(f"      - {comp_name}: {comp_expr}")
    else:
        print("  ✗ NO METRICS DETECTED!")

    print(f"\nDetected Synonyms: {resolved.synonyms}")
    print(f"GL Accounts: {len(resolved.gl_accounts)}")

    if resolved.suggested_query:
        print(f"\nSQL Template Retrieved: YES")
        print(f"Template (first 200 chars):")
        print(f"  {resolved.suggested_query[:200]}...")
    else:
        print(f"\nSQL Template Retrieved: NO")

    print(f"\n{'=' * 80}\n")

    return resolved

if __name__ == "__main__":
    resolved = test_roic_detection()

    # Exit code based on success
    if resolved.metrics:
        print("✅ SUCCESS: ROIC metric detected!")
        sys.exit(0)
    else:
        print("❌ FAILURE: ROIC metric NOT detected!")
        sys.exit(1)
