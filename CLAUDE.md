# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mantrix Axis AI** (STOX.AI) is an AI-powered supply chain intelligence platform that converts natural language queries into SQL for BigQuery and PostgreSQL databases. The platform features conversational AI interfaces, financial analytics, process mining, document intelligence, and market signal monitoring.

**Architecture**: Full-stack application with React (Vite) frontend and FastAPI backend, using multiple databases (BigQuery, PostgreSQL, MongoDB, Neo4j, Weaviate) and Redis caching.

## Development Commands

### Starting the Application

```bash
# Start development environment (recommended)
./start_dev.sh
# This starts:
# - Frontend on http://localhost:5174
# - Backend on http://localhost:8000
# - Redis (if not running)
# - Optionally prompts for Docker services

# Stop development environment
./stop_dev.sh

# Start frontend only
cd frontend && npm start

# Start backend only
cd backend && source venv/bin/activate && uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

### Building and Installation

```bash
# Install all dependencies (from root)
npm run install

# Install frontend dependencies
cd frontend && npm install

# Install backend dependencies
cd backend && pip install -r requirements.txt

# Build frontend for production
cd frontend && npm run build
```

### Testing

```bash
# Backend tests (run from backend directory)
cd backend
source venv/bin/activate

# Run individual test files
python test_apis.py
python test_query_flow.py
python test_column_synonyms.py
python test_roic_calculation.py

# Run test queries
./test_queries.sh

# Frontend linting
cd frontend && npm run lint
```

### Docker Services

```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d mongodb neo4j weaviate redis postgres

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Check service health
docker-compose ps
```

## Architecture

### Backend Structure (`backend/src/`)

**Core Modules (`core/`)**:
- `sql_generator.py` - Main SQL generation orchestrator using LLM with knowledge graph integration
- `llm_client.py` - Anthropic Claude API client for NLP-to-SQL conversion (68KB, central to AI functionality)
- `cache_manager.py` - Redis-based multi-tier caching system with TTL management
- `query_optimizer.py` - SQL query optimization and validation
- `financial_semantic_parser.py` - Financial domain query parsing and intent detection
- `conversation_context.py` - Multi-turn conversation state management with MongoDB persistence

**Knowledge Graph (`core/knowledge_graph/`)**:
- Uses Jena RDF/SPARQL for semantic query understanding
- `jena_client.py` - Apache Jena integration for RDF triple store
- `jena_query_resolver.py` - SPARQL query resolution for table/column relationships
- `join_path_finder.py` - Automatic join path detection across tables
- `column_matcher.py` - Semantic column matching using embeddings
- Knowledge graph provides schema intelligence for SQL generation

**Agents (`agents/`)**:
- `orchestrator.py` - Multi-agent coordination for complex workflows (55KB)
- `financial_crew.py` - Financial analysis agent crew using CrewAI (53KB)
- `financial_agents.py` - Specialized financial domain agents

**API Routes (`api/`)**:
- `routes.py` - Main NLP-to-SQL endpoints (94KB, primary API surface)
- `margen_routes.py` - Margin analysis endpoints (56KB)
- `agent_routes.py` - Agent mode interface
- `conversation_routes.py` - Conversation history management
- `pulse_routes.py` - Enterprise Pulse monitoring
- `process_mining_routes.py` - Process mining analytics
- `vision_routes.py` - Document/image intelligence
- `markets_routes.py` - Markets.AI signal endpoints
- `control_center_routes.py` - Control center dashboard

**Database Clients (`db/`)**:
- `bigquery.py` - Google BigQuery client with query execution
- `postgresql_client.py` - PostgreSQL connection and query handling (26KB)
- `mongodb_client.py` - MongoDB for conversation persistence
- `weaviate_client.py` - Weaviate vector database for embeddings

**Configuration**:
- `config.py` - Pydantic settings from environment variables
- Environment variables loaded from `.env` file (see docker-compose.yml for required vars)

### Frontend Structure (`frontend/src/`)

**Core App**:
- `App.jsx` - Main application with routing and Clerk authentication
- Uses React Router v6 for navigation
- Protected routes with Clerk integration

**Major Components (`components/`)**:
- `AgentModeInterface.jsx` - Main agent chat interface (151KB, central UI component)
- `CoreAIDashboard.jsx` - Primary analytics dashboard (171KB)
- `SimpleChatInterface.jsx` - Basic chat UI
- `DataCatalog.jsx` - Data source exploration
- `EmailIntelligence.jsx` - Email analysis features
- `DocumentIntelligence.jsx` - Document processing
- Control center components in `components/controlcenter/`

**Services (`services/`)**:
- `api.js` - Axios-based API client with interceptors
- `chatStorageService.js` - LocalStorage-based chat persistence
- `stoxService.js` - STOX.AI specific services

**Styling**:
- Material-UI (MUI) v5 for component library
- Custom theme in `theme.js` and `themes/`
- Vite as build tool (port 5174)

### Data Flow

1. **User Query** → Frontend chat interface → `apiService.executeQuery()`
2. **API Layer** → `POST /api/v1/query` → `routes.py:execute_query_endpoint()`
3. **SQL Generation**:
   - Cache check via `CacheManager`
   - Knowledge graph lookup via Jena for schema/relationships
   - LLM call via `LLMClient` (Anthropic Claude) with schema context
   - Query optimization via `QueryOptimizer`
4. **Execution** → BigQuery/PostgreSQL via respective clients
5. **Response** → Results cached → Returned to frontend → Visualized

### Key Integration Points

**LLM Integration**:
- Primary: Anthropic Claude (`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`)
- Embeddings: OpenAI text-embedding-3-small (`OPENAI_API_KEY`)
- Configured in `backend/src/config.py`

**Database Connections**:
- BigQuery: `GOOGLE_CLOUD_PROJECT`, `BIGQUERY_DATASET`, `GOOGLE_APPLICATION_CREDENTIALS`
- PostgreSQL: `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DATABASE`
- MongoDB: `MONGODB_URL` (for conversation history)
- Weaviate: `WEAVIATE_URL` (for vector embeddings)
- Neo4j: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` (optional graph DB)
- Redis: `REDIS_HOST`, `REDIS_PORT` (for caching)

