"""
Sentiment Analysis Service
Crowd-level emotion aggregation and rule evaluation
"""
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Sentiment Analysis Service",
    description="Crowd emotion aggregation for VantageNet",
    version="0.1.0"
)

@app.get("/health")
async def health_check():
    """Health check endpoint for service monitoring."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "sentiment-analysis",
            "version": "0.1.0"
        }
    )

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Sentiment Analysis",
        "description": "Crowd emotion aggregation service",
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
        port=int(os.getenv("SENTIMENT_ANALYSIS_PORT", 8003)),
        reload=True
    )
