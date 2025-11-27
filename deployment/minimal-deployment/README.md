# Minimal Deployment - Mantrix Axis AI

This is a minimal deployment setup for testing the application before moving to AWS ECS. It simulates the ECS environment using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- At least 8GB of available RAM
- Required API keys (Anthropic, OpenAI)
- AWS Cognito configured
- Google Cloud credentials for BigQuery

## Quick Start

### 1. Set Up Environment Variables

Copy the environment template and fill in your values:

```bash
cp .env.template .env
# Edit .env with your actual API keys and configuration
```

**Required variables:**
- `ANTHROPIC_API_KEY` - For Claude AI (NLP-to-SQL)
- `OPENAI_API_KEY` - For embeddings
- `AWS_COGNITO_USER_POOL_ID` - For authentication
- `AWS_COGNITO_REGION` - AWS region for Cognito
- `AWS_COGNITO_CLIENT_ID` - Cognito client ID
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `BIGQUERY_DATASET` - BigQuery dataset name

### 2. Google Cloud Credentials

Place your GCP service account JSON file in this directory and update the path in `.env`:

```bash
cp /path/to/your/gcp-key.json ./gcp-key.json
# Update GOOGLE_APPLICATION_CREDENTIALS in .env
```

### 3. Build and Start Services

```bash
# Build the Docker images
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 4. Access the Application

Once all services are running:

- **Application (via Load Balancer)**: http://localhost:8080
- **Frontend Direct**: http://localhost
- **Backend API Direct**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 5. Verify Services

Check that all services are healthy:

```bash
# Check backend health
curl http://localhost:8000/api/v1/health

# Check frontend health
curl http://localhost/health

# Check load balancer
curl http://localhost:8080/lb-health

# Check database connections
docker-compose exec postgres psql -U mantrix -d mantrix_madison -c "SELECT 1"
docker-compose exec redis redis-cli ping
docker-compose exec mongodb mongosh --eval "db.runCommand({ping: 1})"
```

## Service Ports

| Service | Internal Port | External Port | Description |
|---------|--------------|---------------|-------------|
| Load Balancer | 80 | 8080 | Main application entry point |
| Frontend | 80 | 80 | React application |
| Backend | 8000 | 8000 | FastAPI server |
| PostgreSQL | 5432 | 5433 | Application database |
| Redis | 6379 | 6379 | Cache layer |
| MongoDB | 27017 | 27017 | Conversation storage |
| Weaviate | 8080 | 8082 | Vector database |

## Troubleshooting

### Services Not Starting

Check logs for specific service:
```bash
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres
```

### Database Connection Issues

Ensure databases are fully initialized:
```bash
# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready -U mantrix

# Check MongoDB connection
docker-compose exec mongodb mongosh --eval "db.runCommand({ping: 1})"
```

### Memory Issues

If services are crashing due to memory:
```bash
# Check Docker memory allocation
docker info | grep "Total Memory"

# Increase Docker Desktop memory to at least 8GB
```

### Port Conflicts

If ports are already in use:
```bash
# Check what's using the ports
lsof -i :8080
lsof -i :8000
lsof -i :5433

# Stop conflicting services or modify ports in docker-compose.yml
```

## Monitoring

### View Real-time Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Resource Usage
```bash
# Check container resource usage
docker stats

# Check specific container
docker stats mantrix-backend
```

## Stopping and Cleanup

```bash
# Stop all services (data persists)
docker-compose down

# Stop and remove volumes (CAUTION: deletes all data)
docker-compose down -v

# Remove all images
docker-compose down --rmi all
```

## Next Steps

Once the minimal deployment is working:

1. Test all core features:
   - NLP-to-SQL query execution
   - Authentication via Cognito
   - Database connections
   - Caching with Redis
   - Vector search with Weaviate

2. Performance baseline:
   - Measure query response times
   - Check memory usage
   - Monitor CPU utilization

3. Proceed to Phase 1:
   - Implement code protection (Cython, PyInstaller)
   - Create protected Docker images
   - Set up AWS ECS infrastructure

## Architecture

This setup simulates the following AWS ECS architecture locally:

```
       Load Balancer (nginx:8080)
              |
      +-------+-------+
      |               |
Frontend (nginx:80)  Backend (FastAPI:8000)
                      |
          +-----------+-----------+
          |           |           |
     PostgreSQL    Redis     MongoDB
      (RDS)    (ElastiCache) (DocumentDB)
                      |
                  Weaviate
                (Vector DB)
```

## Support

For issues or questions:
1. Check the logs first: `docker-compose logs`
2. Verify all environment variables are set correctly
3. Ensure all prerequisites are met
4. Check the troubleshooting section above