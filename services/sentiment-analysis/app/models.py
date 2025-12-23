"""Pydantic models for Sentiment Analysis Service."""
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field


class EmotionStats(BaseModel):
    """Statistics for a single emotion type."""
    
    count: int = Field(..., description="Number of occurrences")
    avg_confidence: float = Field(..., ge=0.0, le=1.0, description="Average confidence")
    percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of total")
    
    class Config:
        json_schema_extra = {
            "example": {
                "count": 28,
                "avg_confidence": 0.88,
                "percentage": 66.7
            }
        }


class CrowdSentiment(BaseModel):
    """Crowd-level emotion aggregation result (VANTA-18)."""
    
    timestamp: datetime = Field(..., description="Timestamp of aggregation")
    camera_id: str = Field(..., description="Camera identifier")
    total_faces_observed: int = Field(..., ge=0, description="Total faces in window")
    emotion_distribution: Dict[str, EmotionStats] = Field(
        ...,
        description="Distribution of emotions with statistics"
    )
    dominant_emotion: Optional[str] = Field(
        None,
        description="Most prevalent emotion (highest count)"
    )
    mood_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Mood score: (happiness_count - anger_count) / total_faces"
    )
    trend: Literal["improving", "stable", "declining"] = Field(
        ...,
        description="Mood trend compared to previous window"
    )
    trend_magnitude: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Magnitude of mood change (0.0 to 1.0)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-01-15T14:23:45.123Z",
                "camera_id": "cam_0",
                "total_faces_observed": 42,
                "emotion_distribution": {
                    "happy": {"count": 28, "avg_confidence": 0.88, "percentage": 66.7},
                    "neutral": {"count": 10, "avg_confidence": 0.75, "percentage": 23.8},
                    "sad": {"count": 3, "avg_confidence": 0.82, "percentage": 7.1},
                    "angry": {"count": 1, "avg_confidence": 0.61, "percentage": 2.4}
                },
                "dominant_emotion": "happy",
                "mood_score": 0.73,
                "trend": "improving",
                "trend_magnitude": 0.15
            }
        }


class EmotionData(BaseModel):
    """Input model for emotion detection results from Redis."""
    
    camera_id: str = Field(..., description="Camera identifier")
    timestamp: datetime = Field(..., description="Timestamp of emotion detection")
    frame_number: int = Field(..., description="Frame number")
    faces: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of detected faces with bounding boxes"
    )
    emotions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of emotion predictions per face"
    )
    emotion_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of each emotion detected"
    )
    dominant_emotion: Optional[str] = Field(
        None,
        description="Most prevalent emotion in frame"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "camera_id": "cam_001",
                "timestamp": "2024-01-15T10:30:00Z",
                "frame_number": 150,
                "faces": [
                    {
                        "bbox": [100, 200, 300, 400],
                        "emotions": {
                            "happy": 0.85,
                            "neutral": 0.10,
                            "sad": 0.05
                        },
                        "dominant_emotion": "happy"
                    }
                ],
                "emotion_counts": {"happy": 2, "neutral": 1},
                "dominant_emotion": "happy"
            }
        }


class SentimentResult(BaseModel):
    """Aggregated sentiment result for publishing."""
    
    timestamp: datetime = Field(..., description="Timestamp of sentiment calculation")
    window_start: datetime = Field(..., description="Aggregation window start")
    window_end: datetime = Field(..., description="Aggregation window end")
    camera_ids: List[str] = Field(..., description="Cameras included in aggregation")
    total_faces: int = Field(..., description="Total faces analyzed")
    emotion_distribution: Dict[str, float] = Field(
        ...,
        description="Percentage distribution of emotions"
    )
    dominant_emotion: str = Field(..., description="Overall dominant emotion")
    sentiment_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Sentiment score from -1 (negative) to 1 (positive)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in sentiment calculation"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-01-15T10:30:10Z",
                "window_start": "2024-01-15T10:30:00Z",
                "window_end": "2024-01-15T10:30:10Z",
                "camera_ids": ["cam_001", "cam_002"],
                "total_faces": 15,
                "emotion_distribution": {
                    "happy": 0.60,
                    "neutral": 0.30,
                    "sad": 0.10
                },
                "dominant_emotion": "happy",
                "sentiment_score": 0.75,
                "confidence": 0.85
            }
        }


class RuleDefinition(BaseModel):
    """Rule configuration for sentiment evaluation."""
    
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field(..., description="Rule purpose description")
    condition: str = Field(..., description="Rule condition expression")
    action: str = Field(..., description="Action to take when triggered")
    priority: int = Field(default=0, description="Rule priority (higher = more important)")
    enabled: bool = Field(default=True, description="Whether rule is active")
    
    class Config:
        json_schema_extra = {
            "example": {
                "rule_id": "high_negative_sentiment",
                "name": "High Negative Sentiment Alert",
                "description": "Trigger alert when negative sentiment exceeds threshold",
                "condition": "sentiment_score < -0.5 and confidence > 0.7",
                "action": "send_alert",
                "priority": 10,
                "enabled": True
            }
        }


class DatabaseStatus(BaseModel):
    """PostgreSQL database connection status."""
    
    connected: bool
    connection_pool_size: Optional[int] = None
    error: Optional[str] = None


class RedisStatus(BaseModel):
    """Redis connection status."""
    
    connected: bool
    input_streams: int = 0
    consumer_group_exists: bool = False
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Health check timestamp")
    database: DatabaseStatus = Field(..., description="PostgreSQL status")
    redis: RedisStatus = Field(..., description="Redis status")
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Service metrics"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "sentiment-analysis",
                "version": "0.1.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "database": {
                    "connected": True,
                    "connection_pool_size": 10
                },
                "redis": {
                    "connected": True,
                    "input_streams": 2,
                    "consumer_group_exists": True
                },
                "metrics": {
                    "emotions_processed": 1250,
                    "sentiments_published": 125,
                    "uptime_seconds": 3600,
                    "memory_usage_mb": 128
                }
            }
        }
