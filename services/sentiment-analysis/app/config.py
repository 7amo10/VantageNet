"""Configuration management for Sentiment Analysis Service."""
import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Service configuration with environment variable support."""
    
    # Service Info
    service_name: str = "sentiment-analysis"
    service_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = Field(default=8003, env="SENTIMENT_ANALYSIS_PORT")
    log_level: str = "INFO"
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6380, env="REDIS_PORT")
    redis_db: int = 0
    redis_input_pattern: str = "emotion:results:*"
    redis_output_stream: str = "sentiment:crowd"
    redis_consumer_group: str = "sentiment-analysis-group"
    redis_consumer_name: str = "sentiment-worker-1"
    redis_block_ms: int = 5000
    redis_batch_size: int = 10
    
    # PostgreSQL Configuration
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5434, env="POSTGRES_PORT")
    postgres_user: str = Field(default="vantage", env="POSTGRES_USER")
    postgres_password: str = Field(default="vantage_secret", env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="vantage_db", env="POSTGRES_DB")
    
    # Aggregation Configuration
    aggregation_window_seconds: int = Field(
        default=10,
        description="Time window for emotion aggregation"
    )
    min_emotions_for_sentiment: int = Field(
        default=3,
        description="Minimum emotions needed to calculate sentiment"
    )
    
    # Rules Configuration
    rules_config_path: str = Field(
        default="config/rules.json",
        description="Path to rules configuration file"
    )
    
    # Performance
    max_memory_mb: int = 256
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
