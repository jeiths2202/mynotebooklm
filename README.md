# NotebookLM Clone with HybridRAG

A production-ready RAG-based document Q&A system with **HybridRAG** (Vector + BM25 + Knowledge Graph), powered by local LLM (Ollama) and Cross-Encoder Reranking.

## Features

- **HybridRAG Search**: Combines Dense Vector, Sparse BM25, and Knowledge Graph retrieval
- **Cross-Encoder Reranking**: Uses `ms-marco-MiniLM-L-6-v2` for improved relevance
- **RRF Fusion**: Reciprocal Rank Fusion for combining multi-source results
- **Local LLM**: Runs with Ollama (gemma:2b or EEVE-Korean-10.8B)
- **Local Embeddings**: Uses `all-MiniLM-L6-v2` via sentence-transformers
- **Document Upload**: Support for PDF, TXT, and DOCX files
- **Multi-notebook Management**: Organize documents into separate notebooks
- **Source Citations**: See which documents were used to generate answers

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                            │
│                      http://localhost:5173                          │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                            │
│                     http://localhost:8000                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ Notebooks   │  │ Documents   │  │   Chat      │                  │
│  │   API       │  │    API      │  │   API       │                  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                  │
│         │                │                │                         │
│         └────────────────┴────────────────┘                         │
│                          │                                          │
│                          ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    RAG Service                                │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │              HybridRetriever                            │ │   │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐              │ │   │
│  │  │  │  Vector   │ │   BM25    │ │   Graph   │              │ │   │
│  │  │  │  Search   │ │  Search   │ │  Search   │              │ │   │
│  │  │  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘              │ │   │
│  │  │        └─────────────┼─────────────┘                    │ │   │
│  │  │                      ▼                                  │ │   │
│  │  │            ┌─────────────────┐                          │ │   │
│  │  │            │   RRF Fusion    │                          │ │   │
│  │  │            └────────┬────────┘                          │ │   │
│  │  │                     ▼                                   │ │   │
│  │  │            ┌─────────────────┐                          │ │   │
│  │  │            │ Cross-Encoder   │                          │ │   │
│  │  │            │    Reranker     │                          │ │   │
│  │  │            └────────┬────────┘                          │ │   │
│  │  └─────────────────────┼───────────────────────────────────┘ │   │
│  │                        ▼                                     │   │
│  │               ┌─────────────────┐                            │   │
│  │               │   LLM Client    │                            │   │
│  │               │   (Ollama)      │                            │   │
│  │               └────────┬────────┘                            │   │
│  └────────────────────────┼─────────────────────────────────────┘   │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Neo4j Graph  │  │    Ollama     │  │   Vector +    │
│   Database    │  │   LLM API     │  │  BM25 Store   │
│  :7687/:7474  │  │    :11434     │  │   (JSON)      │
└───────────────┘  └───────────────┘  └───────────────┘
```

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | React UI |
| **Backend API** | http://localhost:8000 | FastAPI REST API |
| **API Documentation** | http://localhost:8000/docs | Swagger UI |
| **Neo4j Browser** | http://localhost:7474 | Graph Database UI |
| **Ollama API** | http://localhost:11434 | Local LLM Server |

## Prerequisites

- Python 3.10+
- Node.js 18+
- Docker (for Neo4j)
- Ollama (for local LLM)

## Quick Start

### 1. Install Ollama and Download Model

```bash
# Install Ollama from https://ollama.ai

# Download a small model for CPU
ollama pull gemma:2b

# Or for Korean language support (requires more RAM/GPU)
ollama pull EEVE-Korean-10.8B:latest
```

### 2. Start Neo4j (Docker)

```bash
docker-compose up -d
```

### 3. Start Backend

```bash
cd backend

# Create virtual environment (first time only)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Start Ollama (if not running)

```bash
ollama serve
```

### 5. Start Frontend (Optional)

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Notebooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/notebooks` | List all notebooks |
| `POST` | `/api/notebooks` | Create a notebook |
| `GET` | `/api/notebooks/{id}` | Get notebook details |
| `DELETE` | `/api/notebooks/{id}` | Delete a notebook |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/notebooks/{id}/documents` | List documents in a notebook |
| `POST` | `/api/notebooks/{id}/documents` | Upload a document |
| `DELETE` | `/api/documents/{id}` | Delete a document |