**Authentication**:
- Clerk for user auth: `CLERK_SECRET_KEY` (backend), `VITE_CLERK_PUBLISHABLE_KEY` (frontend)

## Important Patterns

### Adding New API Endpoints

1. Create route handler in appropriate `backend/src/api/*_routes.py`
2. Use FastAPI router pattern with Pydantic models from `api/models.py`
3. Add router to `backend/src/main.py` with `app.include_router()`
4. Add frontend service method in `frontend/src/services/api.js`

### Working with the Knowledge Graph

- Knowledge graph is initialized lazily via singleton pattern (`jena_singleton.py`)
- Use `get_jena_knowledge_graph()` and `get_jena_query_resolver()` for access
- Schema metadata loaded via `backend/load_table_metadata_to_jena.py`
- SPARQL queries resolved in `jena_query_resolver.py`

### Cache Management

- Multi-tier cache with different TTLs (frequent: 7 days, infrequent: 1 day)
- Cache keys use SHA256 hashing of query + context
- Invalidation strategies in `cache_manager.py`
- Feature flags: `CACHE_ENABLED`, `CACHE_SQL_ENABLED`, etc.

### Conversation State

- Conversations stored in MongoDB (`nlp_sql_conversations` database)
- Each conversation has unique ID and message history
- Context maintained across turns via `ConversationContext` class
- Access via `conversation_routes.py` endpoints

### Background Schedulers

Two schedulers run on app startup (see `main.py:lifespan`):
1. **Enterprise Pulse** - Monitors data quality/freshness (60s interval)
2. **Markets.AI Signals** - Fetches market data (30min interval)

Both are async tasks that run until shutdown.

## Environment Setup

**Required Services**:
- Python 3.9+ with virtual environment (`backend/venv/`)
- Node.js 18+ for frontend
- Redis server (localhost:6379 or via Docker)
- Docker and Docker Compose for optional services

**Critical Environment Variables** (see `docker-compose.yml` for full list):
```bash
# AI Services
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project
BIGQUERY_DATASET=your-dataset
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-key.json

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mantrix
POSTGRES_PASSWORD=mantrix123
POSTGRES_DATABASE=mantrix_madison

# Service URLs (defaults for local development)
REDIS_HOST=localhost
MONGODB_URL=mongodb://localhost:27017
WEAVIATE_URL=http://localhost:8082
NEO4J_URI=bolt://localhost:7687
```

## Testing Strategy

**Backend Tests**:
- Test files in `backend/` directory (not in `tests/` subdirectory)
- Run directly with Python: `python test_*.py`
- Focus on query generation, API endpoints, and data flow
- No pytest configuration found - tests use direct execution

**Manual Testing**:
- API docs available at http://localhost:8000/docs (FastAPI auto-generated)
- Test queries via `test_queries.sh` script
- Frontend dev server with hot reload at http://localhost:5174

## Common Tasks

**Debugging SQL Generation**:
1. Check logs in `logs/backend.log` and `logs/frontend.log`
2. Enable detailed logging: `LOG_LEVEL=DEBUG` in environment
3. Use `/api/v1/explain` endpoint to see query analysis
4. Check cache with `/api/v1/cache/stats`

**Adding Financial Metrics**:
- Define in `backend/src/core/financial_hierarchy.py`
- Add templates in `backend/src/core/financial_templates.py`
- Update semantic parser in `backend/src/core/financial_semantic_parser.py`

**Modifying Agent Behavior**:
- Agent orchestration in `backend/src/agents/orchestrator.py`
- CrewAI agents in `backend/src/agents/financial_crew.py`
- Frontend agent UI in `frontend/src/components/AgentModeInterface.jsx`

**Working with Process Mining**:
- Routes in `backend/src/api/process_mining_routes.py`
- Core logic in `backend/src/core/process_mining/`
- Frontend page in `frontend/src/pages/ProcessMiningPage.jsx`
