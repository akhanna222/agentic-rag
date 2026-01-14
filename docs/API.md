# API Reference

Complete API documentation for the Agentic RAG system.

**Base URL**: `http://your-server:8001`

**Interactive Docs**: `http://your-server:8001/docs` (Swagger UI)

---

## Authentication

When `REQUIRE_API_KEY=true`, all endpoints (except `/health`) require authentication.

### Header Authentication
```
X-API-Key: your-api-key-here
```

### Example with cURL
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8001/api/v1/diseases
```

---

## Endpoints Overview

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| System | `/health` | GET | Health check |
| n8n | `/api/v1/ask` | GET/POST | Simple query |
| n8n | `/api/v1/ask/async` | POST | Async query with webhook |
| n8n | `/api/v1/diseases` | GET/POST | Disease management |
| Diseases | `/diseases` | GET/POST | List/Create diseases |
| Diseases | `/diseases/{name}` | DELETE | Delete disease |
| Diseases | `/diseases/{name}/documents` | GET | List documents |
| Documents | `/upload/{disease}` | POST | Upload document |
| Documents | `/upload/{disease}/url` | POST | Upload from URL |
| Documents | `/documents/{disease}/{id}` | DELETE | Delete document |
| Query | `/query` | POST | Full query with options |
| Query | `/query/simple` | POST | Simple form-based query |

---

## System Endpoints

### Health Check

Check if the API is running.

**Request**
```
GET /health
```

**Response**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "api_key_required": false
}
```

---

## n8n Integration Endpoints

### Simple Query (GET)

Best for n8n HTTP Request nodes with query parameters.

**Request**
```
GET /api/v1/ask?disease={disease}&question={question}&verify={bool}
```

**Parameters**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| disease | string | Yes | Disease collection name |
| question | string | Yes | Your question |
| verify | boolean | No | Enable verification (default: true) |

**Example**
```bash
curl "http://localhost:8001/api/v1/ask?disease=diabetes&question=What%20are%20symptoms?&verify=true"
```

**Response**
```json
{
  "success": true,
  "answer": "Based on the documents, symptoms of diabetes include...",
  "verified": true,
  "confidence": 0.92,
  "sources": [
    {
      "file": "diabetes-guide.pdf",
      "excerpt": "Common symptoms include increased thirst..."
    }
  ],
  "disease": "diabetes"
}
```

### Simple Query (POST)

Best for n8n HTTP Request nodes with JSON body.

**Request**
```
POST /api/v1/ask
Content-Type: application/json
```

**Body**
```json
{
  "disease": "diabetes",
  "question": "What are the treatment options?",
  "verify": true
}
```

**Response**
```json
{
  "success": true,
  "answer": "Treatment options for diabetes include...",
  "verified": true,
  "confidence": 0.88,
  "sources": [...],
  "disease": "diabetes"
}
```

### Async Query with Webhook

For long-running queries that need immediate response.

**Request**
```
POST /api/v1/ask/async
Content-Type: application/json
```

**Body**
```json
{
  "disease": "diabetes",
  "query": "Provide a comprehensive treatment plan",
  "use_verification": true,
  "max_attempts": 5,
  "webhook_url": "https://your-n8n-instance/webhook/abc123"
}
```

**Immediate Response**
```json
{
  "success": true,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Query processing started. Results will be sent to webhook.",
  "webhook_url": "https://your-n8n-instance/webhook/abc123"
}
```

**Webhook Callback** (sent to your webhook URL)
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "answer": "A comprehensive treatment plan for diabetes...",
  "verified": true,
  "confidence": 0.91,
  "references": [...]
}
```

### List Diseases (n8n)

Returns diseases in a format suitable for n8n dropdowns.

**Request**
```
GET /api/v1/diseases
```

**Response**
```json
{
  "success": true,
  "diseases": ["Diabetes", "Hypertension", "Asthma"],
  "details": [
    {
      "name": "diabetes",
      "display_name": "Diabetes",
      "document_count": 5
    },
    ...
  ]
}
```

### Create Disease (n8n)

Create a disease using query parameter.

**Request**
```
POST /api/v1/diseases?name=Heart%20Disease
```

**Response**
```json
{
  "success": true,
  "name": "heart_disease",
  "display_name": "Heart Disease",
  "document_count": 0
}
```

---

## Disease Management

### List All Diseases

**Request**
```
GET /diseases
```

**Response**
```json
[
  {
    "name": "diabetes",
    "display_name": "Diabetes",
    "document_count": 5
  },
  {
    "name": "hypertension",
    "display_name": "Hypertension",
    "document_count": 3
  }
]
```

### Create Disease

**Request**
```
POST /diseases
Content-Type: application/json
```

**Body**
```json
{
  "name": "Alzheimer's Disease"
}
```

**Response**
```json
{
  "name": "alzheimers_disease",
  "display_name": "Alzheimer's Disease",
  "document_count": 0
}
```

### Delete Disease

**Request**
```
DELETE /diseases/{disease_name}
```

**Response**
```json
{
  "success": true,
  "message": "Disease 'diabetes' deleted successfully"
}
```

### List Disease Documents

**Request**
```
GET /diseases/{disease_name}/documents
```

**Response**
```json
{
  "success": true,
  "documents": [
    {
      "document_id": "abc123",
      "filename": "diabetes-guide.pdf",
      "disease": "diabetes"
    }
  ]
}
```

---

## Document Management

### Upload Document

Upload a file to a disease collection.

**Request**
```
POST /upload/{disease_name}
Content-Type: multipart/form-data
```

**Form Data**
| Field | Type | Description |
|-------|------|-------------|
| file | File | Document to upload |

**Supported Formats**: PDF, JSON, PNG, JPG, JPEG, GIF, MD, TXT

**Example with cURL**
```bash
curl -X POST \
  -H "X-API-Key: your-key" \
  -F "file=@document.pdf" \
  http://localhost:8001/upload/diabetes
