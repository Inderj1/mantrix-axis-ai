# Mantrix Axis AI - System Architecture

**Version:** 2.0 (November 2025)
**Status:** Production Ready (AWS Marketplace)

---

## High-Level Architecture

```
                                    MANTRIX AXIS AI
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                                                                          │
    │   ┌──────────────────────────────────────────────────────────────────┐  │
    │   │                      REACT FRONTEND (Vite)                        │  │
    │   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │  │
    │   │  │ Agent Chat  │  │  Dashboard  │  │    Control Center       │   │  │
    │   │  │ Interface   │  │  Analytics  │  │  (DB Config, Health)    │   │  │
    │   │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │  │
    │   └──────────────────────────────────────────────────────────────────┘  │
    │                                    │                                     │
    │                                    ▼ REST API                            │
    │   ┌──────────────────────────────────────────────────────────────────┐  │
    │   │                    FASTAPI BACKEND (Python)                       │  │
    │   │                                                                   │  │
    │   │   ┌───────────────────────────────────────────────────────────┐  │  │
    │   │   │                    API LAYER                               │  │  │
    │   │   │  routes.py │ agent_routes.py │ connector_routes.py │ ...  │  │  │
    │   │   └───────────────────────────────────────────────────────────┘  │  │
    │   │                              │                                    │  │
    │   │   ┌───────────────────────────────────────────────────────────┐  │  │
    │   │   │                   CORE LAYER                               │  │  │
    │   │   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │  │  │
    │   │   │  │ SQL         │  │ Knowledge   │  │ Federation      │    │  │  │
    │   │   │  │ Generator   │  │ Graph       │  │ Factory         │    │  │  │
    │   │   │  │             │  │ (Jena RDF)  │  │ (100GB+ JOINs)  │    │  │  │
    │   │   │  └─────────────┘  └─────────────┘  └─────────────────┘    │  │  │
    │   │   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │  │  │
    │   │   │  │ Cross-DB    │  │ Query       │  │ Format          │    │  │  │
    │   │   │  │ Executor    │  │ Optimizer   │  │ Normalizer      │    │  │  │
    │   │   │  │             │  │ (Pushdown)  │  │ (SAP Leading 0) │    │  │  │
    │   │   │  └─────────────┘  └─────────────┘  └─────────────────┘    │  │  │
    │   │   └───────────────────────────────────────────────────────────┘  │  │
    │   │                              │                                    │  │
    │   │   ┌───────────────────────────────────────────────────────────┐  │  │
    │   │   │                DATABASE LAYER                              │  │  │
    │   │   │  ┌──────────────────────────────────────────────────┐     │  │  │
    │   │   │  │            Connector Factory                      │     │  │  │
    │   │   │  │  (Permission-Enforced Database Access)            │     │  │  │
    │   │   │  └──────────────────────────────────────────────────┘     │  │  │
    │   │   │       │           │           │           │          │     │  │  │
    │   │   │       ▼           ▼           ▼           ▼          ▼     │  │  │
    │   │   │  ┌────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌───────┐ │  │  │
    │   │   │  │BigQuery│ │Snowflake│ │PostgreSQL│ │Redshift│ │Databri│ │  │  │
    │   │   │  │        │ │ (Pool)  │ │  (Pool)  │ │        │ │ cks   │ │  │  │
    │   │   │  └────────┘ └─────────┘ └──────────┘ └────────┘ └───────┘ │  │  │
    │   │   └───────────────────────────────────────────────────────────┘  │  │
    │   └──────────────────────────────────────────────────────────────────┘  │
    │                                                                          │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         SUPPORTING SERVICES                              │
    │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐    │
    │   │   Redis    │  │  MongoDB   │  │  Weaviate  │  │  AWS Cognito   │    │
    │   │  (Cache)   │  │ (History)  │  │ (Vectors)  │  │  (Auth/JWT)    │    │
    │   └────────────┘  └────────────┘  └────────────┘  └────────────────┘    │
    └─────────────────────────────────────────────────────────────────────────┘
```

---

## NLP-to-SQL Query Flow

