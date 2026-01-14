"""
Configuration for the Agentic RAG System
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Model Configuration
VISION_MODEL = "gpt-4o"  # For document parsing
EMBEDDING_MODEL = "text-embedding-3-small"
REASONING_MODEL = "o1-mini"  # For verification
GENERATION_MODEL = "gpt-4o"  # For answer generation

# RAG Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K_RETRIEVAL = 5
MAX_VERIFICATION_ATTEMPTS = 5
CONFIDENCE_THRESHOLD = 0.8

# Vector DB Configuration
VECTOR_DB_DIR = DATA_DIR / "vectordb"

# Supported file types
SUPPORTED_EXTENSIONS = {".pdf", ".json", ".png", ".jpg", ".jpeg", ".gif", ".md", ".txt"}

# Server Configuration
HOST = "0.0.0.0"
PORT = 8000
