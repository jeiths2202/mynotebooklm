from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import notebooks_router, documents_router, chat_router
from app.services import RAGService
from app.storage import NotebookStore, FileManager

# Create FastAPI app
app = FastAPI(
    title="NotebookLM Clone",
    description="RAG-based document Q&A system powered by Llama3",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("Initializing services...")

    # Initialize storage
    app.state.notebook_store = NotebookStore()
    app.state.file_manager = FileManager()

    # Initialize RAG service (this will load the embedding model)
    app.state.rag_service = RAGService()

    print("Services initialized successfully!")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "NotebookLM Clone API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Mount routers
app.include_router(
    notebooks_router,
    prefix="/api/notebooks",
    tags=["notebooks"]
)

app.include_router(
    documents_router,
    prefix="/api",
    tags=["documents"]
)

app.include_router(
    chat_router,
    prefix="/api",
    tags=["chat"]
)


if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
