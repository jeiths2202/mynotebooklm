from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class Document(BaseModel):
    """Internal document model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    notebook_id: str
    filename: str
    file_type: str
    chunk_count: int = 0
    uploaded_at: datetime = Field(default_factory=datetime.now)


class DocumentResponse(BaseModel):
    """Response model for document"""
    id: str
    notebook_id: str
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: datetime
