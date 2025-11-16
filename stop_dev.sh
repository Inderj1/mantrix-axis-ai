#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping all development services...${NC}"

# Stop Frontend
echo -e "\n${YELLOW}Stopping Frontend...${NC}"
pkill -f "npm start" && echo -e "${GREEN}✓ Frontend stopped${NC}" || echo -e "${RED}✗ Frontend not running${NC}"

# Stop Backend
echo -e "\n${YELLOW}Stopping Backend...${NC}"
pkill -f "uvicorn src.main:app" && echo -e "${GREEN}✓ Backend stopped${NC}" || echo -e "${RED}✗ Backend not running${NC}"

# Stop required Docker services (Redis, Weaviate, MongoDB)
echo -e "\n${YELLOW}Stopping required Docker services (Redis, Weaviate, MongoDB)...${NC}"
docker-compose stop redis weaviate mongodb && echo -e "${GREEN}✓ Required services stopped${NC}" || echo -e "${YELLOW}! Required services not running${NC}"

# Optional: Stop all Docker services
echo -e "\n${YELLOW}Additional Docker Services:${NC}"
read -p "Do you want to stop all Docker services (Neo4j)? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose down && echo -e "${GREEN}✓ All Docker services stopped${NC}" || echo -e "${YELLOW}! No additional services running${NC}"
else
    echo -e "${YELLOW}Neo4j left running (if it was started)${NC}"
fi

echo -e "\n${GREEN}All development services stopped!${NC}"
