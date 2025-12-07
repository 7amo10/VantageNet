"""
Emotion Detection Service
Face detection + emotion classification using YOLO and FER
This service runs LOCALLY with your my_env virtual environment (PyTorch)
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
import psutil
import torch
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .config import settings
from .models import HealthResponse
from .redis_consumer import redis_consumer
from .model_loader import model_loader
from .processor import frame_processor

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "%(name)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    Handles model loading, Redis connection, and graceful shutdown.
    """
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    
    # Connect to Redis
    redis_connected = await redis_consumer.connect()
    if not redis_connected:
        logger.error("Failed to connect to Redis, exiting")
        sys.exit(1)
    
    logger.info("Successfully connected to Redis")
    
    # Load ML models
    logger.info("Loading ML models...")
    models_loaded = await model_loader.load_models()
    
    if not models_loaded:
        logger.error("Failed to load models, exiting")
        sys.exit(1)
    
    logger.info("✓ All models loaded successfully")
    
    # Start frame processor
    await frame_processor.start()
    
    logger.info(f"✓ Service ready on port {settings.port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down service...")
    
    # Stop frame processor gracefully (finish current frame)
    await frame_processor.stop()
    
    # Stop Redis consumer
    await redis_consumer.stop()
    
    # Disconnect from Redis
    await redis_consumer.disconnect()
    
    # Unload models
    model_loader.unload_models()
    
    logger.info("Service shutdown complete")


app = FastAPI(
    title="Emotion Detection Service",
    description="Face detection and emotion classification for VantageNet",
    version=settings.service_version,
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint with model status and metrics.
    
    Returns:
    - Service status and version
    - Redis connection status  
    - Model loading status
    - Processing statistics
    - Memory usage
    - PyTorch/CUDA availability
    """
    redis_connected = await redis_consumer.is_connected()
    model_status = model_loader.get_model_status()
    stats = frame_processor.get_stats()
    
    # Get memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    # Check PyTorch
    pytorch_available = torch.cuda.is_available() if hasattr(torch, 'cuda') else False
    
    return HealthResponse(
        status="healthy" if redis_connected and model_loader.models_loaded else "degraded",
        service=settings.service_name,
        version=settings.service_version,
        redis_connected=redis_connected,
        models=model_status,
        frames_processed=stats["frames_processed"],
        memory_usage_mb=round(memory_mb, 2),
        pytorch_available=True,
        cuda_available=pytorch_available
    )


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Emotion Detection Service",
        "description": "Face detection + emotion classification using YOLOv8 and DeepFace",
        "version": settings.service_version,
        "endpoints": {
            "health": "/health",
            "docs": "/docs"
        },
        "config": {
            "redis_stream_pattern": settings.redis_stream_pattern,
            "process_every_n_frames": settings.process_every_n_frames,
            "max_memory_mb": settings.max_memory_mb,
            "yolo_model": settings.yolo_model_path,
            "fer_model": settings.fer_model_name
        },
        "note": "This service runs locally with your PyTorch virtual environment"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )

