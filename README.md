# NotebookLM Clone

A RAG-based document Q&A system powered by Llama3-8b-instruct, built with React and FastAPI.

## Features

- **Document Upload**: Support for PDF, TXT, and DOCX files
- **RAG-based Q&A**: Ask questions about your documents and get AI-powered answers
- **Multi-notebook Management**: Organize documents into separate notebooks
- **Source Citations**: See which documents were used to generate answers
- **Environment Switching**: Easy switch between development (mock) and production (GPU) modes

## Architecture

```
Frontend (React + Vite)
    ↓ HTTP
Backend (FastAPI)
    ├── Document Processing (PyPDF2, python-docx)
    ├── Vector Store (ChromaDB - local)
    └── AI Services (switchable)
        ├── Development: Mock Server (localhost:8001)
        └── Production:  GPU Server (192.168.8.11:12800)
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- (Production only) Remote GPU Server with vLLM

## Quick Start

### Option 1: Development Mode (No GPU Required)

Use mock services for testing without GPU server:

```bash
# Windows
scripts\start-dev.bat

# Linux/Mac
./scripts/switch-env.sh dev
cd backend && python -m uvicorn mock_server.main:app --port 8001 --reload &
cd backend && python -m uvicorn app.main:app --port 8000 --reload &
cd frontend && npm run dev
```

### Option 2: Production Mode (GPU Server Required)

Use real GPU server for LLM and Embeddings:

```bash
# Windows
scripts\start-prod.bat

# Linux/Mac
./scripts/switch-env.sh prod
cd backend && python -m uvicorn app.main:app --port 8000 --reload &
cd frontend && npm run dev
```

### Manual Setup

```bash
# 1. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Choose environment
# Copy .env.development or .env.production to .env

# 3. Start backend
python -m uvicorn app.main:app --reload --port 8000

# 4. Frontend setup (in another terminal)
cd frontend
npm install
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000/docs
- **Mock Server** (dev mode): http://localhost:8001

## Environment Switching

### Switch to Development (Mock Services)
```bash
# Windows
scripts\switch-env.bat dev

# Linux/Mac
./scripts/switch-env.sh dev
```

### Switch to Production (GPU Server)
```bash
# Windows
scripts\switch-env.bat prod

# Linux/Mac
./scripts/switch-env.sh prod
```

### Check Current Environment
```bash
# Windows
scripts\switch-env.bat status

# Linux/Mac
./scripts/switch-env.sh status
```

## API Endpoints

### Notebooks
- `GET /api/notebooks` - List all notebooks
- `POST /api/notebooks` - Create a notebook
- `GET /api/notebooks/{id}` - Get notebook details
- `DELETE /api/notebooks/{id}` - Delete a notebook

### Documents
- `GET /api/notebooks/{id}/documents` - List documents in a notebook
- `POST /api/notebooks/{id}/documents` - Upload a document
- `DELETE /api/documents/{id}` - Delete a document

### Chat
- `POST /api/notebooks/{id}/chat` - Send a query

## Project Structure

```
mynotebooklm/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── models/        # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── storage/       # Data persistence
│   ├── mock_server/       # Mock LLM & Embedding APIs
│   ├── data/              # Uploads & ChromaDB
│   ├── .env.development   # Dev environment config
│   ├── .env.production    # Prod environment config
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks
│   │   └── services/      # API client
│   └── package.json
│
├── scripts/
│   ├── switch-env.sh      # Environment switcher (Linux/Mac)
│   ├── switch-env.bat     # Environment switcher (Windows)
│   ├── start-dev.bat      # Quick start dev mode (Windows)
│   └── start-prod.bat     # Quick start prod mode (Windows)
│
└── README.md
```

## Configuration

### Development (.env.development)

```env
LLM_API_URL=http://localhost:8001/v1/chat/completions
EMBEDDING_API_URL=http://localhost:8001/v1/embeddings
ENVIRONMENT=development
USE_MOCK_SERVICES=true
```

### Production (.env.production)

```env
LLM_API_URL=http://192.168.8.11:12800/v1/chat/completions
EMBEDDING_API_URL=http://192.168.8.11:12800/v1/embeddings
ENVIRONMENT=production
USE_MOCK_SERVICES=false
```

## Mock Server

The mock server provides OpenAI-compatible endpoints for testing:

- `POST /v1/chat/completions` - Mock LLM responses
- `POST /v1/embeddings` - Mock embedding vectors

Start the mock server:
```bash
cd backend
python -m uvicorn mock_server.main:app --port 8001 --reload
```

## License

MIT
