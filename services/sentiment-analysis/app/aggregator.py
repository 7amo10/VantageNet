"""Emotion aggregation logic for sentiment analysis."""
import logging
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .config import settings
from .models import EmotionData, SentimentResult

logger = logging.getLogger(__name__)


class EmotionAggregator:
    """Aggregates emotion data into sentiment scores."""
    
    # Emotion to sentiment score mapping
    # Positive emotions: happy (0.8), surprise (0.3)
    # Neutral: neutral (0.0)
    # Negative: sad (-0.6), angry (-0.8), fear (-0.7), disgust (-0.7)
    EMOTION_SCORES = {
        "happy": 0.8,
        "surprise": 0.3,
        "neutral": 0.0,
        "sad": -0.6,
        "angry": -0.8,
        "fear": -0.7,
        "disgust": -0.7
    }
    
    def __init__(self):
        """Initialize aggregator with empty buffer."""
        self.emotion_buffer: List[EmotionData] = []
        self.window_seconds = settings.aggregation_window_seconds
        self.min_emotions = settings.min_emotions_for_sentiment
        
    def add_emotion(self, emotion_data: EmotionData) -> None:
        """
        Add emotion data to aggregation buffer.
        
        Args:
            emotion_data: Emotion detection result to add
        """
        self.emotion_buffer.append(emotion_data)
        logger.debug(
            f"Added emotion from {emotion_data.camera_id}, "
            f"buffer size: {len(self.emotion_buffer)}"
        )
        
        # Clean old data
        self._cleanup_old_data()
    
    def _cleanup_old_data(self) -> None:
        """Remove emotion data older than aggregation window."""
        cutoff_time = datetime.now() - timedelta(seconds=self.window_seconds * 2)
        
        original_size = len(self.emotion_buffer)
        self.emotion_buffer = [
            e for e in self.emotion_buffer
            if e.timestamp > cutoff_time
        ]
        
        removed = original_size - len(self.emotion_buffer)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} old emotion records")
    
    def can_aggregate(self) -> bool:
        """
        Check if enough data is available for aggregation.
        
        Returns:
            bool: True if aggregation can be performed
        """
        return len(self.emotion_buffer) >= self.min_emotions
    
    def aggregate(self) -> Optional[SentimentResult]:
        """
        Aggregate buffered emotions into sentiment result.
        
        Returns:
            Optional[SentimentResult]: Aggregated sentiment or None if insufficient data
        """
        if not self.can_aggregate():
            logger.debug(
                f"Insufficient data for aggregation: {len(self.emotion_buffer)} < {self.min_emotions}"
            )
            return None
        
        try:
            # Get time window
            now = datetime.now()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            # Filter emotions in window
            window_emotions = [
                e for e in self.emotion_buffer
                if e.timestamp >= window_start
            ]
            
            if len(window_emotions) < self.min_emotions:
                return None
            
            # Collect statistics
            camera_ids = list(set(e.camera_id for e in window_emotions))
            total_faces = sum(len(e.faces) for e in window_emotions)
            
            # Aggregate emotion counts
            emotion_totals = defaultdict(int)
            for emotion_data in window_emotions:
                for emotion, count in emotion_data.emotion_counts.items():
                    emotion_totals[emotion] += count
            
            # Calculate emotion distribution
            total_emotion_count = sum(emotion_totals.values())
            if total_emotion_count == 0:
                logger.warning("No emotions detected in aggregation window")
                return None
            
            emotion_distribution = {
                emotion: count / total_emotion_count
                for emotion, count in emotion_totals.items()
            }
            
            # Find dominant emotion
            dominant_emotion = max(emotion_totals.items(), key=lambda x: x[1])[0]
            
            # Calculate sentiment score (weighted average)
            sentiment_score = sum(
                self.EMOTION_SCORES.get(emotion, 0.0) * percentage
                for emotion, percentage in emotion_distribution.items()
            )
            
            # Calculate confidence based on data consistency
            confidence = self._calculate_confidence(
                window_emotions,
                emotion_distribution,
                dominant_emotion
            )
            
            result = SentimentResult(
                timestamp=now,
                window_start=window_start,
                window_end=now,
                camera_ids=camera_ids,
                total_faces=total_faces,
                emotion_distribution=emotion_distribution,
                dominant_emotion=dominant_emotion,
                sentiment_score=round(sentiment_score, 3),
                confidence=round(confidence, 3)
            )
            
            logger.info(
                f"Aggregated sentiment: score={result.sentiment_score:.2f}, "
                f"dominant={result.dominant_emotion}, "
                f"confidence={result.confidence:.2f}, "
                f"faces={total_faces}, cameras={len(camera_ids)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error during aggregation: {e}")
            return None
    
    def _calculate_confidence(
        self,
        emotions: List[EmotionData],
        distribution: Dict[str, float],
        dominant: str
    ) -> float:
        """
        Calculate confidence score for sentiment result.
        
        Confidence is higher when:
        - More emotions are analyzed
        - Dominant emotion has high percentage
        - Multiple cameras agree
        
        Args:
            emotions: List of emotion data in window
            distribution: Emotion percentage distribution
            dominant: Dominant emotion
            
        Returns:
            float: Confidence score 0.0-1.0
        """
        # Factor 1: Data volume (more data = higher confidence)
        volume_factor = min(len(emotions) / (self.min_emotions * 3), 1.0)
        
        # Factor 2: Dominant emotion percentage
        dominant_percentage = distribution.get(dominant, 0.0)
        dominant_factor = dominant_percentage
        
        # Factor 3: Camera agreement (more cameras = higher confidence)
        unique_cameras = len(set(e.camera_id for e in emotions))
        camera_factor = min(unique_cameras / 3, 1.0)  # Normalize to 3 cameras
        
        # Weighted average
        confidence = (
            0.4 * volume_factor +
            0.4 * dominant_factor +
            0.2 * camera_factor
        )
        
        return confidence
    
    def get_buffer_stats(self) -> Dict[str, int]:
        """
        Get current buffer statistics.
        
        Returns:
            Dict with buffer statistics
        """
        return {
            "buffer_size": len(self.emotion_buffer),
            "can_aggregate": self.can_aggregate(),
            "unique_cameras": len(set(e.camera_id for e in self.emotion_buffer))
        }
