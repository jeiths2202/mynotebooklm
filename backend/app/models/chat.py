from pydantic import BaseModel, Field
from typing import List, Optional


class MessageSource(BaseModel):
    """Source document reference for RAG response"""
    document_id: str
    filename: str
    chunk_text: str
    relevance_score: float


class ChatRequest(BaseModel):
    """Request model for chat query"""
    query: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """Response model for chat"""
    answer: str
    sources: List[MessageSource]
    notebook_id: str
