"""
SQL Generator that uses Jena/RDF for all mapping lookups.
This replaces Neo4j with a semantic web approach using RDFLib.
"""

import structlog
from typing import Dict, List, Optional, Any, Tuple

from .sql_generator import SQLGenerator
from .knowledge_graph.jena_query_resolver import JenaQueryResolver
from .knowledge_graph.jena_client import JenaKnowledgeGraph

logger = structlog.get_logger()


class JenaSQLGenerator(SQLGenerator):
    """SQL Generator that uses Jena/RDF for all mapping lookups instead of Neo4j."""
    
    def __init__(self, **kwargs):
        """Initialize with Jena resolver."""
        # Initialize parent first
        super().__init__(**kwargs)
        
        # Initialize knowledge graph
        self.jena_graph = JenaKnowledgeGraph()
        
        # Create Jena resolver
        self.jena_resolver = JenaQueryResolver(self.jena_graph)
        
        # Override the kg_query_resolver if it exists
        if hasattr(self, 'kg_query_resolver'):
            self.kg_query_resolver = self.jena_resolver
        
        # Also set as knowledge_graph for compatibility
        if hasattr(self, 'knowledge_graph'):
            self.knowledge_graph = self.jena_graph
            
        logger.info("Initialized Jena SQL Generator")
    
    def _enhance_with_financial_context(self, query: str) -> Optional[Dict[str, Any]]:
        """Override to use Jena resolver directly."""
        if not self.jena_resolver:
            return super()._enhance_with_financial_context(query)
            
        try:
            # Use Jena resolver for all lookups
            resolved = self.jena_resolver.resolve_query(query)
            
            if resolved.query_type == "unknown":
                return None
                
            # Build financial context from RDF data
            financial_context = {
                "query_type": resolved.query_type,
                "confidence": resolved.confidence_score
            }
            
            # Add metrics if found
            if resolved.metrics:
                financial_context["metrics"] = []
                for metric in resolved.metrics:
                    metric_dict = {
                        "metric_code": metric.metric_code,
                        "metric_name": metric.metric_name,
                        "formula": metric.formula,
                        "formula_components": metric.formula_components,
                        "sub_buckets": metric.sub_buckets
                    }
                    financial_context["metrics"].append(metric_dict)
                    
            # Add GL accounts if found
            if resolved.gl_accounts:
                financial_context["gl_accounts"] = []
                for gl in resolved.gl_accounts:
                    gl_dict = {
                        "account_number": gl.account_number,
                        "description": gl.description,
                        "bucket_code": gl.bucket_code,
                        "is_active": gl.is_active
                    }
                    financial_context["gl_accounts"].append(gl_dict)
                    
            # Add synonyms resolved
            if resolved.synonyms_resolved:
                financial_context["synonyms_resolved"] = resolved.synonyms_resolved
                
            # Add business rules
            if resolved.business_rules:
                financial_context["business_rules"] = resolved.business_rules
                
            # Add suggested query if available
            if resolved.suggested_query:
                financial_context["suggested_query"] = resolved.suggested_query
                logger.info(f"✅ SQL template added to financial_context (length: {len(resolved.suggested_query)} chars)")
            else:
                logger.warning("⚠️ No SQL template retrieved from Jena resolver")
                
            logger.info(f"Jena resolved query type: {resolved.query_type} with confidence: {resolved.confidence_score}")
            return financial_context
            
        except Exception as e:
            logger.error(f"Jena query resolution failed: {e}")
            # Fall back to parent implementation
            return super()._enhance_with_financial_context(query)
    
    def _get_metric_formula(self, metric_code: str) -> Optional[Dict[str, Any]]:
        """Get metric formula from Jena instead of files."""
        if not self.jena_resolver:
            return None
            
        metric = self.jena_resolver.get_metric_formula(metric_code)
        if metric:
            return {
                "metric_code": metric.metric_code,
                "metric_name": metric.metric_name,
                "formula": metric.formula,
                "formula_components": metric.formula_components,
                "sub_buckets": metric.sub_buckets
            }
        return None
    
    def _get_gl_accounts_for_bucket(self, bucket_code: str, client_id: Optional[str] = None) -> List[str]:
        """Get GL accounts for a bucket from Jena."""
        if not self.jena_resolver:
            return []
            
        gl_mappings = self.jena_resolver.get_gl_accounts_for_bucket(bucket_code, client_id)
        return [gl.account_number for gl in gl_mappings if gl.is_active]
    
    def generate_sql(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate SQL using Jena mappings."""
        # Add client context if available
        if context and "client_id" in context and self.jena_resolver:
            # Pass client context to resolver
            jena_context = {"client_id": context["client_id"]}
            resolved = self.jena_resolver.resolve_query(query, jena_context)
            
            # Merge resolved context with input context
            if resolved.query_type != "unknown":
                context = context or {}
                context["jena_resolved"] = {
                    "query_type": resolved.query_type,
                    "metrics": [m.__dict__ for m in resolved.metrics],
                    "gl_accounts": [g.__dict__ for g in resolved.gl_accounts],
                    "synonyms": resolved.synonyms_resolved,
                    "business_rules": resolved.business_rules,
                    "confidence": resolved.confidence_score
                }
                
        # Call parent implementation with enhanced context
        return super().generate_sql(query, context)
    
    def close(self):
        """Clean up resources."""
        if self.jena_resolver:
            self.jena_resolver.close()
        super().close()