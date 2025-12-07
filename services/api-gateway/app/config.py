"""Configuration for API Gateway Service."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Service configuration with environment variable support."""
    
    # Service Info
    service_name: str = "api-gateway"
    service_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = Field(default=8000, env="API_GATEWAY_PORT")
    log_level: str = "INFO"
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Service URLs (for service-to-service communication)
    video_ingestion_url: str = Field(
        default="http://localhost:8001",
        env="VIDEO_INGESTION_URL"
    )
    emotion_detection_url: str = Field(
        default="http://localhost:8002",
        env="EMOTION_DETECTION_URL"
    )
    sentiment_analysis_url: str = Field(
        default="http://localhost:8003",
        env="SENTIMENT_ANALYSIS_URL"
    )
    
    # Database (for rules and config)
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5434, env="POSTGRES_PORT")
    postgres_user: str = Field(default="vantage", env="POSTGRES_USER")
    postgres_password: str = Field(default="vantage_secret", env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="vantage_db", env="POSTGRES_DB")
    
    # Redis (for real-time updates)
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6380, env="REDIS_PORT")
    redis_db: int = 0
    redis_sentiment_stream: str = "sentiment:crowd"
    
    # Performance
    max_memory_mb: int = 256
    request_timeout: int = 30
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
