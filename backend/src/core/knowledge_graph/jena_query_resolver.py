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

    def __init__(self, graph_client: Optional[JenaKnowledgeGraph] = None,
                 organization_id: str = None,
                 database_type: str = None):
        self.graph = graph_client or JenaKnowledgeGraph()
        self.organization_id = organization_id or 'default'
        self.database_type = database_type

    def get_column_mappings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all column synonym mappings for prompt enhancement.

        Returns a dictionary mapping user terms to column information.
        """
        # Build additional triple patterns for organization and database filtering
        extra_patterns = []
        if self.organization_id:
            extra_patterns.append(f'?table schema:organizationId "{self.organization_id}" .')
        if self.database_type:
            extra_patterns.append(f'?table schema:databaseType "{self.database_type}" .')

        extra_patterns_clause = "\n            ".join(extra_patterns) if extra_patterns else ""

        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        PREFIX schema: <http://example.com/schema#>
        SELECT ?synonym_term ?column_name ?table_name ?confidence ?description
        WHERE {{
            ?synonym a fin:ColumnSynonym ;
                     fin:term ?synonym_term ;
                     fin:synonymOf ?column ;
                     fin:confidence ?confidence .
            OPTIONAL {{ ?synonym fin:description ?description }}
            ?column schema:columnName ?column_name ;
                    schema:belongsToTable ?table .
            ?table schema:tableName ?table_name .
            {extra_patterns_clause}
        }}
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
        """Get relevant metrics from RDF based on query.

        Optimized: Single SPARQL query with OPTIONAL clauses to avoid N+1 problem.
        """
        metrics = []
        query_lower = query.lower()

        # Single SPARQL query to get metrics with all their related data
        # Uses OPTIONAL to include formula components and buckets in one query
        sparql = """
        PREFIX fin: <http://example.com/finance#>
        SELECT ?metric ?code ?name ?formula ?order ?component_name ?sql_expr ?bucket_code
        WHERE {
            ?metric a fin:L1Metric ;
                    fin:code ?code ;
                    fin:name ?name ;
                    fin:formula ?formula ;
                    fin:calculationOrder ?order .
            OPTIONAL {
                ?metric fin:usesFormula ?formula_node .
                ?formula_node fin:componentName ?component_name ;
                              fin:sqlExpression ?sql_expr .
            }
            OPTIONAL {
                ?metric fin:contains ?bucket .
                ?bucket fin:code ?bucket_code .
            }
        }
        ORDER BY ?order
        """

        # Execute query once and collect into list
        all_results = list(self.graph.query(sparql))
        logger.info(f"Total L1 metric rows in KG: {len(all_results)}")

        # Group results by metric URI
        metric_data = {}
        for row in all_results:
            metric_uri = str(row["metric"])
            code = str(row["code"]).lower()
            name = str(row["name"]).lower()

            # Only process metrics that match the query
            if code not in query_lower and name not in query_lower:
                continue

            if metric_uri not in metric_data:
                logger.info(f"✓ MATCHED metric: {code}")
                metric_data[metric_uri] = {
                    "code": str(row["code"]),
                    "name": str(row["name"]),
                    "formula": str(row["formula"]),
                    "order": row["order"],
                    "formula_components": {},
                    "sub_buckets": set()
                }

            # Collect formula components (may have multiple)
            if row.get("component_name") and row.get("sql_expr"):
                component_name = str(row["component_name"])
                sql_expr = str(row["sql_expr"])
                metric_data[metric_uri]["formula_components"][component_name] = sql_expr

            # Collect sub-buckets (may have multiple)
            if row.get("bucket_code"):
                metric_data[metric_uri]["sub_buckets"].add(str(row["bucket_code"]))

        logger.info(f"Matched {len(metric_data)} unique metrics from query")

        # Convert to MetricFormula objects
        for data in metric_data.values():
            metric = MetricFormula(
                metric_code=data["code"],
                metric_name=data["name"],
                formula=data["formula"],
                formula_components=data["formula_components"],
                sub_buckets=list(data["sub_buckets"])
            )
            metrics.append(metric)

        return metrics
    
    def _get_relevant_gl_accounts(self, query: str, metrics: List[MetricFormula],
                                 context: Optional[Dict[str, Any]] = None) -> List[GLMapping]:
        """Get relevant GL accounts from RDF.

        Optimized: Single batched query for all bucket codes instead of N+1.
        """
        gl_accounts = []
        seen_accounts = set()  # Avoid duplicates
        client_id = context.get("client_id") if context else None

        # Collect all bucket codes from all metrics
        all_bucket_codes = set()
        for metric in metrics:
            all_bucket_codes.update(metric.sub_buckets)

        # If we have bucket codes, get GL accounts for all buckets in one query
        if all_bucket_codes:
            # Build VALUES clause for SPARQL
            bucket_values = " ".join([f'"{code}"' for code in all_bucket_codes])

            sparql = f"""
            PREFIX fin: <http://example.com/finance#>
            SELECT ?gl ?account_num ?desc ?actual_bucket_code ?active
            WHERE {{
                VALUES ?bucket_code {{ {bucket_values} }}
                ?gl a fin:GLAccount ;
                    fin:accountNumber ?account_num ;
                    fin:description ?desc ;
                    fin:isActive ?active ;
                    fin:partOf ?bucket .
                ?bucket fin:code ?bucket_code .
                OPTIONAL {{ ?gl fin:bucketCode ?actual_bucket_code }}
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
                account_num = str(row["account_num"])
                if account_num not in seen_accounts:
                    seen_accounts.add(account_num)
                    gl_mapping = GLMapping(
                        account_number=account_num,
                        description=str(row["desc"]),
                        bucket_code=str(row.get("actual_bucket_code", "")),
                        client_id=client_id,
                        is_active=bool(row["active"])
                    )
                    gl_accounts.append(gl_mapping)

        # Check for direct GL account references in query
        gl_pattern = re.compile(r'\b(?:gl|account)\s*(\d{4,})\b', re.IGNORECASE)
        matches = gl_pattern.findall(query)

        if matches:
            # Batch query for all directly referenced account numbers
            account_values = " ".join([f'"{num}"' for num in matches])

            sparql = f"""
            PREFIX fin: <http://example.com/finance#>
            SELECT ?gl ?account_num ?desc ?bucket_code ?active
            WHERE {{
                VALUES ?account_num {{ {account_values} }}
                ?gl a fin:GLAccount ;
                    fin:accountNumber ?account_num ;
                    fin:description ?desc ;
                    fin:isActive ?active .
                OPTIONAL {{ ?gl fin:bucketCode ?bucket_code }}
            }}
            """

            results = self.graph.query(sparql)

            for row in results:
                account_num = str(row["account_num"])
                if account_num not in seen_accounts:
                    seen_accounts.add(account_num)
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
        """Get applicable business rules from RDF.

        Optimized: Single batched query for all metric codes instead of N+1.
        """
        if not metrics:
            return []

        # Build VALUES clause with all metric codes
        metric_codes = [f'"{m.metric_code}"' for m in metrics]
        metric_values = " ".join(metric_codes)

        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        SELECT ?rule ?name ?desc ?type ?condition ?action ?priority
        WHERE {{
            VALUES ?metric_code {{ {metric_values} }}
            ?rule a fin:BusinessRule ;
                  fin:name ?name ;
                  fin:description ?desc ;
                  fin:ruleType ?type ;
                  fin:condition ?condition ;
                  fin:action ?action ;
                  fin:priority ?priority ;
                  fin:isActive true ;
                  fin:appliesTo ?metric .
            ?metric fin:code ?metric_code .
        }}
        ORDER BY ?priority
        """

        rules = []
        seen_rules = set()  # Avoid duplicates
        results = self.graph.query(sparql)

        for row in results:
            rule_uri = str(row["rule"])
            if rule_uri not in seen_rules:
                seen_rules.add(rule_uri)
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
    
    def get_table_row_count(self, table_name: str) -> Optional[int]:
        """
        Get approximate row count for a table from RDF metadata.

        This is much faster than running EXPLAIN or COUNT(*) queries.

        Args:
            table_name: Name of the table

        Returns:
            Row count if available, None otherwise
        """
        # Build additional triple patterns for organization and database filtering
        # These are WHERE clause patterns, not FILTER expressions
        extra_patterns = []
        if self.organization_id:
            extra_patterns.append(f'?table schema:organizationId "{self.organization_id}" .')
        if self.database_type:
            extra_patterns.append(f'?table schema:databaseType "{self.database_type}" .')

        extra_patterns_clause = "\n            ".join(extra_patterns) if extra_patterns else ""

        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        PREFIX schema: <http://example.com/schema#>

        SELECT ?rowCount
        WHERE {{
            ?table a fin:Table ;
                   fin:tableName "{table_name}" ;
                   schema:rowCount ?rowCount .
            {extra_patterns_clause}
        }}
        LIMIT 1
        """

        try:
            results = self.graph.query(sparql)
            if results:
                row_count = int(results[0].get('rowCount', 0))
                logger.debug(f"Got row count from Jena: {table_name} = {row_count:,} rows")
                return row_count
        except Exception as e:
            logger.warning(f"Failed to get row count for {table_name}: {e}")

        return None

    def get_table_row_counts(self, table_names: List[str]) -> Dict[str, int]:
        """
        Get row counts for multiple tables in a single query.

        Args:
            table_names: List of table names

        Returns:
            Dict mapping table name to row count
        """
        if not table_names:
            return {}

        # Build additional triple patterns for organization and database filtering
        extra_patterns = []
        if self.organization_id:
            extra_patterns.append(f'?table schema:organizationId "{self.organization_id}" .')
        if self.database_type:
            extra_patterns.append(f'?table schema:databaseType "{self.database_type}" .')

        # Build VALUES clause for table names
        values_clause = " ".join([f'"{t}"' for t in table_names])
        extra_patterns_clause = "\n            ".join(extra_patterns) if extra_patterns else ""

        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        PREFIX schema: <http://example.com/schema#>

        SELECT ?tableName ?rowCount
        WHERE {{
            VALUES ?tableName {{ {values_clause} }}
            ?table a fin:Table ;
                   fin:tableName ?tableName ;
                   schema:rowCount ?rowCount .
            {extra_patterns_clause}
        }}
        """

        row_counts = {}
        try:
            results = self.graph.query(sparql)
            for row in results:
                table_name = str(row.get('tableName'))
                row_count = int(row.get('rowCount', 0))
                row_counts[table_name] = row_count

            logger.info(f"Got row counts from Jena for {len(row_counts)}/{len(table_names)} tables")
        except Exception as e:
            logger.warning(f"Failed to get row counts: {e}")

        return row_counts

    def get_column_selectivity(self, table_name: str, column_name: str) -> Optional[float]:
        """
        Get selectivity for a specific column.

        Selectivity = cardinality / row_count (higher = more unique values)

        Args:
            table_name: Name of the table
            column_name: Name of the column

        Returns:
            Selectivity value (0.0 - 1.0) if available, None otherwise
        """
        # Build additional triple patterns for organization and database filtering
        extra_patterns = []
        if self.organization_id:
            extra_patterns.append(f'?table schema:organizationId "{self.organization_id}" .')
        if self.database_type:
            extra_patterns.append(f'?table schema:databaseType "{self.database_type}" .')

        extra_patterns_clause = "\n            ".join(extra_patterns) if extra_patterns else ""

        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        PREFIX schema: <http://example.com/schema#>
        PREFIX stats: <http://example.com/statistics#>

        SELECT ?selectivity
        WHERE {{
            ?table a fin:Table ;
                   fin:tableName "{table_name}" .
            ?column a fin:Column ;
                    fin:columnName "{column_name}" ;
                    fin:belongsTo ?table ;
                    stats:selectivity ?selectivity .
            {extra_patterns_clause}
        }}
        LIMIT 1
        """

        try:
            results = self.graph.query(sparql)
            if results:
                selectivity = float(results[0].get('selectivity', 0.5))
                logger.debug(f"Got selectivity from Jena: {table_name}.{column_name} = {selectivity:.4f}")
                return selectivity
        except Exception as e:
            logger.warning(f"Failed to get selectivity for {table_name}.{column_name}: {e}")

        return None

    def get_high_selectivity_columns(self, table_name: str, min_selectivity: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get columns with high selectivity (good for filtering).

        Args:
            table_name: Name of the table
            min_selectivity: Minimum selectivity threshold (default 0.5 = 50% unique)

        Returns:
            List of column info dicts with name, selectivity, cardinality
        """
        # Build additional triple patterns for organization and database filtering
        extra_patterns = []
        if self.organization_id:
            extra_patterns.append(f'?table schema:organizationId "{self.organization_id}" .')
        if self.database_type:
            extra_patterns.append(f'?table schema:databaseType "{self.database_type}" .')

        extra_patterns_clause = "\n            ".join(extra_patterns) if extra_patterns else ""

        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        PREFIX schema: <http://example.com/schema#>
        PREFIX stats: <http://example.com/statistics#>

        SELECT ?columnName ?selectivity ?cardinality ?hasIndex
        WHERE {{
            ?table a fin:Table ;
                   fin:tableName "{table_name}" .
            ?column a fin:Column ;
                    fin:columnName ?columnName ;
                    fin:belongsTo ?table ;
                    stats:selectivity ?selectivity .
            OPTIONAL {{ ?column stats:cardinality ?cardinality }}
            OPTIONAL {{ ?column stats:hasIndex ?hasIndex }}
            FILTER(?selectivity >= {min_selectivity})
            {extra_patterns_clause}
        }}
        ORDER BY DESC(?selectivity)
        """

        columns = []
        try:
            results = self.graph.query(sparql)
            for row in results:
                columns.append({
                    "column_name": str(row.get('columnName')),
                    "selectivity": float(row.get('selectivity', 0)),
                    "cardinality": int(row.get('cardinality', 0)) if row.get('cardinality') else None,
                    "has_index": bool(row.get('hasIndex', False))
                })

            logger.debug(f"Found {len(columns)} high-selectivity columns for {table_name}")
        except Exception as e:
            logger.warning(f"Failed to get high selectivity columns for {table_name}: {e}")

        return columns

    def find_materialized_view(
        self,
        base_table: str,
        aggregation_columns: Optional[List[str]] = None,
        group_by_columns: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find a materialized view that can satisfy an aggregation query on the given base table.

        Matches MV if:
        1. MV aggregates the base table
        2. MV includes the required aggregation columns (or all if not specified)
        3. MV includes the required group by columns (or all if not specified)

        Args:
            base_table: Name of the base table being queried
            aggregation_columns: Columns being aggregated (e.g., ['revenue', 'quantity'])
            group_by_columns: Columns in GROUP BY (e.g., ['store_id'])

        Returns:
            Dict with mv_name, aggregation_columns, group_by_columns, row_count if found
            None if no matching MV exists

        Example:
            # Find MV for "SELECT SUM(revenue) FROM sales GROUP BY store_id"
            mv = resolver.find_materialized_view(
                base_table="SALES",
                aggregation_columns=["REVENUE"],
                group_by_columns=["STORE_ID"]
            )
            # Returns: {"mv_name": "SALES_BY_STORE", "group_by_columns": ["STORE_ID"], ...}
        """
        # Build additional triple patterns for organization and database filtering
        extra_patterns = []
        if self.organization_id:
            extra_patterns.append(f'?mv schema:organizationId "{self.organization_id}" .')
        if self.database_type:
            extra_patterns.append(f'?mv schema:databaseType "{self.database_type}" .')

        extra_patterns_clause = "\n            ".join(extra_patterns) if extra_patterns else ""

        # First, get all MVs for this base table
        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        PREFIX schema: <http://example.com/schema#>

        SELECT ?mvName ?rowCount ?refreshSchedule
               (GROUP_CONCAT(DISTINCT ?aggCol; separator=",") AS ?aggregationColumns)
               (GROUP_CONCAT(DISTINCT ?groupCol; separator=",") AS ?groupByColumns)
        WHERE {{
            ?mv a fin:MaterializedView ;
                schema:tableName ?mvName ;
                schema:isMaterializedViewOf ?baseTable .
            ?baseTable schema:tableName ?baseTableName .
            FILTER(UCASE(?baseTableName) = "{base_table.upper()}")

            OPTIONAL {{ ?mv schema:aggregatesColumn ?aggCol }}
            OPTIONAL {{ ?mv schema:groupByColumn ?groupCol }}
            OPTIONAL {{ ?mv schema:rowCount ?rowCount }}
            OPTIONAL {{ ?mv schema:refreshSchedule ?refreshSchedule }}
            {extra_patterns_clause}
        }}
        GROUP BY ?mvName ?rowCount ?refreshSchedule
        """

        try:
            results = self.graph.query(sparql)

            best_match = None
            best_score = 0

            for row in results:
                mv_agg_cols = set(
                    c.strip().upper()
                    for c in str(row.aggregationColumns or "").split(",")
                    if c.strip()
                )
                mv_group_cols = set(
                    c.strip().upper()
                    for c in str(row.groupByColumns or "").split(",")
                    if c.strip()
                )

                # Check if MV satisfies the query requirements
                score = 0

                # Check aggregation columns match
                if aggregation_columns:
                    required_agg = set(c.upper() for c in aggregation_columns)
                    if required_agg.issubset(mv_agg_cols):
                        score += len(required_agg)  # More matching columns = higher score
                    else:
                        continue  # Skip if missing required aggregation columns
                else:
                    score += len(mv_agg_cols)  # Bonus for having aggregation columns

                # Check group by columns match
                if group_by_columns:
                    required_group = set(c.upper() for c in group_by_columns)
                    if required_group.issubset(mv_group_cols):
                        score += len(required_group) * 2  # Group by columns weighted more
                    else:
                        continue  # Skip if missing required group by columns
                else:
                    score += len(mv_group_cols)  # Bonus for having group by columns

                # Track best match
                if score > best_score:
                    best_score = score
                    best_match = {
                        "mv_name": str(row.mvName),
                        "aggregation_columns": list(mv_agg_cols),
                        "group_by_columns": list(mv_group_cols),
                        "row_count": int(row.rowCount) if row.rowCount else 0,
                        "refresh_schedule": str(row.refreshSchedule) if row.refreshSchedule else "unknown",
                        "match_score": score
                    }

            if best_match:
                logger.info(
                    f"Found materialized view for {base_table}: {best_match['mv_name']} "
                    f"(score: {best_match['match_score']})"
                )
            else:
                logger.debug(f"No matching materialized view found for {base_table}")

            return best_match

        except Exception as e:
            logger.warning(f"Failed to find materialized view for {base_table}: {e}")
            return None

    def get_join_selectivity(self, left_col: str, right_col: str) -> Optional[float]:
        """
        Get estimated join selectivity between two columns.

        Returns a factor 0-1 where lower = more selective (fewer rows after join).

        Args:
            left_col: Left side join column name
            right_col: Right side join column name

        Returns:
            Selectivity factor if known, None otherwise
        """
        # Build additional triple patterns for organization and database filtering
        # Note: For join relationships, we filter on the relationship itself
        extra_patterns = []
        if self.organization_id:
            extra_patterns.append(f'?rel schema:organizationId "{self.organization_id}" .')
        if self.database_type:
            extra_patterns.append(f'?rel schema:databaseType "{self.database_type}" .')

        extra_patterns_clause = "\n            ".join(extra_patterns) if extra_patterns else ""

        # Look for FK relationship that indicates join pattern
        sparql = f"""
        PREFIX fin: <http://example.com/finance#>
        PREFIX schema: <http://example.com/schema#>
        PREFIX stats: <http://example.com/stats#>

        SELECT ?selectivity
        WHERE {{
            ?rel a fin:JoinRelationship ;
                 schema:sourceColumn ?srcCol ;
                 schema:targetColumn ?tgtCol .
            ?srcCol schema:columnName ?srcColName .
            ?tgtCol schema:columnName ?tgtColName .
            FILTER(
                (UCASE(?srcColName) = "{left_col.upper()}" && UCASE(?tgtColName) = "{right_col.upper()}")
                || (UCASE(?srcColName) = "{right_col.upper()}" && UCASE(?tgtColName) = "{left_col.upper()}")
            )
            OPTIONAL {{ ?rel stats:joinSelectivity ?selectivity }}
            {extra_patterns_clause}
        }}
        LIMIT 1
        """

        try:
            results = self.graph.query(sparql)
            if results:
                selectivity = float(results[0].get('selectivity', 0.8))
                logger.debug(f"Got join selectivity for {left_col}-{right_col}: {selectivity:.4f}")
                return selectivity
        except Exception as e:
            logger.debug(f"No join selectivity found for {left_col}-{right_col}: {e}")

        return None

    def close(self):
        """Close the graph connection."""
        self.graph.close()