"""Abstract rule interface and rule types for VANTA-19."""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from collections import deque

from .models import CrowdSentiment

logger = logging.getLogger(__name__)


class Alert:
    """Alert triggered by a rule."""
    
    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        camera_id: str,
        timestamp: datetime,
        severity: str,
        message: str,
        sentiment_snapshot: Dict[str, Any]
    ):
        """
        Initialize alert.
        
        Args:
            rule_id: Rule identifier
            rule_name: Human-readable rule name
            camera_id: Camera that triggered the alert
            timestamp: When the alert was triggered
            severity: Alert severity (info, warning, critical)
            message: Human-readable alert message
            sentiment_snapshot: Sentiment data that triggered the rule
        """
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.camera_id = camera_id
        self.timestamp = timestamp
        self.severity = severity
        self.message = message
        self.sentiment_snapshot = sentiment_snapshot
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "message": self.message,
            "sentiment_snapshot": self.sentiment_snapshot
        }


class Rule(ABC):
    """Abstract base class for rules."""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        enabled: bool = True,
        priority: int = 0
    ):
        """
        Initialize rule.
        
        Args:
            rule_id: Unique rule identifier
            name: Human-readable rule name
            enabled: Whether rule is active
            priority: Rule priority (higher = more important)
        """
        self.rule_id = rule_id
        self.name = name
        self.enabled = enabled
        self.priority = priority
    
    @abstractmethod
    def evaluate(self, sentiment: CrowdSentiment) -> Optional[Alert]:
        """
        Evaluate sentiment against rule.
        
        Args:
            sentiment: Crowd sentiment to evaluate
            
        Returns:
            Alert if triggered, None otherwise
        """
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """
        Get rule configuration.
        
        Returns:
            Dictionary with rule configuration
        """
        pass


class ThresholdRule(Rule):
    """Trigger if emotion percentage exceeds threshold."""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        emotion: str,
        threshold: float,
        action: str = "alert",
        enabled: bool = True,
        priority: int = 0,
        **kwargs  # Accept unknown params from database
    ):
        """
        Initialize threshold rule.
        
        Args:
            rule_id: Unique rule identifier
            name: Human-readable rule name
            emotion: Emotion to monitor (happy, sad, angry, etc.)
            threshold: Threshold percentage (0.0 to 1.0)
            action: Action to take when triggered
            enabled: Whether rule is active
            priority: Rule priority
        """
        super().__init__(rule_id, name, enabled, priority)
        self.emotion = emotion
        self.threshold = threshold
        self.action = action
    
    def evaluate(self, sentiment: CrowdSentiment) -> Optional[Alert]:
        """Evaluate if emotion exceeds threshold."""
        if not self.enabled:
            return None
        
        # Check if emotion exists in distribution
        emotion_stats = sentiment.emotion_distribution.get(self.emotion)
        if not emotion_stats:
            return None
        
        # Convert percentage (0-100) to ratio (0-1) for comparison
        emotion_ratio = emotion_stats.percentage / 100.0
        
        if emotion_ratio > self.threshold:
            message = (
                f"Emotion '{self.emotion}' exceeds threshold: "
                f"{emotion_stats.percentage:.1f}% > {self.threshold*100:.1f}%"
            )
            
            return Alert(
                rule_id=self.rule_id,
                rule_name=self.name,
                camera_id=sentiment.camera_id,
                timestamp=sentiment.timestamp,
                severity="warning",
                message=message,
                sentiment_snapshot={
                    "dominant_emotion": sentiment.dominant_emotion,
                    "mood_score": sentiment.mood_score,
                    "total_faces": sentiment.total_faces_observed,
                    "triggered_emotion": self.emotion,
                    "triggered_percentage": emotion_stats.percentage
                }
            )
        
        return None
    
    def get_config(self) -> Dict[str, Any]:
        """Get threshold rule configuration."""
        return {
            "type": "threshold",
            "rule_id": self.rule_id,
            "name": self.name,
            "emotion": self.emotion,
            "threshold": self.threshold,
            "action": self.action,
            "enabled": self.enabled,
            "priority": self.priority
        }


