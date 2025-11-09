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
    redis-cli shutdown 2>/dev/null
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

# Install/update required dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"
cd backend
source venv/bin/activate
pip install -q rdflib crewai nest-asyncio 2>/dev/null || echo -e "${YELLOW}⚠ Some dependencies may need manual installation${NC}"
cd ..
echo -e "${GREEN}✓ Dependencies checked${NC}"

# Clean up any existing processes on required ports
echo -e "\n${YELLOW}Cleaning up existing processes...${NC}"
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5174 2>/dev/null | xargs kill -9 2>/dev/null || true
echo -e "${GREEN}✓ Ports freed${NC}"

# Start Redis
echo -e "\n${YELLOW}Starting Redis...${NC}"
if pgrep -f "redis-server" > /dev/null; then
    echo -e "${GREEN}✓ Redis already running${NC}"
else
    redis-server --daemonize yes
    sleep 1
    if pgrep -f "redis-server" > /dev/null; then
        echo -e "${GREEN}✓ Redis started successfully${NC}"
    else
        echo -e "${RED}✗ Failed to start Redis${NC}"
        exit 1
    fi
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

# Optional: Start Docker services (MongoDB, Neo4j, Weaviate)
echo -e "\n${YELLOW}Docker Services (optional):${NC}"
read -p "Do you want to start Docker services (MongoDB, Neo4j, Weaviate)? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Starting Docker services...${NC}"
    docker-compose up -d mongodb neo4j weaviate
    sleep 3
    echo -e "${GREEN}✓ Docker services started${NC}"
    echo -e "  MongoDB: localhost:27017"
    echo -e "  Neo4j: localhost:7474 (browser), localhost:7687 (bolt)"
    echo -e "  Weaviate: localhost:8082"
fi

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  All services running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Frontend:${NC}  http://localhost:5174"
echo -e "${GREEN}Backend:${NC}   http://localhost:8000"
echo -e "${GREEN}API Docs:${NC}  http://localhost:8000/docs"
echo -e "${GREEN}Redis:${NC}     localhost:6379"
echo -e "\n${YELLOW}Logs:${NC}"
echo -e "  Backend:  tail -f logs/backend.log"
echo -e "  Frontend: tail -f logs/frontend.log"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}"

# Keep script running and tail logs
tail -f logs/backend.log logs/frontend.log
