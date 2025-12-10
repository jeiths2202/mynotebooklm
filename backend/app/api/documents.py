from typing import List
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Request

from app.models import Document, DocumentResponse
from app.storage import NotebookStore, FileManager
from app.services import RAGService

router = APIRouter()


def get_notebook_store(request: Request) -> NotebookStore:
    return request.app.state.notebook_store


def get_file_manager(request: Request) -> FileManager:
    return request.app.state.file_manager


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


@router.get("/notebooks/{notebook_id}/documents", response_model=List[DocumentResponse])
async def list_documents(notebook_id: str, request: Request):
    """List all documents in a notebook"""
    store = get_notebook_store(request)

    # Verify notebook exists
    notebook = store.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    documents = store.list_documents(notebook_id)
    return documents


@router.post("/notebooks/{notebook_id}/documents", response_model=DocumentResponse)
async def upload_document(
    notebook_id: str,
    file: UploadFile = File(...),
    request: Request = None
):
    """Upload a document to a notebook"""
    store = get_notebook_store(request)
    file_manager = get_file_manager(request)
    rag_service = get_rag_service(request)

    # Verify notebook exists
    notebook = store.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Validate file
    error = file_manager.validate_file(file)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Create document record
    document = Document(
        notebook_id=notebook_id,
        filename=file.filename,
        file_type=Path(file.filename).suffix.lower()
    )

    # Save file
    file_path = await file_manager.save_file(notebook_id, file, document.id)

    try:
        # Process document (extract text, generate embeddings, store in vector DB)
        chunk_count = rag_service.process_document(
            notebook_id=notebook_id,
            document_id=document.id,
            file_path=file_path
        )

        document.chunk_count = chunk_count

        # Save document metadata
        store.create_document(document)

        return document

    except Exception as e:
        # Clean up file on error
        file_manager.delete_file(file_path)
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, request: Request):
    """Get a document by ID"""
    store = get_notebook_store(request)
    document = store.get_document(document_id)

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, request: Request):
    """Delete a document"""
    store = get_notebook_store(request)
    file_manager = get_file_manager(request)
    rag_service = get_rag_service(request)

    # Get document
    document = store.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from vector store
    rag_service.delete_document(document.notebook_id, document_id)

    # Delete file
    file_path = file_manager.get_file_path(document.notebook_id, document_id)
    if file_path:
        file_manager.delete_file(file_path)

    # Delete from store
    store.delete_document(document_id)

    return {"message": "Document deleted successfully"}
