"""
Agentic RAG API - FastAPI Backend
Multi-disease RAG system with verification
Enhanced for n8n and external integrations
"""
import os
import uuid
import shutil
import httpx
import asyncio
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager
from functools import wraps

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query, Header, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from config import (
    HOST, PORT, DATA_DIR, UPLOAD_DIR,
    SUPPORTED_EXTENSIONS, MAX_VERIFICATION_ATTEMPTS,
    API_KEY, API_KEY_HEADER, REQUIRE_API_KEY, WEBHOOK_TIMEOUT
)
from document_processor import get_processor
from vector_store import get_vector_store
from rag_engine import get_rag_engine
from agentic_verifier import get_agentic_verifier


# ==================== Pydantic Models ====================

class QueryRequest(BaseModel):
    disease: str = Field(..., description="Disease collection to query")
    query: str = Field(..., description="Question to ask")
    use_verification: bool = Field(True, description="Enable agentic verification")
    max_attempts: int = Field(MAX_VERIFICATION_ATTEMPTS, description="Max verification attempts")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for async callback")


class QueryResponse(BaseModel):
    success: bool = True
    answer: str
    verified: bool
    confidence: float
    references: List[dict]
    disease: str
    attempts: Optional[List[dict]] = None
    warning: Optional[str] = None


class N8nQueryRequest(BaseModel):
    """Simplified request format for n8n"""
    disease: str
    question: str
    verify: bool = True


class DiseaseCreate(BaseModel):
    name: str


class DiseaseResponse(BaseModel):
    name: str
    display_name: str
    document_count: int


class DocumentResponse(BaseModel):
    success: bool = True
    document_id: str
    filename: str
    disease: str
    chunks_added: int


class HealthResponse(BaseModel):
    status: str
    version: str
    api_key_required: bool


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


# ==================== API Key Authentication ====================

api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)):
    """Verify API key for protected endpoints"""
    if not REQUIRE_API_KEY:
        return True

    if not API_KEY:
        # No API key configured, allow all requests
        return True

    if api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    return True


# ==================== Startup/Shutdown ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Agentic RAG API starting...")
    print(f"Data directory: {DATA_DIR}")
    print(f"API Key Required: {REQUIRE_API_KEY}")

    yield

    # Shutdown
    print("Agentic RAG API shutting down...")


# ==================== Create FastAPI App ====================

