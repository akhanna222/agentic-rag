# Agentic RAG - Medical Document Intelligence

A multi-disease RAG (Retrieval-Augmented Generation) system with agentic verification for zero-hallucination medical information retrieval.

## Features

- **Multi-format Document Support**: PDF, JSON, images (PNG, JPG), Markdown, and text files
- **OpenAI Vision Processing**: Extracts text from images and scanned PDFs using GPT-4 Vision
- **Per-Disease Collections**: Each disease has its own isolated vector database
- **Agentic Verification**: Multi-step verification loop using reasoning models to ensure accuracy
- **Zero-Hallucination Design**: Strict context-based answering with source citations
- **Simple Upload UI**: Web interface for managing diseases and uploading documents
- **RESTful API**: Full API access for integration with other systems

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
├── scripts/
│   ├── setup-ec2.sh         # EC2 Ubuntu setup script
│   └── run-local.sh         # Local development script
├── Dockerfile
├── docker-compose.yml
└── nginx.conf               # Production nginx config
```

## Quick Start

### Local Development

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd agentic-rag
   ```

2. Create environment file:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. Run locally:
   ```bash
   chmod +x scripts/run-local.sh
   ./scripts/run-local.sh
   ```

4. Access at `http://localhost:8000`

### Docker Deployment

1. Build and run:
   ```bash
   docker-compose up -d
   ```

2. For production with Nginx:
   ```bash
   docker-compose --profile production up -d
   ```

### EC2 Deployment

1. SSH into your EC2 instance (Ubuntu)

2. Clone the repository:
   ```bash
   git clone <repo-url>
   cd agentic-rag
   ```

3. Run setup script:
   ```bash
   chmod +x scripts/setup-ec2.sh
   ./scripts/setup-ec2.sh
   ```

4. Configure API key:
   ```bash
   nano /opt/agentic-rag/.env
   ```

5. Start the service:
   ```bash
   cd /opt/agentic-rag
   docker-compose up -d
   ```

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

### Example: Simple Query (GET)

**HTTP Request Node Configuration:**
- Method: `GET`
- URL: `http://your-server:8000/api/v1/ask`
- Authentication: Header Auth
- Query Parameters:
  - `disease`: `diabetes`
  - `question`: `What are the symptoms?`
  - `verify`: `true`

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

### Example: Simple Query (POST)

**HTTP Request Node Configuration:**
- Method: `POST`
- URL: `http://your-server:8000/api/v1/ask`
- Body Content Type: `JSON`
- Body:
```json
{
  "disease": "diabetes",
  "question": "What are the treatment options?",
  "verify": true
}
```

### Example: Async Query with Webhook

For long-running queries, use async mode with a webhook callback:

1. Add a **Webhook** node to receive the callback
2. Add an **HTTP Request** node:
   - Method: `POST`
   - URL: `http://your-server:8000/api/v1/ask/async`
   - Body:
   ```json
   {
     "disease": "diabetes",
     "query": "Complex question here...",
     "use_verification": true,
     "webhook_url": "{{ $node.Webhook.webhookUrl }}"
   }
   ```

### Example: Upload Document from URL

Fetch and process a document from a URL:
- Method: `POST`
- URL: `http://your-server:8000/upload/diabetes/url`
- Query Parameters:
  - `url`: `https://example.com/document.pdf`

### Example n8n Workflow

```
[Trigger] → [HTTP Request: List Diseases] → [Set Disease] → [HTTP Request: Ask Question] → [Response]
```

## API Reference

### Diseases

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/diseases` | GET | List all disease collections |
| `/diseases` | POST | Create a new disease collection |
| `/diseases/{name}` | DELETE | Delete a disease collection |
| `/diseases/{name}/documents` | GET | List documents in a disease |

### Documents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload/{disease}` | POST | Upload document to a disease |
| `/documents/{disease}/{id}` | DELETE | Delete a document |

### Query

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | POST | Query with agentic verification |

**Request Body:**
```json
{
  "disease": "diabetes",
  "query": "What are the symptoms?",
  "use_verification": true,
  "max_attempts": 5
}
```

**Response:**
```json
{
  "answer": "According to the documents...",
  "verified": true,
  "confidence": 0.92,
  "references": [...],
  "attempts": [...],
  "disease": "diabetes"
}
```

## How Agentic Verification Works

1. **Initial Query**: User submits a question for a specific disease
2. **Retrieval**: Relevant chunks are retrieved from the disease's vector store
3. **Generation**: Answer is generated strictly from retrieved context
4. **Verification**: A reasoning model (o1-mini) verifies the answer against context
5. **Iteration**: If confidence < threshold, query is refined and steps 2-4 repeat
6. **Result**: Returns best answer after up to N attempts with confidence score

This multi-step verification ensures:
- All claims are supported by source documents
- No hallucinations or external knowledge
- Clear source citations
- Confidence transparency

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | Your OpenAI API key |
| `VISION_MODEL` | gpt-4o | Model for document parsing |
| `EMBEDDING_MODEL` | text-embedding-3-small | Model for embeddings |
| `REASONING_MODEL` | o1-mini | Model for verification |
| `GENERATION_MODEL` | gpt-4o | Model for answer generation |
| `CHUNK_SIZE` | 1000 | Characters per chunk |
| `CHUNK_OVERLAP` | 200 | Overlap between chunks |
| `TOP_K_RETRIEVAL` | 5 | Number of chunks to retrieve |
| `MAX_VERIFICATION_ATTEMPTS` | 5 | Max verification retries |
| `CONFIDENCE_THRESHOLD` | 0.8 | Minimum confidence to pass |
| `REQUIRE_API_KEY` | false | Enable API key authentication |
| `RAG_API_KEY` | - | API key for authentication (when enabled) |

## Security Notes

- Store API keys in environment variables, not in code
- Use HTTPS in production (configure nginx with SSL)
- Consider rate limiting for production deployments
- Review uploaded documents for sensitive information

## License

MIT License
