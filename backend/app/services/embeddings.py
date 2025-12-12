from typing import List
import httpx
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy loading for sentence-transformers
_local_model = None


def get_local_embedding_model():
    """Lazy load local embedding model"""
    global _local_model
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading local embedding model: all-MiniLM-L6-v2")
            _local_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Local embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load local embedding model: {e}")
            _local_model = False
    return _local_model if _local_model is not False else None


class EmbeddingService:
    """Manages text embedding generation using remote API or local model"""

    def __init__(self, use_local: bool = None):
        self.api_url = settings.embedding_api_url
        self.model = settings.embedding_model
        self._dimension = settings.embedding_dimension
        self.timeout = httpx.Timeout(60.0, connect=10.0)

        # Determine whether to use local model
        self.use_local = use_local if use_local is not None else settings.use_local_embeddings
        self._local_model = None

        if self.use_local:
            print(f"Embedding service configured: LOCAL (model: all-MiniLM-L6-v2)")
        else:
            print(f"Embedding service configured: {self.api_url} (model: {self.model})")

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        if not texts:
            return []

        if self.use_local:
            return self._encode_local(texts)
        else:
            return self._encode_remote(texts)

    def _encode_local(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local sentence-transformers model"""
        if self._local_model is None:
            self._local_model = get_local_embedding_model()

        if self._local_model is None:
            raise RuntimeError("Local embedding model not available")

        embeddings = self._local_model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def _encode_remote(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings via remote API"""
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
