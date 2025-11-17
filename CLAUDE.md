# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mantrix Axis AI** (STOX.AI) is an AI-powered supply chain intelligence platform that converts natural language queries into SQL for multiple databases (BigQuery, PostgreSQL, Snowflake, Databricks, Redshift). The platform features conversational AI, financial analytics, process mining, document intelligence, and market signal monitoring.

**Architecture**: Full-stack application with React (Vite) frontend and FastAPI backend, using multiple databases and Redis caching. The system employs Apache Jena knowledge graphs for semantic schema understanding and multi-agent orchestration via CrewAI.

## Development Commands

### Starting the Application

```bash
# Start complete development environment (recommended)
./start_dev.sh
# Starts: Frontend (5174), Backend (8000), Redis, Weaviate, MongoDB
# Logs to: logs/backend.log and logs/frontend.log

# Stop all services
./stop_dev.sh

# Start services individually
cd frontend && npm start                                                    # Frontend only
cd backend && source venv/bin/activate && uvicorn src.main:app --reload    # Backend only
```

### Installing Dependencies

```bash
# Install all dependencies (from root)
npm run install

# Backend only
cd backend && pip install -r requirements.txt

# Frontend only
cd frontend && npm install

# Build frontend for production
cd frontend && npm run build
```

### Testing

```bash
# Backend tests (run from backend directory with venv activated)
cd backend && source venv/bin/activate
python test_apis.py
python test_query_flow.py
python test_column_synonyms.py
./run_tests.sh                    # Run all test files
./test_queries.sh                 # Test query execution

# Frontend linting
cd frontend && npm run lint
```

### Docker Services

```bash
docker-compose up -d                                       # Start all services
docker-compose up -d mongodb neo4j weaviate redis postgres # Start specific services
docker-compose down                                        # Stop all services
docker-compose logs -f [service-name]                      # View logs
docker-compose ps                                          # Check service health
```

## Architecture

### Backend Structure (`backend/src/`)

**Core SQL Generation Flow**:
1. `api/routes.py:execute_query_endpoint()` - Main entry point (94KB, handles all NLP-to-SQL requests)
2. `core/sql_generator.py` - Orchestrates entire SQL generation pipeline (64KB):
   - Cache check via `CacheManager` (Redis)
   - Financial semantic parsing via `financial_semantic_parser.py`
   - Knowledge graph lookup via Jena (`core/knowledge_graph/`)
   - LLM call via `LLMClient` (Anthropic Claude)
   - Format normalization via `FormatNormalizer` (fixes leading zeros in JOINs)
   - Query optimization via `QueryOptimizer`
3. Database execution via connector factory (`db/connector_factory.py`)
4. Results cached and returned

**Multi-Database Architecture**:
- `db/base_connector.py` - Abstract base class defining standard interface
- `db/connector_factory.py` - Factory pattern with permission enforcement
- `db/connectors/` - Database-specific implementations:
  - `bigquery_connector.py` - Google BigQuery (with page tokens, cost estimation)
  - `snowflake_connector.py` - Snowflake (warehouse management, key-pair auth)
  - `postgresql_connector.py` - PostgreSQL
  - `redshift_connector.py` - Amazon Redshift
  - `databricks_connector.py` - Databricks (Spark SQL)
- `core/database_permissions.py` - Permission levels (none/read/write/admin) with organization isolation

**Knowledge Graph System** (`core/knowledge_graph/`):
- Uses Apache Jena RDF/SPARQL for semantic schema understanding
- `jena_singleton.py` - Singleton pattern for lazy initialization
- `jena_client.py` - RDF triple store operations
- `jena_query_resolver.py` - SPARQL query resolution for table/column relationships
- `join_path_finder.py` - Automatic JOIN path discovery across tables
- `column_matcher.py` - Semantic column matching using embeddings
- Schema metadata loaded via `backend/load_table_metadata_to_jena.py`

