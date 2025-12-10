from typing import List, Dict, Any, AsyncIterator
import httpx

from app.config import settings


class LLMClient:
    """Client for vLLM API (OpenAI-compatible endpoint)"""

    def __init__(self):
        self.api_url = settings.llm_api_url
        self.model = settings.llm_model
        self.timeout = httpx.Timeout(60.0, connect=10.0)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False
    ) -> str:
        """Generate a response from the LLM"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
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
        """Get a single (non-streaming) response"""
        response = await client.post(self.api_url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _stream_response(
        self,
        client: httpx.AsyncClient,
        payload: Dict[str, Any]
    ) -> str:
        """Get a streaming response and concatenate chunks"""
        full_response = ""

        async with client.stream("POST", self.api_url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        import json
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        full_response += content
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
