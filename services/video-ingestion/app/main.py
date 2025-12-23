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
from app.annotation_overlay import annotation_overlay

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
    
    # Start annotation overlay for server-side rendering
    try:
        await annotation_overlay.connect()
        await annotation_overlay.start()
        logger.info("Annotation overlay started")
    except Exception as e:
        logger.error(f"Failed to start annotation overlay: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down service...")
    await annotation_overlay.stop()
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
    import argparse
    import uvicorn
    
    parser = argparse.ArgumentParser(description='Video Ingestion Service')
    parser.add_argument('--camera-id', type=str, help='Camera ID for test mode')
    parser.add_argument('--source', type=str, help='Video source path for test mode')
    parser.add_argument('--fps', type=int, default=30, help='Target FPS for test mode')
    
    args = parser.parse_args()
    
    # If test mode (camera-id and source provided), run in CLI mode
    if args.camera_id and args.source:
        logger.info(f"Running in CLI test mode: camera_id={args.camera_id}, source={args.source}")
        
        async def run_test_ingestion():
            """Run video ingestion in test mode"""
            from app.video_capture import VideoCapture
            from app.models import CameraSourceType
            
            # Connect to Redis
            await redis_client.connect()
            logger.info("Connected to Redis")
            
            # Determine source type based on file extension
            if args.source.endswith(('.mp4', '.avi', '.mov')):
                source_type = CameraSourceType.FILE
            elif args.source.startswith('rtsp://'):
                source_type = CameraSourceType.RTSP
            else:
                source_type = CameraSourceType.WEBCAM
            
            # Create video capture
            capture = VideoCapture(
                camera_id=args.camera_id,
                name=f"Test Camera {args.camera_id}",
                source_type=source_type,
                source_url=args.source,
                fps=args.fps,
                loop=False  # Don't loop video files in test mode
            )
            
            # Start processing
            await capture.start()
            logger.info(f"Started ingestion from {args.source}")
            
            # Wait for capture to become active
            from app.models import CameraStatus
            for _ in range(10):
                if capture.status == CameraStatus.ACTIVE:
                    break
                await asyncio.sleep(0.5)
            
            if capture.status != CameraStatus.ACTIVE:
                logger.error("Camera failed to start")
                return
            
            logger.info(f"Camera active, processing video...")
            
            try:
                # Keep running until video ends or interrupted
                while capture.status == CameraStatus.ACTIVE:
                    await asyncio.sleep(1)
                    logger.info(f"Frames processed: {capture.frame_count}, dropped: {capture.frames_dropped}")
                logger.info(f"Video processing completed. Final status: {capture.status}")
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
            finally:
                await capture.stop()
                await redis_client.disconnect()
                logger.info("Stopped ingestion")
        
        # Run async test mode
        asyncio.run(run_test_ingestion())
    else:
        # Run as FastAPI service
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=True,
            log_config=None  # Use our custom logging
        )
