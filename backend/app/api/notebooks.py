from typing import List
from fastapi import APIRouter, HTTPException, Request

from app.models import Notebook, NotebookCreate, NotebookResponse
from app.storage import NotebookStore, FileManager
from app.services import RAGService

router = APIRouter()


def get_notebook_store(request: Request) -> NotebookStore:
    return request.app.state.notebook_store


def get_file_manager(request: Request) -> FileManager:
    return request.app.state.file_manager


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


@router.get("", response_model=List[NotebookResponse])
async def list_notebooks(request: Request):
    """List all notebooks"""
    store = get_notebook_store(request)
    notebooks = store.list_notebooks()
    return notebooks


@router.post("", response_model=NotebookResponse)
async def create_notebook(notebook_create: NotebookCreate, request: Request):
    """Create a new notebook"""
    store = get_notebook_store(request)
    notebook = Notebook(name=notebook_create.name)
    created = store.create_notebook(notebook)
    return created


@router.get("/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(notebook_id: str, request: Request):
    """Get a notebook by ID"""
    store = get_notebook_store(request)
    notebook = store.get_notebook(notebook_id)

    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Update document count
    documents = store.list_documents(notebook_id)
    notebook.document_count = len(documents)

    return notebook


@router.delete("/{notebook_id}")
async def delete_notebook(notebook_id: str, request: Request):
    """Delete a notebook and all its documents"""
    store = get_notebook_store(request)
    file_manager = get_file_manager(request)
    rag_service = get_rag_service(request)

    # Check if notebook exists
    notebook = store.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Delete from vector store
    rag_service.delete_notebook(notebook_id)

    # Delete files
    file_manager.delete_notebook_files(notebook_id)

    # Delete from store
    store.delete_notebook(notebook_id)

    return {"message": "Notebook deleted successfully"}


@router.patch("/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    notebook_id: str,
    notebook_update: NotebookCreate,
    request: Request
):
    """Update a notebook's name"""
    store = get_notebook_store(request)

    updated = store.update_notebook(notebook_id, notebook_update.name)
    if not updated:
        raise HTTPException(status_code=404, detail="Notebook not found")

    return updated
