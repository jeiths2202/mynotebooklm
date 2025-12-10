from typing import List
import httpx

from app.config import settings


class EmbeddingService:
    """Manages text embedding generation using remote API (OpenAI-compatible)"""

    def __init__(self):
        self.api_url = settings.embedding_api_url
        self.model = settings.embedding_model
        self._dimension = settings.embedding_dimension
        self.timeout = httpx.Timeout(60.0, connect=10.0)
        print(f"Embedding service configured: {self.api_url} (model: {self.model})")

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts via remote API"""
        if not texts:
            return []

        # OpenAI-compatible embeddings API format
        payload = {
            "model": self.model,
            "input": texts
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.api_url, json=payload)
            response.raise_for_status()

            data = response.json()

            # Extract embeddings from response
            # OpenAI format: {"data": [{"embedding": [...], "index": 0}, ...]}
            embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
            return embeddings

    def encode_single(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embeddings = self.encode([text])
        return embeddings[0] if embeddings else []

    async def encode_async(self, texts: List[str]) -> List[List[float]]:
        """Async version of encode for better performance"""
        if not texts:
            return []

        payload = {
            "model": self.model,
            "input": texts
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.api_url, json=payload)
            response.raise_for_status()

            data = response.json()
            embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
            return embeddings

    async def encode_single_async(self, text: str) -> List[float]:
        """Async version of encode_single"""
        embeddings = await self.encode_async([text])
        return embeddings[0] if embeddings else []

    @property
    def dimension(self) -> int:
        """Return the embedding dimension"""
        return self._dimension
