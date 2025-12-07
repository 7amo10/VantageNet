"""
Emotion Detection Service
Face detection + emotion classification using YOLO and FER
This service runs LOCALLY with your my_env virtual environment (PyTorch)
"""
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Emotion Detection Service",
    description="Face detection and emotion classification for VantageNet",
    version="0.1.0"
)

# PyTorch availability check
PYTORCH_AVAILABLE = False
try:
    import torch
    PYTORCH_AVAILABLE = True
    PYTORCH_VERSION = torch.__version__
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    PYTORCH_VERSION = "Not installed"
    CUDA_AVAILABLE = False

@app.get("/health")
async def health_check():
    """Health check endpoint for service monitoring."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "emotion-detection",
            "version": "0.1.0",
            "pytorch": {
                "available": PYTORCH_AVAILABLE,
                "version": PYTORCH_VERSION,
                "cuda_available": CUDA_AVAILABLE
            }
        }
    )

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Emotion Detection",
        "description": "Face detection + emotion classification service",
        "note": "This service runs locally with your PyTorch virtual environment",
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
        port=int(os.getenv("EMOTION_DETECTION_PORT", 8002)),
        reload=True
    )