**Format Normalization**:
- `core/format_normalizer.py` - Fixes SAP leading zero issues in JOINs (e.g., '0000123' vs '123')
- Automatically detects format mismatches and applies `LTRIM(column, '0')` transformations
- Improves JOIN accuracy by 100-1000x in real-world SAP data

**Multi-Agent System** (`agents/`):
- `orchestrator.py` - Coordinates multi-agent workflows (55KB)
- `financial_crew.py` - CrewAI-based financial analysis agents (53KB)
- `financial_agents.py` - Specialized domain agents
- API: `api/agent_routes.py`

**API Routes** (`api/`):
- `routes.py` - Main NLP-to-SQL endpoints (94KB)
- `margen_routes.py` - Margin analysis (56KB)
- `agent_routes.py` - Agent mode interface
- `conversation_routes.py` - Conversation history (MongoDB)
- `pulse_routes.py` - Enterprise Pulse monitoring
- `process_mining_routes.py` - Process mining analytics
- `vision_routes.py` - Document/image intelligence
- `markets_routes.py` - Markets.AI signal endpoints
- `control_center_routes.py` - Dashboard
- `connector_routes.py` - Database connector management
- `permissions_routes.py` - Permission management (admin-only)

**Authentication**:
- AWS Cognito JWT validation (`api/middleware/auth_middleware.py`)
- Organization-based multi-tenancy
- User groups: Admins, Users
- Environment: `AWS_COGNITO_USER_POOL_ID`, `AWS_COGNITO_REGION`, `AWS_COGNITO_CLIENT_ID`

**Database Clients** (`db/`):
- `bigquery.py` - Legacy BigQuery client (being migrated to connector pattern)
- `postgresql_client.py` - PostgreSQL for internal app database (26KB)
- `mongodb_client.py` - Conversation history persistence
- `weaviate_client.py` - Vector embeddings (enriched with schema metadata)

**Configuration**:
- `config.py` - Pydantic settings from `.env` file
- All settings use uppercase environment variable names
- See docker-compose.yml for complete variable list

### Frontend Structure (`frontend/src/`)

**Core App**:
- `App.jsx` - React Router v6 routing + Clerk authentication
- Protected routes with Clerk session management

**Major Components** (`components/`):
- `AgentModeInterface.jsx` - Main agent chat interface (151KB)
- `CoreAIDashboard.jsx` - Primary analytics dashboard (171KB)
- `SimpleChatInterface.jsx` - Basic chat UI
- `DataCatalog.jsx` - Data source exploration
- `controlcenter/` - Control center dashboard components

**Services** (`services/`):
- `api.js` - Axios API client with interceptors (14KB)
- `chatStorageService.js` - LocalStorage chat persistence
- `stoxService.js` - STOX.AI specific services

**Styling**:
- Material-UI (MUI) v5 component library
- Custom themes in `themes/`
- Vite build tool (dev server on port 5174)

### Background Schedulers

Three async schedulers run on backend startup (see `main.py:lifespan`):
1. **Enterprise Pulse** - Data quality monitoring (60s interval)
2. **Markets.AI Signals** - Market data fetching (30min interval)
3. **Pipeline Scheduler** - Schema/metadata refresh (daily 2:00 AM)

## Important Patterns

### Adding New Database Connector

1. Create connector in `backend/src/db/connectors/your_db_connector.py`:
   ```python
   from src.db.base_connector import BaseDatabaseConnector

   class YourDBConnector(BaseDatabaseConnector):
       def connect(self): ...
       def execute_query(self, query, params=None): ...
       def get_schema(self): ...
       # Implement all abstract methods
   ```

2. Register in `connector_factory.py`:
   ```python
   connector_classes = {
       "bigquery": BigQueryConnector,
       "snowflake": SnowflakeConnector,
       "yourdb": YourDBConnector,  # Add here
   }
   ```

3. Add configuration to `config.py`:
   ```python
   yourdb_host: str = Field(default="localhost", alias="YOURDB_HOST")
   yourdb_user: str = Field(..., alias="YOURDB_USER")
   ```

4. Update permissions in `database_permissions.py` if needed

### Adding New API Endpoint

