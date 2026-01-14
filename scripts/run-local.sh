#!/bin/bash
# Run Agentic RAG locally for development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    echo "Please create a .env file with your OPENAI_API_KEY"
    echo "You can copy from .env.example:"
    echo "  cp .env.example .env"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-api-key-here" ]; then
    echo "Error: Please set a valid OPENAI_API_KEY in .env"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r backend/requirements.txt

# Create data directories
mkdir -p data/uploads data/vectordb

# Run the application
echo ""
echo "Starting Agentic RAG..."
echo "Access at: http://localhost:8000"
echo ""

cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
