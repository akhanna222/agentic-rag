# Agentic RAG - Medical Document Intelligence

A multi-disease RAG (Retrieval-Augmented Generation) system with agentic verification for zero-hallucination medical information retrieval.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)

## Features

- **Multi-format Document Support**: PDF, JSON, images (PNG, JPG), Markdown, and text files
- **OpenAI Vision Processing**: Extracts text from images and scanned PDFs using GPT-4 Vision
- **Per-Disease Collections**: Each disease has its own isolated vector database
- **Agentic Verification**: Multi-step verification loop (up to 5 retries) using reasoning models
- **Zero-Hallucination Design**: Strict context-based answering with source citations
- **n8n Integration**: Simple REST API designed for workflow automation
- **Simple Upload UI**: Web interface for managing diseases and uploading documents

## Documentation

| Document | Description |
|----------|-------------|
| [Setup Guide](docs/SETUP.md) | Complete installation instructions |
| [API Reference](docs/API.md) | Full API documentation |
| [Roadmap](docs/ROADMAP.md) | Future features and plans |

---

## Quick Start (5 minutes)

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/akhanna222/agentic-rag.git
cd agentic-rag

# Configure
cp .env.example .env
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# Run
docker-compose up -d

# Access
open http://localhost:8001
```

### Option 2: Local Development

```bash
# Clone and setup
git clone https://github.com/akhanna222/agentic-rag.git
cd agentic-rag

# Configure
cp .env.example .env
# Edit .env and add OPENAI_API_KEY

# Run
chmod +x scripts/run-local.sh
./scripts/run-local.sh
```

### Option 3: EC2 Deployment

```bash
# On your EC2 instance (Ubuntu)
git clone https://github.com/akhanna222/agentic-rag.git
cd agentic-rag
chmod +x scripts/setup-ec2.sh
./scripts/setup-ec2.sh

# Configure and start
nano /opt/agentic-rag/.env  # Add OPENAI_API_KEY
cd /opt/agentic-rag && docker-compose up -d
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Query                                   │
│                    "What are the symptoms?"                         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    1. RETRIEVAL                                      │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│   │  Diabetes   │    │ Hypertension│    │   Asthma    │            │
│   │  VectorDB   │    │  VectorDB   │    │  VectorDB   │            │
│   └──────┬──────┘    └─────────────┘    └─────────────┘            │
│          │                                                          │
│          ▼ Top-K relevant chunks                                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    2. GENERATION                                     │
│                                                                      │
│   Context + Query → GPT-4o → Answer with [Source] citations         │
│                                                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    3. VERIFICATION (Agentic Loop)                    │
│                                                                      │
│   ┌──────────────────────────────────────────────────────────┐      │
│   │  o1-mini Reasoning Model checks:                         │      │
│   │  • Is every claim supported by context?                  │      │
│   │  • Are there any hallucinations?                         │      │
│   │  • Confidence score 0.0 - 1.0                            │      │
│   └──────────────────────────┬───────────────────────────────┘      │
│                              │                                       │
│              ┌───────────────┴───────────────┐                      │
│              │                               │                      │
│         Confidence ≥ 0.8              Confidence < 0.8              │
│              │                               │                      │
│              ▼                               ▼                      │
│         ✅ Return                    Refine query & retry           │
│         Answer                       (up to 5 attempts)             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
agentic-rag/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── document_processor.py # OpenAI Vision document parsing
│   ├── vector_store.py      # ChromaDB per-disease collections
│   ├── rag_engine.py        # RAG retrieval and generation
│   ├── agentic_verifier.py  # Verification loop with reasoning model
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Main UI
│   ├── styles.css           # Styling
│   └── app.js               # Frontend logic
├── docs/
│   ├── SETUP.md             # Complete setup guide
│   ├── API.md               # API reference
│   └── ROADMAP.md           # Future plans
├── scripts/
│   ├── setup-ec2.sh         # EC2 Ubuntu setup script
│   └── run-local.sh         # Local development script
├── Dockerfile
├── docker-compose.yml
└── nginx.conf               # Production nginx config
```

---

## n8n Integration

This API is designed for easy integration with n8n workflow automation.

### Quick Setup

1. **Enable API Authentication** (recommended):
   ```bash
   # In .env file
   REQUIRE_API_KEY=true
   RAG_API_KEY=your-secure-key-here
   ```

2. **n8n Credentials**: Create a "Header Auth" credential with:
   - Name: `X-API-Key`
   - Value: `your-secure-key-here`

### n8n Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ask` | GET/POST | Simple query (recommended for n8n) |
| `/api/v1/ask/async` | POST | Async query with webhook callback |
| `/api/v1/diseases` | GET | List diseases (for dropdowns) |
| `/api/v1/diseases?name=X` | POST | Create disease |
| `/upload/{disease}/url` | POST | Upload document from URL |

