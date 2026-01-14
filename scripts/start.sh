#!/bin/bash
# Smart startup script for Agentic RAG
# Handles port conflicts, container cleanup, and startup verification

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="agentic-rag"
DEFAULT_PORT=8001
MAX_PORT=8010
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Agentic RAG - Smart Startup Script   ${NC}"
echo -e "${GREEN}========================================${NC}"

cd "$PROJECT_DIR"

# Function to check if port is available
is_port_available() {
    local port=$1
    if command -v lsof &> /dev/null; then
        ! lsof -i:$port &> /dev/null
    elif command -v netstat &> /dev/null; then
        ! netstat -tuln | grep -q ":$port "
    elif command -v ss &> /dev/null; then
        ! ss -tuln | grep -q ":$port "
    else
        # Try to connect - if it fails, port is likely available
        ! (echo > /dev/tcp/localhost/$port) 2>/dev/null
    fi
}

# Function to find available port
find_available_port() {
    local port=$DEFAULT_PORT
    while [ $port -le $MAX_PORT ]; do
        if is_port_available $port; then
            echo $port
            return 0
        fi
        echo -e "${YELLOW}Port $port is in use, trying next...${NC}" >&2
        port=$((port + 1))
    done
    echo -e "${RED}No available ports found between $DEFAULT_PORT and $MAX_PORT${NC}" >&2
    return 1
}

# Function to check what's using a port
check_port_usage() {
    local port=$1
    echo -e "${YELLOW}Checking what's using port $port...${NC}"

    if command -v lsof &> /dev/null; then
        lsof -i:$port 2>/dev/null || true
    fi

    # Check Docker containers
    echo -e "${YELLOW}Docker containers using port $port:${NC}"
    docker ps --format "{{.Names}}: {{.Ports}}" 2>/dev/null | grep "$port" || echo "None"
}

# Step 1: Check for .env file
echo -e "\n${YELLOW}Step 1: Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}WARNING: Please edit .env and add your OPENAI_API_KEY${NC}"
    echo "Edit the file: nano $PROJECT_DIR/.env"
fi

# Check if OPENAI_API_KEY is set
if grep -q "OPENAI_API_KEY=sk-your" .env 2>/dev/null || ! grep -q "OPENAI_API_KEY=" .env 2>/dev/null; then
    echo -e "${RED}ERROR: OPENAI_API_KEY is not configured in .env${NC}"
    echo "Please edit .env and add your OpenAI API key"
    echo "Example: OPENAI_API_KEY=sk-proj-xxxxx"
    exit 1
fi

echo -e "${GREEN}✓ Environment file found${NC}"

# Step 2: Stop and remove existing container
echo -e "\n${YELLOW}Step 2: Cleaning up existing containers...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm -f $CONTAINER_NAME 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Step 3: Find available port
echo -e "\n${YELLOW}Step 3: Finding available port...${NC}"
AVAILABLE_PORT=$(find_available_port)
if [ -z "$AVAILABLE_PORT" ]; then
    echo -e "${RED}Failed to find available port${NC}"
    check_port_usage $DEFAULT_PORT
    exit 1
fi
echo -e "${GREEN}✓ Using port: $AVAILABLE_PORT${NC}"

# Step 4: Update .env with port
echo -e "\n${YELLOW}Step 4: Configuring port...${NC}"
if grep -q "^PORT=" .env; then
    sed -i "s/^PORT=.*/PORT=$AVAILABLE_PORT/" .env
else
    echo "PORT=$AVAILABLE_PORT" >> .env
fi
echo -e "${GREEN}✓ Port configured: $AVAILABLE_PORT${NC}"

# Step 5: Remove version from docker-compose (suppress warning)
echo -e "\n${YELLOW}Step 5: Updating docker-compose.yml...${NC}"
sed -i '/^version:/d' docker-compose.yml 2>/dev/null || true
echo -e "${GREEN}✓ docker-compose.yml updated${NC}"

# Step 6: Build and start
echo -e "\n${YELLOW}Step 6: Building and starting container...${NC}"
docker-compose build --quiet
docker-compose up -d

# Step 7: Wait for startup
echo -e "\n${YELLOW}Step 7: Waiting for application to start...${NC}"
MAX_WAIT=30
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:$AVAILABLE_PORT/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Application is running!${NC}"
        break
    fi
    echo -n "."
    sleep 1
    WAITED=$((WAITED + 1))
done
echo ""

# Step 8: Verify and show status
echo -e "\n${YELLOW}Step 8: Verifying deployment...${NC}"
HEALTH_RESPONSE=$(curl -s "http://localhost:$AVAILABLE_PORT/health" 2>/dev/null || echo "FAILED")

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  SUCCESS! Agentic RAG is running!     ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "Web UI:      ${GREEN}http://localhost:$AVAILABLE_PORT${NC}"
    echo -e "API Docs:    ${GREEN}http://localhost:$AVAILABLE_PORT/docs${NC}"
    echo -e "Health:      ${GREEN}http://localhost:$AVAILABLE_PORT/health${NC}"
    echo ""
    echo -e "External access: ${GREEN}http://$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_IP"):$AVAILABLE_PORT${NC}"
    echo ""
    echo "Health check response:"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  STARTUP FAILED - Checking logs...    ${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Container status:${NC}"
    docker ps -a | grep $CONTAINER_NAME || true
    echo ""
    echo -e "${YELLOW}Container logs (last 50 lines):${NC}"
    docker logs $CONTAINER_NAME --tail 50 2>&1 || true
    echo ""
    echo -e "${RED}Please check the logs above for errors${NC}"
    echo "Common issues:"
    echo "  1. OPENAI_API_KEY not set correctly"
    echo "  2. Missing dependencies"
    echo "  3. Port still in use"
    exit 1
fi
