"""
Mock Server for LLM and Embedding APIs
Provides OpenAI-compatible endpoints for testing without GPU server

Usage:
    python -m uvicorn mock_server.main:app --port 8001 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import time

app = FastAPI(
    title="Mock AI Services",
    description="Mock LLM and Embedding APIs for development",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Models ==============

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: dict


class EmbeddingRequest(BaseModel):
    model: str
    input: List[str] | str


class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: dict


# ============== Mock Responses ==============

MOCK_RESPONSES = [
    "Based on the provided documents, I can see that {topic}. The key points are: 1) The documents discuss various aspects of the subject matter. 2) There are several important considerations mentioned. 3) The overall conclusion suggests careful analysis is needed.",
    "According to the context provided, {topic}. This is supported by multiple references in the documents. The main findings indicate that the information is comprehensive and well-documented.",
    "From my analysis of the uploaded documents, {topic}. The documents contain relevant information that addresses your question. Key takeaways include the importance of understanding the context and applying the knowledge appropriately.",
    "The documents you've provided contain information about {topic}. After reviewing the content, I can summarize that the material covers several important aspects. The sources are consistent in their findings.",
]


def generate_mock_embedding(dimension: int = 384) -> List[float]:
    """Generate a random embedding vector"""
    return [random.uniform(-1, 1) for _ in range(dimension)]


def generate_mock_response(prompt: str) -> str:
    """Generate a mock LLM response based on the prompt"""
    # Extract topic from prompt
    topic = "the subject matter you asked about"
    if "question:" in prompt.lower():
        parts = prompt.lower().split("question:")
        if len(parts) > 1:
            topic = parts[1].strip()[:100]

    response = random.choice(MOCK_RESPONSES).format(topic=topic)
    return response


# ============== Endpoints ==============

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Mock AI Services",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "embeddings": "/v1/embeddings"
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """Mock OpenAI-compatible chat completions endpoint"""

    # Simulate some processing time
    time.sleep(random.uniform(0.5, 1.5))

    # Get the last user message
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    # Generate mock response
    mock_response = generate_mock_response(user_message)

    return ChatCompletionResponse(
        id=f"mock-{int(time.time())}",
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role="assistant", content=mock_response),
                finish_reason="stop"
            )
        ],
        usage={
            "prompt_tokens": len(user_message.split()),
            "completion_tokens": len(mock_response.split()),
            "total_tokens": len(user_message.split()) + len(mock_response.split())
        }
    )


@app.post("/v1/embeddings", response_model=EmbeddingResponse)
async def embeddings(request: EmbeddingRequest):
    """Mock OpenAI-compatible embeddings endpoint"""

    # Handle both string and list inputs
    inputs = request.input if isinstance(request.input, list) else [request.input]

    # Generate mock embeddings
    embeddings_data = [
        EmbeddingData(
            embedding=generate_mock_embedding(384),
            index=i
        )
        for i, text in enumerate(inputs)
    ]

    return EmbeddingResponse(
        data=embeddings_data,
        model=request.model,
        usage={
            "prompt_tokens": sum(len(text.split()) for text in inputs),
            "total_tokens": sum(len(text.split()) for text in inputs)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
