from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    # LLM Configuration (Ollama)
    llm_api_url: str = "http://localhost:11434/v1/chat/completions"
    llm_model: str = "EEVE-Korean-10.8B:latest"

    # Embedding API Configuration (Remote Server)
    embedding_api_url: str = "http://localhost:8001/v1/embeddings"
    embedding_model: str = "mock-all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # all-MiniLM-L6-v2 dimension
    use_local_embeddings: bool = True  # Use local sentence-transformers instead of remote API

    # Environment Configuration
    environment: str = "development"
    use_mock_services: bool = False

    # Data Paths
    base_dir: Path = Path(__file__).parent.parent
    upload_dir: Path = base_dir / "data" / "uploads"
    chroma_dir: Path = base_dir / "data" / "chroma"
    bm25_dir: Path = base_dir / "data" / "bm25"
    notebooks_file: Path = base_dir / "data" / "notebooks.json"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # RAG Settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 3  # Reduced for faster LLM response with local models

    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "notebooklm123"

    # HybridRAG Settings
    use_hybrid_rag: bool = True
    use_graph_search: bool = True
    use_bm25_search: bool = True
    use_reranker: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rrf_k: int = 60  # RRF fusion parameter
    graph_k_hop: int = 2  # Graph traversal depth

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_dir.mkdir(parents=True, exist_ok=True)
settings.bm25_dir.mkdir(parents=True, exist_ok=True)
