"""Main RAG Pipeline - Orchestrates retrieval and generation."""

import logging
import json
import time
import httpx
from typing import Optional
from dataclasses import dataclass

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from document retrieval."""
    document_ids: list[str]
    documents: list[str]
    scores: list[float]
    metadata: list[dict]


@dataclass
class RAGResponse:
    """Final RAG response with answer and sources."""
    answer: str
    sources: list[dict]
    confidence: float
    latency_ms: float


class RAGPipeline:
    """Main RAG orchestration class."""

    def __init__(self):
        """Initialize RAG pipeline components."""
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.llm_model = settings.LLM_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL
        self.client = httpx.AsyncClient()
        logger.info(f"RAG Pipeline initialized with {self.llm_model}")

    async def query(
        self,
        tenant_id: str,
        query: str,
        top_k: int = settings.TOP_K_DOCUMENTS,
    ) -> RAGResponse:
        """Execute RAG query: retrieve documents and generate answer."""
        start_time = time.time()

        try:
            # Load sample data from prepared chunks
            try:
                with open("data/processed/rag_training_data.jsonl", "r") as f:
                    chunks = [json.loads(line) for line in f if line.strip()]
            except FileNotFoundError:
                # Fallback: provide default response
                return RAGResponse(
                    answer="No training data found. Please run: python scripts/download_training_data.py && python scripts/chunk_and_prepare_data.py",
                    sources=[],
                    confidence=0.0,
                    latency_ms=int((time.time() - start_time) * 1000)
                )

            if not chunks:
                return RAGResponse(
                    answer="No documents indexed. Please prepare training data first.",
                    sources=[],
                    confidence=0.0,
                    latency_ms=int((time.time() - start_time) * 1000)
                )

            # Simple keyword matching for demonstration (no vector DB needed for MVP)
            relevant_chunks = self._retrieve_by_keywords(query, chunks, top_k)

            if not relevant_chunks:
                relevant_chunks = chunks[:min(top_k, len(chunks))]

            # Format context from retrieved chunks
            context = "\n\n".join([
                f"Source: {chunk.get('source', 'Unknown')}\n{chunk.get('text', '')}"
                for chunk in relevant_chunks
            ])

            # Generate answer using Ollama
            answer = await self._generate_answer(query, context)

            # Calculate confidence based on relevance
            confidence = min(0.85, 0.5 + (len(relevant_chunks) / (top_k * 2)))

            # Format sources
            sources = [
                {
                    "document_id": chunk.get("document_id", "unknown"),
                    "document_name": chunk.get("source", "Unknown Source"),
                    "chunk_id": chunk.get("chunk_id", 0),
                    "score": 0.9,
                    "text": chunk.get("text", "")[:200]
                }
                for chunk in relevant_chunks
            ]

            latency_ms = int((time.time() - start_time) * 1000)

            return RAGResponse(
                answer=answer,
                sources=sources,
                confidence=confidence,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error(f"Error in RAG query: {str(e)}")
            raise

    def _retrieve_by_keywords(self, query: str, chunks: list, top_k: int) -> list:
        """Simple keyword-based retrieval."""
        query_words = set(query.lower().split())

        scored_chunks = []
        for chunk in chunks:
            text = chunk.get("text", "").lower()
            score = sum(1 for word in query_words if word in text)
            if score > 0:
                scored_chunks.append((chunk, score))

        # Sort by score and return top-k
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, score in scored_chunks[:top_k]]

    async def _generate_answer(self, query: str, context: str) -> str:
        """Generate answer using Ollama."""
        prompt = f"""Based on the following documents, answer the user's question.

Documents:
{context}

Question: {query}

Answer:"""

        try:
            response = await self.client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": settings.LLM_TEMPERATURE,
                    "top_p": settings.LLM_TOP_P,
                },
                timeout=30.0
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Unable to generate answer").strip()
            else:
                return f"Error from LLM: {response.status_code}"

        except httpx.ConnectError:
            return "Error: Cannot connect to Ollama. Make sure it's running at " + self.ollama_url
        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            return f"Error generating answer: {str(e)}"

    async def retrieve(
        self,
        tenant_id: str,
        query: str,
        top_k: int = settings.TOP_K_DOCUMENTS,
    ) -> RetrievalResult:
        """Retrieve top-k documents matching query."""
        raise NotImplementedError("Use query() instead")

    async def generate(
        self,
        query: str,
        context: str,
        sources: list[dict],
    ) -> str:
        """Generate answer from context using LLM."""
        return await self._generate_answer(query, context)
