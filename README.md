# Mantrix Axis AI (STOX.AI)

**AI-Powered Supply Chain Intelligence Platform**

[![License](https://img.shields.io/badge/license-ISC-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18.2+-61DAFB.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-latest-009688.svg)](https://fastapi.tiangolo.com/)

Convert natural language queries into optimized SQL for BigQuery and PostgreSQL databases. Features conversational AI interfaces, financial analytics, process mining, document intelligence, and market signal monitoring.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Features

### Core Capabilities

- **Natural Language to SQL**: Convert plain English questions to optimized BigQuery/PostgreSQL queries using Claude AI
- **Conversational AI**: Multi-turn conversations with context awareness and conversation history
- **Knowledge Graph**: Semantic understanding of database schema using Apache Jena RDF/SPARQL
- **Multi-Tier Caching**: Redis-based caching with intelligent TTL management for performance
- **Financial Analytics**: Specialized financial metrics, margin analysis, and ROIC calculations
- **Process Mining**: Business process discovery and analysis from event logs
- **Document Intelligence**: Extract insights from documents and images using vision AI
- **Market Signals**: Monitor and analyze market data from FRED, EIA, and BLS APIs
- **Agent Mode**: Multi-agent system using CrewAI for complex analytical workflows

### Technology Stack

**Frontend**:
- React 18.2 with Vite
- Material-UI (MUI) v5
- Clerk Authentication
- Axios for API communication
- React Router v6

**Backend**:
- FastAPI (Python 3.9+)
- Anthropic Claude AI (primary LLM)
- OpenAI (embeddings)
- Structured logging with structlog

**Databases**:
- Google BigQuery (primary data warehouse)
- PostgreSQL (application database)
- MongoDB (conversation history)
- Neo4j (optional graph database)
- Weaviate (vector embeddings)
- Redis (caching layer)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite)                  │
│         Material-UI │ Clerk Auth │ Port: 5174               │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────▼──────────────────────────────────┐
│                   Backend API (FastAPI)                      │
│                        Port: 8000                            │
├──────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ SQL Gen    │  │ LLM Client   │  │ Knowledge Graph  │    │
│  │ Optimizer  │  │ (Claude AI)  │  │ (Jena/SPARQL)    │    │
│  └────────────┘  └──────────────┘  └──────────────────┘    │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ Cache Mgr  │  │ Agents/Crew  │  │ Conversation Ctx │    │
│  │ (Redis)    │  │ (CrewAI)     │  │ (MongoDB)        │    │
│  └────────────┘  └──────────────┘  └──────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
┌────────▼────────┐ ┌──────▼──────┐ ┌───────▼────────┐
│   BigQuery      │ │ PostgreSQL  │ │    Weaviate    │
│  (Analytics)    │ │   (App DB)  │ │  (Embeddings)  │
└─────────────────┘ └─────────────┘ └────────────────┘
```

### Key Components

**Backend** (`backend/src/`):
- **API Layer** (`api/`): 20+ route modules handling different features
- **Core Services** (`core/`): SQL generation, LLM integration, caching, optimization
- **Knowledge Graph** (`core/knowledge_graph/`): Schema intelligence and join path discovery
- **Agents** (`agents/`): Multi-agent orchestration for complex workflows
- **Database Clients** (`db/`): Connections to BigQuery, PostgreSQL, MongoDB, Weaviate

**Frontend** (`frontend/src/`):
- **Components** (`components/`): 90+ React components for UI
- **Pages** (`pages/`): Main application pages
- **Services** (`services/`): API client and state management
- **Themes** (`themes/`): Material-UI theming

---

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- Redis server (for caching)
- Docker and Docker Compose (optional, for services)
- Google Cloud Project with BigQuery enabled
- Anthropic API key (Claude AI)
- OpenAI API key (for embeddings)

### 1. Clone Repository

```bash
git clone <repository-url>
cd mantrix-axis-ai
```

### 2. Environment Setup

Create a `.env` file in the backend directory:

```bash
cp .env.example backend/.env
# Edit backend/.env with your API keys and configuration
```

Required environment variables:
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `OPENAI_API_KEY` - Your OpenAI API key
- `GOOGLE_CLOUD_PROJECT` - Your GCP project ID
- `BIGQUERY_DATASET` - Your BigQuery dataset name
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to GCP service account key

See [Environment Variables](#environment-variables) for complete list.

### 3. Start Development Environment

```bash
# Quick start (recommended)
./start_dev.sh
```

This script will:
- Create Python virtual environment (if needed)
- Install backend dependencies
- Start Redis (if not running)
- Start backend API on http://localhost:8000
- Start frontend dev server on http://localhost:5174
- Optionally start Docker services (MongoDB, Neo4j, Weaviate)

**Manual start**:

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm start
```

### 4. Access Application

- **Frontend**: http://localhost:5174
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative API Docs**: http://localhost:8000/redoc (ReDoc)

### 5. Stop Services

```bash
./stop_dev.sh
# or Ctrl+C if using start_dev.sh
```

---

## Development Setup

### Backend Development

#### Install Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Run Backend Only

```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

#### Backend Structure

```
backend/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings and configuration
│   ├── api/                 # API route handlers
│   │   ├── routes.py        # Main NLP-to-SQL endpoints
│   │   ├── margen_routes.py # Margin analysis
│   │   ├── agent_routes.py  # Agent mode
│   │   └── ...
│   ├── core/                # Core business logic
│   │   ├── sql_generator.py      # Main SQL generation
│   │   ├── llm_client.py         # LLM integration
│   │   ├── cache_manager.py      # Redis caching
│   │   ├── knowledge_graph/      # Schema intelligence
│   │   └── ...
│   ├── agents/              # Multi-agent system
│   ├── db/                  # Database clients
│   └── models/              # Data models
├── tests/                   # Test files
└── requirements.txt         # Python dependencies
```

### Frontend Development

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Run Frontend Only

```bash
cd frontend
npm start  # Starts on http://localhost:5174
```

#### Frontend Structure

```
frontend/
├── src/
│   ├── main.jsx             # React app entry point
│   ├── App.jsx              # Main app component with routing
│   ├── components/          # React components
│   │   ├── AgentModeInterface.jsx
│   │   ├── CoreAIDashboard.jsx
│   │   └── ...
│   ├── pages/               # Page components
│   ├── services/            # API client
│   │   └── api.js           # Axios API service
│   ├── themes/              # MUI themes
│   └── utils/               # Utility functions
├── package.json
└── vite.config.js           # Vite configuration
```

### Docker Services

Start all supporting services (MongoDB, Neo4j, Weaviate, Redis, PostgreSQL):

```bash
docker-compose up -d
```

Check service status:

```bash
docker-compose ps
```

View logs:

```bash
docker-compose logs -f [service-name]
```

Stop services:

```bash
docker-compose down
```

---

## Environment Variables

### Required Variables

Create a `.env` file in the `backend/` directory with these required variables:

```bash
# AI Services (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx

# Google Cloud / BigQuery (REQUIRED)
GOOGLE_CLOUD_PROJECT=your-project-id
BIGQUERY_DATASET=your-dataset-name
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-key.json
```

### Optional Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development  # or production
LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR

# LLM Models
ANTHROPIC_MODEL=claude-3-5-sonnet-20240620
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_ENABLED=true
CACHE_TTL_SQL_FREQUENT=604800  # 7 days in seconds

# MongoDB (Conversations)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=nlp_sql_conversations

# PostgreSQL (Application DB)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mantrix
POSTGRES_PASSWORD=mantrix123
POSTGRES_DATABASE=mantrix_madison

# Weaviate (Vector DB)
WEAVIATE_URL=http://localhost:8082

# Neo4j (Optional Graph DB)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# Clerk Authentication (Frontend)
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx

# Clerk Authentication (Backend)
CLERK_SECRET_KEY=sk_test_xxxxx

# Markets.AI API Keys (Optional - all free)
FRED_API_KEY=your-fred-key
EIA_API_KEY=your-eia-key
BLS_API_KEY=your-bls-key
```

See `docker-compose.yml` for complete list of environment variables.

---

## API Documentation

### Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Query Endpoints

```http
POST /api/v1/query
```
Execute natural language query and return results.

**Request**:
```json
{
  "question": "What are the top 10 customers by revenue?",
  "conversationId": "optional-conversation-id"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "sql": "SELECT customer_name, SUM(revenue) ...",
    "results": [...],
    "execution_time": 1.23
  }
}
```

#### Generate SQL (without execution)

```http
POST /api/v1/generate
```

#### Conversation History

```http
GET /api/v1/conversations/{conversation_id}
POST /api/v1/conversations
DELETE /api/v1/conversations/{conversation_id}
```

#### Agent Mode

```http
POST /api/v1/agents/execute
```
Execute complex multi-step analysis using agent system.

#### Cache Management

```http
GET /api/v1/cache/stats      # Cache statistics
GET /api/v1/cache/popular    # Popular queries
DELETE /api/v1/cache/clear   # Clear cache
```

#### Health Check

```http
GET /api/v1/health
```

---

## Testing

### Backend Tests

Tests are located in `backend/` directory (root level).

#### Run All Tests

```bash
cd backend
source venv/bin/activate

# Run individual test files
python test_apis.py
python test_query_flow.py
python test_column_synonyms.py
python test_roic_calculation.py
```

#### Run Query Tests

```bash
cd backend
./test_queries.sh
```

### Frontend Tests

```bash
cd frontend
npm run lint  # Run ESLint
```

### Test Coverage

*Note: Comprehensive test suite with pytest and coverage reporting is planned for Phase 4 of the enhancement roadmap.*

---

## Deployment

### Development Deployment

Use `./start_dev.sh` for local development.

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed EC2 deployment instructions.

**Quick overview**:
1. Launch EC2 instance (t3.medium recommended)
2. Configure DNS to point to EC2
3. SSH into instance
4. Clone repository
5. Run `./deploy.sh`
6. Configure SSL with Let's Encrypt

**Production checklist**:
- [ ] Set `API_ENV=production`
- [ ] Use strong passwords (auto-generated in deploy.sh)
- [ ] Enable SSL/TLS
- [ ] Configure firewall (UFW)
- [ ] Set up monitoring and logging
- [ ] Configure automated backups
- [ ] Review security settings

---

## Troubleshooting

### Common Issues

#### Backend won't start

```bash
# Check logs
tail -f logs/backend.log

# Common causes:
# 1. Missing environment variables
#    Solution: Check .env file, see Environment Variables section

# 2. Port 8000 already in use
lsof -ti:8000  # Find process using port
kill -9 <PID>  # Kill process

# 3. Redis not running
redis-cli ping  # Should return "PONG"
redis-server --daemonize yes  # Start Redis
```

#### Frontend won't start

```bash
# Check logs
tail -f logs/frontend.log

# Common causes:
# 1. Dependencies not installed
cd frontend && npm install

# 2. Port 5174 in use
lsof -ti:5174
kill -9 <PID>

# 3. Node version too old
node --version  # Should be 18+
```

#### Database Connection Errors

```bash
# Test BigQuery connection
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
bq ls  # Should list datasets

# Test PostgreSQL connection
psql -h localhost -U mantrix -d mantrix_madison

# Test MongoDB connection
mongosh mongodb://localhost:27017
```

#### LLM API Errors

```bash
# Test Anthropic API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-sonnet-20240229","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'

# Test OpenAI API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### Cache Issues

```bash
# Clear Redis cache
redis-cli FLUSHALL

# Check cache stats
curl http://localhost:8000/api/v1/cache/stats
```

#### Knowledge Graph Issues

```bash
# Reload table metadata
cd backend
python load_table_metadata_to_jena.py

# Test Jena queries
python test_jena_queries.py
```

### Debug Mode

Enable detailed logging:

```bash
# In .env file
LOG_LEVEL=DEBUG

# Restart backend
```

### Getting Help

1. Check [CLAUDE.md](CLAUDE.md) for architecture details
2. Review API docs at http://localhost:8000/docs
3. Check logs in `logs/backend.log` and `logs/frontend.log`
4. Search existing GitHub issues
5. Create new issue with:
   - Error message
   - Steps to reproduce
   - Environment details (OS, Python version, Node version)
   - Relevant logs

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow, code standards, and contribution guidelines.

### Quick Guidelines

1. **Fork and clone** the repository
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Follow code standards**: Run linters before committing
4. **Write tests** for new features
5. **Update documentation** for API changes
6. **Commit with clear messages**: Use conventional commits
7. **Push and create PR**: Describe changes and link issues

---

## License

ISC License - See [LICENSE](LICENSE) file for details.

---

## Project Status

**Current Version**: 1.0.0
**Status**: Active Development
**Roadmap**: See enhancement roadmap for planned features and improvements

### Key Metrics

- **90+ React Components**
- **20+ API Route Modules**
- **6 Database Integrations**
- **Multiple AI Agents** (CrewAI)
- **100+ Financial Metrics** supported

---

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [Anthropic Claude](https://www.anthropic.com/claude)
- UI components from [Material-UI](https://mui.com/)
- Authentication by [Clerk](https://clerk.com/)
- Knowledge graph with [Apache Jena](https://jena.apache.org/)

---

**For detailed architecture information, see [CLAUDE.md](CLAUDE.md)**
**For deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)**
