from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy loading of sentence-transformers to avoid slow startup
_reranker_model = None


def get_reranker_model():
    """Lazy load the reranker model"""
    global _reranker_model
    if _reranker_model is None:
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading reranker model: {settings.reranker_model}")
            _reranker_model = CrossEncoder(settings.reranker_model)
            logger.info("Reranker model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            _reranker_model = False  # Mark as failed
    return _reranker_model if _reranker_model is not False else None


@dataclass
class RankedResult:
    """Result after reranking"""
    text: str
    metadata: Dict[str, Any]
    original_score: float
    rerank_score: float
    source: str  # 'vector', 'bm25', 'graph'


class Reranker:
    """Cross-Encoder based reranker for HybridRAG"""

    def __init__(self):
        self._model = None
        self._available = None

    @property
    def is_available(self) -> bool:
        """Check if reranker is available"""
        if self._available is None:
            self._model = get_reranker_model()
            self._available = self._model is not None
        return self._available

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[RankedResult]:
        """
        Rerank documents using Cross-Encoder

        Args:
            query: The search query
            documents: List of dicts with 'text', 'metadata', 'score', 'source' keys
            top_k: Number of top results to return

        Returns:
            List of RankedResult sorted by rerank score
        """
        if not documents:
            return []

        if not self.is_available or not settings.use_reranker:
            # Fallback: return documents sorted by original score
            logger.warning("Reranker not available, using original scores")
            results = [
                RankedResult(
                    text=doc["text"],
                    metadata=doc.get("metadata", {}),
                    original_score=doc.get("score", 0.0),
                    rerank_score=doc.get("score", 0.0),
                    source=doc.get("source", "unknown")
                )
                for doc in documents
            ]
            results.sort(key=lambda x: x.rerank_score, reverse=True)
            return results[:top_k]

        try:
            # Prepare query-document pairs for cross-encoder
            pairs = [(query, doc["text"]) for doc in documents]

            # Get rerank scores
            scores = self._model.predict(pairs)

            # Normalize scores to 0-1 range
            min_score = min(scores)
            max_score = max(scores)
            score_range = max_score - min_score if max_score != min_score else 1.0

            results = []
            for doc, score in zip(documents, scores):
                normalized_score = (score - min_score) / score_range
                results.append(RankedResult(
                    text=doc["text"],
                    metadata=doc.get("metadata", {}),
                    original_score=doc.get("score", 0.0),
                    rerank_score=float(normalized_score),
                    source=doc.get("source", "unknown")
                ))

            # Sort by rerank score
            results.sort(key=lambda x: x.rerank_score, reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            # Fallback to original scores
            results = [
                RankedResult(
                    text=doc["text"],
                    metadata=doc.get("metadata", {}),
                    original_score=doc.get("score", 0.0),
                    rerank_score=doc.get("score", 0.0),
                    source=doc.get("source", "unknown")
                )
                for doc in documents
            ]
            results.sort(key=lambda x: x.rerank_score, reverse=True)
            return results[:top_k]

    def rerank_with_fusion_score(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        fusion_weight: float = 0.7
    ) -> List[RankedResult]:
        """
        Rerank documents and combine rerank score with original fusion score

        Args:
            query: The search query
            documents: List of dicts with 'text', 'metadata', 'score', 'source' keys
            top_k: Number of top results to return
            fusion_weight: Weight for rerank score (1-fusion_weight for original)

        Returns:
            List of RankedResult with combined scores
        """
        reranked = self.rerank(query, documents, top_k=len(documents))

        # Combine rerank score with original score
        for result in reranked:
            combined = (fusion_weight * result.rerank_score +
                       (1 - fusion_weight) * result.original_score)
            result.rerank_score = combined

        # Re-sort by combined score
        reranked.sort(key=lambda x: x.rerank_score, reverse=True)
        return reranked[:top_k]


class RerankerSimple:
    """Simple reranker fallback using keyword overlap"""

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[RankedResult]:
        """Rerank using simple keyword overlap scoring"""
        query_words = set(query.lower().split())

        results = []
        for doc in documents:
            text = doc.get("text", "")
            doc_words = set(text.lower().split())

            # Calculate overlap score
            overlap = len(query_words.intersection(doc_words))
            overlap_score = overlap / max(len(query_words), 1)

            # Combine with original score
            original_score = doc.get("score", 0.0)
            combined_score = 0.5 * overlap_score + 0.5 * original_score

            results.append(RankedResult(
                text=text,
                metadata=doc.get("metadata", {}),
                original_score=original_score,
                rerank_score=combined_score,
                source=doc.get("source", "unknown")
            ))

        results.sort(key=lambda x: x.rerank_score, reverse=True)
        return results[:top_k]

    @property
    def is_available(self) -> bool:
        return True
