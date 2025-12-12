from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import re
from pathlib import Path
import logging

from rank_bm25 import BM25Okapi

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BM25SearchResult:
    """Result from BM25 search"""
    text: str
    metadata: Dict[str, Any]
    score: float


class BM25Store:
    """BM25-based sparse search store for HybridRAG"""

    def __init__(self):
        self.data_dir = settings.bm25_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.collections: Dict[str, Dict[str, Any]] = {}
        self._bm25_indexes: Dict[str, BM25Okapi] = {}
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
                    self._rebuild_bm25_index(collection_name)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load BM25 collection {collection_name}: {e}")
                self.collections[collection_name] = {
                    "documents": [],
                    "metadatas": [],
                    "tokenized_docs": []
                }

    def _save_collection(self, collection_name: str) -> None:
        """Save a collection to disk"""
        file_path = self._get_collection_path(collection_name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.collections[collection_name], f, ensure_ascii=False)

    def _get_collection_name(self, notebook_id: str) -> str:
        """Generate collection name for a notebook"""
        return f"bm25_nb_{notebook_id[:8]}"

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25"""
        # Convert to lowercase and split on non-alphanumeric characters
        text = text.lower()
        # Keep Korean characters along with alphanumeric
        tokens = re.findall(r'[\w가-힣]+', text)
        # Filter out very short tokens
        tokens = [t for t in tokens if len(t) > 1]
        return tokens

    def _rebuild_bm25_index(self, collection_name: str) -> None:
        """Rebuild BM25 index for a collection"""
        collection = self.collections.get(collection_name)
        if not collection or not collection.get("tokenized_docs"):
            self._bm25_indexes[collection_name] = None
            return

        tokenized_docs = collection["tokenized_docs"]
        if tokenized_docs:
            self._bm25_indexes[collection_name] = BM25Okapi(tokenized_docs)
        else:
            self._bm25_indexes[collection_name] = None

    def get_or_create_collection(self, notebook_id: str) -> str:
        """Get or create a collection for a notebook"""
        collection_name = self._get_collection_name(notebook_id)
        if collection_name not in self.collections:
            self.collections[collection_name] = {
                "notebook_id": notebook_id,
                "documents": [],
                "metadatas": [],
                "tokenized_docs": []
            }
            self._bm25_indexes[collection_name] = None
            self._save_collection(collection_name)
        return collection_name

    def add_documents(
        self,
        notebook_id: str,
        document_id: str,
        texts: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """Add documents to the BM25 store"""
        collection_name = self.get_or_create_collection(notebook_id)
        collection = self.collections[collection_name]

        for text, metadata in zip(texts, metadatas):
            metadata_copy = metadata.copy()
            metadata_copy["document_id"] = document_id

            tokens = self._tokenize(text)

            collection["documents"].append(text)
            collection["metadatas"].append(metadata_copy)
            collection["tokenized_docs"].append(tokens)

        # Rebuild BM25 index
        self._rebuild_bm25_index(collection_name)
        self._save_collection(collection_name)

    def search(
        self,
        notebook_id: str,
        query: str,
        top_k: int = 5
    ) -> List[BM25SearchResult]:
        """Search documents using BM25"""
        collection_name = self.get_or_create_collection(notebook_id)
        collection = self.collections[collection_name]
        bm25_index = self._bm25_indexes.get(collection_name)

        if not bm25_index or not collection["documents"]:
            return []

        # Tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Get BM25 scores
        scores = bm25_index.get_scores(query_tokens)

        # Get top-k results
        scored_docs = list(enumerate(scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        top_results = scored_docs[:top_k]

        results = []
        for idx, score in top_results:
            if score > 0:  # Only include documents with positive scores
                results.append(BM25SearchResult(
                    text=collection["documents"][idx],
                    metadata=collection["metadatas"][idx],
                    score=float(score)
                ))

        return results

    def delete_document(self, notebook_id: str, document_id: str) -> None:
        """Delete all chunks for a document"""
        collection_name = self._get_collection_name(notebook_id)
        if collection_name not in self.collections:
            return

        collection = self.collections[collection_name]

        # Find indices to delete (in reverse order)
        indices_to_delete = []
        for i, metadata in enumerate(collection["metadatas"]):
            if metadata.get("document_id") == document_id:
                indices_to_delete.append(i)

        # Delete in reverse order
        for i in reversed(indices_to_delete):
            collection["documents"].pop(i)
            collection["metadatas"].pop(i)
            collection["tokenized_docs"].pop(i)

        # Rebuild BM25 index
        self._rebuild_bm25_index(collection_name)
        self._save_collection(collection_name)

    def delete_notebook(self, notebook_id: str) -> None:
        """Delete entire collection for a notebook"""
        collection_name = self._get_collection_name(notebook_id)
        if collection_name in self.collections:
            del self.collections[collection_name]
            if collection_name in self._bm25_indexes:
                del self._bm25_indexes[collection_name]
            file_path = self._get_collection_path(collection_name)
            if file_path.exists():
                file_path.unlink()

    def get_document_count(self, notebook_id: str) -> int:
        """Get the number of documents in a notebook's collection"""
        collection_name = self._get_collection_name(notebook_id)
        if collection_name not in self.collections:
            return 0
        return len(self.collections[collection_name]["documents"])

    def get_statistics(self, notebook_id: str) -> Dict[str, Any]:
        """Get statistics for a notebook's BM25 index"""
        collection_name = self._get_collection_name(notebook_id)
        if collection_name not in self.collections:
            return {"documents": 0, "avg_doc_length": 0, "total_tokens": 0}

        collection = self.collections[collection_name]
        tokenized_docs = collection.get("tokenized_docs", [])

        if not tokenized_docs:
            return {"documents": 0, "avg_doc_length": 0, "total_tokens": 0}

        total_tokens = sum(len(doc) for doc in tokenized_docs)
        avg_length = total_tokens / len(tokenized_docs) if tokenized_docs else 0

        return {
            "documents": len(tokenized_docs),
            "avg_doc_length": round(avg_length, 2),
            "total_tokens": total_tokens
        }