app = FastAPI(
    title="Agentic RAG API",
    description="""
## Multi-disease RAG system with agentic verification

### Features:
- **Multi-format document support**: PDF, JSON, images, Markdown, TXT
- **Per-disease collections**: Isolated vector stores for each disease
- **Agentic verification**: Multi-step answer validation
- **n8n Integration**: Simple endpoints for workflow automation

### Authentication:
Set `X-API-Key` header when `REQUIRE_API_KEY=true`

### n8n Integration:
Use the `/api/v1/*` endpoints for easy n8n integration
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "detail": str(exc)}
    )


# ==================== Health Check ====================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint - no authentication required"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "api_key_required": REQUIRE_API_KEY
    }


# ==================== n8n Simple API (v1) ====================

@app.get("/api/v1/ask", tags=["n8n Integration"])
async def n8n_ask_get(
    disease: str = Query(..., description="Disease collection name"),
    question: str = Query(..., description="Your question"),
    verify: bool = Query(True, description="Enable verification"),
    _: bool = Depends(verify_api_key)
):
    """
    Simple GET endpoint for n8n HTTP Request node

    **n8n Setup:**
    1. Add HTTP Request node
    2. Method: GET
    3. URL: `http://your-server:8000/api/v1/ask`
    4. Query Parameters:
       - disease: `diabetes`
       - question: `What are the symptoms?`
       - verify: `true`
    5. Headers: `X-API-Key: your-api-key` (if required)
    """
    if verify:
        verifier = get_agentic_verifier()
        result = verifier.agentic_query(
            disease_name=disease,
            query=question,
            max_attempts=MAX_VERIFICATION_ATTEMPTS
        )
    else:
        engine = get_rag_engine()
        result = engine.query(disease_name=disease, query=question)
        result["verified"] = False
        result["confidence"] = 0.0

    return {
        "success": True,
        "answer": result.get("answer", ""),
        "verified": result.get("verified", False),
        "confidence": result.get("confidence", 0.0),
        "sources": [
            {"file": ref.get("filename"), "excerpt": ref.get("excerpt", "")[:200]}
            for ref in result.get("references", [])
        ],
        "disease": disease
    }


@app.post("/api/v1/ask", tags=["n8n Integration"])
async def n8n_ask_post(
    request: N8nQueryRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Simple POST endpoint for n8n HTTP Request node

    **n8n Setup:**
    1. Add HTTP Request node
    2. Method: POST
    3. URL: `http://your-server:8000/api/v1/ask`
    4. Body Content Type: JSON
    5. Body: `{"disease": "diabetes", "question": "What are symptoms?"}`
    6. Headers: `X-API-Key: your-api-key` (if required)
    """
    if request.verify:
        verifier = get_agentic_verifier()
        result = verifier.agentic_query(
            disease_name=request.disease,
            query=request.question,
            max_attempts=MAX_VERIFICATION_ATTEMPTS
        )
    else:
        engine = get_rag_engine()
        result = engine.query(disease_name=request.disease, query=request.question)
        result["verified"] = False
        result["confidence"] = 0.0

    return {
        "success": True,
        "answer": result.get("answer", ""),
        "verified": result.get("verified", False),
        "confidence": result.get("confidence", 0.0),
        "sources": [
            {"file": ref.get("filename"), "excerpt": ref.get("excerpt", "")[:200]}
            for ref in result.get("references", [])
        ],
        "disease": request.disease
    }


@app.get("/api/v1/diseases", tags=["n8n Integration"])
async def n8n_list_diseases(_: bool = Depends(verify_api_key)):
    """
    List all disease collections - n8n friendly

    Returns simple array of disease names for dropdowns
    """
    store = get_vector_store()
    diseases = store.list_diseases()
    return {
        "success": True,
        "diseases": [d["display_name"] for d in diseases],
        "details": diseases
    }


@app.post("/api/v1/diseases", tags=["n8n Integration"])
async def n8n_create_disease(
    name: str = Query(..., description="Disease name to create"),
    _: bool = Depends(verify_api_key)
):
    """Create a new disease collection via query parameter"""
    store = get_vector_store()
    result = store.create_disease(name)
    return {"success": True, **result}


# ==================== Webhook Support ====================

async def send_webhook(webhook_url: str, data: dict):
    """Send result to webhook URL"""
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
            await client.post(webhook_url, json=data)
    except Exception as e:
        print(f"Webhook delivery failed: {e}")


@app.post("/api/v1/ask/async", tags=["n8n Integration"])
async def n8n_ask_async(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_api_key)
):
    """
    Async query with webhook callback

    For long-running queries, provide a webhook_url to receive results.
    Useful for n8n workflows that need immediate response.

    **n8n Setup:**
    1. Add Webhook node to receive callback
    2. Add HTTP Request node:
       - POST to `/api/v1/ask/async`
       - Body: `{"disease": "...", "query": "...", "webhook_url": "{{$node.Webhook.webhookUrl}}"}`
    """
    if not request.webhook_url:
        raise HTTPException(400, "webhook_url is required for async requests")

    # Generate request ID
    request_id = str(uuid.uuid4())

    async def process_and_callback():
        try:
            if request.use_verification:
                verifier = get_agentic_verifier()
                result = verifier.agentic_query(
                    disease_name=request.disease,
                    query=request.query,
                    max_attempts=request.max_attempts
                )
            else:
                engine = get_rag_engine()
                result = engine.query(disease_name=request.disease, query=request.query)
                result["verified"] = False
                result["confidence"] = 0.0

            await send_webhook(request.webhook_url, {
                "request_id": request_id,
                "success": True,
                **result
            })
        except Exception as e:
            await send_webhook(request.webhook_url, {
                "request_id": request_id,
                "success": False,
                "error": str(e)
            })

    background_tasks.add_task(process_and_callback)

    return {
        "success": True,
        "request_id": request_id,
        "message": "Query processing started. Results will be sent to webhook.",
        "webhook_url": request.webhook_url
    }


# ==================== Standard API Endpoints ====================

@app.get("/diseases", response_model=List[DiseaseResponse], tags=["Diseases"])
async def list_diseases(_: bool = Depends(verify_api_key)):
    """List all disease collections"""
    store = get_vector_store()
    return store.list_diseases()


@app.post("/diseases", response_model=DiseaseResponse, tags=["Diseases"])
async def create_disease(disease: DiseaseCreate, _: bool = Depends(verify_api_key)):
    """Create a new disease collection"""
    store = get_vector_store()
    return store.create_disease(disease.name)


@app.delete("/diseases/{disease_name}", tags=["Diseases"])
async def delete_disease(disease_name: str, _: bool = Depends(verify_api_key)):
    """Delete a disease collection"""
    store = get_vector_store()

    deleted = store.delete_disease(disease_name)

    disease_folder = UPLOAD_DIR / disease_name
    if disease_folder.exists():
        shutil.rmtree(disease_folder)

    if deleted:
        return {"success": True, "message": f"Disease '{disease_name}' deleted successfully"}
    raise HTTPException(status_code=404, detail="Disease not found")


@app.get("/diseases/{disease_name}/documents", tags=["Diseases"])
async def get_disease_documents(disease_name: str, _: bool = Depends(verify_api_key)):
    """Get all documents in a disease collection"""
    store = get_vector_store()
    return {"success": True, "documents": store.get_disease_documents(disease_name)}


# ==================== Document Upload ====================

