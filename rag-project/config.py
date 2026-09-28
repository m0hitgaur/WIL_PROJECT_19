"""
Configuration Manager for Financial RAG System.
Loads environment variables and provides centralized settings.
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Base Paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parent
    DATA_DIR: Path = Path(__file__).resolve().parent / "data"
    TABLE_IMAGE_DIR: Path = Path(__file__).resolve().parent / "output" / "table_crops"

    # Neo4j Database Configuration
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(default="password", description="Neo4j password")
    NEO4J_DATABASE: str = Field(default="neo4j", description="Neo4j database name")

    # Ollama Local Models
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama API base URL")
    OLLAMA_LLM_MODEL: str = Field(default="qwen2.5:14b", description="Core LLM for reasoning & graph extraction")
    OLLAMA_VLM_MODEL: str = Field(default="qwen2.5-vl:7b", description="Vision-Language Model for tables")
    OLLAMA_EMBED_MODEL: str = Field(default="bge-m3", description="Embedding model for vector index")

    # Ingestion & Indexing
    CHUNK_SIZE: int = Field(default=800, description="Target chunk size in characters/tokens")
    CHUNK_OVERLAP: int = Field(default=100, description="Chunk overlap")
    EMBEDDING_DIM: int = Field(default=1024, description="Vector dimension for index creation")
    VECTOR_INDEX_NAME: str = Field(default="chunk_embeddings", description="Neo4j native vector index name")

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        self.TABLE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        (self.PROJECT_ROOT / "output").mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
