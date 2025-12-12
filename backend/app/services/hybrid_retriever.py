from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging
from collections import defaultdict

from app.config import settings
from .vector_store import VectorStore
from .bm25_store import BM25Store, BM25SearchResult
from .graph_store import GraphStore, GraphSearchResult
from .embeddings import EmbeddingService
from .entity_extractor import EntityExtractor
from .reranker import Reranker, RankedResult

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Final retrieval result from HybridRetriever"""
    text: str
    metadata: Dict[str, Any]
    score: float
    sources: List[str] = field(default_factory=list)  # ['vector', 'bm25', 'graph']
    entities: List[Dict[str, Any]] = field(default_factory=list)


class HybridRetriever:
    """
    Hybrid retriever combining:
    1. Dense vector search (semantic similarity)
    2. Sparse BM25 search (keyword matching)
    3. Graph traversal (entity relationships)

    Uses Reciprocal Rank Fusion (RRF) to combine results and
    Cross-Encoder reranking for final ranking.
    """

    def __init__(
        self,
        vector_store: VectorStore = None,
        bm25_store: BM25Store = None,
        graph_store: GraphStore = None,
        embedding_service: EmbeddingService = None,
        entity_extractor: EntityExtractor = None,
        reranker: Reranker = None
    ):
        self.vector_store = vector_store or VectorStore()
        self.bm25_store = bm25_store or BM25Store()
        self.graph_store = graph_store or GraphStore()
        self.embedding_service = embedding_service or EmbeddingService()
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.reranker = reranker or Reranker()

        self.rrf_k = settings.rrf_k

    async def retrieve(
        self,
        notebook_id: str,
        query: str,
        top_k: int = None,
        use_vector: bool = True,
        use_bm25: bool = None,
        use_graph: bool = None,
        use_reranker: bool = None
    ) -> List[RetrievalResult]:
        """
        Execute hybrid retrieval combining multiple search methods.

        Args:
            notebook_id: The notebook to search in
            query: The search query
            top_k: Number of results to return
            use_vector: Whether to use vector search
            use_bm25: Whether to use BM25 search
            use_graph: Whether to use graph search
            use_reranker: Whether to apply reranking

        Returns:
            List of RetrievalResult sorted by relevance
        """
        top_k = top_k or settings.top_k
        use_bm25 = use_bm25 if use_bm25 is not None else settings.use_bm25_search
        use_graph = use_graph if use_graph is not None else settings.use_graph_search
        use_reranker = use_reranker if use_reranker is not None else settings.use_reranker

        # Collect results from all sources
        all_results: Dict[str, Dict[str, Any]] = {}  # text_hash -> result info

        # 1. Vector Search
        if use_vector:
            vector_results = await self._vector_search(notebook_id, query, top_k * 2)
            self._merge_results(all_results, vector_results, "vector")

        # 2. BM25 Search
        if use_bm25:
            bm25_results = self._bm25_search(notebook_id, query, top_k * 2)
            self._merge_results(all_results, bm25_results, "bm25")

        # 3. Graph Search
        graph_entities = []
        if use_graph and self.graph_store.is_connected:
            graph_results = self._graph_search(notebook_id, query, top_k)
            self._merge_graph_results(all_results, graph_results)
            graph_entities = [
                {"name": r.entity_name, "type": r.entity_type, "related": r.related_entities}
                for r in graph_results
            ]

        if not all_results:
            return []

        # 4. Reciprocal Rank Fusion
        fused_results = self._rrf_fusion(all_results)

        # 5. Reranking
        if use_reranker and self.reranker.is_available:
            documents = [
                {
                    "text": r["text"],
                    "metadata": r["metadata"],
                    "score": r["rrf_score"],
                    "source": ",".join(r["sources"])
                }
                for r in fused_results
            ]
            reranked = self.reranker.rerank(query, documents, top_k=top_k)

            return [
                RetrievalResult(
                    text=r.text,
                    metadata=r.metadata,
                    score=r.rerank_score,
                    sources=r.source.split(","),
                    entities=graph_entities if "graph" in r.source else []
                )
                for r in reranked
            ]
        else:
            # Return RRF results without reranking
            return [
                RetrievalResult(
                    text=r["text"],
                    metadata=r["metadata"],
                    score=r["rrf_score"],
                    sources=r["sources"],
                    entities=graph_entities if "graph" in r["sources"] else []
                )
                for r in fused_results[:top_k]
            ]

    async def _vector_search(
        self,
        notebook_id: str,
        query: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Execute vector similarity search"""
        try:
            query_embedding = self.embedding_service.encode_single(query)

            results = self.vector_store.query(
                notebook_id=notebook_id,
                query_embedding=query_embedding,
                top_k=top_k
            )

            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            distances = results.get("distances", [])

            return [
                {
                    "text": doc,
                    "metadata": meta,
                    "score": max(0, 1 - dist),  # Convert distance to similarity
                    "rank": i + 1
                }
                for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances))
            ]
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _bm25_search(
        self,
        notebook_id: str,
        query: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Execute BM25 keyword search"""
        try:
            results = self.bm25_store.search(
                notebook_id=notebook_id,
                query=query,
                top_k=top_k
            )

            # Normalize BM25 scores
            if results:
                max_score = max(r.score for r in results) or 1.0
                return [
                    {
                        "text": r.text,
                        "metadata": r.metadata,
                        "score": r.score / max_score,
                        "rank": i + 1
                    }
                    for i, r in enumerate(results)
                ]
            return []
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    def _graph_search(
        self,
        notebook_id: str,
        query: str,
        top_k: int
    ) -> List[GraphSearchResult]:
        """Execute graph traversal search"""
        try:
            # Extract potential entities from query
            query_entities = self.entity_extractor.extract_entities_from_query(query)

            if query_entities:
                # Search by extracted entities
                return self.graph_store.search_by_entities(
                    notebook_id=notebook_id,
                    query_entities=query_entities,
                    k_hop=settings.graph_k_hop,
                    top_k=top_k
                )
            else:
                # Fuzzy search by query terms
                return self.graph_store.search_by_query(
                    notebook_id=notebook_id,
                    query=query,
                    top_k=top_k
                )
        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return []

    def _merge_results(
        self,
        all_results: Dict[str, Dict[str, Any]],
        new_results: List[Dict[str, Any]],
        source: str
    ) -> None:
        """Merge new results into the result pool"""
        for result in new_results:
            text = result["text"]
            # Use first 100 chars as key to handle duplicates
            key = text[:100].lower().strip()

            if key in all_results:
                # Update existing result
                all_results[key]["sources"].append(source)
                all_results[key]["ranks"][source] = result["rank"]
                all_results[key]["scores"][source] = result["score"]
            else:
                # Add new result
                all_results[key] = {
                    "text": text,
                    "metadata": result["metadata"],
                    "sources": [source],
                    "ranks": {source: result["rank"]},
                    "scores": {source: result["score"]}
                }

    def _merge_graph_results(
        self,
        all_results: Dict[str, Dict[str, Any]],
        graph_results: List[GraphSearchResult]
    ) -> None:
        """Merge graph search results into the result pool"""
        for i, result in enumerate(graph_results):
            if not result.context_text:
                continue

            text = result.context_text
            key = text[:100].lower().strip()

            if key in all_results:
                all_results[key]["sources"].append("graph")
                all_results[key]["ranks"]["graph"] = i + 1
                all_results[key]["scores"]["graph"] = result.relevance_score
                all_results[key]["entities"] = result.related_entities
            else:
                all_results[key] = {
                    "text": text,
                    "metadata": {
                        "entity": result.entity_name,
                        "entity_type": result.entity_type
                    },
                    "sources": ["graph"],
                    "ranks": {"graph": i + 1},
                    "scores": {"graph": result.relevance_score},
                    "entities": result.related_entities
                }

    def _rrf_fusion(
        self,
        all_results: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply Reciprocal Rank Fusion to combine results from multiple sources.

        RRF score = sum(1 / (k + rank_i)) for each source i
        """
        for key, result in all_results.items():
            rrf_score = 0.0
            for source, rank in result["ranks"].items():
                rrf_score += 1.0 / (self.rrf_k + rank)
            result["rrf_score"] = rrf_score

        # Sort by RRF score
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )

        return sorted_results

    def get_retrieval_stats(self, notebook_id: str) -> Dict[str, Any]:
        """Get statistics about the retrieval indexes"""
        stats = {
            "vector_store": {
                "documents": self.vector_store.get_document_count(notebook_id)
            },
            "bm25_store": self.bm25_store.get_statistics(notebook_id),
            "graph_store": self.graph_store.get_statistics(notebook_id) if self.graph_store.is_connected else {"connected": False}
        }
        return stats
