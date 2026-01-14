"""
Agentic RAG API - FastAPI Backend
Multi-disease RAG system with verification
"""
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import (
    HOST, PORT, DATA_DIR, UPLOAD_DIR,
    SUPPORTED_EXTENSIONS, MAX_VERIFICATION_ATTEMPTS
)
from document_processor import get_processor
from vector_store import get_vector_store
from rag_engine import get_rag_engine
from agentic_verifier import get_agentic_verifier


# Pydantic Models
class QueryRequest(BaseModel):
    disease: str
    query: str
    use_verification: bool = True
    max_attempts: int = MAX_VERIFICATION_ATTEMPTS


class QueryResponse(BaseModel):
    answer: str
    verified: bool
    confidence: float
    references: List[dict]
    disease: str
    attempts: Optional[List[dict]] = None
    warning: Optional[str] = None


class DiseaseCreate(BaseModel):
    name: str


class DiseaseResponse(BaseModel):
    name: str
    display_name: str
    document_count: int


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    disease: str
    chunks_added: int


class HealthResponse(BaseModel):
    status: str
    version: str


# Startup/Shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Agentic RAG API starting...")
    print(f"Data directory: {DATA_DIR}")

    yield

    # Shutdown
    print("Agentic RAG API shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Agentic RAG API",
    description="Multi-disease RAG system with agentic verification",
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


# Health check
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


# Disease Management
@app.get("/diseases", response_model=List[DiseaseResponse])
async def list_diseases():
    """List all disease collections"""
    store = get_vector_store()
    return store.list_diseases()


@app.post("/diseases", response_model=DiseaseResponse)
async def create_disease(disease: DiseaseCreate):
    """Create a new disease collection"""
    store = get_vector_store()
    return store.create_disease(disease.name)


@app.delete("/diseases/{disease_name}")
async def delete_disease(disease_name: str):
    """Delete a disease collection"""
    store = get_vector_store()

    # Delete vector store collection
    deleted = store.delete_disease(disease_name)

    # Delete upload folder
    disease_folder = UPLOAD_DIR / disease_name
    if disease_folder.exists():
        shutil.rmtree(disease_folder)

    if deleted:
        return {"message": f"Disease '{disease_name}' deleted successfully"}
    raise HTTPException(status_code=404, detail="Disease not found")


@app.get("/diseases/{disease_name}/documents")
async def get_disease_documents(disease_name: str):
    """Get all documents in a disease collection"""
    store = get_vector_store()
    return store.get_disease_documents(disease_name)


# Document Upload
@app.post("/upload/{disease_name}", response_model=DocumentResponse)
async def upload_document(
    disease_name: str,
    file: UploadFile = File(...)
):
    """
    Upload a document to a disease collection

    Supported formats: PDF, JSON, PNG, JPG, JPEG, GIF, MD, TXT
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Supported: {SUPPORTED_EXTENSIONS}"
        )

    # Read file content
    content = await file.read()

    # Generate document ID
    document_id = str(uuid.uuid4())

    # Save file to disk
    disease_folder = UPLOAD_DIR / disease_name
    disease_folder.mkdir(parents=True, exist_ok=True)

    file_path = disease_folder / f"{document_id}_{file.filename}"
    with open(file_path, 'wb') as f:
        f.write(content)

    try:
        # Process document
        processor = get_processor()
        result = processor.process_document(
            file_path=Path(file.filename),
            file_content=content
        )

        # Add to vector store
        store = get_vector_store()
        chunks_added = store.add_document(
            disease_name=disease_name,
            document_id=document_id,
            chunks=result["chunks"],
            filename=file.filename
        )

        return {
            "document_id": document_id,
            "filename": file.filename,
            "disease": disease_name,
            "chunks_added": chunks_added
        }

    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{disease_name}/{document_id}")
async def delete_document(disease_name: str, document_id: str):
    """Delete a document from a disease collection"""
    store = get_vector_store()
    deleted = store.delete_document(disease_name, document_id)

    # Delete file from disk
    disease_folder = UPLOAD_DIR / disease_name
    if disease_folder.exists():
        for file in disease_folder.glob(f"{document_id}_*"):
            file.unlink()

    if deleted:
        return {"message": f"Document '{document_id}' deleted successfully"}
    raise HTTPException(status_code=404, detail="Document not found")


# RAG Query
@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Query the RAG system

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

    return result


@app.post("/query/simple")
async def simple_query(
    disease: str = Form(...),
    query: str = Form(...)
):
    """Simple query endpoint for form submissions"""
    engine = get_rag_engine()
    return engine.query(disease_name=disease, query=query)


# Serve frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/")
async def serve_frontend():
    """Serve the frontend"""
    return FileResponse(FRONTEND_DIR / "index.html")


# Mount static files if frontend exists
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
