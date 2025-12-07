"""
Video Ingestion Service
RTSP stream processing and frame publishing to Redis
"""
import os
import sys
import asyncio
import logging
import psutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import HealthResponse
from app.redis_client import redis_client
from app.camera_manager import camera_manager
from app.routers import router as camera_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "%(name)s", "message": "%(message)s"}',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    
    try:
        await redis_client.connect()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        # Continue without Redis for now
    
    yield
    
    # Shutdown
    logger.info("Shutting down service...")
    await camera_manager.stop_all()
    await redis_client.disconnect()
    logger.info("Service shutdown complete")


app = FastAPI(
    title="Video Ingestion Service",
    description="RTSP stream processing for VantageNet Emotion Analytics",
    version=settings.service_version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include camera management routes
app.include_router(camera_router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """
    Health check endpoint for service monitoring.
    
    Returns:
    - Service status and version
    - Redis connection status
    - Active camera count
    - Total frames processed
    - Current memory usage
    """
    redis_connected = await redis_client.is_connected()
    stats = camera_manager.get_stats()
    
    # Get memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    return HealthResponse(
        status="healthy" if redis_connected else "degraded",
        service=settings.service_name,
        version=settings.service_version,
        redis_connected=redis_connected,
        active_cameras=stats["active_cameras"],
        total_frames_processed=stats["total_frames_processed"],
        memory_usage_mb=round(memory_mb, 2)
    )


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Video Ingestion Service",
        "description": "RTSP stream processing and frame publishing to Redis",
        "version": settings.service_version,
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "cameras": "/cameras"
        },
        "config": {
            "target_fps": settings.target_fps,
            "max_concurrent_streams": settings.max_concurrent_streams,
            "frame_max_size_kb": settings.frame_max_size_kb
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_config=None  # Use our custom logging
    )
