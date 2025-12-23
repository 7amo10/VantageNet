"""
API Gateway Service
REST + WebSocket APIs for VantageNet
"""
import asyncio
import logging
import sys
import psutil
from datetime import datetime
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from .config import settings
from .models import HealthResponse, ErrorResponse
from .database import database
from .websocket_manager import manager as ws_manager
from .websocket_broadcaster import broadcaster
from .routers import cameras_router, rules_router, analytics_router, alerts_router

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
    
    # Connect to database
    try:
        await database.connect()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
    
    # Start WebSocket broadcaster (VANTA-31)
    try:
        await broadcaster.start()
        logger.info("WebSocket broadcaster initialized")
    except Exception as e:
        logger.error(f"Failed to start broadcaster: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Gateway...")
    
    # Stop WebSocket broadcaster
    try:
        await broadcaster.stop()
        logger.info("WebSocket broadcaster stopped")
    except Exception as e:
        logger.error(f"Error stopping broadcaster: {e}")
    
    # Disconnect database
    try:
        await database.disconnect()
        logger.info("Database disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting database: {e}")


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
app.include_router(alerts_router)


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
            "alerts": "/api/alerts",
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
    
    VANTA-31: Enhanced with:
    - Max 100 concurrent connections
    - 30s inactivity timeout
    - Automatic reconnection support
    - 4 message types: sentiment_update, alert_triggered, rule_evaluation, camera_status
    
    Message Types:
    - sentiment_update: Real-time sentiment data (every 2s)
    - alert_triggered: Rule-triggered alerts (immediate)
    - rule_evaluation: Rule evaluation results (debugging)
    - camera_status: Camera connected/disconnected
    - connected: Connection confirmation
    - pong: Response to ping keepalive
    """
    # Try to connect (enforces max connections limit)
    connected = await ws_manager.connect(websocket)
    
    if not connected:
        return  # Connection rejected
    
    try:
        while True:
            # Wait for client messages with 30s timeout (VANTA-31 requirement)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle ping/pong for keepalive
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    # Log other client messages (for debugging)
                    logger.debug(f"WebSocket received: {data}")
                    
            except asyncio.TimeoutError:
                # Connection timeout after 30s of inactivity
                logger.info("WebSocket connection timeout after 30s inactivity")
                await websocket.close(code=1000, reason="Timeout")
                break
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
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
