"""Configuration management for Emotion Detection Service."""
import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Service configuration with environment variable support."""
    
    # Service Info
    service_name: str = "emotion-detection"
    service_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = Field(default=8002, env="EMOTION_DETECTION_PORT")
    log_level: str = "INFO"
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6380, env="REDIS_PORT")
    redis_db: int = 0
    redis_stream_pattern: str = "emotion:frames:*"
    redis_consumer_group: str = "emotion-detection-group"
    redis_consumer_name: str = "emotion-worker-1"
    redis_block_ms: int = 5000  # Block for 5 seconds when reading
    redis_batch_size: int = 10  # Read up to 10 messages at a time
    
    # Model Configuration
    yolo_model_path: str = Field(
        default="yolov8n.pt",
        description="Path to YOLOv8 model (will auto-download if not found)"
    )
    fer_model_name: str = Field(
        default="Emotion",
        description="DeepFace emotion model name"
    )
    fer_backend: str = Field(
        default="opencv",
        description="DeepFace backend (opencv, ssd, etc.)"
    )
    
    # Processing Configuration
    process_every_n_frames: int = Field(
        default=5,  # Increased from 3 for memory optimization
        description="Process every Nth frame for efficiency"
    )
    max_memory_mb: int = Field(
        default=512,  # Reduced from 2000 for 12GB system
        description="Maximum memory usage in MB"
    )
    confidence_threshold: float = Field(
        default=0.5,
        description="Minimum confidence for face detection"
    )
    
    # Performance
    batch_processing: bool = True
    use_cuda: bool = True  # Will be checked at runtime
    num_workers: int = 1
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
