#!/bin/bash
# Stop Agentic RAG containers

CONTAINER_NAME="agentic-rag"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Stopping Agentic RAG..."
docker-compose down 2>/dev/null || docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm -f $CONTAINER_NAME 2>/dev/null || true

echo "✓ Agentic RAG stopped"
