from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from app.config import settings
from app.models import MessageSource
from .document_processor import DocumentProcessor
from .embeddings import EmbeddingService
from .vector_store import VectorStore
from .bm25_store import BM25Store
from .graph_store import GraphStore, Entity, Relation
from .entity_extractor import EntityExtractor
from .hybrid_retriever import HybridRetriever
from .reranker import Reranker
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class RAGService:
    """Orchestrates the HybridRAG pipeline: document processing, retrieval, and generation"""

    def __init__(
        self,
        document_processor: DocumentProcessor = None,
        embedding_service: EmbeddingService = None,
        vector_store: VectorStore = None,
        bm25_store: BM25Store = None,
        graph_store: GraphStore = None,
        entity_extractor: EntityExtractor = None,
        reranker: Reranker = None,
        hybrid_retriever: HybridRetriever = None,
        llm_client: LLMClient = None
    ):
        self.document_processor = document_processor or DocumentProcessor()
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.bm25_store = bm25_store or BM25Store()
        self.graph_store = graph_store or GraphStore()
        self.entity_extractor = entity_extractor or EntityExtractor()
        self.reranker = reranker or Reranker()
        self.llm_client = llm_client or LLMClient()

        # Initialize hybrid retriever with all components
        self.hybrid_retriever = hybrid_retriever or HybridRetriever(
            vector_store=self.vector_store,
            bm25_store=self.bm25_store,
            graph_store=self.graph_store,
            embedding_service=self.embedding_service,
            entity_extractor=self.entity_extractor,
            reranker=self.reranker
        )

        self.use_hybrid = settings.use_hybrid_rag

    async def process_document(
        self,
        notebook_id: str,
        document_id: str,
        file_path: Path
    ) -> int:
        """
        Process a document and add to all stores (vector, BM25, graph).
        Returns chunk count.
        """
        # Extract and chunk text
        chunks = self.document_processor.process_file(file_path, document_id)

        if not chunks:
            return 0

        texts = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        # 1. Generate embeddings and store in vector store
        embeddings = self.embedding_service.encode(texts)
        self.vector_store.add_documents(
            notebook_id=notebook_id,
            document_id=document_id,
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )

        # 2. Add to BM25 store
        if settings.use_bm25_search:
            self.bm25_store.add_documents(
                notebook_id=notebook_id,
                document_id=document_id,
                texts=texts,
                metadatas=metadatas
            )

        # 3. Extract entities and add to graph store
        if settings.use_graph_search and self.graph_store.is_connected:
            await self._process_entities(notebook_id, document_id, texts)

        return len(chunks)

    async def _process_entities(
        self,
        notebook_id: str,
        document_id: str,
        texts: List[str]
    ) -> None:
        """Extract entities from texts and store in graph"""
        try:
            all_entities: List[Entity] = []
            all_relations: List[Relation] = []

            # Process chunks in batches to avoid overwhelming the LLM
            batch_size = 3
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                combined_text = "\n\n".join(batch)

                result = await self.entity_extractor.extract(combined_text)
                all_entities.extend(result.entities)
                all_relations.extend(result.relations)

            # Deduplicate entities by name
            unique_entities = {}
            for entity in all_entities:
                key = entity.name.lower()
                if key not in unique_entities:
                    unique_entities[key] = entity

            # Store in graph
            self.graph_store.add_entities(
                notebook_id=notebook_id,
                document_id=document_id,
                entities=list(unique_entities.values()),
                relations=all_relations,
                chunk_texts=texts[:10]  # Store first 10 chunks for context
            )

            logger.info(
                f"Extracted {len(unique_entities)} entities and "
                f"{len(all_relations)} relations from document {document_id}"
            )

        except Exception as e:
            logger.error(f"Entity extraction failed for document {document_id}: {e}")

    async def query(
        self,
        notebook_id: str,
        query: str,
        top_k: int = None,
        use_hybrid: bool = None
    ) -> Dict[str, Any]:
        """Execute RAG query: retrieve context and generate answer"""
        top_k = top_k or settings.top_k
        use_hybrid = use_hybrid if use_hybrid is not None else self.use_hybrid

        if use_hybrid and settings.use_hybrid_rag:
            return await self._hybrid_query(notebook_id, query, top_k)
        else:
            return await self._simple_query(notebook_id, query, top_k)

    async def _hybrid_query(
        self,
        notebook_id: str,
        query: str,
        top_k: int
    ) -> Dict[str, Any]:
        """Execute HybridRAG query with vector + BM25 + graph"""
        # Retrieve using hybrid retriever
        results = await self.hybrid_retriever.retrieve(
            notebook_id=notebook_id,
            query=query,
            top_k=top_k
        )

        if not results:
            return {
                "answer": "No relevant documents found in this notebook. Please upload some documents first.",
                "sources": [],
                "entities": []
            }

        # Build context for LLM
        context_chunks = []
        sources = []
        all_entities = []

        for result in results:
            context_chunks.append({
                "text": result.text,
                "filename": result.metadata.get("filename", "Unknown"),
                "document_id": result.metadata.get("document_id", ""),
                "chunk_index": result.metadata.get("chunk_index", 0),
                "sources": result.sources
            })

            sources.append(MessageSource(
                document_id=result.metadata.get("document_id", ""),
                filename=result.metadata.get("filename", "Unknown"),
                chunk_text=result.text[:200] + "..." if len(result.text) > 200 else result.text,
                relevance_score=round(result.score, 3)
            ))

            if result.entities:
                all_entities.extend(result.entities)

        # Get entity context for enhanced prompt
        entity_context = ""
        if all_entities and self.graph_store.is_connected:
            entity_names = [e.get("name", "") for e in all_entities if e.get("name")][:5]
            entity_context = self.graph_store.get_entity_context(
                notebook_id=notebook_id,
                entity_names=entity_names
            )

        # Generate response using LLM
        messages = self._build_hybrid_rag_messages(query, context_chunks, entity_context)
        answer = await self.llm_client.generate(messages)

        return {
            "answer": answer,
            "sources": sources,
            "entities": all_entities[:10],  # Limit entities in response
            "retrieval_mode": "hybrid"
        }

    async def _simple_query(
        self,
        notebook_id: str,
        query: str,
        top_k: int
    ) -> Dict[str, Any]:
        """Execute simple vector-only RAG query (fallback)"""
        # Generate query embedding
        query_embedding = self.embedding_service.encode_single(query)

        # Retrieve relevant chunks
        results = self.vector_store.query(
            notebook_id=notebook_id,
            query_embedding=query_embedding,
            top_k=top_k
        )

        documents = results["documents"]
        metadatas = results["metadatas"]
        distances = results["distances"]

        if not documents:
            return {
                "answer": "No relevant documents found in this notebook. Please upload some documents first.",
                "sources": [],
                "retrieval_mode": "simple"
            }

        # Build context for LLM
        context_chunks = []
        sources = []

        for doc, meta, dist in zip(documents, metadatas, distances):
            context_chunks.append({
                "text": doc,
                "filename": meta.get("filename", "Unknown"),
                "document_id": meta.get("document_id", ""),
                "chunk_index": meta.get("chunk_index", 0)
            })

            relevance = max(0, 1 - dist)
            sources.append(MessageSource(
                document_id=meta.get("document_id", ""),
                filename=meta.get("filename", "Unknown"),
                chunk_text=doc[:200] + "..." if len(doc) > 200 else doc,
                relevance_score=round(relevance, 3)
            ))

        # Generate response using LLM
        messages = self.llm_client.build_rag_messages(query, context_chunks)
        answer = await self.llm_client.generate(messages)

        return {
            "answer": answer,
            "sources": sources,
            "retrieval_mode": "simple"
        }

    def _build_hybrid_rag_messages(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        entity_context: str = ""
    ) -> List[Dict[str, str]]:
        """Build messages for HybridRAG query with entity context"""
        # Format context from retrieved chunks
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            filename = chunk.get("filename", "Unknown")
            text = chunk.get("text", "")
            sources = chunk.get("sources", [])
            source_info = f" (via: {', '.join(sources)})" if sources else ""
            context_parts.append(f"[Source {i}: {filename}{source_info}]\n{text}")

        context = "\n\n---\n\n".join(context_parts)

        system_prompt = """You are a helpful assistant that answers questions based on the provided documents and knowledge graph information.
Follow these rules:
1. Only use information from the provided context to answer questions
2. If entity/relationship information is provided, use it to give more accurate answers
3. If the context doesn't contain enough information, say so
4. Cite which source documents you used in your answer
5. Be concise but thorough in your responses
6. Use Korean if the user asks in Korean, English if they ask in English"""

        user_prompt = f"""Based on the following documents:

{context}"""

        if entity_context:
            user_prompt += f"""

Related Entities and Relationships:
{entity_context}"""

        user_prompt += f"""

---

Question: {query}

Please provide a detailed answer based on the documents and entity information above."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def delete_document(self, notebook_id: str, document_id: str) -> None:
        """Delete a document from all stores"""
        self.vector_store.delete_document(notebook_id, document_id)
        self.bm25_store.delete_document(notebook_id, document_id)
        if self.graph_store.is_connected:
            self.graph_store.delete_document(notebook_id, document_id)

    def delete_notebook(self, notebook_id: str) -> None:
        """Delete all documents for a notebook from all stores"""
        self.vector_store.delete_notebook(notebook_id)
        self.bm25_store.delete_notebook(notebook_id)
        if self.graph_store.is_connected:
            self.graph_store.delete_notebook(notebook_id)

    def get_stats(self, notebook_id: str) -> Dict[str, Any]:
        """Get retrieval statistics for a notebook"""
        return self.hybrid_retriever.get_retrieval_stats(notebook_id)
