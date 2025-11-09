#!/usr/bin/env python3
"""Quick test to verify knowledge graph initialization."""
import os
os.environ['SKIP_REDIS'] = 'true'

from src.core.knowledge_graph.jena_singleton import get_jena_knowledge_graph

print("=" * 80)
print("Testing Jena Knowledge Graph Initialization")
print("=" * 80)

try:
    kg = get_jena_knowledge_graph()
    print(f"\n✓ Knowledge graph initialized successfully")
    print(f"  Graph has {len(kg.graph)} triples")
except Exception as e:
    print(f"\n✗ Failed to initialize knowledge graph: {e}")
    import traceback
    traceback.print_exc()
