"""
Vector Store using ChromaDB with per-disease collections
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
    VECTOR_DB_DIR,
    TOP_K_RETRIEVAL,
    DATA_DIR
)


class VectorStore:
    """Manage vector embeddings per disease using ChromaDB"""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

        # Ensure vector DB directory exists
        VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistent storage
        self.chroma_client = chromadb.PersistentClient(
            path=str(VECTOR_DB_DIR),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Cache for collections
        self._collections = {}

    def _get_collection(self, disease_name: str) -> chromadb.Collection:
        """Get or create collection for a disease"""
        collection_name = self._sanitize_name(disease_name)

        if collection_name not in self._collections:
            self._collections[collection_name] = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"disease": disease_name, "hnsw:space": "cosine"}
            )

        return self._collections[collection_name]

    def _sanitize_name(self, name: str) -> str:
        """Sanitize collection name for ChromaDB"""
        # ChromaDB collection names must be 3-63 chars, alphanumeric with underscores
        sanitized = "".join(c if c.isalnum() else "_" for c in name.lower())
        sanitized = sanitized.strip("_")

        # Ensure minimum length
        if len(sanitized) < 3:
            sanitized = f"disease_{sanitized}"

        # Truncate if too long
        return sanitized[:63]

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding

    def add_document(
        self,
        disease_name: str,
        document_id: str,
        chunks: List[Dict[str, Any]],
        filename: str
    ) -> int:
        """
        Add document chunks to disease-specific collection

        Args:
            disease_name: Name of the disease (collection)
            document_id: Unique document identifier
            chunks: List of text chunks with metadata
            filename: Original filename

        Returns:
            Number of chunks added
        """
        collection = self._get_collection(disease_name)

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for chunk in chunks:
            chunk_id = f"{document_id}_chunk_{chunk['id']}"

            # Generate embedding
            embedding = self.get_embedding(chunk['text'])

            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk['text'])
            metadatas.append({
                "document_id": document_id,
                "filename": filename,
                "chunk_id": chunk['id'],
                "char_count": chunk['char_count'],
                "disease": disease_name
            })

        # Add to collection
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        return len(chunks)

    def search(
        self,
        disease_name: str,
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks in disease collection

        Args:
            disease_name: Name of the disease to search
            query: Search query
            top_k: Number of results to return

        Returns:
            List of matching chunks with scores
        """
        if top_k is None:
            top_k = TOP_K_RETRIEVAL

        collection = self._get_collection(disease_name)

        # Check if collection has documents
        if collection.count() == 0:
            return []

        # Generate query embedding
        query_embedding = self.get_embedding(query)

        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    "id": chunk_id,
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "score": 1 - results['distances'][0][i],  # Convert distance to similarity
                    "distance": results['distances'][0][i]
                })

        return formatted_results

    def delete_document(self, disease_name: str, document_id: str) -> bool:
        """Delete all chunks for a document"""
        collection = self._get_collection(disease_name)

        # Get all chunks for this document
        results = collection.get(
            where={"document_id": document_id}
        )

        if results['ids']:
            collection.delete(ids=results['ids'])
            return True

        return False

    def list_diseases(self) -> List[Dict[str, Any]]:
        """List all disease collections"""
        collections = self.chroma_client.list_collections()
        diseases = []

        for col in collections:
            collection = self.chroma_client.get_collection(col.name)
            diseases.append({
                "name": col.name,
                "display_name": col.metadata.get("disease", col.name) if col.metadata else col.name,
                "document_count": collection.count()
            })

        return diseases

    def get_disease_documents(self, disease_name: str) -> List[Dict[str, Any]]:
        """Get all unique documents in a disease collection"""
        collection = self._get_collection(disease_name)

        # Get all items
        results = collection.get(include=["metadatas"])

        # Extract unique documents
        documents = {}
        for metadata in results['metadatas']:
            doc_id = metadata.get('document_id')
            if doc_id and doc_id not in documents:
                documents[doc_id] = {
                    "document_id": doc_id,
                    "filename": metadata.get('filename', 'Unknown'),
                    "disease": metadata.get('disease', disease_name)
                }

        return list(documents.values())

    def create_disease(self, disease_name: str) -> Dict[str, Any]:
        """Create a new disease collection"""
        collection = self._get_collection(disease_name)

        # Create disease folder for uploads
        disease_folder = DATA_DIR / "uploads" / disease_name
        disease_folder.mkdir(parents=True, exist_ok=True)

        return {
            "name": self._sanitize_name(disease_name),
            "display_name": disease_name,
            "document_count": 0
        }

    def delete_disease(self, disease_name: str) -> bool:
        """Delete a disease collection"""
        collection_name = self._sanitize_name(disease_name)

        try:
            self.chroma_client.delete_collection(collection_name)
            if collection_name in self._collections:
                del self._collections[collection_name]
            return True
        except Exception:
            return False


# Singleton instance
_store = None

def get_vector_store() -> VectorStore:
    """Get or create vector store instance"""
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
