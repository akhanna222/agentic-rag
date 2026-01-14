#!/bin/bash
# View Agentic RAG container logs

CONTAINER_NAME="agentic-rag"

echo "=== Agentic RAG Logs ==="
echo ""

# Check if container exists
if ! docker ps -a | grep -q $CONTAINER_NAME; then
    echo "Container '$CONTAINER_NAME' not found"
    echo "Run: ./scripts/start.sh to start the application"
    exit 1
fi

# Show container status
echo "Container Status:"
docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Show logs
echo "Logs (use Ctrl+C to exit):"
docker logs -f $CONTAINER_NAME --tail 100
