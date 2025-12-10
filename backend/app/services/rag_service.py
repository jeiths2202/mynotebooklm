from typing import List, Dict, Any
from pathlib import Path

from app.config import settings
from app.models import MessageSource
from .document_processor import DocumentProcessor
from .embeddings import EmbeddingService
from .vector_store import VectorStore
from .llm_client import LLMClient


class RAGService:
    """Orchestrates the RAG pipeline: document processing, retrieval, and generation"""

    def __init__(
        self,
        document_processor: DocumentProcessor = None,
        embedding_service: EmbeddingService = None,
        vector_store: VectorStore = None,
        llm_client: LLMClient = None
    ):
        self.document_processor = document_processor or DocumentProcessor()
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.llm_client = llm_client or LLMClient()

    def process_document(
        self,
        notebook_id: str,
        document_id: str,
        file_path: Path
    ) -> int:
        """Process a document and add to vector store. Returns chunk count."""
        # Extract and chunk text
        chunks = self.document_processor.process_file(file_path, document_id)

        if not chunks:
            return 0

        # Generate embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_service.encode(texts)

        # Store in vector database
        metadatas = [chunk.metadata for chunk in chunks]
        self.vector_store.add_documents(
            notebook_id=notebook_id,
            document_id=document_id,
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )

        return len(chunks)

    async def query(
        self,
        notebook_id: str,
        query: str,
        top_k: int = None
    ) -> Dict[str, Any]:
        """Execute RAG query: retrieve context and generate answer"""
        top_k = top_k or settings.top_k

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
                "sources": []
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

            # Convert distance to relevance score (1 - normalized_distance)
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
            "sources": sources
        }

    def delete_document(self, notebook_id: str, document_id: str) -> None:
        """Delete a document from the vector store"""
        self.vector_store.delete_document(notebook_id, document_id)

    def delete_notebook(self, notebook_id: str) -> None:
        """Delete all documents for a notebook"""
        self.vector_store.delete_notebook(notebook_id)