```
    User Query: "Show me top customers by revenue last quarter"
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────┐
    │                    1. CACHE CHECK (Redis)                      │
    │    SHA256(query + context) → Check SQL cache (7-day TTL)       │
    │    Cache hit? → Return cached SQL → Execute → Return results   │
    └───────────────────────────────────────────────────────────────┘
                                    │ Cache miss
                                    ▼
    ┌───────────────────────────────────────────────────────────────┐
    │              2. FINANCIAL SEMANTIC PARSER                      │
    │    Parse financial terms → Identify metrics, time periods      │
    │    "revenue" → Net_Sales, "last quarter" → Q3 2024            │
    └───────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────┐
    │              3. KNOWLEDGE GRAPH LOOKUP (Jena RDF)              │
    │    SPARQL queries for:                                         │
    │    - Table relationships (JOINs)                               │
    │    - Column mappings (semantic → physical)                     │
    │    - Data types and constraints                                │
    │    Redis-cached with gzip+turtle (24h TTL)                     │
    └───────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────┐
    │                   4. LLM SQL GENERATION                        │
    │    Claude claude-sonnet-4-5-20250929 with:                                     │
    │    - Schema context from Knowledge Graph                       │
    │    - Financial templates                                       │
    │    - Query examples                                            │
    │    → Generated SQL                                             │
    └───────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────┐
    │                 5. FORMAT NORMALIZATION                        │
    │    SAP leading zero fix: '0000123' vs '123'                    │
    │    Apply LTRIM(column, '0') to JOIN columns                    │
    │    100-1000x JOIN accuracy improvement                         │
    └───────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────┐
    │                  6. QUERY OPTIMIZATION                         │
    │    - Pushdown filters to source databases                      │
    │    - Remove redundant clauses                                  │
    │    - Estimate costs (BigQuery dry-run)                         │
    │    → 90-95% data reduction                                     │
    └───────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────┐
    │              7. DATABASE EXECUTION                             │
    │    Connector Factory → Permission check → Execute              │
    │    Results → Cache → Return to user                            │
    └───────────────────────────────────────────────────────────────┘
```

---

## Cross-Database Federation Architecture

```
    Cross-DB JOIN Request
    "JOIN BigQuery.orders WITH Snowflake.customers"
                                    │
                                    ▼
    ┌───────────────────────────────────────────────────────────────┐
    │              CROSS-DATABASE EXECUTOR                           │
    │                                                                │
    │    1. Estimate row counts (EXPLAIN or metadata)                │
    │    2. Select strategy based on data size                       │
    └───────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
    │  PANDAS      │      │  STAGING     │      │  S3 FEDERATION   │
    │  Strategy    │      │  Strategy    │      │  Strategy        │
    │              │      │              │      │                  │
    │  < 1M rows   │      │ 1-10M rows   │      │  > 10M rows      │
    │  (~1 GB)     │      │ (~1-10 GB)   │      │  (10-100GB+)     │
    │              │      │              │      │                  │
    │  In-memory   │      │  Temp tables │      │  Stream → S3     │
    │  pd.merge()  │      │  in target   │      │  → Spectrum/Omni │
    └──────────────┘      └──────────────┘      └──────────────────┘
                                                        │
                                                        ▼
                            ┌────────────────────────────────────────┐
                            │         FEDERATION FACTORY             │
                            │                                        │
                            │   ┌──────────────────────────────┐    │
                            │   │  Redshift Spectrum (Default) │    │
                            │   │  → S3 Parquet + External Tbl │    │
                            │   └──────────────────────────────┘    │
                            │   ┌──────────────────────────────┐    │
                            │   │  BigQuery Omni               │    │
                            │   │  → External tables on S3/GCS │    │
                            │   └──────────────────────────────┘    │
                            │   ┌──────────────────────────────┐    │
                            │   │  Snowflake External Stage    │    │
                            │   │  → S3 stage + COPY INTO      │    │
                            │   └──────────────────────────────┘    │
                            └────────────────────────────────────────┘
```

---

## Knowledge Graph Architecture (Jena RDF)