### Chat (HybridRAG)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/notebooks/{id}/chat` | Send a RAG query |
| `GET` | `/api/notebooks/{id}/stats` | Get retrieval statistics |

#### Chat Request Example

```bash
curl -X POST "http://localhost:8000/api/notebooks/{notebook_id}/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is error code 001?", "use_hybrid": true}'
```

#### Chat Response Example

```json
{
  "answer": "Error code 001 indicates...",
  "sources": [
    {
      "document_id": "...",
      "filename": "error_guide.pdf",
      "chunk_text": "...",
      "relevance_score": 0.95
    }
  ],
  "notebook_id": "...",
  "entities": [],
  "retrieval_mode": "hybrid"
}
```

## Project Structure

```
mynotebooklm/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── notebooks.py         # Notebook CRUD API
│   │   │   ├── documents.py         # Document upload/manage API
│   │   │   └── chat.py              # HybridRAG query API
│   │   ├── services/
│   │   │   ├── rag_service.py       # RAG orchestration
│   │   │   ├── hybrid_retriever.py  # 3-way search + RRF fusion
│   │   │   ├── vector_store.py      # Dense vector store (JSON-based)
│   │   │   ├── bm25_store.py        # Sparse keyword search
│   │   │   ├── graph_store.py       # Neo4j knowledge graph
│   │   │   ├── reranker.py          # Cross-Encoder reranking
│   │   │   ├── embeddings.py        # Local/Remote embeddings
│   │   │   ├── llm_client.py        # Ollama API client
│   │   │   ├── entity_extractor.py  # LLM-based entity extraction
│   │   │   └── document_processor.py # PDF/DOCX/TXT processing
│   │   ├── config.py                # Settings management
│   │   ├── main.py                  # FastAPI application
│   │   └── models/                  # Pydantic schemas
│   ├── data/
│   │   ├── uploads/                 # Uploaded documents
│   │   ├── bm25/                    # BM25 indices
│   │   ├── vector_store/            # Vector embeddings
│   │   └── notebooks.json           # Notebook metadata
│   ├── .env                         # Environment configuration
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/              # React components
│   │   ├── pages/                   # Page components
│   │   └── services/                # API client
│   └── package.json
│
├── docker-compose.yml               # Neo4j container
└── README.md
```

## Configuration

### Environment Variables (.env)

```env
# LLM Configuration (Ollama)
LLM_API_URL=http://localhost:11434/api/chat
LLM_MODEL=gemma:2b

# Embedding Configuration (Local)
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
USE_LOCAL_EMBEDDINGS=true

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=notebooklm123

# HybridRAG Settings
USE_HYBRID_RAG=true
USE_GRAPH_SEARCH=true
USE_BM25_SEARCH=true
USE_RERANKER=true
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RRF_K=60
GRAPH_K_HOP=2

# Environment
ENVIRONMENT=development
USE_MOCK_SERVICES=false
```

### Model Options

| Model | Size | Speed | Korean Support |
|-------|------|-------|----------------|
| `gemma:2b` | 1.7GB | Fast (CPU) | Limited |
| `llama3:8b` | 4.7GB | Medium | Limited |
| `EEVE-Korean-10.8B` | 7.7GB | Slow (CPU) / Fast (GPU) | Excellent |

## Components

### HybridRetriever

Combines three search methods with RRF fusion:

1. **Vector Search**: Semantic similarity using dense embeddings
2. **BM25 Search**: Keyword matching using sparse term frequency
3. **Graph Search**: Knowledge graph traversal (Neo4j)

### Cross-Encoder Reranker

Re-ranks combined results using a cross-encoder model for improved relevance.

### Local Embeddings

Uses `sentence-transformers` with `all-MiniLM-L6-v2` model for fast, local embedding generation.

## Troubleshooting

### Ollama Connection Error

```bash
# Ensure Ollama is running
ollama serve

# Check available models
ollama list

# Pull a model if needed
ollama pull gemma:2b
```

### Neo4j Connection Error

```bash
# Check Docker container status
docker ps

# Start Neo4j if not running
docker-compose up -d

# Check Neo4j logs
docker logs mynotebooklm-neo4j-1
```

### Slow LLM Response (CPU)

For faster responses on CPU, use a smaller model:

```bash
# Use gemma:2b instead of larger models
# Edit .env:
LLM_MODEL=gemma:2b
```

## License

MIT
