from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class MessageSource(BaseModel):
    """Source document reference for RAG response"""
    document_id: str
    filename: str
    chunk_text: str
    relevance_score: float


class EntityInfo(BaseModel):
    """Entity information from knowledge graph"""
    name: str
    type: Optional[str] = None
    relation: Optional[str] = None
    related: Optional[List[Dict[str, Any]]] = None


class ChatRequest(BaseModel):
    """Request model for chat query"""
    query: str = Field(..., min_length=1, max_length=2000)
    use_hybrid: Optional[bool] = None  # Override hybrid mode setting


class ChatResponse(BaseModel):
    """Response model for chat"""
    answer: str
    sources: List[MessageSource]
    notebook_id: str
    entities: Optional[List[Dict[str, Any]]] = None  # Related entities from graph
    retrieval_mode: Optional[str] = None  # 'hybrid' or 'simple'