```
    ┌────────────────────────────────────────────────────────────────────┐
    │                    KNOWLEDGE GRAPH (Apache Jena)                    │
    │                                                                     │
    │   ┌─────────────────────────────────────────────────────────────┐  │
    │   │                      RDF TRIPLE STORE                        │  │
    │   │                                                              │  │
    │   │    Subject          Predicate           Object               │  │
    │   │    ─────────────────────────────────────────────────         │  │
    │   │    fin:customers    fin:hasColumn       fin:customer_id      │  │
    │   │    fin:customer_id  fin:dataType        xsd:string           │  │
    │   │    fin:customer_id  fin:semanticType    fin:CustomerID       │  │
    │   │    fin:customers    fin:relatedTo       fin:orders           │  │
    │   │    fin:Net_Sales    fin:formula         "SUM(amount)"        │  │
    │   └─────────────────────────────────────────────────────────────┘  │
    │                              │                                      │
    │                              ▼                                      │
    │   ┌─────────────────────────────────────────────────────────────┐  │
    │   │                    JENA QUERY RESOLVER                       │  │
    │   │                                                              │  │
    │   │    SPARQL Queries:                                           │  │
    │   │    - find_tables_for_columns(["customer_id", "revenue"])     │  │
    │   │    - get_join_path(table_a, table_b)                         │  │
    │   │    - get_column_semantics(column_name)                       │  │
    │   │                                                              │  │
    │   │    Optimizations:                                            │  │
    │   │    - Batched queries with VALUES clause                      │  │
    │   │    - OPTIONAL clauses to avoid N+1                           │  │
    │   │    - Redis caching (gzip+turtle, 24h TTL)                    │  │
    │   └─────────────────────────────────────────────────────────────┘  │
    │                                                                     │
    │   ┌─────────────────────────────────────────────────────────────┐  │
    │   │                    STORAGE OPTIONS                           │  │
    │   │                                                              │  │
    │   │    ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐  │  │
    │   │    │  In-Memory  │   │   File      │   │   Redis Cache   │  │  │
    │   │    │  (rdflib)   │   │  (.ttl.gz)  │   │   (compressed)  │  │  │
    │   │    └─────────────┘   └─────────────┘   └─────────────────┘  │  │
    │   └─────────────────────────────────────────────────────────────┘  │
    └────────────────────────────────────────────────────────────────────┘
```

---

## Caching Architecture

```
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    MULTI-TIER REDIS CACHE                           │
    │                                                                      │
    │   ┌───────────────────────────────────────────────────────────────┐ │
    │   │                      CACHE TIERS                               │ │
    │   │                                                                │ │
    │   │   ┌──────────────────┬──────────────────┬───────────────────┐ │ │
    │   │   │     SQL Cache    │   Schema Cache   │  Embedding Cache  │ │ │
    │   │   ├──────────────────┼──────────────────┼───────────────────┤ │ │
    │   │   │  Key: SHA256     │  Key: table_name │  Key: text_hash   │ │ │
    │   │   │       (query+ctx)│                  │                   │ │ │
    │   │   │                  │                  │                   │ │ │
    │   │   │  TTL: 7 days     │  TTL: 24 hours   │  TTL: 30 days     │ │ │
    │   │   │  (frequent) or   │                  │                   │ │ │
    │   │   │  1 day (rare)    │                  │                   │ │ │
    │   │   └──────────────────┴──────────────────┴───────────────────┘ │ │
    │   │                                                                │ │
    │   │   ┌──────────────────────────────────────────────────────────┐│ │
    │   │   │              Knowledge Graph Cache                        ││ │
    │   │   │                                                           ││ │
    │   │   │   Format: gzip-compressed Turtle                          ││ │
    │   │   │   Compression: 5-10x size reduction                       ││ │
    │   │   │   Validation: MD5 hash of source .ttl file                ││ │
    │   │   │   TTL: 24 hours                                           ││ │
    │   │   └──────────────────────────────────────────────────────────┘│ │
    │   └───────────────────────────────────────────────────────────────┘ │
    │                                                                      │
    │   Feature Flags:                                                     │
    │   - CACHE_ENABLED (global)                                          │
    │   - CACHE_SQL_ENABLED                                               │
    │   - CACHE_SCHEMA_ENABLED                                            │
    │   - CACHE_EMBEDDING_ENABLED                                         │
    └─────────────────────────────────────────────────────────────────────┘
```

---

## Database Connector Architecture

