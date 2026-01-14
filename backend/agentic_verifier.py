"""
Agentic Verifier - Multi-step verification with reasoning model
Ensures zero hallucination through iterative refinement
"""
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI
from dataclasses import dataclass

from config import (
    OPENAI_API_KEY,
    REASONING_MODEL,
    MAX_VERIFICATION_ATTEMPTS,
    CONFIDENCE_THRESHOLD,
    TOP_K_RETRIEVAL
)
from rag_engine import get_rag_engine


@dataclass
class VerificationResult:
    """Result of answer verification"""
    is_verified: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]
    reasoning: str


class AgenticVerifier:
    """
    Agentic verification system that validates RAG answers
    and retries with refined queries if confidence is low
    """

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.rag_engine = get_rag_engine()

    def verify_answer(
        self,
        query: str,
        answer: str,
        context: List[Dict[str, Any]],
        disease_name: str
    ) -> VerificationResult:
        """
        Verify an answer using the reasoning model

        Args:
            query: Original user query
            answer: Generated answer to verify
            context: Retrieved context chunks
            disease_name: Disease being queried

        Returns:
            VerificationResult with confidence and issues
        """
        # Build context for verification
        context_str = "\n\n---\n\n".join([
            f"[Chunk {i + 1}]: {chunk.get('text', chunk.get('excerpt', ''))}"
            for i, chunk in enumerate(context)
        ])

        verification_prompt = f"""You are a rigorous medical fact-checker. Your task is to verify if an answer is accurate and well-supported by the provided context.

DISEASE CONTEXT: {disease_name}

ORIGINAL QUESTION: {query}

PROVIDED CONTEXT:
{context_str}

ANSWER TO VERIFY:
{answer}

VERIFICATION TASK:
1. Check if EVERY claim in the answer is directly supported by the context
2. Identify any statements that go beyond the provided context
3. Check for potential hallucinations or unsupported inferences
4. Verify medical terminology and facts are accurate
5. Assess overall answer quality and completeness

Respond with a JSON object:
{{
    "is_verified": true/false,
    "confidence": 0.0-1.0,
    "supported_claims": ["list of claims that are well-supported"],
    "unsupported_claims": ["list of claims not in context"],
    "issues": ["specific problems found"],
    "suggestions": ["how to improve the answer"],
    "reasoning": "detailed explanation of your verification"
}}

Be strict - medical information must be precise."""

        try:
            response = self.client.chat.completions.create(
                model=REASONING_MODEL,
                messages=[
                    {"role": "user", "content": verification_prompt}
                ],
                max_completion_tokens=4096
            )

            # Parse response
            content = response.choices[0].message.content

            # Extract JSON from response
            json_str = self._extract_json(content)
            result = json.loads(json_str)

            return VerificationResult(
                is_verified=result.get("is_verified", False),
                confidence=result.get("confidence", 0.0),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
                reasoning=result.get("reasoning", "")
            )

        except Exception as e:
            # On error, return low confidence
            return VerificationResult(
                is_verified=False,
                confidence=0.0,
                issues=[f"Verification error: {str(e)}"],
                suggestions=["Retry with more specific query"],
                reasoning="Verification failed due to technical error"
            )

    def _extract_json(self, content: str) -> str:
        """Extract JSON from model response"""
        # Try to find JSON in the response
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1

        if start_idx != -1 and end_idx > start_idx:
            return content[start_idx:end_idx]

        raise ValueError("No valid JSON found in response")

    def refine_query(
        self,
        original_query: str,
        previous_answer: str,
        verification_result: VerificationResult,
        disease_name: str,
        attempt: int
    ) -> str:
        """
        Generate a refined query based on verification feedback

        Args:
            original_query: Original user query
            previous_answer: Previous answer that failed verification
            verification_result: Result of verification
            disease_name: Disease context
            attempt: Current attempt number

        Returns:
            Refined query string
        """
        refinement_prompt = f"""Based on a failed answer verification, generate an improved search query.

Original Question: {original_query}
Disease: {disease_name}
Attempt: {attempt} of {MAX_VERIFICATION_ATTEMPTS}

Previous Answer Issues:
{chr(10).join(f"- {issue}" for issue in verification_result.issues)}

Suggestions:
{chr(10).join(f"- {s}" for s in verification_result.suggestions)}

Generate a more specific or differently-phrased query that might retrieve better context.
Focus on the specific information gaps identified.

Return ONLY the refined query, nothing else."""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": refinement_prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )

        return response.choices[0].message.content.strip()

    def agentic_query(
        self,
        disease_name: str,
        query: str,
        max_attempts: int = None
    ) -> Dict[str, Any]:
        """
        Execute agentic RAG with verification loop

        Args:
            disease_name: Disease to query
            query: User question
            max_attempts: Maximum retry attempts (default from config)

        Returns:
            Verified answer with metadata
        """
        if max_attempts is None:
            max_attempts = MAX_VERIFICATION_ATTEMPTS

        attempts = []
        current_query = query
        best_result = None
        best_confidence = 0.0

        for attempt in range(1, max_attempts + 1):
            # Get RAG response
            rag_result = self.rag_engine.query(
                disease_name=disease_name,
                query=current_query,
                top_k=TOP_K_RETRIEVAL + (attempt - 1)  # Increase context on retries
            )

            if rag_result.get("status") == "no_context":
                return {
                    "answer": rag_result["answer"],
                    "verified": False,
                    "confidence": 0.0,
                    "attempts": [{"attempt": 1, "status": "no_context"}],
                    "references": [],
                    "disease": disease_name
                }

            # Verify the answer
            verification = self.verify_answer(
                query=query,  # Always verify against original query
                answer=rag_result["answer"],
                context=rag_result.get("retrieved_chunks", []),
                disease_name=disease_name
            )

            attempt_record = {
                "attempt": attempt,
                "query_used": current_query,
                "confidence": verification.confidence,
                "is_verified": verification.is_verified,
                "issues": verification.issues,
                "reasoning": verification.reasoning[:500]  # Truncate for response
            }
            attempts.append(attempt_record)

            # Track best result
            if verification.confidence > best_confidence:
                best_confidence = verification.confidence
                best_result = {
                    "answer": rag_result["answer"],
                    "references": rag_result["references"],
                    "retrieved_chunks": rag_result.get("retrieved_chunks", []),
                    "verification": verification
                }

            # Check if verified with high confidence
            if verification.is_verified and verification.confidence >= CONFIDENCE_THRESHOLD:
                return {
                    "answer": rag_result["answer"],
                    "verified": True,
                    "confidence": verification.confidence,
                    "attempts": attempts,
                    "references": rag_result["references"],
                    "disease": disease_name,
                    "verification_reasoning": verification.reasoning,
                    "final_attempt": attempt
                }

            # Refine query for next attempt if not last
            if attempt < max_attempts:
                current_query = self.refine_query(
                    original_query=query,
                    previous_answer=rag_result["answer"],
                    verification_result=verification,
                    disease_name=disease_name,
                    attempt=attempt
                )

        # Return best result after all attempts
        if best_result:
            return {
                "answer": best_result["answer"],
                "verified": best_result["verification"].is_verified,
                "confidence": best_confidence,
                "attempts": attempts,
                "references": best_result["references"],
                "disease": disease_name,
                "verification_reasoning": best_result["verification"].reasoning,
                "warning": f"Answer confidence ({best_confidence:.2f}) below threshold ({CONFIDENCE_THRESHOLD}). Please verify independently.",
                "final_attempt": len(attempts)
            }

        return {
            "answer": "Unable to generate a verified answer after multiple attempts.",
            "verified": False,
            "confidence": 0.0,
            "attempts": attempts,
            "references": [],
            "disease": disease_name,
            "error": "All verification attempts failed"
        }


# Singleton instance
_verifier = None

def get_agentic_verifier() -> AgenticVerifier:
    """Get or create agentic verifier instance"""
    global _verifier
    if _verifier is None:
        _verifier = AgenticVerifier()
    return _verifier