class TrendRule(Rule):
    """Trigger if trend changes significantly."""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        direction: str = "declining",  # improving, declining, stable
        min_magnitude: float = 0.1,
        action: str = "alert",
        enabled: bool = True,
        priority: int = 0,
        **kwargs  # Accept unknown params from database
    ):
        """
        Initialize trend rule.
        
        Args:
            rule_id: Unique rule identifier
            name: Human-readable rule name
            direction: Expected trend direction (improving/declining/stable)
            min_magnitude: Minimum magnitude for trigger (0.0 to 1.0)
            action: Action to take when triggered
            enabled: Whether rule is active
            priority: Rule priority
        """
        super().__init__(rule_id, name, enabled, priority)
        self.direction = direction
        self.min_magnitude = min_magnitude
        self.action = action
    
    def evaluate(self, sentiment: CrowdSentiment) -> Optional[Alert]:
        """Evaluate if trend matches rule."""
        if not self.enabled:
            return None
        
        # Check if trend matches
        if sentiment.trend != self.direction:
            return None
        
        # Check if magnitude is significant
        if sentiment.trend_magnitude is None:
            return None
        
        if sentiment.trend_magnitude >= self.min_magnitude:
            message = (
                f"Mood trend is {sentiment.trend} with magnitude "
                f"{sentiment.trend_magnitude:.2f} (>= {self.min_magnitude:.2f})"
            )
            
            return Alert(
                rule_id=self.rule_id,
                rule_name=self.name,
                camera_id=sentiment.camera_id,
                timestamp=sentiment.timestamp,
                severity="critical" if sentiment.trend == "declining" else "info",
                message=message,
                sentiment_snapshot={
                    "trend": sentiment.trend,
                    "trend_magnitude": sentiment.trend_magnitude,
                    "mood_score": sentiment.mood_score,
                    "dominant_emotion": sentiment.dominant_emotion,
                    "total_faces": sentiment.total_faces_observed
                }
            )
        
        return None
    
    def get_config(self) -> Dict[str, Any]:
        """Get trend rule configuration."""
        return {
            "type": "trend",
            "rule_id": self.rule_id,
            "name": self.name,
            "direction": self.direction,
            "min_magnitude": self.min_magnitude,
            "action": self.action,
            "enabled": self.enabled,
            "priority": self.priority
        }


class DurationRule(Rule):
    """Trigger if condition persists for X seconds."""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        emotion: str = "angry",
        threshold: float = 0.5,
        duration_seconds: int = 60,
        action: str = "alert",
        enabled: bool = True,
        priority: int = 0,
        **kwargs  # Accept unknown params from database
    ):
        """
        Initialize duration rule.
        
        Args:
            rule_id: Unique rule identifier
            name: Human-readable rule name
            emotion: Emotion to monitor
            threshold: Emotion percentage threshold (0.0 to 1.0)
            duration_seconds: How long condition must persist
            action: Action to take when triggered
            enabled: Whether rule is active
            priority: Rule priority
        """
        super().__init__(rule_id, name, enabled, priority)
        self.emotion = emotion
        self.threshold = threshold
        self.duration_seconds = duration_seconds
        self.action = action
        
        # Track condition state per camera
        self._condition_start: Dict[str, datetime] = {}
        # Keep history of last N evaluations
        self._history: Dict[str, deque] = {}
        self._max_history = 100
    
    def evaluate(self, sentiment: CrowdSentiment) -> Optional[Alert]:
        """Evaluate if condition persists for duration."""
        if not self.enabled:
            return None
        
        camera_id = sentiment.camera_id
        
        # Initialize history for camera if needed
        if camera_id not in self._history:
            self._history[camera_id] = deque(maxlen=self._max_history)
        
        # Check if emotion meets threshold
        emotion_stats = sentiment.emotion_distribution.get(self.emotion)
        condition_met = False
        
        if emotion_stats:
            emotion_ratio = emotion_stats.percentage / 100.0
            condition_met = emotion_ratio > self.threshold
        
        # Update history
        self._history[camera_id].append({
            "timestamp": sentiment.timestamp,
            "condition_met": condition_met
        })
        
        # If condition is met
        if condition_met:
            # Start tracking if not already
            if camera_id not in self._condition_start:
                self._condition_start[camera_id] = sentiment.timestamp
            
            # Check if duration reached
            duration = (sentiment.timestamp - self._condition_start[camera_id]).total_seconds()
            
            if duration >= self.duration_seconds:
                message = (
                    f"Emotion '{self.emotion}' exceeded {self.threshold*100:.1f}% "
                    f"for {duration:.0f} seconds (>= {self.duration_seconds}s)"
                )
                
                # Reset tracking after alert
                del self._condition_start[camera_id]
                
                return Alert(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    camera_id=camera_id,
                    timestamp=sentiment.timestamp,
                    severity="critical",
                    message=message,
                    sentiment_snapshot={
                        "dominant_emotion": sentiment.dominant_emotion,
                        "mood_score": sentiment.mood_score,
                        "total_faces": sentiment.total_faces_observed,
                        "triggered_emotion": self.emotion,
                        "triggered_percentage": emotion_stats.percentage if emotion_stats else 0,
                        "duration_seconds": int(duration)
                    }
                )
        else:
            # Condition not met, reset tracking
            if camera_id in self._condition_start:
                del self._condition_start[camera_id]
        
        return None
    
    def get_config(self) -> Dict[str, Any]:
        """Get duration rule configuration."""
        return {
            "type": "duration",
            "rule_id": self.rule_id,
            "name": self.name,
            "emotion": self.emotion,
            "threshold": self.threshold,
            "duration_seconds": self.duration_seconds,
            "action": self.action,
            "enabled": self.enabled,
            "priority": self.priority
        }
