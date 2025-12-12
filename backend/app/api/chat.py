from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any

from app.models import ChatRequest, ChatResponse
from app.storage import NotebookStore
from app.services import RAGService

router = APIRouter()


def get_notebook_store(request: Request) -> NotebookStore:
    return request.app.state.notebook_store


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


@router.post("/notebooks/{notebook_id}/chat", response_model=ChatResponse)
async def chat(notebook_id: str, chat_request: ChatRequest, request: Request):
    """Send a query to the HybridRAG system"""
    store = get_notebook_store(request)
    rag_service = get_rag_service(request)

    # Verify notebook exists
    notebook = store.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Check if notebook has documents
    documents = store.list_documents(notebook_id)
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="No documents in this notebook. Please upload some documents first."
        )

    try:
        # Execute RAG query (hybrid or simple based on settings/request)
        result = await rag_service.query(
            notebook_id=notebook_id,
            query=chat_request.query,
            use_hybrid=chat_request.use_hybrid
        )

        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            notebook_id=notebook_id,
            entities=result.get("entities"),
            retrieval_mode=result.get("retrieval_mode")
        )

    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing query: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {type(e).__name__}: {str(e)}"
        )


@router.get("/notebooks/{notebook_id}/stats")
async def get_notebook_stats(notebook_id: str, request: Request) -> Dict[str, Any]:
    """Get retrieval statistics for a notebook"""
    store = get_notebook_store(request)
    rag_service = get_rag_service(request)

    # Verify notebook exists
    notebook = store.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    try:
        stats = rag_service.get_stats(notebook_id)
        return {
            "notebook_id": notebook_id,
            "notebook_name": notebook.name,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting stats: {str(e)}"
        )
