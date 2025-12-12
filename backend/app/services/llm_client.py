from typing import List, Dict, Any, AsyncIterator
import httpx
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for Ollama API (native format)"""

    def __init__(self):
        # Use Ollama's native API format
        self.base_url = settings.llm_api_url.replace("/v1/chat/completions", "").replace("/api/chat", "")
        self.api_url = f"{self.base_url}/api/chat"
        self.model = settings.llm_model
        self.timeout = httpx.Timeout(600.0, connect=10.0)  # 10 min timeout for LLM with large context on CPU

        logger.info(f"LLM Client configured: {self.api_url} (model: {self.model})")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False
    ) -> str:
        """Generate a response from the LLM using Ollama native API"""
        # Ollama API format
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if stream:
                return await self._stream_response(client, payload)
            else:
                return await self._single_response(client, payload)

    async def _single_response(
        self,
        client: httpx.AsyncClient,
        payload: Dict[str, Any]
    ) -> str:
        """Get a single (non-streaming) response from Ollama"""
        logger.info(f"Sending request to Ollama: {self.api_url}")
        response = await client.post(self.api_url, json=payload)
        response.raise_for_status()

        data = response.json()
        # Ollama native format: {"message": {"role": "assistant", "content": "..."}}
        return data["message"]["content"]

    async def _stream_response(
        self,
        client: httpx.AsyncClient,
        payload: Dict[str, Any]
    ) -> str:
        """Get a streaming response from Ollama and concatenate chunks"""
        import json
        full_response = ""

        async with client.stream("POST", self.api_url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Ollama stream format: {"message": {"content": "..."}, "done": false}
                    content = data.get("message", {}).get("content", "")
                    full_response += content
                    if data.get("done", False):
                        break
                except Exception:
                    continue

        return full_response

    def build_rag_messages(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Build messages for RAG query"""
        # Format context from retrieved chunks
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            filename = chunk.get("filename", "Unknown")
            text = chunk.get("text", "")
            context_parts.append(f"[Source {i}: {filename}]\n{text}")

        context = "\n\n---\n\n".join(context_parts)

        system_prompt = """You are a helpful assistant that answers questions based on the provided documents.
Follow these rules:
1. Only use information from the provided context to answer questions
2. If the context doesn't contain enough information, say so
3. Cite which source documents you used in your answer
4. Be concise but thorough in your responses
5. Use Korean if the user asks in Korean, English if they ask in English"""

        user_prompt = f"""Based on the following documents:

{context}

---

Question: {query}

Please provide a detailed answer based on the documents above."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
