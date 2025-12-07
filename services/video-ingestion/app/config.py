"""
Configuration settings for Video Ingestion Service
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Service Configuration
    service_name: str = "video-ingestion"
    service_version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8001
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6380
    redis_stream_prefix: str = "emotion:frames"
    
    # Video Processing Configuration
    target_fps: int = 10
    frame_max_size_kb: int = 50
    jpeg_quality: int = 85
    max_concurrent_streams: int = 2  # Reduced from 4 
    
    # Connection Management
    reconnect_interval_seconds: int = 30
    max_reconnect_attempts: int = 10
    
    # Memory Limits
    max_memory_mb: int = 256  # Reduced from 512 
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
