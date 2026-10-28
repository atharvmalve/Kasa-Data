from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://yugabyte:yugabyte@127.0.0.1:5433/yugabyte",
        description="SQLAlchemy database URL for YugabyteDB"
    )

    # Server
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Ingestion Safeguards
    MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB default
    MAX_PDF_PAGES: int = 100

    # Chunking
    TARGET_CHUNK_TOKENS: int = 400
    MAX_CHUNK_TOKENS: int = 510
    CHUNK_OVERLAP_TOKENS: int = 50

    # Local Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Optional Groq LLM Enrichment
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

