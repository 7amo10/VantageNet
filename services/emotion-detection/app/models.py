"""Pydantic models for type safety and validation."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class FrameData(BaseModel):
    """Frame data received from Redis stream."""
    camera_id: str
    frame_number: int
    timestamp: str
    frame_data: bytes
    frame_size_bytes: int
    metadata: Optional[Dict[str, Any]] = None


class FaceDetection(BaseModel):
    """Individual face detection result."""
    bbox: List[float] = Field(description="Bounding box [x1, y1, x2, y2]")
    confidence: float
    face_id: Optional[str] = None


class EmotionPrediction(BaseModel):
    """Emotion classification result for a single face."""
    face_id: str
    emotion: str
    confidence: float
    all_emotions: Dict[str, float] = Field(
        description="All emotion probabilities"
    )


class EmotionResult(BaseModel):
    """Complete emotion detection result for a frame."""
    camera_id: str
    frame_number: int
    timestamp: str
    processed_at: str
    faces_detected: int
    faces: List[FaceDetection]
    emotions: List[EmotionPrediction]
    processing_time_ms: float
    frame_width: Optional[int] = None  # Width of processed frame
    frame_height: Optional[int] = None  # Height of processed frame
    metadata: Optional[Dict[str, Any]] = None


class ModelStatus(BaseModel):
    """Model loading status."""
    name: str
    loaded: bool
    memory_mb: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    redis_connected: bool
    models: List[ModelStatus]
    frames_processed: int
    memory_usage_mb: float
    pytorch_available: bool
    cuda_available: bool