### Example: Simple Query (GET)

**HTTP Request Node Configuration:**
```
Method: GET
URL: http://your-server:8001/api/v1/ask
Query Parameters:
  - disease: diabetes
  - question: What are the symptoms?
  - verify: true
Headers:
  - X-API-Key: your-api-key
```

**Response:**
```json
{
  "success": true,
  "answer": "Based on the documents...",
  "verified": true,
  "confidence": 0.92,
  "sources": [{"file": "guide.pdf", "excerpt": "..."}]
}
```

### Example: Async Query with Webhook

For long-running queries:

```json
POST /api/v1/ask/async
{
  "disease": "diabetes",
  "query": "Complex question here...",
  "use_verification": true,
  "webhook_url": "{{ $node.Webhook.webhookUrl }}"
}
```

See [API Documentation](docs/API.md) for complete n8n integration examples.

---

## API Reference

### Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/diseases` | GET | List all diseases |
| `/diseases` | POST | Create a disease |
| `/diseases/{name}` | DELETE | Delete a disease |
| `/upload/{disease}` | POST | Upload document |
| `/query` | POST | Query with verification |
| `/api/v1/ask` | GET/POST | Simple query (n8n) |

### Query Example

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "disease": "diabetes",
    "query": "What are the symptoms?",
    "use_verification": true
  }'
```

**Response:**
```json
{
  "success": true,
  "answer": "According to the documents, symptoms include...",
  "verified": true,
  "confidence": 0.92,
  "references": [
    {
      "source_id": 1,
      "filename": "diabetes-guide.pdf",
      "excerpt": "Common symptoms include..."
    }
  ]
}
```

See [Full API Documentation](docs/API.md) for complete reference.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | Your OpenAI API key |
| `REQUIRE_API_KEY` | false | Enable API authentication |
| `RAG_API_KEY` | - | API key for authentication |
| `VISION_MODEL` | gpt-4o | Model for document parsing |
| `EMBEDDING_MODEL` | text-embedding-3-small | Embedding model |
| `REASONING_MODEL` | o1-mini | Verification model |
| `GENERATION_MODEL` | gpt-4o | Answer generation model |
| `MAX_VERIFICATION_ATTEMPTS` | 5 | Max verification retries |
| `CONFIDENCE_THRESHOLD` | 0.8 | Minimum confidence score |

See [Setup Guide](docs/SETUP.md) for complete configuration options.

---

## Roadmap

### Coming Soon (v1.1 - v1.3)
- Enhanced document processing (OCR improvements, table extraction)
- Hybrid search (semantic + keyword)
- Chat interface with conversation history
- Admin dashboard with analytics

### Future (v2.0+)
- Multi-tenant architecture
- Knowledge graph integration
- HIPAA compliance features
- Fine-tuned medical models

See [Full Roadmap](docs/ROADMAP.md) for detailed plans.

---

## Security Notes

- Store API keys in environment variables, not in code
- Use HTTPS in production (configure nginx with SSL)
- Enable `REQUIRE_API_KEY=true` for production
- Review uploaded documents for sensitive information
- Consider rate limiting for production deployments

---

## Contributing

Contributions are welcome! Please see our [Roadmap](docs/ROADMAP.md) for areas where help is needed.

1. Fork the repository
2. Create a feature branch
3. Submit a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/akhanna222/agentic-rag/issues)
- **Discussions**: [GitHub Discussions](https://github.com/akhanna222/agentic-rag/discussions)
