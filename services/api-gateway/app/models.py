"""Pydantic models for API Gateway Service."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class CameraSourceType(str, Enum):
    """Camera source types."""
    RTSP = "rtsp"
    WEBCAM = "webcam"
    FILE = "file"


class CameraStatus(str, Enum):
    """Camera status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class CameraCreate(BaseModel):
    """Camera creation request."""
    name: str = Field(..., description="Camera display name")
    source_type: CameraSourceType
    source_url: str = Field(..., description="RTSP URL, webcam index, or file path")
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CameraUpdate(BaseModel):
    """Camera update request."""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class CameraResponse(BaseModel):
    """Camera response model."""
    camera_id: str
    name: str
    source_type: CameraSourceType
    source_url: str
    enabled: bool
    status: CameraStatus
    frames_processed: int = 0
    last_frame_time: Optional[datetime] = None
    created_at: datetime
    metadata: Dict[str, Any]


class RuleAction(str, Enum):
    """Rule action types."""
    LOG = "log"
    ALERT = "alert"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"
    EMAIL = "email"


class RuleType(str, Enum):
    """Rule type enums (VANTA-25)."""
    THRESHOLD = "threshold"
    TREND = "trend"
    DURATION = "duration"
    SENTIMENT = "sentiment"


class RuleCreate(BaseModel):
    """Rule creation request (VANTA-20, VANTA-25)."""
    name: str = Field(..., min_length=1, max_length=200, description="Rule name")
    type: RuleType = Field(..., description="Rule type: threshold, trend, duration, or sentiment")
    condition_json: dict = Field(..., description="Rule configuration as JSON")
    action: RuleAction
    enabled: bool = True

    @classmethod
    def validate_condition_json(cls, v: dict, values: dict) -> dict:
        """Validate condition_json based on rule type."""
        rule_type = values.get('type')
        
        # Validate threshold values are in valid range (0.0-1.0)
        if 'threshold' in v:
            threshold = v['threshold']
            if not isinstance(threshold, (int, float)) or not (0.0 <= threshold <= 1.0):
                raise ValueError("Threshold must be a number between 0.0 and 1.0")
        
        # Validate sentiment_threshold
        if 'sentiment_threshold' in v:
            threshold = v['sentiment_threshold']
            if not isinstance(threshold, (int, float)) or not (0.0 <= threshold <= 1.0):
                raise ValueError("Sentiment threshold must be a number between 0.0 and 1.0")
        
        # Validate confidence threshold
        if 'min_confidence' in v:
            confidence = v['min_confidence']
            if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
                raise ValueError("Confidence must be a number between 0.0 and 1.0")
        
        return v


class RuleUpdate(BaseModel):
    """Rule update request (VANTA-20, VANTA-25)."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[RuleType] = None
    condition_json: Optional[dict] = None
    action: Optional[RuleAction] = None
    enabled: Optional[bool] = None


class RuleResponse(BaseModel):
    """Rule response model (VANTA-20, VANTA-25)."""
    id: str
    name: str
    type: str
    condition_json: dict
    action: RuleAction
    enabled: bool
    created_at: datetime
    updated_at: datetime


class RuleEvaluationResponse(BaseModel):
    """Rule evaluation history response (VANTA-25)."""
    id: str
    rule_id: str
    camera_id: Optional[str] = None
    evaluated_at: datetime
    matched: bool
    emotion: Optional[str] = None
    sentiment_score: Optional[float] = None
    threshold_value: Optional[float] = None
    evaluation_result: Optional[dict] = None
    action_taken: Optional[str] = None


class EmotionStats(BaseModel):
    """Emotion statistics."""
    emotion: str
    count: int
    percentage: float


class SentimentSummary(BaseModel):
    """Current sentiment summary."""
    timestamp: datetime
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    dominant_emotion: str
    total_faces: int
    active_cameras: int
    emotion_distribution: Dict[str, float]
    confidence: float = Field(..., ge=0.0, le=1.0)


class AnalyticsResponse(BaseModel):
    """Analytics summary response."""
    current_sentiment: SentimentSummary
    recent_emotions: List[EmotionStats]
    period_start: datetime
    period_end: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: datetime
    services: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    memory_usage_mb: float


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str  # "sentiment_update", "emotion_event", "alert", "ping"
    data: Dict[str, Any]
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