```
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    DATABASE CONNECTOR LAYER                          │
    │                                                                      │
    │   ┌───────────────────────────────────────────────────────────────┐ │
    │   │                  BaseDatabaseConnector (ABC)                   │ │
    │   │                                                                │ │
    │   │   Abstract Methods:                                            │ │
    │   │   ├── connect()                                                │ │
    │   │   ├── disconnect()                                             │ │
    │   │   ├── execute_query(query, params) → Dict                      │ │
    │   │   ├── get_table_schema(table) → Dict                           │ │
    │   │   ├── list_tables(schema) → List[str]                          │ │
    │   │   ├── get_dataset_schema(schema) → List[Dict]                  │ │
    │   │   ├── validate_query(query) → Dict                             │ │
    │   │   └── get_capabilities() → DatabaseCapabilities                │ │
    │   │                                                                │ │
    │   │   Streaming Support (Default impl, override for native):       │ │
    │   │   ├── execute_query_streaming(query, chunk_size) → Iterator    │ │
    │   │   └── execute_query_streaming_async(query) → AsyncIterator     │ │
    │   └───────────────────────────────────────────────────────────────┘ │
    │                              │                                       │
    │        ┌─────────────────────┼─────────────────────┐                │
    │        │                     │                     │                │
    │        ▼                     ▼                     ▼                │
    │   ┌──────────┐         ┌──────────┐         ┌──────────────┐       │
    │   │ BigQuery │         │Snowflake │         │  PostgreSQL  │       │
    │   │Connector │         │Connector │         │  Connector   │       │
    │   │          │         │          │         │              │       │
    │   │ Features:│         │ Features:│         │ Features:    │       │
    │   │ -Page tok│         │ -Queue   │         │ -Threaded    │       │
    │   │ -Dry-run │         │  pool    │         │  pool        │       │
    │   │  cost    │         │ -Warehouse│        │ -Connection  │       │
    │   │ -Batch   │         │  mgmt    │         │  reuse       │       │
    │   │  insert  │         │ -Key-pair│         │              │       │
    │   └──────────┘         └──────────┘         └──────────────┘       │
    │        │                     │                     │                │
    │        └─────────────────────┼─────────────────────┘                │
    │                              │                                       │
    │                              ▼                                       │
    │   ┌───────────────────────────────────────────────────────────────┐ │
    │   │                   CONNECTOR FACTORY                            │ │
    │   │                                                                │ │
    │   │   create_connector(db_type, config) → BaseDatabaseConnector   │ │
    │   │                                                                │ │
    │   │   Permission Enforcement:                                      │ │
    │   │   ├── Organization isolation                                   │ │
    │   │   ├── Access levels: NONE, READ, WRITE, ADMIN                 │ │
    │   │   └── check_user_access(user_id, db_type, level, org_id)      │ │
    │   └───────────────────────────────────────────────────────────────┘ │
    └─────────────────────────────────────────────────────────────────────┘
```

---

## Authentication & Multi-Tenancy

