import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings.
    
    This class manages all configuration settings for the application,
    loaded from environment variables or .env file.
    """
    # Application settings
    APP_NAME: str = "Research Paper Search"
    API_PREFIX: str = "/api"
    DEBUG: bool = False
    
    # File storage settings
    UPLOAD_DIR: str = Field(default="storage/papers")
    MAX_UPLOAD_SIZE: int = 25 * 1024 * 1024  # 25MB
    
    # Database settings
    VECTOR_DB_PATH: str = Field(default="storage/vector_db")
    METADATA_DB_PATH: str = Field(default="storage/metadata.db")
    
    # LLM settings
    LLM_MODEL_DIR: str = Field(default="models")
    LLM_MODEL_NAME: str = "all-MiniLM-L6-v2"  # Default lightweight model
    EMBEDDING_DIMENSION: int = 384  # Dimension for the default model
    
    # API settings
    CORS_ORIGINS: list[str] = ["*"]
    
    # Search settings
    DEFAULT_SEARCH_LIMIT: int = 10
    SIMILARITY_THRESHOLD: float = 0.2

    # HNSW Vector DB settings
    USE_HYBRID_VECTOR_DB: bool = True  # Set to True to enable hybrid indexing
    MEMORY_THRESHOLD: float = 0.85      # Memory threshold to switch to flat indexing (0-1)
    HNSW_M: int = 32                    # HNSW M parameter (connections per layer)
    HNSW_EF_CONSTRUCTION: int = 200     # HNSW efConstruction parameter (build accuracy) 
    HNSW_EF_SEARCH: int = 128           # HNSW efSearch parameter (search accuracy)
    RERANK_SIZE: int = 30    
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create global settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
os.makedirs(os.path.dirname(settings.METADATA_DB_PATH), exist_ok=True)
os.makedirs(settings.LLM_MODEL_DIR, exist_ok=True)
