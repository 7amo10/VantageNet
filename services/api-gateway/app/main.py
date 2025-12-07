"""
API Gateway Service
REST + WebSocket APIs for VantageNet
"""
import os
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="VantageNet API Gateway",
    description="REST + WebSocket APIs for Emotion Analytics Platform",
    version="0.1.0"
)

# CORS configuration for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint for service monitoring."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "api-gateway",
            "version": "0.1.0"
        }
    )

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "VantageNet API Gateway",
        "description": "Central API for Emotion Analytics Platform",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "websocket": "/ws"
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message received: {data}")
    except Exception:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("API_GATEWAY_PORT", 8000)),
        reload=True
    )