1. Define Pydantic models in `backend/src/api/models.py`
2. Create route handler in appropriate `backend/src/api/*_routes.py`
3. Use FastAPI router pattern with dependency injection
4. Add router to `backend/src/main.py` via `app.include_router()`
5. Add frontend service method in `frontend/src/services/api.js`

### Working with Knowledge Graph

- Access via singleton: `get_jena_knowledge_graph()` and `get_jena_query_resolver()`
- SPARQL queries executed in `jena_query_resolver.py`
- Add new schema metadata via `backend/load_table_metadata_to_jena.py`
- RDF triples built in `pipeline/rdf_builder.py`

### Cache Management

- Multi-tier Redis cache with varying TTLs:
  - SQL (frequent): 7 days
  - SQL (infrequent): 1 day
  - Schema: 24 hours
  - Embeddings: 30 days
- Cache keys: SHA256 hash of query + context
- Feature flags: `CACHE_ENABLED`, `CACHE_SQL_ENABLED`, etc.
- Access via `CacheManager` singleton in `core/cache_manager.py`
- Stats endpoint: `GET /api/v1/cache/stats`

### Conversation State

- Stored in MongoDB (`nlp_sql_conversations` database)
- Each conversation has unique ID and message history
- Context maintained via `ConversationContext` class
- API endpoints in `conversation_routes.py`

### Authentication & Permissions

- JWT validation via AWS Cognito
- Middleware: `api/middleware/auth_middleware.py`
- Permission enforcement in `connector_factory.py`
- Admin-only routes use `@require_admin` decorator
- Organization isolation via `organization_id` in tokens

## Environment Setup

**Required Services**:
- Python 3.9+ with virtual environment (`backend/venv/`)
- Node.js 18+ for frontend
- Redis (localhost:6379 or Docker)
- Docker and Docker Compose for optional services

**Critical Environment Variables**:
```bash
# AI Services (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929  # Default
OPENAI_API_KEY=sk-...  # For embeddings

# Google Cloud (REQUIRED)
GOOGLE_CLOUD_PROJECT=your-project
BIGQUERY_DATASET=your-dataset
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-key.json

# AWS Cognito (REQUIRED for auth)
AWS_COGNITO_USER_POOL_ID=us-east-1_xxxxxx
AWS_COGNITO_REGION=us-east-1
AWS_COGNITO_CLIENT_ID=xxxxxxxxxx

# Service URLs (defaults shown)
REDIS_HOST=localhost
MONGODB_URL=mongodb://localhost:27017
WEAVIATE_URL=http://localhost:8082

# Multi-Database Connectors (as needed)
SNOWFLAKE_ACCOUNT=xy12345.us-east-1
SNOWFLAKE_USER=username
SNOWFLAKE_PASSWORD=password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH

POSTGRES_HOST=localhost
POSTGRES_USER=mantrix
POSTGRES_PASSWORD=mantrix123
POSTGRES_DATABASE=mantrix_madison

# See MULTI_DATABASE_IMPLEMENTATION_PLAN.md for Redshift, Databricks config
```

## Testing Strategy

**Backend Tests**:
- Test files in `backend/` root directory (not in subdirectory)
- Direct execution: `python test_*.py` (no pytest runner currently)
- Run all: `./run_tests.sh`
- Test query execution: `./test_queries.sh`
- Focus areas: SQL generation, API endpoints, knowledge graph, connectors

**API Testing**:
- Interactive docs: http://localhost:8000/docs (Swagger)
- Alternative docs: http://localhost:8000/redoc

**Frontend**:
- Linting: `cd frontend && npm run lint`
- Dev server with hot reload: http://localhost:5174

## Key Data Flows

**NLP Query Execution**:
1. User query → Frontend (`AgentModeInterface.jsx`) → `api.js:executeQuery()`
2. Backend → `POST /api/v1/query` → `routes.py:execute_query_endpoint()`
3. Cache check → Financial parsing → Knowledge graph schema lookup
4. LLM call (Claude) with schema context → SQL generation
5. Format normalization (if needed) → Query optimization
6. Database execution via connector → Results cached → Return to frontend

