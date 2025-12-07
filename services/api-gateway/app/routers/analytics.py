"""API routers for analytics endpoints."""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter

from ..models import (
    AnalyticsResponse,
    SentimentSummary,
    EmotionStats
)
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsResponse)
async def get_analytics_summary():
    """
    Get current sentiment analytics summary.
    
    For Sprint 1: Returns dummy data.
    Sprint 2: Will query sentiment-analysis service and PostgreSQL.
    """
    now = datetime.now()
    
    # Dummy data for Sprint 1
    current_sentiment = SentimentSummary(
        timestamp=now,
        sentiment_score=0.42,
        dominant_emotion="happy",
        total_faces=15,
        active_cameras=2,
        emotion_distribution={
            "happy": 0.53,
            "neutral": 0.27,
            "surprised": 0.13,
            "sad": 0.07
        },
        confidence=0.78
    )
    
    recent_emotions = [
        EmotionStats(emotion="happy", count=8, percentage=0.53),
        EmotionStats(emotion="neutral", count=4, percentage=0.27),
        EmotionStats(emotion="surprised", count=2, percentage=0.13),
        EmotionStats(emotion="sad", count=1, percentage=0.07)
    ]
    
    return AnalyticsResponse(
        current_sentiment=current_sentiment,
        recent_emotions=recent_emotions,
        period_start=now - timedelta(seconds=30),
        period_end=now
    )
