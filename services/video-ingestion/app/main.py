"""
Video Ingestion Service
RTSP stream processing and frame publishing to Redis
"""
import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Video Ingestion Service",
    description="RTSP stream processing for VantageNet Emotion Analytics",
    version="0.1.0"
)

@app.get("/health")
async def health_check():
    """Health check endpoint for service monitoring."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "video-ingestion",
            "version": "0.1.0"
        }
    )

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Video Ingestion",
        "description": "RTSP stream processing service",
        "endpoints": {
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("VIDEO_INGESTION_PORT", 8001)),
        reload=True
    )