**Schema Pipeline** (scheduled daily 2:00 AM):
1. `pipeline/orchestrator.py` coordinates extraction
2. `pipeline/multi_db_schema_extractor.py` fetches from all databases
3. `pipeline/rdf_builder.py` builds RDF triples (Jena)
4. `pipeline/vector_builder.py` creates enriched embeddings (Weaviate)
5. Results cached in Redis for fast access

**Multi-Agent Workflow**:
1. User request → `POST /api/v1/agents/execute`
2. `agents/orchestrator.py` decomposes into tasks
3. CrewAI agents execute in parallel/sequence
4. Results aggregated and returned

## Common Development Tasks

**Debugging SQL Generation**:
1. Check logs: `tail -f logs/backend.log`
2. Enable debug: `LOG_LEVEL=DEBUG` in `.env`
3. Use explain endpoint: `POST /api/v1/explain`
4. Check cache stats: `GET /api/v1/cache/stats`
5. Verify knowledge graph: Run `backend/test_jena_queries.py`

**Adding Financial Metrics**:
- Define in `backend/src/core/financial_hierarchy.py`
- Add SQL templates in `backend/src/core/financial_templates.py`
- Update parser in `backend/src/core/financial_semantic_parser.py`

**Modifying Agent Behavior**:
- Orchestration logic: `backend/src/agents/orchestrator.py`
- CrewAI configuration: `backend/src/agents/financial_crew.py`
- Frontend UI: `frontend/src/components/AgentModeInterface.jsx`

**Working with Process Mining**:
- Backend routes: `backend/src/api/process_mining_routes.py`
- Core logic: `backend/src/core/process_mining/`
- Frontend: `frontend/src/pages/ProcessMiningPage.jsx`

**Reloading Schema Metadata**:
```bash
cd backend
source venv/bin/activate
python load_table_metadata_to_jena.py  # Reload knowledge graph
python -c "from src.pipeline.orchestrator import PipelineOrchestrator; PipelineOrchestrator().execute_pipeline()"  # Full pipeline
```

**Managing Permissions**:
```bash
# Via API (requires admin auth)
POST /api/v1/permissions/databases/{db_type}  # Grant permissions
GET /api/v1/permissions/user/{user_id}        # Check user permissions
```

## Technology Stack

**Backend**:
- FastAPI (async web framework)
- Anthropic Claude (primary LLM)
- OpenAI (embeddings)
- Apache Jena (RDF/SPARQL knowledge graph)
- CrewAI (multi-agent orchestration)
- structlog (structured logging)

**Databases**:
- Google BigQuery (primary data warehouse)
- Snowflake, Databricks, Redshift, PostgreSQL (via connectors)
- PostgreSQL (internal app database)
- MongoDB (conversation history)
- Weaviate (vector embeddings)
- Redis (multi-tier caching)
- Neo4j (optional graph database)

**Frontend**:
- React 18.2 + Vite
- Material-UI (MUI) v5
- Clerk (authentication)
- Axios (API client)
- React Router v6

## Project-Specific Notes

**Leading Zero Issue (SAP Data)**:
- Problem: SAP tables store customer IDs as '0000123' vs '123'
- Solution: `FormatNormalizer` automatically detects and applies `LTRIM(column, '0')`
- Impact: 100-1000x improvement in JOIN accuracy
- Test: See `RUN_THIS_FIRST.md` Step 3 for validation query

**Conversation Context**:
- Conversations persist across sessions in MongoDB
- Each turn maintains full message history
- Context includes previous SQL queries and results
- Use `conversation_id` parameter to maintain context

**Cost Optimization**:
- BigQuery connector supports dry-run cost estimation
- Results cached in Redis to avoid redundant queries
- Query optimizer removes redundant clauses
- Pagination prevents large result sets

**Security**:
- All database operations go through permission-enforced factory
- Organization-level data isolation
- JWT tokens validated against Cognito
- No direct database credentials in code (use environment variables)
