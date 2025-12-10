from typing import List, Dict, Any, Optional
import json
import math
from pathlib import Path

from app.config import settings


class VectorStore:
    """In-memory vector store with persistence (Windows-compatible, no C++ required)"""

    def __init__(self):
        self.data_dir = settings.chroma_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.collections: Dict[str, Dict[str, Any]] = {}
        self._load_all_collections()

    def _get_collection_path(self, collection_name: str) -> Path:
        """Get file path for a collection"""
        return self.data_dir / f"{collection_name}.json"

    def _load_all_collections(self) -> None:
        """Load all existing collections from disk"""
        for file_path in self.data_dir.glob("*.json"):
            collection_name = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.collections[collection_name] = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.collections[collection_name] = {
                    "ids": [],
                    "embeddings": [],
                    "documents": [],
                    "metadatas": []
                }

    def _save_collection(self, collection_name: str) -> None:
        """Save a collection to disk"""
        file_path = self._get_collection_path(collection_name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.collections[collection_name], f, ensure_ascii=False)

    def _get_collection_name(self, notebook_id: str) -> str:
        """Generate collection name for a notebook"""
        return f"nb_{notebook_id[:8]}"

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def get_or_create_collection(self, notebook_id: str) -> str:
        """Get or create a collection for a notebook, returns collection name"""
        collection_name = self._get_collection_name(notebook_id)
        if collection_name not in self.collections:
            self.collections[collection_name] = {
                "ids": [],
                "embeddings": [],
                "documents": [],
                "metadatas": [],
                "notebook_id": notebook_id
            }
            self._save_collection(collection_name)
        return collection_name

    def add_documents(
        self,
        notebook_id: str,
        document_id: str,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """Add document chunks to the vector store"""
        collection_name = self.get_or_create_collection(notebook_id)
        collection = self.collections[collection_name]

        for i, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
            doc_id = f"{document_id}_{i}"
            metadata_copy = metadata.copy()
            metadata_copy["document_id"] = document_id

            collection["ids"].append(doc_id)
            collection["embeddings"].append(embedding)
            collection["documents"].append(text)
            collection["metadatas"].append(metadata_copy)

        self._save_collection(collection_name)

    def query(
        self,
        notebook_id: str,
        query_embedding: List[float],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Query the vector store for similar documents"""
        collection_name = self.get_or_create_collection(notebook_id)
        collection = self.collections[collection_name]

        if not collection["embeddings"]:
            return {"documents": [], "metadatas": [], "distances": []}

        # Calculate similarities
        similarities = []
        for i, embedding in enumerate(collection["embeddings"]):
            sim = self._cosine_similarity(query_embedding, embedding)
            # Convert similarity to distance (ChromaDB uses L2 distance, we use 1-cosine)
            distance = 1.0 - sim
            similarities.append((i, distance))

        # Sort by distance (ascending, lower is more similar)
        similarities.sort(key=lambda x: x[1])

        # Get top_k results
        top_results = similarities[:top_k]

        documents = [collection["documents"][i] for i, _ in top_results]
        metadatas = [collection["metadatas"][i] for i, _ in top_results]
        distances = [dist for _, dist in top_results]

        return {
            "documents": documents,
            "metadatas": metadatas,
            "distances": distances
        }

    def delete_document(self, notebook_id: str, document_id: str) -> None:
        """Delete all chunks for a document"""
        collection_name = self.get_or_create_collection(notebook_id)
        collection = self.collections[collection_name]

        # Find indices to delete (in reverse to avoid index shifting)
        indices_to_delete = []
        for i, metadata in enumerate(collection["metadatas"]):
            if metadata.get("document_id") == document_id:
                indices_to_delete.append(i)

        # Delete in reverse order
        for i in reversed(indices_to_delete):
            collection["ids"].pop(i)
            collection["embeddings"].pop(i)
            collection["documents"].pop(i)
            collection["metadatas"].pop(i)

        self._save_collection(collection_name)

    def delete_notebook(self, notebook_id: str) -> None:
        """Delete entire collection for a notebook"""
        collection_name = self._get_collection_name(notebook_id)
        if collection_name in self.collections:
            del self.collections[collection_name]
            file_path = self._get_collection_path(collection_name)
            if file_path.exists():
                file_path.unlink()

    def get_document_count(self, notebook_id: str) -> int:
        """Get the number of chunks in a notebook's collection"""
        collection_name = self._get_collection_name(notebook_id)
        if collection_name not in self.collections:
            return 0
        return len(self.collections[collection_name]["ids"])
