"""
SPARQL-based query resolver using Jena/RDFLib knowledge graph.
Provides the same interface as Neo4j resolver but uses SPARQL queries.
"""

from typing import Dict, List, Optional, Any, Tuple
import structlog
from dataclasses import dataclass
import re

from .jena_client import JenaKnowledgeGraph

logger = structlog.get_logger()


@dataclass
class MetricFormula:
    """Represents a metric formula from RDF."""
    metric_code: str
    metric_name: str
    formula: str
    formula_components: Dict[str, str]
    sub_buckets: List[str]
    
    
@dataclass
class GLMapping:
    """Represents a GL account mapping from RDF."""
    account_number: str
    description: str
    bucket_code: Optional[str]
    client_id: Optional[str]
    is_active: bool = True


@dataclass
class ResolvedQuery:
    """Result of query resolution using RDF."""
    query_type: str  # 'L1', 'L2', 'L3', 'unknown'
    metrics: List[MetricFormula]
    gl_accounts: List[GLMapping]
    synonyms_resolved: Dict[str, str]
    business_rules: List[Dict[str, Any]]
    suggested_query: Optional[str] = None
    confidence_score: float = 0.0


class JenaQueryResolver:
    """Query resolver using SPARQL against RDF knowledge graph."""

    def __init__(self, graph_client: Optional[JenaKnowledgeGraph] = None):
        self.graph = graph_client or JenaKnowledgeGraph()

    def get_column_mappings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all column synonym mappings for prompt enhancement.

        Returns a dictionary mapping user terms to column information.
        """
        sparql = """
        PREFIX fin: <http://example.com/finance#>
        SELECT ?synonym_term ?column_name ?table_name ?confidence ?description
        WHERE {
            ?synonym a fin:ColumnSynonym ;
                     fin:term ?synonym_term ;
                     fin:synonymOf ?column ;
                     fin:confidence ?confidence .
            OPTIONAL { ?synonym fin:description ?description }
            ?column fin:columnName ?column_name ;
                    fin:belongsToTable ?table .
            ?table fin:tableName ?table_name .
        }
        ORDER BY DESC(?confidence)
        """

        mappings = {}
        results = self.graph.query(sparql)

        for row in results:
            syn_term = str(row["synonym_term"]).lower()
            column_name = str(row["column_name"])
            table_name = str(row["table_name"])
            confidence = float(row["confidence"])
            description = str(row.get("description", "")) if row.get("description") else ""

            if syn_term not in mappings:
                mappings[syn_term] = []

            mappings[syn_term].append({
                'column': column_name,
                'table': table_name,
                'confidence': confidence,
                'description': description
            })

        logger.info(f"Loaded {len(mappings)} column synonym mappings from KG")
        return mappings
        
    def resolve_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> ResolvedQuery:
        """Resolve a natural language query using RDF mappings."""
        logger.info(f"Resolving query: {query}")
        
        # 1. Resolve synonyms
        synonyms_resolved = self._resolve_synonyms(query)
        normalized_query = self._apply_synonyms(query, synonyms_resolved)
        
        # 2. Detect query type
        query_type = self._detect_query_type(normalized_query)
        
        # 3. Get relevant metrics
        metrics = self._get_relevant_metrics(normalized_query, query_type)
        
        # 4. Get GL accounts if needed
        gl_accounts = self._get_relevant_gl_accounts(normalized_query, metrics, context)
        
        # 5. Get applicable business rules
        business_rules = self._get_business_rules(metrics, context)
        
        # 6. Generate suggested query
        suggested_query = self._generate_suggested_query(query_type, metrics, gl_accounts)
        
        return ResolvedQuery(
            query_type=query_type,
            metrics=metrics,
            gl_accounts=gl_accounts,
            synonyms_resolved=synonyms_resolved,
            business_rules=business_rules,
            suggested_query=suggested_query,
            confidence_score=self._calculate_confidence(query_type, metrics, gl_accounts)
        )
    
    def _resolve_synonyms(self, query: str) -> Dict[str, str]:
        """Resolve synonyms from RDF (both metric and column synonyms)."""
        synonyms = {}
        query_lower = query.lower()

        # SPARQL query to find metric synonyms
        sparql_metrics = """
        PREFIX fin: <http://example.com/finance#>
        SELECT ?synonym_term ?primary_term
        WHERE {
            ?synonym a fin:Synonym ;
                     fin:term ?synonym_term ;
                     fin:isPrimary false ;
                     fin:synonymOf ?primary .
            ?primary fin:term ?primary_term ;
                     fin:isPrimary true .
        }
        """

        # SPARQL query to find column synonyms
        sparql_columns = """
        PREFIX fin: <http://example.com/finance#>
        SELECT ?synonym_term ?column_name ?table_name ?confidence
        WHERE {
            ?synonym a fin:ColumnSynonym ;
                     fin:term ?synonym_term ;
                     fin:synonymOf ?column ;
                     fin:confidence ?confidence .
            ?column fin:columnName ?column_name ;
                    fin:belongsToTable ?table .
            ?table fin:tableName ?table_name .
        }
        ORDER BY DESC(?confidence)
        """

        # Resolve metric synonyms
        results = self.graph.query(sparql_metrics)
        for row in results:
            syn_term = str(row["synonym_term"])
            primary_term = str(row["primary_term"])
            if syn_term.lower() in query_lower:
                synonyms[syn_term] = primary_term

        # Resolve column synonyms
        column_synonyms = {}
        results = self.graph.query(sparql_columns)
        for row in results:
            syn_term = str(row["synonym_term"])
            column_name = str(row["column_name"])
            table_name = str(row["table_name"])
            confidence = float(row["confidence"])

            if syn_term.lower() in query_lower:
                # Store with confidence for later selection
                if syn_term not in column_synonyms:
                    column_synonyms[syn_term] = []
                column_synonyms[syn_term].append({
                    'column': column_name,
                    'table': table_name,
                    'confidence': confidence
                })

        # Select best column match (highest confidence)
        for syn_term, matches in column_synonyms.items():
            best_match = max(matches, key=lambda x: x['confidence'])
            synonyms[syn_term] = best_match['column']
            logger.info(f"Column synonym resolved: '{syn_term}' -> {best_match['table']}.{best_match['column']} (confidence: {best_match['confidence']})")

        logger.info(f"Resolved synonyms: {synonyms}")
        return synonyms
    
    def _apply_synonyms(self, query: str, synonyms: Dict[str, str]) -> str:
        """Apply synonym replacements to query."""
        normalized = query
        for synonym, primary in synonyms.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(synonym), re.IGNORECASE)
            normalized = pattern.sub(primary, normalized)
        return normalized
    
    def _detect_query_type(self, query: str) -> str:
        """Detect if query is L1, L2, or L3 based on keywords and patterns."""
        query_lower = query.lower()
        
        # Check for L1 metric mentions
        sparql = """
        PREFIX fin: <http://example.com/finance#>
        SELECT (COUNT(?m) as ?count)
        WHERE {
            ?m a fin:L1Metric ;
               fin:name ?name .
            FILTER(CONTAINS(LCASE($query), LCASE(?name)))
        }
        """
        
        results = list(self.graph.query(sparql, initBindings={"query": query}))
        l1_count = int(results[0]["count"]) if results else 0
        
        # Check for L2 keywords
        l2_keywords = ["breakdown", "break down", "components", "detail", "composition"]
        has_l2_keyword = any(kw in query_lower for kw in l2_keywords)
        
        # Check for GL patterns
        gl_pattern_keywords = ["gl account", "general ledger", "account number", "gl code"]
        has_gl_pattern = any(kw in query_lower for kw in gl_pattern_keywords)
        
        if l1_count > 0 and not has_l2_keyword:
            return "L1"
        elif has_l2_keyword or (l1_count > 0 and has_l2_keyword):
            return "L2"
        elif has_gl_pattern or "gl" in query_lower:
            return "L3"
        else:
            return "unknown"
    
    def _get_relevant_metrics(self, query: str, query_type: str) -> List[MetricFormula]:
        """Get relevant metrics from RDF based on query."""
        metrics = []
        query_lower = query.lower()

        # SPARQL to find all L1 metrics
        sparql = """
        PREFIX fin: <http://example.com/finance#>
        SELECT ?metric ?code ?name ?formula ?order
        WHERE {
            ?metric a fin:L1Metric ;
                    fin:code ?code ;
                    fin:name ?name ;
                    fin:formula ?formula ;
                    fin:calculationOrder ?order .
        }
        ORDER BY ?order
        """

        metric_results = self.graph.query(sparql)

        logger.info(f"Total L1 metrics in KG: {len(list(metric_results))}")

        # Re-query since we consumed the generator
        metric_results = self.graph.query(sparql)

        # Filter metrics that match the query
        matched_metrics = []
        for row in metric_results:
            code = str(row["code"]).lower()
            name = str(row["name"]).lower()
            logger.info(f"Checking metric: code='{code}', name='{name}' against query='{query_lower}'")
            if code in query_lower or name in query_lower:
                logger.info(f"✓ MATCHED metric: {code}")
                matched_metrics.append(row)
            else:
                logger.debug(f"✗ No match for metric: {code}")

        logger.info(f"Matched {len(matched_metrics)} metrics from query")

        # Process matched metrics
        metric_results = matched_metrics
        
        for row in metric_results:
            metric_uri = row["metric"]
            metric_code = str(row["code"])
            
            # Get formula components
            formula_sparql = f"""
            PREFIX fin: <http://example.com/finance#>
            SELECT ?component_name ?sql_expr
            WHERE {{
                <{metric_uri}> fin:usesFormula ?formula .
                ?formula fin:componentName ?component_name ;
                         fin:sqlExpression ?sql_expr .
            }}
            """
            
            formula_results = self.graph.query(formula_sparql)
            
            formula_components = {}
            for f_row in formula_results:
                formula_components[str(f_row["component_name"])] = str(f_row["sql_expr"])
            
            # Get sub-buckets
            bucket_sparql = f"""
            PREFIX fin: <http://example.com/finance#>
            SELECT ?bucket_code
            WHERE {{
                <{metric_uri}> fin:contains ?bucket .
                ?bucket fin:code ?bucket_code .
            }}
            """
            
            bucket_results = self.graph.query(bucket_sparql)
            
            sub_buckets = [str(b["bucket_code"]) for b in bucket_results]
            
            metric = MetricFormula(
                metric_code=metric_code,
                metric_name=str(row["name"]),
                formula=str(row["formula"]),
                formula_components=formula_components,
                sub_buckets=sub_buckets
            )
            metrics.append(metric)
                
        return metrics
    
    def _get_relevant_gl_accounts(self, query: str, metrics: List[MetricFormula], 
                                 context: Optional[Dict[str, Any]] = None) -> List[GLMapping]:
        """Get relevant GL accounts from RDF."""
        gl_accounts = []
        client_id = context.get("client_id") if context else None
        
        # If we have metrics with buckets, get GL accounts for those buckets
        if metrics:
            for metric in metrics:
                for bucket_code in metric.sub_buckets:
                    sparql = f"""
                    PREFIX fin: <http://example.com/finance#>
                    SELECT ?gl ?account_num ?desc ?bucket_code ?active
                    WHERE {{
                        ?gl a fin:GLAccount ;
                            fin:accountNumber ?account_num ;
                            fin:description ?desc ;
                            fin:isActive ?active ;
                            fin:partOf ?bucket .
                        ?bucket fin:code "{bucket_code}" .
                        OPTIONAL {{ ?gl fin:bucketCode ?bucket_code }}
                    """
                    
                    # Add client filter if specified
                    if client_id:
                        sparql += f"""
                        ?gl fin:belongsTo ?client .
                        ?client fin:code "{client_id}" .
                        """
                        
                    sparql += "}"
                    
                    results = self.graph.query(sparql)
                    
                    for row in results:
                        gl_mapping = GLMapping(
                            account_number=str(row["account_num"]),
                            description=str(row["desc"]),
                            bucket_code=str(row.get("bucket_code", "")),
                            client_id=client_id,
                            is_active=bool(row["active"])
                        )
                        gl_accounts.append(gl_mapping)
        
        # Check for direct GL account references
        gl_pattern = re.compile(r'\b(?:gl|account)\s*(\d{4,})\b', re.IGNORECASE)
        matches = gl_pattern.findall(query)
        
        for account_num in matches:
            sparql = f"""
            PREFIX fin: <http://example.com/finance#>
            SELECT ?gl ?desc ?bucket_code ?active
            WHERE {{
                ?gl a fin:GLAccount ;
                    fin:accountNumber "{account_num}" ;
                    fin:description ?desc ;
                    fin:isActive ?active .
                OPTIONAL {{ ?gl fin:bucketCode ?bucket_code }}
            }}
            """
            
            results = self.graph.query(sparql)
            
            for row in results:
                gl_mapping = GLMapping(
                    account_number=account_num,
                    description=str(row["desc"]),
                    bucket_code=str(row.get("bucket_code", "")),
                    client_id=client_id,
                    is_active=bool(row["active"])
                )
                gl_accounts.append(gl_mapping)
                    
        return gl_accounts
    
    def _get_business_rules(self, metrics: List[MetricFormula], 
                           context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get applicable business rules from RDF."""
        rules = []
        
        for metric in metrics:
            sparql = f"""
            PREFIX fin: <http://example.com/finance#>
            SELECT ?rule ?name ?desc ?type ?condition ?action ?priority
            WHERE {{
                ?rule a fin:BusinessRule ;
                      fin:name ?name ;
                      fin:description ?desc ;
                      fin:ruleType ?type ;
                      fin:condition ?condition ;
                      fin:action ?action ;
                      fin:priority ?priority ;
                      fin:isActive true ;
                      fin:appliesTo ?metric .
                ?metric fin:code "{metric.metric_code}" .
            }}
            ORDER BY ?priority
            """
            
            results = self.graph.query(sparql)
            
            for row in results:
                rules.append({
                    "name": str(row["name"]),
                    "description": str(row["desc"]),
                    "rule_type": str(row["type"]),
                    "condition": str(row["condition"]),
                    "action": str(row["action"]),
                    "priority": int(row["priority"])
                })
                    
        return rules
    
    def _generate_suggested_query(self, query_type: str, metrics: List[MetricFormula],
                                 gl_accounts: List[GLMapping]) -> Optional[str]:
        """Generate a suggested SQL query based on resolved components."""
        # First, try to get SQL template from KG for the metric
        if metrics:
            metric = metrics[0]
            logger.info(f"Attempting to retrieve SQL template for metric: {metric.metric_code}")
            sql_template = self._get_sql_template_for_metric(metric.metric_code)
            if sql_template:
                logger.info(f"Successfully retrieved SQL template for {metric.metric_code}")
                return sql_template
            else:
                logger.warning(f"No SQL template found for {metric.metric_code}")

        # Fallback to generic template generation
        if query_type == "L1" and metrics:
            metric = metrics[0]

            # Fallback to formula-based generation
            if metric.formula_components:
                calc = list(metric.formula_components.values())[0]
                return f"""
SELECT
    {calc} as {metric.metric_code.lower()},
    -- Add dimensions as needed
FROM your_table
GROUP BY dimension
"""

        elif query_type == "L2" and metrics:
            metric = metrics[0]
            if metric.sub_buckets:
                return f"""
SELECT
    CASE
        -- Add bucket categorization logic
        WHEN gl_account IN (/* bucket accounts */) THEN '{metric.sub_buckets[0]}'
        -- Add more buckets
    END as bucket,
    SUM(amount) as total
FROM your_table
GROUP BY bucket
"""

        elif query_type == "L3" and gl_accounts:
            account_list = ", ".join([f"'{gl.account_number}'" for gl in gl_accounts[:5]])
            return f"""
SELECT
    gl_account,
    gl_description,
    SUM(amount) as total
FROM your_table
WHERE gl_account IN ({account_list})
GROUP BY gl_account, gl_description
"""

        return None

    def _get_sql_template_for_metric(self, metric_code: str) -> Optional[str]:
        """Retrieve SQL template from KG for a specific metric."""
        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        SELECT ?template_name ?sql_template ?description
        WHERE {{
            ?metric a fin:L1Metric ;
                    fin:code "{metric_code}" .
            ?template a fin:QueryTemplate ;
                      fin:forMetric ?metric ;
                      fin:sqlTemplate ?sql_template ;
                      fin:templateName ?template_name ;
                      fin:description ?description .
        }}
        LIMIT 1
        """

        try:
            results = list(self.graph.query(sparql))
            if results:
                row = results[0]
                sql_template = str(row["sql_template"])
                template_name = str(row["template_name"])
                logger.info(f"Found SQL template for {metric_code} from KG: {template_name}")
                return sql_template
        except Exception as e:
            logger.warning(f"Failed to retrieve SQL template for {metric_code}: {e}")

        return None
    
    def _calculate_confidence(self, query_type: str, metrics: List[MetricFormula], 
                            gl_accounts: List[GLMapping]) -> float:
        """Calculate confidence score for the resolution."""
        score = 0.0
        
        if query_type != "unknown":
            score += 0.3
            
        if metrics:
            score += 0.4
            
        if gl_accounts:
            score += 0.2
            
        if metrics and all(m.formula_components for m in metrics):
            score += 0.1
            
        return min(score, 1.0)
    
    def get_metric_formula(self, metric_code: str) -> Optional[MetricFormula]:
        """Get a specific metric formula from RDF."""
        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        SELECT ?metric ?name ?formula ?order
        WHERE {{
            ?metric a fin:L1Metric ;
                    fin:code "{metric_code}" ;
                    fin:name ?name ;
                    fin:formula ?formula ;
                    fin:calculationOrder ?order .
        }}
        """
        
        results = list(self.graph.query(sparql))
        
        if results:
            row = results[0]
            metric_uri = row["metric"]
            
            # Get formula components and buckets (reuse logic from _get_relevant_metrics)
            formula_sparql = f"""
            PREFIX fin: <http://example.com/finance#>
            SELECT ?component_name ?sql_expr
            WHERE {{
                <{metric_uri}> fin:usesFormula ?formula .
                ?formula fin:componentName ?component_name ;
                         fin:sqlExpression ?sql_expr .
            }}
            """
            
            formula_results = self.graph.query(formula_sparql)
            
            formula_components = {}
            for f_row in formula_results:
                formula_components[str(f_row["component_name"])] = str(f_row["sql_expr"])
            
            # Get sub-buckets
            bucket_sparql = f"""
            PREFIX fin: <http://example.com/finance#>
            SELECT ?bucket_code
            WHERE {{
                <{metric_uri}> fin:contains ?bucket .
                ?bucket fin:code ?bucket_code .
            }}
            """
            
            bucket_results = self.graph.query(bucket_sparql)
            
            sub_buckets = [str(b["bucket_code"]) for b in bucket_results]
            
            return MetricFormula(
                metric_code=metric_code,
                metric_name=str(row["name"]),
                formula=str(row["formula"]),
                formula_components=formula_components,
                sub_buckets=sub_buckets
            )
                
        return None
    
    def get_gl_accounts_for_bucket(self, bucket_code: str, client_id: Optional[str] = None) -> List[GLMapping]:
        """Get all GL accounts for a specific bucket."""
        gl_accounts = []
        
        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        SELECT ?gl ?account_num ?desc ?bucket_code ?active
        WHERE {{
            ?gl a fin:GLAccount ;
                fin:accountNumber ?account_num ;
                fin:description ?desc ;
                fin:isActive ?active ;
                fin:partOf ?bucket .
            ?bucket fin:code "{bucket_code}" .
            OPTIONAL {{ ?gl fin:bucketCode ?bucket_code }}
        """
        
        if client_id:
            sparql += f"""
            ?gl fin:belongsTo ?client .
            ?client fin:code "{client_id}" .
            """
            
        sparql += "}"
        
        results = self.graph.query(sparql)
        
        for row in results:
            gl_mapping = GLMapping(
                account_number=str(row["account_num"]),
                description=str(row["desc"]),
                bucket_code=str(row.get("bucket_code", bucket_code)),
                client_id=client_id,
                is_active=bool(row["active"])
            )
            gl_accounts.append(gl_mapping)
                
        return gl_accounts
    
    def close(self):
        """Close the graph connection."""
        self.graph.close()