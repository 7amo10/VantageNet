"""Crowd-level emotion aggregation for VANTA-18."""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal

from .models import CrowdSentiment, EmotionStats

logger = logging.getLogger(__name__)


class CrowdEmotionAggregator:
    """Aggregates individual face emotions into crowd-level sentiment."""
    
    def __init__(self, window_seconds: int = 30):
        """
        Initialize the crowd emotion aggregator.
        
        Args:
            window_seconds: Sliding window size in seconds (default: 30)
        """
        self.window_seconds = window_seconds
        
        # Buffer stores: (timestamp, camera_id, emotion, confidence)
        self.emotion_buffer: List[tuple] = []
        
        # Previous window for trend calculation
        self.previous_mood_score: Dict[str, float] = {}
        
    def add_emotion(
        self,
        camera_id: str,
        timestamp: datetime,
        emotion: str,
        confidence: float
    ) -> None:
        """
        Add individual emotion to the buffer.
        
        Args:
            camera_id: Camera identifier
            timestamp: When the emotion was detected
            emotion: Emotion type (happy, sad, angry, etc.)
            confidence: Confidence score (0.0 to 1.0)
        """
        self.emotion_buffer.append((timestamp, camera_id, emotion, confidence))
        
        # Cleanup old data
        self._cleanup_old_data()
        
    def _cleanup_old_data(self) -> None:
        """Remove emotions older than 2x window size."""
        cutoff_time = datetime.now() - timedelta(seconds=self.window_seconds * 2)
        
        original_size = len(self.emotion_buffer)
        self.emotion_buffer = [
            e for e in self.emotion_buffer
            if e[0] > cutoff_time
        ]
        
        removed = original_size - len(self.emotion_buffer)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} old emotion records")
    
    def aggregate_camera(
        self,
        camera_id: str,
        current_time: Optional[datetime] = None
    ) -> Optional[CrowdSentiment]:
        """
        Aggregate emotions for a specific camera into crowd sentiment.
        
        Args:
            camera_id: Camera to aggregate
            current_time: Current timestamp (defaults to now)
            
        Returns:
            CrowdSentiment if sufficient data, None otherwise
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Get emotions in the sliding window
        window_start = current_time - timedelta(seconds=self.window_seconds)
        window_emotions = [
            (ts, cam, emotion, conf)
            for ts, cam, emotion, conf in self.emotion_buffer
            if cam == camera_id and ts >= window_start and ts <= current_time
        ]
        
        # Need at least one emotion
        if not window_emotions:
            logger.debug(f"No emotions for camera {camera_id} in window")
            return None
        
        # Count emotions and confidences
        emotion_counts: Dict[str, int] = defaultdict(int)
        emotion_confidences: Dict[str, List[float]] = defaultdict(list)
        
        for _, _, emotion, confidence in window_emotions:
            emotion_counts[emotion] += 1
            emotion_confidences[emotion].append(confidence)
        
        total_faces = sum(emotion_counts.values())
        
        if total_faces == 0:
            logger.debug(f"No faces for camera {camera_id}")
            return None
        
        # Calculate emotion statistics
        emotion_distribution: Dict[str, EmotionStats] = {}
        
        for emotion, count in emotion_counts.items():
            avg_confidence = sum(emotion_confidences[emotion]) / len(emotion_confidences[emotion])
            percentage = (count / total_faces) * 100.0
            
            emotion_distribution[emotion] = EmotionStats(
                count=count,
                avg_confidence=round(avg_confidence, 3),
                percentage=round(percentage, 1)
            )
        
        # Determine dominant emotion (highest count)
        dominant_emotion = max(emotion_counts, key=emotion_counts.get)
        
        # Calculate mood score: (happy_count - angry_count) / total_faces
        happy_count = emotion_counts.get("happy", 0)
        angry_count = emotion_counts.get("angry", 0)
        mood_score = (happy_count - angry_count) / total_faces
        mood_score = max(-1.0, min(1.0, mood_score))  # Clamp to [-1, 1]
        
        # Calculate trend
        trend, trend_magnitude = self._calculate_trend(camera_id, mood_score)
        
        return CrowdSentiment(
            timestamp=current_time,
            camera_id=camera_id,
            total_faces_observed=total_faces,
            emotion_distribution=emotion_distribution,
            dominant_emotion=dominant_emotion,
            mood_score=round(mood_score, 3),
            trend=trend,
            trend_magnitude=round(trend_magnitude, 3) if trend_magnitude else None
        )
    
    def _calculate_trend(
        self,
        camera_id: str,
        current_mood_score: float
    ) -> tuple[Literal["improving", "stable", "declining"], Optional[float]]:
        """
        Calculate mood trend by comparing with previous window.
        
        Args:
            camera_id: Camera identifier
            current_mood_score: Current mood score
            
        Returns:
            Tuple of (trend_direction, trend_magnitude)
        """
        # Get previous mood score for this camera
        previous_mood = self.previous_mood_score.get(camera_id)
        
        if previous_mood is None:
            # First aggregation, trend is stable
            self.previous_mood_score[camera_id] = current_mood_score
            return "stable", 0.0
        
        # Calculate change
        change = current_mood_score - previous_mood
        magnitude = abs(change)
        
        # Update previous mood
        self.previous_mood_score[camera_id] = current_mood_score
        
        # Determine trend (threshold: 0.05 for meaningful change)
        if magnitude < 0.05:
            trend = "stable"
        elif change > 0:
            trend = "improving"
        else:
            trend = "declining"
        
        return trend, magnitude
    
    def aggregate_all_cameras(
        self,
        current_time: Optional[datetime] = None
    ) -> List[CrowdSentiment]:
        """
        Aggregate emotions for all active cameras.
        
        Args:
            current_time: Current timestamp (defaults to now)
            
        Returns:
            List of CrowdSentiment for each camera
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Get unique camera IDs in the window
        window_start = current_time - timedelta(seconds=self.window_seconds)
        active_cameras = set(
            cam for ts, cam, _, _ in self.emotion_buffer
            if ts >= window_start
        )
        
        # Aggregate each camera
        results = []
        for camera_id in active_cameras:
            sentiment = self.aggregate_camera(camera_id, current_time)
            if sentiment:
                results.append(sentiment)
        
        return results
    
    def get_buffer_stats(self) -> Dict[str, int]:
        """
        Get statistics about the current buffer.
        
        Returns:
            Dictionary with buffer statistics
        """
        total = len(self.emotion_buffer)
        cameras = len(set(cam for _, cam, _, _ in self.emotion_buffer))
        
        return {
            "total_emotions": total,
            "active_cameras": cameras,
            "window_seconds": self.window_seconds
        }
