from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class NotebookCreate(BaseModel):
    """Request model for creating a notebook"""
    name: str = Field(..., min_length=1, max_length=100)


class Notebook(BaseModel):
    """Internal notebook model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    document_count: int = 0


class NotebookResponse(BaseModel):
    """Response model for notebook"""
    id: str
    name: str
    created_at: datetime
    document_count: int
