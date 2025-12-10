from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    # LLM Configuration
    llm_api_url: str = "http://192.168.8.11:12800/v1/chat/completions"
    llm_model: str = "llama3-8b-instruct"

    # Embedding API Configuration (Remote Server)
    embedding_api_url: str = "http://192.168.8.11:12800/v1/embeddings"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # all-MiniLM-L6-v2 dimension

    # Environment Configuration
    environment: str = "development"
    use_mock_services: bool = False

    # Data Paths
    base_dir: Path = Path(__file__).parent.parent
    upload_dir: Path = base_dir / "data" / "uploads"
    chroma_dir: Path = base_dir / "data" / "chroma"
    notebooks_file: Path = base_dir / "data" / "notebooks.json"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # RAG Settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5

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
