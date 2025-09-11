"""Configuration settings for the Business Intelligence RAG System."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    llm_model: str = Field(default="gpt-4-turbo-preview", env="LLM_MODEL")
    max_tokens: int = Field(default=2000, env="MAX_TOKENS")
    temperature: float = Field(default=0.7, env="TEMPERATURE")

    # Qdrant Configuration
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_collection_name: str = Field(default="business_documents", env="QDRANT_COLLECTION_NAME")

    # Application Settings
    app_name: str = Field(default="Business Intelligence RAG System", env="APP_NAME")
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    chunk_size: int = Field(default=512, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")

    # RAG Query Performance Settings
    rag_response_mode: str = Field(default="compact", env="RAG_RESPONSE_MODE")  # compact, tree_summarize, simple
    rag_similarity_top_k: int = Field(default=3, env="RAG_SIMILARITY_TOP_K")  # Number of similar chunks to retrieve
    rag_enable_caching: bool = Field(default=True, env="RAG_ENABLE_CACHING")  # Cache embeddings for faster queries

    # Enterprise Features
    hf_hub_disable_symlinks_warning: Optional[str] = Field(default=None, env="HF_HUB_DISABLE_SYMLINKS_WARNING")

    # Multi-Tenant Configuration
    enable_multi_tenancy: bool = Field(default=False, env="ENABLE_MULTI_TENANCY")
    jwt_secret_key: str = Field(default="your-secret-key-change-this", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    session_duration_hours: int = Field(default=8, env="SESSION_DURATION_HOURS")
    max_tenants_per_instance: int = Field(default=100, env="MAX_TENANTS_PER_INSTANCE")

    # Tenant Database
    tenant_db_path: str = Field(default="data/multi_tenant.db", env="TENANT_DB_PATH")
    tenant_facts_db_path: str = Field(default="data/multi_tenant_facts.db", env="TENANT_FACTS_DB_PATH")

    # Rate Limiting
    rate_limit_basic: str = Field(default="60/minute", env="RATE_LIMIT_BASIC")
    rate_limit_premium: str = Field(default="300/minute", env="RATE_LIMIT_PREMIUM")
    rate_limit_enterprise: str = Field(default="1000/minute", env="RATE_LIMIT_ENTERPRISE")
    rate_limit_custom: str = Field(default="unlimited", env="RATE_LIMIT_CUSTOM")

    # Paths
    data_dir: Path = Field(default=Path("data"))
    upload_dir: Path = Field(default=Path("data/uploads"))
    cache_dir: Path = Field(default=Path("data/cache"))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


# Singleton instance
settings = Settings()
