"""
RDF-based knowledge graph client using RDFLib (Apache Jena compatible).
This replaces the Neo4j implementation with a semantic web approach.
"""

import os
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import structlog
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
from pathlib import Path

from src.core.financial_hierarchy import FinancialHierarchyConfig
from src.core.financial_semantic_parser import FinancialSemanticParser

logger = structlog.get_logger()


class JenaKnowledgeGraph:
    """RDF-based knowledge graph for financial data using RDFLib."""
    
    def __init__(self, data_file: str = "financial_kg.ttl", use_cache: str = "redis"):
        """Initialize the RDF graph.

        Args:
            data_file: Path to the TTL file
            use_cache: Cache strategy - "redis" (default), "memory", or "none"
        """
        self.data_file = data_file
        self.use_cache = use_cache

        if use_cache == "redis":
            # Use Redis-cached store for multi-process sharing
            from .jena_redis_store import get_redis_graph
            self.graph = get_redis_graph()
            logger.info("Using Redis-cached RDF store")
            # Still need to define namespace
            self.FIN = Namespace("http://example.com/finance#")
            self._fin = lambda prop: self.FIN[prop]
            # Load table metadata into cached graph
            self._load_table_metadata()
            return
        elif use_cache == "memory":
            # Use singleton memory store for single-process performance
            from .jena_memory_store import get_memory_graph
            self.graph = get_memory_graph()
            logger.info("Using in-memory RDF store (singleton)")
            # Still need to define namespace
            self.FIN = Namespace("http://example.com/finance#")
            self._fin = lambda prop: self.FIN[prop]
            # Load table metadata into cached graph
            self._load_table_metadata()
            return

        # Otherwise create new graph
        self.graph = Graph()

        # Define namespaces
        self.FIN = Namespace("http://example.com/finance#")
        self.graph.bind("fin", self.FIN)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        self.graph.bind("xsd", XSD)

        # Create helper for property access
        self._fin = lambda prop: self.FIN[prop]

        # Load ontology
        ontology_path = Path(__file__).parent.parent.parent.parent / "ontologies" / "financial-core.ttl"
        if ontology_path.exists():
            self.graph.parse(ontology_path, format="turtle")
            logger.info("Loaded financial ontology")

        # Load existing data if available
        if os.path.exists(self.data_file):
            self.graph.parse(self.data_file, format="turtle")
            logger.info(f"Loaded existing knowledge graph from {self.data_file}")
        else:
            logger.info("Starting with empty knowledge graph")
            self._load_from_sources()

        # Load table metadata (always load this)
        self._load_table_metadata()
    
    def _load_from_sources(self):
        """Load data from original Python/JSON source files."""
        logger.info("Loading data from source files...")
        
        # Load financial hierarchy
        self._load_financial_hierarchy()
        
        # Load GL mappings
        self._load_gl_mappings()
        
        # Load synonyms
        self._load_synonyms()
        
        # Load sample business rules
        self._load_business_rules()
        
        # Save to file
        self.save()
        
        logger.info("Initial data loaded successfully")
    
    def _load_financial_hierarchy(self):
        """Load L1 metrics and L2 buckets from financial_hierarchy.py."""
        hierarchy = FinancialHierarchyConfig()
        
        # Load L1 Metrics
        for metric_code, metric in hierarchy.l1_metrics.items():
            metric_uri = self.FIN[metric_code]
            
            # Add metric properties
            self.graph.add((metric_uri, RDF.type, self.FIN["L1Metric"]))
            self.graph.add((metric_uri, self.FIN["code"], Literal(metric_code)))
            self.graph.add((metric_uri, self.FIN["name"], Literal(metric.metric_name)))
            self.graph.add((metric_uri, self.FIN["displayName"], Literal(metric.metric_name)))
            self.graph.add((metric_uri, self.FIN["description"], Literal(metric.description)))
            self.graph.add((metric_uri, self.FIN["formula"], Literal(metric.formula)))
            self.graph.add((metric_uri, self.FIN["calculationOrder"], Literal(metric.calculation_order)))
            
            if metric.is_percentage:
                self.graph.add((metric_uri, self.FIN["isPercentage"], Literal(True)))
            
            # Add formula components
            for component_name, sql_expr in metric.formula_components.items():
                formula_uri = self.FIN[f"Formula_{metric_code}_{component_name}"]
                self.graph.add((formula_uri, RDF.type, self.FIN["Formula"]))
                self.graph.add((formula_uri, self.FIN["componentName"], Literal(component_name)))
                self.graph.add((formula_uri, self.FIN["sqlExpression"], Literal(sql_expr)))
                self.graph.add((metric_uri, self.FIN["usesFormula"], formula_uri))
        
        # Load L2 Buckets
        for bucket_code, bucket in hierarchy.l2_buckets.items():
            bucket_uri = self.FIN[bucket_code]
            
            # Add bucket properties
            self.graph.add((bucket_uri, RDF.type, self.FIN["L2Bucket"]))
            self.graph.add((bucket_uri, self.FIN["code"], Literal(bucket_code)))
            self.graph.add((bucket_uri, self.FIN["name"], Literal(bucket.bucket_name)))
            self.graph.add((bucket_uri, self.FIN["displayName"], Literal(bucket.bucket_name)))
            self.graph.add((bucket_uri, self.FIN["description"], Literal(bucket.description)))
            self.graph.add((bucket_uri, self.FIN["parentMetric"], Literal(bucket.parent_metric)))
            
            # Add GL ranges if available
            if bucket.gl_account_ranges:
                for start, end in bucket.gl_account_ranges:
                    self.graph.add((bucket_uri, self.FIN["glRangeStart"], Literal(start)))
                    self.graph.add((bucket_uri, self.FIN["glRangeEnd"], Literal(end)))
            
            # Link buckets to metrics
            parent_metric_uri = self.FIN[bucket.parent_metric]
            if (parent_metric_uri, RDF.type, self.FIN["L1Metric"]) in self.graph:
                self.graph.add((parent_metric_uri, self.FIN["contains"], bucket_uri))
        
        logger.info(f"Loaded {len(hierarchy.l1_metrics)} L1 metrics and {len(hierarchy.l2_buckets)} L2 buckets")
    
    def _load_gl_mappings(self):
        """Load GL account mappings from JSON files."""
        gl_mappings_dir = Path(__file__).parent.parent.parent.parent / "files" / "gl_mappings"
        
        if not gl_mappings_dir.exists():
            logger.warning(f"GL mappings directory not found: {gl_mappings_dir}")
            return
        
        for json_file in gl_mappings_dir.glob("*.json"):
            client_name = json_file.stem.replace("_mapping", "")
            logger.info(f"Loading GL mappings for client: {client_name}")
            
            # Create client node
            client_uri = self.FIN[f"Client_{client_name}"]
            self.graph.add((client_uri, RDF.type, self.FIN["Client"]))
            self.graph.add((client_uri, self.FIN["code"], Literal(client_name)))
            self.graph.add((client_uri, self.FIN["name"], Literal(client_name)))
            
            with open(json_file, 'r') as f:
                gl_data = json.load(f)
            
            # Extract accounts
            accounts = gl_data.get("accounts", {})
            
            for account_num, account_data in accounts.items():
                account_uri = self.FIN[f"GL_{account_num}"]
                
                # Add GL account properties
                self.graph.add((account_uri, RDF.type, self.FIN["GLAccount"]))
                self.graph.add((account_uri, self.FIN["accountNumber"], Literal(account_num)))
                self.graph.add((account_uri, self.FIN["description"], Literal(account_data.get("description", ""))))
                self.graph.add((account_uri, self.FIN["isActive"], Literal(account_data.get("is_active", True))))
                
                if account_data.get("bucket_code"):
                    self.graph.add((account_uri, self.FIN["bucketCode"], Literal(account_data["bucket_code"])))
                
                # Link to client
                self.graph.add((account_uri, self.FIN["belongsTo"], client_uri))
                
                # Link to L2 bucket if bucket code matches
                if account_data.get("bucket_code"):
                    # Try to find matching L2 bucket
                    bucket_code = account_data["bucket_code"]
                    # Map detailed bucket codes to our L2 bucket names
                    bucket_mapping = {
                        # Revenue mappings
                        "REV": "REVENUE_SALES",
                        "RA_REV": "REVENUE_SALES",
                        
                        # COGS mappings
                        "COGS_AD": "COGS_MATERIAL",
                        "COGS_CR": "COGS_MATERIAL",
                        "COGS_DL": "COGS_LABOR",
                        "COGS_DM": "COGS_MATERIAL",
                        "COGS_DP": "COGS_MATERIAL",
                        "COGS_EX": "COGS_MATERIAL",
                        "COGS_FG": "COGS_MATERIAL",
                        "COGS_FR": "COGS_MATERIAL",
                        "COGS_OH": "COGS_OVERHEAD",
                        "COGS_OT": "COGS_MATERIAL",
                        "COGS_PK": "COGS_MATERIAL",
                        "COGS_VR": "COGS_MATERIAL",
                        "COGS_WH": "COGS_OVERHEAD",
                        "RA_COGS": "COGS_MATERIAL",
                        
                        # OPEX mappings
                        "GNA_DA": "OPEX_DEPRECIATION",
                        "GNA_FAC": "OPEX_ADMIN",
                        "GNA_INS": "OPEX_ADMIN",
                        "GNA_OT": "OPEX_ADMIN",
                        "GNA_PAY": "OPEX_ADMIN",
                        "GNA_PRO": "OPEX_ADMIN",
                        "GNA_SUP": "OPEX_ADMIN",
                        "IA_GNA_PAY": "OPEX_ADMIN",
                        "IA_GNA_PRO": "OPEX_ADMIN",
                        
                        # Sales & Marketing
                        "SALE_DS": "OPEX_SALES",
                        "SEL_ADV": "OPEX_MARKETING",
                        "SEL_EVT": "OPEX_MARKETING",
                        "SEL_OT": "OPEX_SALES",
                        "SEL_PAY": "OPEX_SALES",
                        "SEL_TRV": "OPEX_SALES",
                        
                        # Other mappings
                        "R&D": "OPEX_RND",
                        "FIN_EXP": "INTEREST_EXPENSE",
                        "FIN_INC": "OTHER_INCOME",
                        "FX_GL": "OTHER_EXPENSE",
                        "OOE": "OTHER_EXPENSE",
                        "OOI": "OTHER_INCOME",
                        "TAX_INC": "TAX_EXPENSE"
                    }
                    
                    if bucket_code in bucket_mapping:
                        bucket_uri = self.FIN[bucket_mapping[bucket_code]]
                        if (bucket_uri, RDF.type, self.FIN["L2Bucket"]) in self.graph:
                            self.graph.add((account_uri, self.FIN["partOf"], bucket_uri))
            
            logger.info(f"Loaded {len(accounts)} GL accounts for {client_name}")
    
    def _load_synonyms(self):
        """Load synonym mappings from semantic parser."""
        # Define synonym groups
        synonym_groups = {
            "L1_METRIC": {
                "margin": ["margin", "gross margin", "net margin", "profit margin"],
                "profit": ["profit", "income", "earnings", "bottom line", "net income"],
                "ebitda": ["ebitda", "ebit", "operating income"],
                "revenue": ["revenue", "sales", "top line", "turnover"],
                "cogs": ["cogs", "cost of goods sold", "cost of sales"],
                "opex": ["opex", "operating expenses", "operational expenses"],
                "efficiency": ["efficiency", "productivity", "utilization"]
            },
            "L2_QUERY": {
                "breakdown": ["breakdown", "break down", "components", "detail", "decompose"],
                "categories": ["categories", "types", "buckets", "groups"],
                "composition": ["composition", "make up", "consist of", "parts"]
            },
            "TIME_PERIOD": {
                "ytd": ["ytd", "year to date", "this year"],
                "mtd": ["mtd", "month to date", "this month"],
                "qtd": ["qtd", "quarter to date", "this quarter"],
                "yoy": ["yoy", "year over year", "vs last year"],
                "mom": ["mom", "month over month", "vs last month"]
            }
        }
        
        for category, terms in synonym_groups.items():
            for primary_term, synonyms in terms.items():
                # Create primary term
                primary_uri = self.FIN[f"Synonym_{primary_term}"]
                self.graph.add((primary_uri, RDF.type, self.FIN["Synonym"]))
                self.graph.add((primary_uri, self.FIN["term"], Literal(primary_term)))
                self.graph.add((primary_uri, self.FIN["isPrimary"], Literal(True)))
                self.graph.add((primary_uri, self.FIN["category"], Literal(category)))
                
                # Create synonym nodes
                for synonym in synonyms:
                    if synonym != primary_term:
                        syn_uri = self.FIN[f"Synonym_{synonym.replace(' ', '_')}"]
                        self.graph.add((syn_uri, RDF.type, self.FIN["Synonym"]))
                        self.graph.add((syn_uri, self.FIN["term"], Literal(synonym)))
                        self.graph.add((syn_uri, self.FIN["isPrimary"], Literal(False)))
                        self.graph.add((syn_uri, self.FIN["category"], Literal(category)))
                        self.graph.add((syn_uri, self.FIN["synonymOf"], primary_uri))
        
        logger.info("Loaded synonym mappings")
    
    def _load_business_rules(self):
        """Load sample business rules."""
        rules = [
            {
                "name": "revenue_recognition",
                "description": "Revenue should only include accounts 4000-4999",
                "rule_type": "validation",
                "condition": "gl_account BETWEEN '4000' AND '4999'",
                "action": "include_in_revenue",
                "priority": 1
            },
            {
                "name": "cost_allocation",
                "description": "Direct costs must be allocated to product lines",
                "rule_type": "allocation",
                "condition": "account_type = 'DIRECT_COST'",
                "action": "allocate_by_product",
                "priority": 2
            },
            {
                "name": "period_closure",
                "description": "Closed periods cannot be modified",
                "rule_type": "constraint",
                "condition": "period_status = 'CLOSED'",
                "action": "reject_modification",
                "priority": 1
            }
        ]
        
        for rule in rules:
            rule_uri = self.FIN[f"Rule_{rule['name']}"]
            self.graph.add((rule_uri, RDF.type, self.FIN["BusinessRule"]))
            self.graph.add((rule_uri, self.FIN["name"], Literal(rule["name"])))
            self.graph.add((rule_uri, self.FIN["description"], Literal(rule["description"])))
            self.graph.add((rule_uri, self.FIN["ruleType"], Literal(rule["rule_type"])))
            self.graph.add((rule_uri, self.FIN["condition"], Literal(rule["condition"])))
            self.graph.add((rule_uri, self.FIN["action"], Literal(rule["action"])))
            self.graph.add((rule_uri, self.FIN["priority"], Literal(rule["priority"])))
            self.graph.add((rule_uri, self.FIN["isActive"], Literal(True)))
            
            # Link to relevant metrics
            if "revenue" in rule["name"]:
                revenue_metric = self.FIN["GROSS_MARGIN"]  # Or any revenue-related metric
                if (revenue_metric, RDF.type, self.FIN["L1Metric"]) in self.graph:
                    self.graph.add((rule_uri, self.FIN["appliesTo"], revenue_metric))

        logger.info(f"Loaded {len(rules)} business rules")

    def _load_table_metadata(self):
        """Load table metadata from table_metadata_kg.ttl if available."""
        table_metadata_file = "table_metadata_kg.ttl"

        if not os.path.exists(table_metadata_file):
            logger.warning(f"Table metadata file not found: {table_metadata_file}")
            logger.info("Run 'python load_table_metadata_to_jena.py' to generate it")
            return

        try:
            # Count triples before loading
            triples_before = len(self.graph)

            # Parse table metadata
            self.graph.parse(table_metadata_file, format="turtle")

            triples_added = len(self.graph) - triples_before
            logger.info(f"Loaded table metadata: +{triples_added:,} triples from {table_metadata_file}")

        except Exception as e:
            logger.error(f"Failed to load table metadata: {e}")

    def query(self, sparql_query: str, **kwargs) -> List[Dict[str, Any]]:
        """Execute a SPARQL query and return results."""
        try:
            results = self.graph.query(sparql_query, initBindings=kwargs)
            return [dict(row.asdict()) for row in results]
        except Exception as e:
            logger.error(f"SPARQL query failed: {e}")
            return []
    
    def save(self):
        """Save the graph to file."""
        self.graph.serialize(self.data_file, format="turtle")
        logger.info(f"Saved knowledge graph to {self.data_file}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the knowledge graph."""
        stats = {}
        
        # Count different node types
        node_types = [
            ("L1Metric", self.FIN["L1Metric"]),
            ("L2Bucket", self.FIN["L2Bucket"]),
            ("GLAccount", self.FIN["GLAccount"]),
            ("Formula", self.FIN["Formula"]),
            ("Synonym", self.FIN["Synonym"]),
            ("BusinessRule", self.FIN["BusinessRule"]),
            ("Client", self.FIN["Client"])
        ]
        
        for name, node_type in node_types:
            count_query = f"""
                SELECT (COUNT(?s) as ?count)
                WHERE {{
                    ?s a <{node_type}> .
                }}
            """
            result = list(self.graph.query(count_query))
            stats[name] = int(result[0][0]) if result else 0
        
        # Count total triples
        stats["TotalTriples"] = len(self.graph)
        
        return stats
    
    def close(self):
        """Save and close the graph."""
        self.save()
        logger.info("Closed Jena knowledge graph")