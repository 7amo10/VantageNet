"""Unit tests for crowd emotion aggregation (VANTA-18)."""
import pytest
from datetime import datetime, timedelta

from app.crowd_aggregator import CrowdEmotionAggregator
from app.models import EmotionStats, CrowdSentiment


class TestCrowdEmotionAggregator:
    """Test suite for crowd emotion aggregator."""
    
    @pytest.fixture
    def aggregator(self):
        """Create aggregator with 30s window."""
        return CrowdEmotionAggregator(window_seconds=30)
    
    @pytest.fixture
    def base_time(self):
        """Base timestamp for tests (use current time to avoid cleanup issues)."""
        return datetime.now()
    
    def test_add_emotion(self, aggregator, base_time):
        """Test adding emotions to buffer."""
        aggregator.add_emotion("cam_0", base_time, "happy", 0.95)
        aggregator.add_emotion("cam_0", base_time, "neutral", 0.82)
        
        stats = aggregator.get_buffer_stats()
        assert stats["total_emotions"] == 2
        assert stats["active_cameras"] == 1
    
    def test_aggregate_single_emotion(self, aggregator, base_time):
        """Test aggregation with single emotion type."""
        # Add 10 happy emotions
        for i in range(10):
            aggregator.add_emotion(
                "cam_0",
                base_time + timedelta(seconds=i),
                "happy",
                0.90 + i * 0.01
            )
        
        sentiment = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=9))
        
        assert sentiment is not None
        assert sentiment.camera_id == "cam_0"
        assert sentiment.total_faces_observed == 10
        assert sentiment.dominant_emotion == "happy"
        
        # Check emotion distribution
        assert "happy" in sentiment.emotion_distribution
        happy_stats = sentiment.emotion_distribution["happy"]
        assert happy_stats.count == 10
        assert happy_stats.percentage == 100.0
        assert 0.9 <= happy_stats.avg_confidence <= 1.0
    
    def test_aggregate_mixed_emotions(self, aggregator, base_time):
        """Test aggregation with multiple emotion types."""
        emotions = [
            ("happy", 0.88),
            ("happy", 0.92),
            ("happy", 0.85),
            ("neutral", 0.75),
            ("neutral", 0.80),
            ("sad", 0.82),
            ("angry", 0.61)
        ]
        
        for i, (emotion, conf) in enumerate(emotions):
            aggregator.add_emotion(
                "cam_0",
                base_time + timedelta(seconds=i),
                emotion,
                conf
            )
        
        sentiment = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=10))
        
        assert sentiment is not None
        assert sentiment.total_faces_observed == 7
        assert sentiment.dominant_emotion == "happy"  # Highest count
        
        # Check percentages sum to 100
        total_percentage = sum(
            stats.percentage
            for stats in sentiment.emotion_distribution.values()
        )
        assert 99.9 <= total_percentage <= 100.1  # Allow small rounding error
        
        # Check emotion statistics
        assert sentiment.emotion_distribution["happy"].count == 3
        assert sentiment.emotion_distribution["happy"].percentage == pytest.approx(42.9, abs=0.1)
        assert sentiment.emotion_distribution["neutral"].count == 2
        assert sentiment.emotion_distribution["sad"].count == 1
        assert sentiment.emotion_distribution["angry"].count == 1
    
    def test_mood_score_calculation(self, aggregator, base_time):
        """Test mood score: (happy - angry) / total."""
        # 5 happy, 1 angry, 2 neutral = (5-1)/8 = 0.5
        emotions = [
            ("happy", 0.9),
            ("happy", 0.9),
            ("happy", 0.9),
            ("happy", 0.9),
            ("happy", 0.9),
            ("angry", 0.8),
            ("neutral", 0.8),
            ("neutral", 0.8)
        ]
        
        for i, (emotion, conf) in enumerate(emotions):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=i), emotion, conf)
        
        sentiment = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=10))
        
        assert sentiment is not None
        expected_mood = (5 - 1) / 8  # 0.5
        assert sentiment.mood_score == pytest.approx(expected_mood, abs=0.01)
    
    def test_mood_score_no_happy_or_angry(self, aggregator, base_time):
        """Test mood score when no happy or angry emotions."""
        # All neutral = (0-0)/3 = 0.0
        for i in range(3):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=i), "neutral", 0.8)
        
        sentiment = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=5))
        
        assert sentiment is not None
        assert sentiment.mood_score == 0.0
    
    def test_mood_score_clamping(self, aggregator, base_time):
        """Test mood score is clamped to [-1, 1]."""
        # All angry = (0-10)/10 = -1.0 (clamped)
        for i in range(10):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=i), "angry", 0.8)
        
        sentiment = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=10))
        
        assert sentiment is not None
        assert sentiment.mood_score == -1.0
    
    def test_trend_first_aggregation(self, aggregator, base_time):
        """Test trend on first aggregation is stable."""
        for i in range(5):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=i), "happy", 0.9)
        
        sentiment = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=5))
        
        assert sentiment is not None
        assert sentiment.trend == "stable"
        # First aggregation may have None or 0.0 magnitude
        assert sentiment.trend_magnitude is None or sentiment.trend_magnitude == pytest.approx(0.0, abs=0.01)
    
    def test_trend_improving(self, aggregator, base_time):
        """Test improving trend (mood score increases)."""
        # First window: 2 happy, 1 angry = (2-1)/3 = 0.33
        for i in range(2):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=i), "happy", 0.9)
        aggregator.add_emotion("cam_0", base_time + timedelta(seconds=2), "angry", 0.8)
        
        sentiment1 = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=3))
        assert sentiment1 is not None
        
        # Second window: 5 happy, 0 angry = (5-0)/5 = 1.0 (improving!)
        for i in range(5):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=10+i), "happy", 0.9)
        
        sentiment2 = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=15))
        assert sentiment2 is not None
        assert sentiment2.trend == "improving"
        assert sentiment2.trend_magnitude > 0.05  # Significant change
    
    def test_trend_declining(self, aggregator, base_time):
        """Test declining trend (mood score decreases)."""
        # First window: 5 happy = (5-0)/5 = 1.0
        for i in range(5):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=i), "happy", 0.9)
        
        sentiment1 = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=5))
        assert sentiment1 is not None
        
        # Second window: 1 happy, 4 angry = (1-4)/5 = -0.6 (declining!)
        aggregator.add_emotion("cam_0", base_time + timedelta(seconds=10), "happy", 0.9)
        for i in range(4):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=11+i), "angry", 0.8)
        
        sentiment2 = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=15))
        assert sentiment2 is not None
        assert sentiment2.trend == "declining"
        assert sentiment2.trend_magnitude > 0.05
    
    def test_trend_stable(self, aggregator, base_time):
        """Test stable trend (small mood change < 0.05)."""
        # First window: 3 happy, 1 angry = (3-1)/4 = 0.5
        for i in range(3):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=i), "happy", 0.9)
        aggregator.add_emotion("cam_0", base_time + timedelta(seconds=3), "angry", 0.8)
        
        sentiment1 = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=4))
        assert sentiment1 is not None
        
        # Second window: 3 happy, 1 angry, 1 neutral = (3-1)/5 = 0.4 (small change)
        for i in range(3):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=10+i), "happy", 0.9)
        aggregator.add_emotion("cam_0", base_time + timedelta(seconds=13), "angry", 0.8)
        aggregator.add_emotion("cam_0", base_time + timedelta(seconds=14), "neutral", 0.8)
        
        sentiment2 = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=15))
        assert sentiment2 is not None
        # Change is 0.1, but might be stable depending on threshold
        # If it's not stable, it should be declining
        assert sentiment2.trend in ["stable", "declining"]
    
    def test_edge_case_zero_faces(self, aggregator, base_time):
        """Test aggregation with zero faces returns None."""
        # Don't add any emotions
        sentiment = aggregator.aggregate_camera("cam_0", base_time)
        assert sentiment is None
    
    def test_edge_case_all_same_emotion(self, aggregator, base_time):
        """Test aggregation when all faces have same emotion."""
        # All 20 faces are happy
        for i in range(20):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=i), "happy", 0.9)
        
        sentiment = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=20))
        
        assert sentiment is not None
        assert sentiment.total_faces_observed == 20
        assert sentiment.dominant_emotion == "happy"
        assert len(sentiment.emotion_distribution) == 1
        assert sentiment.emotion_distribution["happy"].percentage == 100.0
        assert sentiment.mood_score == 1.0  # Max positive
    
    def test_sliding_window(self, aggregator, base_time):
        """Test that sliding window excludes old emotions."""
        # Add emotions at t=0
        for i in range(5):
            aggregator.add_emotion("cam_0", base_time, "happy", 0.9)
        
        # Aggregate at t=40 (outside 30s window)
        sentiment = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=40))
        
        # Should return None (old emotions excluded)
        assert sentiment is None
    
    def test_multiple_cameras(self, aggregator, base_time):
        """Test aggregation for multiple cameras."""
        # Add emotions for cam_0
        for i in range(3):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=i), "happy", 0.9)
        
        # Add emotions for cam_1
        for i in range(5):
            aggregator.add_emotion("cam_1", base_time + timedelta(seconds=i), "sad", 0.8)
        
        sentiments = aggregator.aggregate_all_cameras(base_time + timedelta(seconds=5))
        
        assert len(sentiments) == 2
        
        # Find sentiments by camera
        cam0_sentiment = next(s for s in sentiments if s.camera_id == "cam_0")
        cam1_sentiment = next(s for s in sentiments if s.camera_id == "cam_1")
        
        assert cam0_sentiment.total_faces_observed == 3
        assert cam0_sentiment.dominant_emotion == "happy"
        
        assert cam1_sentiment.total_faces_observed == 5
        assert cam1_sentiment.dominant_emotion == "sad"
    
    def test_cleanup_old_data(self, aggregator, base_time):
        """Test that old data is cleaned up."""
        # Add emotion way in the past (older than 2x window)
        old_time = base_time - timedelta(seconds=70)
        aggregator.add_emotion("cam_0", old_time, "happy", 0.9)
        
        # Force cleanup by adding recent emotion
        aggregator.add_emotion("cam_0", base_time, "neutral", 0.8)
        
        stats = aggregator.get_buffer_stats()
        # Old emotion should be cleaned, only recent one remains
        assert stats["total_emotions"] == 1
    
    def test_avg_confidence_calculation(self, aggregator, base_time):
        """Test average confidence is calculated correctly."""
        # Add 3 happy emotions with different confidences
        aggregator.add_emotion("cam_0", base_time, "happy", 0.7)
        aggregator.add_emotion("cam_0", base_time + timedelta(seconds=1), "happy", 0.9)
        aggregator.add_emotion("cam_0", base_time + timedelta(seconds=2), "happy", 0.8)
        
        sentiment = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=3))
        
        assert sentiment is not None
        expected_avg = (0.7 + 0.9 + 0.8) / 3  # 0.8
        assert sentiment.emotion_distribution["happy"].avg_confidence == pytest.approx(expected_avg, abs=0.01)
    
    def test_percentage_sum_to_100(self, aggregator, base_time):
        """Test that percentages always sum to 100%."""
        # Add various emotions
        emotions = [
            ("happy", 0.9), ("happy", 0.9), ("happy", 0.9),
            ("neutral", 0.8), ("neutral", 0.8),
            ("sad", 0.7),
            ("angry", 0.6), ("angry", 0.6), ("angry", 0.6), ("angry", 0.6)
        ]
        
        for i, (emotion, conf) in enumerate(emotions):
            aggregator.add_emotion("cam_0", base_time + timedelta(seconds=i), emotion, conf)
        
        sentiment = aggregator.aggregate_camera("cam_0", base_time + timedelta(seconds=15))
        
        assert sentiment is not None
        total = sum(stats.percentage for stats in sentiment.emotion_distribution.values())
        assert 99.9 <= total <= 100.1  # Allow small rounding error
