"""Enhanced configuration management."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings as PydanticBaseSettings

logger = logging.getLogger(__name__)


class DatabaseSettings(PydanticBaseSettings):
    """Database configuration settings."""

    repositories_path: Path = Field(default=Path("data/repositories"), description="Path for repository databases")
    sqlite_timeout: int = Field(default=30, description="SQLite connection timeout in seconds")
    backup_enabled: bool = Field(default=True, description="Enable automatic database backups")
    backup_interval_hours: int = Field(default=24, description="Backup interval in hours")

    class Config:
        env_prefix = "DB_"


class LLMSettings(PydanticBaseSettings):
    """LLM service configuration settings."""

    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model to use")
    openai_temperature: float = Field(default=0.3, description="Temperature for LLM responses", ge=0.0, le=2.0)
    openai_max_tokens: int = Field(default=2000, description="Maximum tokens for LLM responses", gt=0)
    openai_timeout: int = Field(default=60, description="Request timeout in seconds")

    # Embedding settings
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model")
    embedding_dimensions: int = Field(default=1536, description="Embedding dimensions")

    class Config:
        env_prefix = "LLM_"


class QdrantSettings(PydanticBaseSettings):
    """Qdrant vector database configuration."""

    host: str = Field(default="localhost", description="Qdrant host")
    port: int = Field(default=6333, description="Qdrant port")
    grpc_port: int = Field(default=6334, description="Qdrant gRPC port")
    api_key: Optional[str] = Field(default=None, description="Qdrant API key")
    https: bool = Field(default=False, description="Use HTTPS")
    collection_name: str = Field(default="business_documents", description="Collection name")

    # Performance settings
    timeout: int = Field(default=30, description="Connection timeout")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    prefer_grpc: bool = Field(default=False, description="Prefer gRPC over HTTP")

    class Config:
        env_prefix = "QDRANT_"


class ProcessingSettings(PydanticBaseSettings):
    """Document and data processing settings."""

    # Document processing
    chunk_size: int = Field(default=512, description="Document chunk size", gt=0)
    chunk_overlap: int = Field(default=50, description="Chunk overlap size", ge=0)
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB", gt=0)
    supported_formats: List[str] = Field(
        default=["pdf", "docx", "txt", "md", "csv"],
        description="Supported file formats"
    )

    # CSV processing
    csv_encoding_fallbacks: List[str] = Field(
        default=["utf-8", "latin-1", "cp1252", "iso-8859-1"],
        description="CSV encoding fallback order"
    )

    # Analysis settings
    anomaly_threshold: float = Field(default=2.0, description="Anomaly detection threshold", gt=0)
    confidence_threshold: float = Field(default=0.7, description="Minimum confidence threshold", ge=0, le=1)

    class Config:
        env_prefix = "PROCESSING_"


class SecuritySettings(PydanticBaseSettings):
    """Security and privacy settings."""

    enable_data_encryption: bool = Field(default=False, description="Enable data encryption at rest")
    log_sensitive_data: bool = Field(default=False, description="Allow logging of sensitive data")
    api_rate_limit: int = Field(default=100, description="API requests per minute", gt=0)
    session_timeout_minutes: int = Field(default=60, description="Session timeout in minutes", gt=0)

    # File security
    allowed_upload_paths: List[str] = Field(
        default=["data/uploads"],
        description="Allowed upload directories"
    )
    scan_uploads: bool = Field(default=True, description="Scan uploaded files for malware")

    class Config:
        env_prefix = "SECURITY_"


class Settings(PydanticBaseSettings):
    """Main application settings."""

    # Application info
    app_name: str = Field(default="Business Intelligence RAG System", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    debug: bool = Field(default=True, description="Enable debug mode")

    # Paths
    data_dir: Path = Field(default=Path("data"), description="Data directory path")
    logs_dir: Path = Field(default=Path("logs"), description="Logs directory path")
    temp_dir: Path = Field(default=Path("temp"), description="Temporary files directory")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        description="Log format string"
    )
    enable_file_logging: bool = Field(default=True, description="Enable file logging")

    # Sub-configurations
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment setting."""
        allowed_envs = ['development', 'staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of: {allowed_envs}')
        return v

    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level setting."""
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of: {allowed_levels}')
        return v.upper()

    def create_directories(self) -> None:
        """Create necessary directories."""
        directories = [
            self.data_dir,
            self.logs_dir,
            self.temp_dir,
            self.database.repositories_path,
            self.data_dir / "uploads",
            self.data_dir / "exports",
            self.data_dir / "cache"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"

    def get_log_file_path(self) -> Path:
        """Get the log file path."""
        return self.logs_dir / f"{self.app_name.lower().replace(' ', '_')}.log"

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return self.dict()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow extra fields for flexibility
        extra = "allow"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """Get application settings (singleton)."""
    global _settings

    if _settings is None or reload:
        try:
            _settings = Settings()
            _settings.create_directories()
            logger.info(f"Settings loaded for environment: {_settings.environment}")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            # Fallback to default settings
            _settings = Settings()

    return _settings


def update_settings(**kwargs) -> Settings:
    """Update specific settings values."""
    global _settings

    if _settings is None:
        _settings = get_settings()

    # Update settings
    for key, value in kwargs.items():
        if hasattr(_settings, key):
            setattr(_settings, key, value)
            logger.info(f"Updated setting {key} = {value}")
        else:
            logger.warning(f"Unknown setting: {key}")

    return _settings