@app.post("/upload/{disease_name}", response_model=DocumentResponse, tags=["Documents"])
async def upload_document(
    disease_name: str,
    file: UploadFile = File(...),
    _: bool = Depends(verify_api_key)
):
    """
    Upload a document to a disease collection

    Supported formats: PDF, JSON, PNG, JPG, JPEG, GIF, MD, TXT

    **n8n Setup:**
    1. Add HTTP Request node
    2. Method: POST
    3. URL: `http://your-server:8000/upload/diabetes`
    4. Body Content Type: Form-Data/Multipart
    5. Add file parameter named 'file'
    """
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Supported: {list(SUPPORTED_EXTENSIONS)}"
        )

    content = await file.read()
    document_id = str(uuid.uuid4())

    disease_folder = UPLOAD_DIR / disease_name
    disease_folder.mkdir(parents=True, exist_ok=True)

    file_path = disease_folder / f"{document_id}_{file.filename}"
    with open(file_path, 'wb') as f:
        f.write(content)

    try:
        processor = get_processor()
        result = processor.process_document(
            file_path=Path(file.filename),
            file_content=content
        )

        store = get_vector_store()
        chunks_added = store.add_document(
            disease_name=disease_name,
            document_id=document_id,
            chunks=result["chunks"],
            filename=file.filename
        )

        return {
            "success": True,
            "document_id": document_id,
            "filename": file.filename,
            "disease": disease_name,
            "chunks_added": chunks_added
        }

    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/{disease_name}/url", tags=["Documents"])
async def upload_from_url(
    disease_name: str,
    url: str = Query(..., description="URL to fetch document from"),
    filename: Optional[str] = Query(None, description="Override filename"),
    _: bool = Depends(verify_api_key)
):
    """
    Upload a document from URL - useful for n8n

    **n8n Setup:**
    1. Add HTTP Request node
    2. Method: POST
    3. URL: `http://your-server:8000/upload/diabetes/url?url=https://example.com/doc.pdf`
    """
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.content

        # Determine filename
        if not filename:
            filename = url.split("/")[-1].split("?")[0]
            if not filename:
                filename = "document"

        file_ext = Path(filename).suffix.lower()
        if not file_ext or file_ext not in SUPPORTED_EXTENSIONS:
            # Try to detect from content-type
            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type:
                filename += ".pdf"
            elif "json" in content_type:
                filename += ".json"
            elif "png" in content_type:
                filename += ".png"
            elif "jpeg" in content_type or "jpg" in content_type:
                filename += ".jpg"
            else:
                filename += ".txt"

        document_id = str(uuid.uuid4())
        disease_folder = UPLOAD_DIR / disease_name
        disease_folder.mkdir(parents=True, exist_ok=True)

        file_path = disease_folder / f"{document_id}_{filename}"
        with open(file_path, 'wb') as f:
            f.write(content)

        processor = get_processor()
        result = processor.process_document(
            file_path=Path(filename),
            file_content=content
        )

        store = get_vector_store()
        chunks_added = store.add_document(
            disease_name=disease_name,
            document_id=document_id,
            chunks=result["chunks"],
            filename=filename
        )

        return {
            "success": True,
            "document_id": document_id,
            "filename": filename,
            "disease": disease_name,
            "chunks_added": chunks_added,
            "source_url": url
        }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")


@app.delete("/documents/{disease_name}/{document_id}", tags=["Documents"])
async def delete_document(
    disease_name: str,
    document_id: str,
    _: bool = Depends(verify_api_key)
):
    """Delete a document from a disease collection"""
    store = get_vector_store()
    deleted = store.delete_document(disease_name, document_id)

    disease_folder = UPLOAD_DIR / disease_name
    if disease_folder.exists():
        for file in disease_folder.glob(f"{document_id}_*"):
            file.unlink()

    if deleted:
        return {"success": True, "message": f"Document '{document_id}' deleted"}
    raise HTTPException(status_code=404, detail="Document not found")


# ==================== RAG Query ====================

@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_rag(request: QueryRequest, _: bool = Depends(verify_api_key)):
    """
    Query the RAG system with full options

    Args:
        disease: Disease collection to query
        query: User question
        use_verification: Enable agentic verification (default: True)
        max_attempts: Max verification attempts (default: 5)
    """
    if request.use_verification:
        verifier = get_agentic_verifier()
        result = verifier.agentic_query(
            disease_name=request.disease,
            query=request.query,
            max_attempts=request.max_attempts
        )
    else:
        engine = get_rag_engine()
        result = engine.query(
            disease_name=request.disease,
            query=request.query
        )
        result["verified"] = False
        result["confidence"] = 0.0
        result["attempts"] = None

    return {"success": True, **result}


@app.post("/query/simple", tags=["Query"])
async def simple_query(
    disease: str = Form(...),
    query: str = Form(...),
    _: bool = Depends(verify_api_key)
):
    """Simple query endpoint for form submissions"""
    engine = get_rag_engine()
    result = engine.query(disease_name=disease, query=query)
    return {"success": True, **result}


# ==================== Frontend ====================

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@app.get("/", tags=["Frontend"])
async def serve_frontend():
    """Serve the frontend"""
    return FileResponse(FRONTEND_DIR / "index.html")


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
