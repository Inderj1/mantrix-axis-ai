#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Starting Mantrix Unified DI - Dev Environment${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    pkill -f "npm start"
    pkill -f "uvicorn src.main:app"
    docker-compose stop redis weaviate mongodb
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo -e "${RED}Virtual environment not found. Creating one...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt 2>/dev/null || true
    cd ..
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment found${NC}"
fi

# Install/update backend dependencies
echo -e "${YELLOW}Checking backend dependencies...${NC}"
cd backend
source venv/bin/activate
pip install -q rdflib crewai nest-asyncio 2>/dev/null || echo -e "${YELLOW}⚠ Some dependencies may need manual installation${NC}"
cd ..
echo -e "${GREEN}✓ Backend dependencies checked${NC}"

# Check and install frontend dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not found. Installing...${NC}"
    cd frontend
    npm install
    cd ..
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Frontend dependencies found${NC}"
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Clean up any existing processes on required ports
echo -e "\n${YELLOW}Cleaning up existing processes...${NC}"
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5174 2>/dev/null | xargs kill -9 2>/dev/null || true
echo -e "${GREEN}✓ Ports freed${NC}"

# Start required Docker services (Redis, Weaviate, MongoDB)
echo -e "\n${YELLOW}Starting required Docker services (Redis, Weaviate, MongoDB)...${NC}"
docker-compose up -d redis weaviate mongodb
sleep 5
if docker ps | grep -q redis && docker ps | grep -q weaviate && docker ps | grep -q mongodb; then
    echo -e "${GREEN}✓ Required services started successfully${NC}"
    echo -e "  Redis: localhost:6379"
    echo -e "  Weaviate: localhost:8082"
    echo -e "  MongoDB: localhost:27017"
else
    echo -e "${RED}✗ Failed to start one or more required services${NC}"
    echo -e "${YELLOW}Run 'docker-compose logs redis weaviate mongodb' to see errors${NC}"
    exit 1
fi

# Start Backend
echo -e "\n${YELLOW}Starting Backend (FastAPI)...${NC}"
cd "$(dirname "$0")/backend"
./venv/bin/python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..
sleep 5

if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Backend started on http://localhost:8000${NC}"
    echo -e "  PID: $BACKEND_PID"
    echo -e "  Logs: logs/backend.log"
else
    echo -e "${RED}✗ Failed to start backend${NC}"
    echo -e "${YELLOW}Check logs/backend.log for details${NC}"
    exit 1
fi

# Start Frontend
echo -e "\n${YELLOW}Starting Frontend (React + Vite)...${NC}"
cd frontend
npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
sleep 3

if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Frontend started on http://localhost:5174${NC}"
    echo -e "  PID: $FRONTEND_PID"
    echo -e "  Logs: logs/frontend.log"
else
    echo -e "${RED}✗ Failed to start frontend${NC}"
    exit 1
fi

# Optional: Start additional Docker services (Neo4j)
echo -e "\n${YELLOW}Additional Docker Services (optional):${NC}"
read -p "Do you want to start Neo4j? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Starting Neo4j...${NC}"
    docker-compose up -d neo4j
    sleep 3
    echo -e "${GREEN}✓ Neo4j started${NC}"
    echo -e "  Neo4j: localhost:7474 (browser), localhost:7687 (bolt)"
fi

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  All services running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Frontend:${NC}  http://localhost:5174"
echo -e "${GREEN}Backend:${NC}   http://localhost:8000"
echo -e "${GREEN}API Docs:${NC}  http://localhost:8000/docs"
echo -e "${GREEN}Redis:${NC}     localhost:6379"
echo -e "${GREEN}Weaviate:${NC}  http://localhost:8082"
echo -e "${GREEN}MongoDB:${NC}   localhost:27017"
echo -e "\n${YELLOW}Logs:${NC}"
echo -e "  Backend:  tail -f logs/backend.log"
echo -e "  Frontend: tail -f logs/frontend.log"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}"

# Keep script running and tail logs
tail -f logs/backend.log logs/frontend.log
