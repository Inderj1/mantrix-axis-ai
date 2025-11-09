"""Knowledge Graph components for enhanced financial query understanding."""

from .models import NodeType, RelationType, GraphNode, GraphRelationship, QueryPath
from .jena_client import JenaKnowledgeGraph
from .jena_query_resolver import JenaQueryResolver, MetricFormula, GLMapping, ResolvedQuery

# Neo4j components are optional (we use Jena/RDF instead)
try:
    from .graph_client import FinancialKnowledgeGraph
    from .graph_builder import KnowledgeGraphBuilder
    from .query_resolver import KnowledgeGraphQueryResolver, GraphQueryResult
    from .graph_traversal import GraphTraversalEngine, TraversalOptions, TraversalStrategy, TraversalResult
except ImportError:
    # Neo4j not available, skip those components
    FinancialKnowledgeGraph = None
    KnowledgeGraphBuilder = None
    KnowledgeGraphQueryResolver = None
    GraphQueryResult = None
    GraphTraversalEngine = None
    TraversalOptions = None
    TraversalStrategy = None
    TraversalResult = None

__all__ = [
    "NodeType",
    "RelationType", 
    "GraphNode",
    "GraphRelationship",
    "QueryPath",
    "FinancialKnowledgeGraph",
    "KnowledgeGraphBuilder",
    "KnowledgeGraphQueryResolver",
    "GraphQueryResult",
    "GraphTraversalEngine",
    "TraversalOptions",
    "TraversalStrategy",
    "TraversalResult",
    "JenaKnowledgeGraph",
    "JenaQueryResolver",
    "MetricFormula",
    "GLMapping",
    "ResolvedQuery"
]