```
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    AWS COGNITO AUTHENTICATION                        │
    │                                                                      │
    │   ┌───────────────────────────────────────────────────────────────┐ │
    │   │                     JWT Token Flow                             │ │
    │   │                                                                │ │
    │   │   User Login                                                   │ │
    │   │       │                                                        │ │
    │   │       ▼                                                        │ │
    │   │   ┌────────────────┐                                          │ │
    │   │   │ Cognito User   │  ──── Groups: Admins, Users              │ │
    │   │   │ Pool           │  ──── Custom Attrs: organization_id      │ │
    │   │   └────────────────┘                                          │ │
    │   │       │                                                        │ │
    │   │       ▼ JWT Token (ID + Access)                               │ │
    │   │   ┌────────────────┐                                          │ │
    │   │   │ Auth Middleware│  ──── Validate signature                 │ │
    │   │   │                │  ──── Extract user_id, org_id, groups    │ │
    │   │   └────────────────┘                                          │ │
    │   │       │                                                        │ │
    │   │       ▼                                                        │ │
    │   │   ┌────────────────┐                                          │ │
    │   │   │ Permission     │  ──── Check database access levels       │ │
    │   │   │ Enforcement    │  ──── Enforce organization isolation     │ │
    │   │   └────────────────┘                                          │ │
    │   └───────────────────────────────────────────────────────────────┘ │
    │                                                                      │
    │   Multi-Tenancy:                                                    │
    │   ├── Each organization has isolated data access                   │
    │   ├── Connectors scoped to organization_id                         │
    │   ├── Admin users can manage org settings                          │
    │   └── Regular users limited to READ access by default              │
    └─────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
mantrix-axis-ai/
├── README.md                    # Project overview
├── CLAUDE.md                    # Claude Code instructions
├── CONTRIBUTING.md              # Contribution guidelines
├── TESTING.md                   # Testing guide
├── docker-compose.yml           # Service orchestration
├── start_dev.sh / stop_dev.sh   # Development scripts
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # This file
│   ├── COGNITO_SETUP.md         # Auth setup
│   ├── DEPLOYMENT_PLAN.md       # AWS deployment
│   ├── PRODUCTION_DEPLOYMENT.md # Production guide
│   ├── SMART_CACHING_GUIDE.md   # Cache configuration
│   └── ...
│
├── backend/                     # Python FastAPI backend
│   ├── src/
│   │   ├── main.py              # App entry point
│   │   ├── config.py            # Pydantic settings
│   │   │
│   │   ├── api/                 # API routes
│   │   │   ├── routes.py        # Main NLP-to-SQL (94KB)
│   │   │   ├── agent_routes.py  # Agent mode
│   │   │   ├── connector_routes.py  # DB connectors
│   │   │   └── ...
│   │   │
│   │   ├── core/                # Core business logic
│   │   │   ├── sql_generator.py # SQL generation (64KB)
│   │   │   ├── cross_database_executor.py  # Multi-DB execution
│   │   │   ├── federation_factory.py       # 100GB+ JOINs
│   │   │   ├── s3_federation.py            # S3/Spectrum federation
│   │   │   ├── format_normalizer.py        # SAP leading zeros
│   │   │   ├── query_pushdown_optimizer.py # Pushdown optimization
│   │   │   │
│   │   │   └── knowledge_graph/            # Jena RDF system
│   │   │       ├── jena_singleton.py       # Lazy initialization
│   │   │       ├── jena_query_resolver.py  # SPARQL queries
│   │   │       ├── jena_redis_store.py     # Redis caching
│   │   │       ├── join_path_finder.py     # JOIN discovery
│   │   │       └── column_matcher.py       # Semantic matching
│   │   │
│   │   ├── db/                  # Database layer
│   │   │   ├── base_connector.py    # Abstract base
│   │   │   ├── connector_factory.py # Factory + permissions
│   │   │   ├── database_capabilities.py
│   │   │   └── connectors/
│   │   │       ├── bigquery_connector.py
│   │   │       ├── snowflake_connector.py  # Queue pool
│   │   │       ├── postgresql_connector.py # Thread pool
│   │   │       ├── redshift_connector.py
│   │   │       └── databricks_connector.py
│   │   │
│   │   ├── agents/              # Multi-agent system
│   │   │   ├── orchestrator.py  # CrewAI orchestration
│   │   │   └── financial_crew.py
│   │   │
│   │   └── pipeline/            # ETL pipelines
│   │       ├── orchestrator.py
│   │       ├── rdf_builder.py
│   │       └── schema_extractor.py
│   │
│   ├── tests/                   # Test directory
│   │   └── fixtures/            # Test data
│   │
│   └── requirements.txt         # Python dependencies
│
├── frontend/                    # React Vite frontend
│   ├── src/
│   │   ├── App.jsx              # Main app
│   │   ├── components/
│   │   │   ├── AgentModeInterface.jsx  # Chat UI (151KB)
│   │   │   ├── CoreAIDashboard.jsx     # Dashboard (171KB)
│   │   │   └── controlcenter/          # Admin UI
│   │   ├── services/
│   │   │   └── api.js           # Axios client
│   │   └── contexts/
│   │       └── AuthContext.jsx  # Cognito auth
│   │
│   └── package.json
│
├── cdk/                         # AWS CDK infrastructure
├── cloudformation/              # CloudFormation templates
└── deployment/                  # Deployment scripts
```

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18 + Vite + MUI v5 | User interface |
| **Backend** | FastAPI (Python 3.9+) | API server |
| **LLM** | Claude claude-sonnet-4-5-20250929 | SQL generation |
| **Embeddings** | OpenAI text-embedding-3-small | Vector search |
| **Knowledge Graph** | Apache Jena (rdflib) | Schema understanding |
| **Cache** | Redis 7.x | Multi-tier caching |
| **Vector DB** | Weaviate | Semantic search |
| **Document Store** | MongoDB | Conversation history |
| **Auth** | AWS Cognito | JWT authentication |
| **Databases** | BigQuery, Snowflake, PostgreSQL, Redshift, Databricks | Data warehouses |
| **Federation** | S3 + Redshift Spectrum | 100GB+ cross-DB JOINs |

---

## Key Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Query cache hit rate | 60-80% | 7-day TTL for frequent queries |
| KG compression ratio | 5-10x | gzip + turtle format |
| Cross-DB JOIN capacity | 100GB+ | S3 federation strategy |
| Query pushdown reduction | 90-95% | Filter/projection pushdown |
| SAP JOIN accuracy improvement | 100-1000x | Leading zero normalization |
| Connection pool reuse | 10-50 connections | Per database type |

---

## Environment Variables (Key)

```bash
# AI Services
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# Auth
AWS_COGNITO_USER_POOL_ID=us-east-1_xxxxx
AWS_COGNITO_REGION=us-east-1
AWS_COGNITO_CLIENT_ID=xxxxx

# Federation (100GB+ JOINs)
FEDERATION_ENABLED=true
FEDERATION_S3_BUCKET=my-federation-bucket
FEDERATION_S3_PREFIX=federation

# Databases
GOOGLE_CLOUD_PROJECT=my-project
BIGQUERY_DATASET=my-dataset
SNOWFLAKE_ACCOUNT=xy12345.us-east-1
# ... see config.py for full list
```

---

*Last updated: November 2025*
