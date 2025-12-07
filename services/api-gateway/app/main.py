"""
API Gateway Service
REST + WebSocket APIs for VantageNet
"""
import logging
import sys
import psutil
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from .config import settings
from .models import HealthResponse, ErrorResponse
from .websocket_manager import manager as ws_manager
from .routers import cameras_router, rules_router, analytics_router

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "%(name)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Service start time
start_time = datetime.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    logger.info(f"API Gateway started on port {settings.port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Gateway...")


# Create FastAPI application
app = FastAPI(
    title="VantageNet API Gateway",
    description="REST + WebSocket APIs for Emotion Analytics Platform",
    version=settings.service_version,
    lifespan=lifespan
)

# CORS configuration for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with structured response."""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# Include routers
app.include_router(cameras_router)
app.include_router(rules_router)
app.include_router(analytics_router)


@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "VantageNet API Gateway",
        "description": "Central REST + WebSocket API for Emotion Analytics Platform",
        "version": settings.service_version,
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "cameras": "/api/cameras",
            "rules": "/api/rules",
            "analytics": "/api/analytics/summary",
            "websocket": "/ws/live"
        },
        "note": "Sprint 1 scaffold - dummy data only"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint with service status.
    
    Returns API Gateway health and WebSocket connection statistics.
    """
    # Calculate uptime
    uptime_seconds = (datetime.now() - start_time).total_seconds()
    
    # Get memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    # Get WebSocket stats
    ws_stats = ws_manager.get_stats()
    
    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.now(),
        services={
            "websocket": {
                "active_connections": ws_stats["active_connections"],
                "total_connections": ws_stats["total_connections"],
                "uptime_seconds": int(uptime_seconds)
            }
        },
        memory_usage_mb=round(memory_mb, 2)
    )


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.
    
    Message Types:
    - sentiment_update: Real-time sentiment data
    - emotion_event: Individual emotion detection events
    - alert: Rule-triggered alerts
    - connected: Connection confirmation
    """
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            
            # Handle ping/pong for keepalive
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Echo for Sprint 1 (Sprint 2 will handle commands)
                await websocket.send_json({
                    "type": "echo",
                    "data": {"message": data},
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("API_GATEWAY_PORT", 8000)),
        reload=True
    )