```

**Response**
```json
{
  "success": true,
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "disease": "diabetes",
  "chunks_added": 12
}
```

### Upload from URL

Download and process a document from a URL.

**Request**
```
POST /upload/{disease_name}/url?url={document_url}&filename={optional_name}
```

**Parameters**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| url | string | Yes | URL to fetch document from |
| filename | string | No | Override filename |

**Example**
```bash
curl -X POST \
  "http://localhost:8001/upload/diabetes/url?url=https://example.com/guide.pdf"
```

**Response**
```json
{
  "success": true,
  "document_id": "550e8400-e29b-41d4-a716-446655440001",
  "filename": "guide.pdf",
  "disease": "diabetes",
  "chunks_added": 8,
  "source_url": "https://example.com/guide.pdf"
}
```

### Delete Document

**Request**
```
DELETE /documents/{disease_name}/{document_id}
```

**Response**
```json
{
  "success": true,
  "message": "Document '550e8400...' deleted"
}
```

---

## Query Endpoints

### Full Query

Query with all options available.

**Request**
```
POST /query
Content-Type: application/json
```

**Body**
```json
{
  "disease": "diabetes",
  "query": "What are the symptoms of type 2 diabetes?",
  "use_verification": true,
  "max_attempts": 5
}
```

**Parameters**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| disease | string | Yes | - | Disease to query |
| query | string | Yes | - | Your question |
| use_verification | boolean | No | true | Enable agentic verification |
| max_attempts | integer | No | 5 | Max verification attempts |

**Response**
```json
{
  "success": true,
  "answer": "According to the documents, symptoms of type 2 diabetes include:\n\n1. Increased thirst [Source 1]\n2. Frequent urination [Source 1]\n3. Unexplained weight loss [Source 2]\n...",
  "verified": true,
  "confidence": 0.92,
  "references": [
    {
      "source_id": 1,
      "filename": "diabetes-symptoms.pdf",
      "excerpt": "Common symptoms include increased thirst (polydipsia)...",
      "relevance_score": 0.95
    },
    {
      "source_id": 2,
      "filename": "type2-guide.pdf",
      "excerpt": "Patients may experience unexplained weight loss...",
      "relevance_score": 0.88
    }
  ],
  "disease": "diabetes",
  "attempts": [
    {
      "attempt": 1,
      "query_used": "What are the symptoms of type 2 diabetes?",
      "confidence": 0.92,
      "is_verified": true,
      "issues": [],
      "reasoning": "All claims are supported by source documents..."
    }
  ],
  "warning": null
}
```

### Simple Form Query

For form-based submissions.

**Request**
```
POST /query/simple
Content-Type: application/x-www-form-urlencoded
```

**Form Data**
```
disease=diabetes&query=What are symptoms?
```

---

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": "Error message here",
  "detail": "Additional details (optional)"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing/invalid API key |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

### Examples

**Missing API Key (401)**
```json
{
  "success": false,
  "error": "Invalid or missing API key"
}
```

**Disease Not Found (404)**
```json
{
  "success": false,
  "error": "Disease not found"
}
```

**Unsupported File Type (400)**
```json
{
  "success": false,
  "error": "Unsupported file type: .exe. Supported: ['.pdf', '.json', '.png', ...]"
}
```

---

## Rate Limits

Currently no rate limits are implemented. For production deployments, consider:
- Adding rate limiting via Nginx
- Using a reverse proxy with rate limiting
- Implementing application-level rate limits

---

## SDKs & Client Libraries

### Python

```python
import requests

class AgenticRAG:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key

    def ask(self, disease, question, verify=True):
        response = requests.get(
            f"{self.base_url}/api/v1/ask",
            params={"disease": disease, "question": question, "verify": verify},
            headers=self.headers
        )
        return response.json()

    def upload(self, disease, file_path):
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/upload/{disease}",
                files={"file": f},
                headers=self.headers
            )
        return response.json()

# Usage
rag = AgenticRAG("http://localhost:8001", api_key="your-key")
result = rag.ask("diabetes", "What are the symptoms?")
print(result["answer"])
```

### JavaScript/Node.js

```javascript
class AgenticRAG {
  constructor(baseUrl, apiKey = null) {
    this.baseUrl = baseUrl;
    this.headers = { 'Content-Type': 'application/json' };
    if (apiKey) this.headers['X-API-Key'] = apiKey;
  }

  async ask(disease, question, verify = true) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/ask`,
      {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({ disease, question, verify })
      }
    );
    return response.json();
  }
}

// Usage
const rag = new AgenticRAG('http://localhost:8001', 'your-key');
const result = await rag.ask('diabetes', 'What are the symptoms?');
console.log(result.answer);
```

---

## Changelog

### v1.0.0
- Initial release
- Full API with n8n integration
- Agentic verification system
