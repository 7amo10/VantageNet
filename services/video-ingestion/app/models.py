"""
Data models for Video Ingestion Service
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class CameraSourceType(str, Enum):
    """Type of camera source"""
    RTSP = "rtsp"
    WEBCAM = "webcam"
    FILE = "file"


class CameraStatus(str, Enum):
    """Camera connection status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class CameraCreate(BaseModel):
    """Request model for creating/registering a camera"""
    name: str = Field(..., description="Camera name")
    source_type: CameraSourceType = Field(..., description="Type of camera source")
    source_url: str = Field(..., description="RTSP URL, webcam index, or file path")
    fps: Optional[int] = Field(default=10, description="Target frames per second", ge=1, le=30)
    enabled: Optional[bool] = Field(default=True, description="Whether camera is enabled")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional camera metadata")


class CameraResponse(BaseModel):
    """Response model for camera information"""
    camera_id: str
    name: str
    source_type: CameraSourceType
    source_url: str
    fps: int
    status: CameraStatus
    enabled: bool
    frames_processed: int
    frames_dropped: int
    last_frame_time: Optional[datetime]
    created_at: datetime
    metadata: Dict[str, Any]


class CameraListResponse(BaseModel):
    """Response model for listing cameras"""
    cameras: List[CameraResponse]
    total: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    redis_connected: bool
    active_cameras: int
    total_frames_processed: int
    memory_usage_mb: float


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    details: Optional[str] = None
