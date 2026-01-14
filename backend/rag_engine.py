"""
RAG Engine for retrieval and answer generation
"""
from typing import List, Dict, Any, Optional
from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    GENERATION_MODEL,
    TOP_K_RETRIEVAL
)
from vector_store import get_vector_store


class RAGEngine:
    """Retrieval-Augmented Generation Engine"""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.vector_store = get_vector_store()

    def retrieve(
        self,
        disease_name: str,
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context from vector store

        Args:
            disease_name: Disease to search in
            query: User query
            top_k: Number of chunks to retrieve

        Returns:
            List of relevant chunks with metadata
        """
        if top_k is None:
            top_k = TOP_K_RETRIEVAL

        results = self.vector_store.search(
            disease_name=disease_name,
            query=query,
            top_k=top_k
        )

        return results

    def generate_answer(
        self,
        query: str,
        context: List[Dict[str, Any]],
        disease_name: str,
        additional_instructions: str = None
    ) -> Dict[str, Any]:
        """
        Generate answer based on retrieved context

        Args:
            query: User query
            context: Retrieved chunks
            disease_name: Disease context
            additional_instructions: Extra guidance for generation

        Returns:
            Generated answer with references
        """
        # Build context string with references
        context_parts = []
        for i, chunk in enumerate(context):
            source = chunk['metadata'].get('filename', 'Unknown')
            context_parts.append(f"[Source {i + 1}: {source}]\n{chunk['text']}")

        context_str = "\n\n---\n\n".join(context_parts)

        system_prompt = f"""You are a precise medical information assistant specialized in {disease_name}.

CRITICAL RULES:
1. ONLY use information explicitly stated in the provided context
2. If the answer is not in the context, say "I cannot find this information in the provided documents"
3. NEVER make assumptions or add information from general knowledge
4. Always cite sources using [Source N] format
5. Be precise and factual - medical accuracy is critical
6. If information is partial or unclear, acknowledge the limitation

{additional_instructions or ''}"""

        user_prompt = f"""Context from {disease_name} documents:

{context_str}

---

Question: {query}

Please provide a precise answer based ONLY on the context above. Include [Source N] citations for every fact you state."""

        response = self.client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Low temperature for factual accuracy
            max_tokens=2048
        )

        answer = response.choices[0].message.content

        # Extract references
        references = self._extract_references(answer, context)

        return {
            "answer": answer,
            "references": references,
            "context_used": len(context),
            "disease": disease_name
        }

    def _extract_references(
        self,
        answer: str,
        context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract and format references from the answer"""
        references = []
        seen_sources = set()

        for i, chunk in enumerate(context):
            source_marker = f"[Source {i + 1}]"
            if source_marker in answer and i not in seen_sources:
                seen_sources.add(i)
                references.append({
                    "source_id": i + 1,
                    "filename": chunk['metadata'].get('filename', 'Unknown'),
                    "excerpt": chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text'],
                    "relevance_score": chunk.get('score', 0)
                })

        return references

    def query(
        self,
        disease_name: str,
        query: str,
        top_k: int = None
    ) -> Dict[str, Any]:
        """
        Full RAG pipeline: retrieve and generate

        Args:
            disease_name: Disease to query
            query: User question
            top_k: Number of chunks to retrieve

        Returns:
            Complete response with answer and references
        """
        # Retrieve relevant context
        context = self.retrieve(disease_name, query, top_k)

        if not context:
            return {
                "answer": "No documents found for this disease. Please upload relevant documents first.",
                "references": [],
                "context_used": 0,
                "disease": disease_name,
                "status": "no_context"
            }

        # Generate answer
        result = self.generate_answer(query, context, disease_name)
        result["status"] = "success"
        result["retrieved_chunks"] = [
            {
                "text": c['text'][:300] + "..." if len(c['text']) > 300 else c['text'],
                "score": c.get('score', 0),
                "filename": c['metadata'].get('filename', 'Unknown')
            }
            for c in context
        ]

        return result


# Singleton instance
_engine = None

def get_rag_engine() -> RAGEngine:
    """Get or create RAG engine instance"""
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine
